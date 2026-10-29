using System.Globalization;
using System.Net;
using System.Text;
using System.Text.Json;
using System.Text.RegularExpressions;

namespace BookingService;

/// <summary>
/// Booking Service (TV4 – C# HttpListener + ADO.NET) — cổng 5004, CSDL booking_db.
/// Là ORCHESTRATOR: kiểm tra User/Movie/Showtime -> lưu đơn PENDING -> gọi Payment -> cập nhật PAID/CANCELLED -> gọi Notification.
///
///   POST /api/booking              đặt vé (điều phối toàn bộ luồng). "payNow": false -> chỉ giữ ghế (PENDING, hạn expiresAt)
///   POST /api/booking/{id}/pay     thanh toán đơn đang giữ ghế {username, paymentMethod}
///   POST /api/booking/{id}/cancel  hủy đơn đang giữ ghế {username} (nhả ghế)
///   GET  /api/booking[?username=&status=&showtimeId=]   danh sách đơn
///   GET  /api/booking/{id}         chi tiết đơn
///   GET  /api/booking/seats?showtimeId=1   các ghế đã bị giữ của một suất (cho Client vẽ sơ đồ ghế)
///   GET  /api/booking/availability?showtimeIds=1,2,3   số ghế đã bị giữ của nhiều suất (Client hiện "còn N ghế")
///   GET  /health
/// </summary>
public static class Program
{
    static readonly IBookingStore Store = Config.Store == "memory" ? new MemoryBookingStore() : new MySqlBookingStore();
    static readonly SemaphoreSlim SeatLock = new(1, 1);          // tránh 2 request cùng giành một ghế trong cùng tiến trình
    static readonly Regex SeatRe = new("^[A-Z][0-9]{1,2}$", RegexOptions.Compiled);
    static readonly Regex IdRe = new("^/api/booking/(\\d+)$", RegexOptions.Compiled);
    static readonly Regex ActionRe = new("^/api/booking/(\\d+)/(pay|cancel)$", RegexOptions.Compiled);

    public static async Task Main()
    {
        var listener = new HttpListener();
        listener.Prefixes.Add(Config.Prefix);
        listener.Start();
        Console.WriteLine($"Booking Service dang chay tai {Config.Prefix} (store={Config.Store}, giu ghe {Config.HoldMinutes} phut)");
        _ = Task.Run(SweepLoop);
        while (true)
        {
            var ctx = await listener.GetContextAsync();
            _ = Task.Run(() => HandleAsync(ctx));
        }
    }

    /// <summary>Định kỳ hủy các đơn PENDING quá hạn giữ ghế (ngoài ra các yêu cầu đọc/đặt cũng tự quét trước).</summary>
    static async Task SweepLoop()
    {
        while (true)
        {
            await Task.Delay(TimeSpan.FromSeconds(30));
            try { await ExpireHolds(); }
            catch (Exception e) { Console.Error.WriteLine($"[booking] quét đơn quá hạn lỗi: {e.Message}"); }
        }
    }

    static async Task ExpireHolds()
    {
        var n = await Store.ExpirePendingAsync(Config.HoldMinutes);
        if (n > 0) Console.WriteLine($"[booking] {n} đơn hết hạn giữ ghế -> CANCELLED");
    }

    // ------------------------------------------------------------------ routing
    static async Task HandleAsync(HttpListenerContext ctx)
    {
        try
        {
            var method = ctx.Request.HttpMethod.ToUpperInvariant();
            var path = ctx.Request.Url!.AbsolutePath.TrimEnd('/');
            if (path.Length == 0) path = "/";

            if (method == "OPTIONS") { Cors(ctx); ctx.Response.StatusCode = 204; ctx.Response.Close(); return; }

            if (path == "/health" && method == "GET")
            {
                await Store.PingAsync();
                await Ok(ctx, new { service = "booking-service", port = Config.Port });
            }
            else if (path == "/api/booking")
            {
                if (method == "POST") await CreateBooking(ctx);
                else if (method == "GET") await ListBookings(ctx);
                else await MethodNotAllowed(ctx, "GET, POST");
            }
            else if (path == "/api/booking/seats")
            {
                if (method != "GET") await MethodNotAllowed(ctx, "GET");
                else await TakenSeats(ctx);
            }
            else if (path == "/api/booking/availability")
            {
                if (method != "GET") await MethodNotAllowed(ctx, "GET");
                else await Availability(ctx);
            }
            else if (ActionRe.Match(path) is { Success: true } a)
            {
                if (method != "POST") await MethodNotAllowed(ctx, "POST");
                else if (a.Groups[2].Value == "pay") await PayBooking(ctx, int.Parse(a.Groups[1].Value));
                else await CancelBooking(ctx, int.Parse(a.Groups[1].Value));
            }
            else if (IdRe.Match(path) is { Success: true } m)
            {
                if (method != "GET") await MethodNotAllowed(ctx, "GET");
                else
                {
                    await ExpireHolds();
                    await Ok(ctx, await Find(int.Parse(m.Groups[1].Value)));
                }
            }
            else throw new ApiException(404, "NOT_FOUND", "Endpoint không tồn tại");
        }
        catch (ApiException e) { await Fail(ctx, e.Status, e.Code, e.Message); }
        catch (Exception e)
        {
            Console.Error.WriteLine($"[booking] lỗi: {e}");           // chi tiết chỉ ghi log, không trả cho client
            await Fail(ctx, 500, "INTERNAL_ERROR", "Lỗi máy chủ nội bộ");
        }
    }

    // ------------------------------------------------------------------ POST /api/booking
    static async Task CreateBooking(HttpListenerContext ctx)
    {
        var body = await ReadJson(ctx);
        // Baseline: username lấy từ body. Cuối kỳ (JWT) sẽ lấy từ claim "sub" của token, không tin body.
        var username = Str(body, "username")?.Trim();
        if (string.IsNullOrEmpty(username) || username.Length > 50) throw Bad("username là bắt buộc (tối đa 50 ký tự)");
        var movieId = PositiveInt(body, "movieId");
        var showtimeId = PositiveInt(body, "showtimeId");
        var seats = ParseSeats(body);
        var method = (Str(body, "paymentMethod") ?? Str(body, "method") ?? "MOMO").Trim().ToUpperInvariant();
        // payNow = false: chỉ giữ ghế; người dùng thanh toán sau qua POST /api/booking/{id}/pay trong HOLD_MINUTES phút
        var payNow = !(body.TryGetProperty("payNow", out var pn) && pn.ValueKind == JsonValueKind.False);

        // 1) Xác thực tham chiếu logic bằng API của các service sở hữu dữ liệu
        var user = await Upstream.SendAsync(HttpMethod.Get, $"{Config.UserUrl}/api/users?username={Uri.EscapeDataString(username)}",
            null, "User Service", "USER_SERVICE_UNAVAILABLE");
        if (!user.IsSuccess) throw new ApiException(502, "USER_SERVICE_ERROR", "User Service trả lỗi khi kiểm tra người dùng");
        if (user.Data is not { ValueKind: JsonValueKind.Array } arr || arr.GetArrayLength() == 0)
            throw new ApiException(404, "USER_NOT_FOUND", $"Không tồn tại người dùng '{username}'");

        var movie = await Upstream.SendAsync(HttpMethod.Get, $"{Config.MovieUrl}/api/movies/{movieId}", null, "Movie Service", "MOVIE_SERVICE_UNAVAILABLE");
        if (movie.Status == 404) throw new ApiException(404, "MOVIE_NOT_FOUND", $"Không tồn tại phim movieId = {movieId}");
        if (!movie.IsSuccess) throw new ApiException(502, "MOVIE_SERVICE_ERROR", "Movie Service trả lỗi khi kiểm tra phim");

        var st = await Upstream.SendAsync(HttpMethod.Get, $"{Config.ShowtimeUrl}/api/showtimes/{showtimeId}", null, "Showtime Service", "SHOWTIME_SERVICE_UNAVAILABLE");
        if (st.Status == 404) throw new ApiException(404, "SHOWTIME_NOT_FOUND", $"Không tồn tại suất chiếu showtimeId = {showtimeId}");
        if (!st.IsSuccess || st.Data is not { ValueKind: JsonValueKind.Object } stData)
            throw new ApiException(502, "SHOWTIME_SERVICE_ERROR", "Showtime Service trả lỗi khi kiểm tra suất chiếu");
        if (stData.GetProperty("movieId").GetInt32() != movieId)
            throw Bad("Suất chiếu không thuộc phim đã chọn (movieId không khớp)");
        if (stData.TryGetProperty("time", out var stTime) && stTime.ValueKind == JsonValueKind.String
            && DateTime.TryParse(stTime.GetString(), CultureInfo.InvariantCulture, DateTimeStyles.None, out var startsAt) && startsAt <= DateTime.Now)
            throw new ApiException(400, "SHOWTIME_CLOSED", "Suất chiếu đã bắt đầu, vui lòng chọn suất khác");
        var total = stData.GetProperty("price").GetInt32() * seats.Count;       // giá lấy từ Showtime, không tin client

        // 2) Kiểm tra ghế trống + lưu đơn PENDING
        Booking pending;
        await SeatLock.WaitAsync();
        try
        {
            await ExpireHolds();                                   // nhả ghế của đơn quá hạn trước khi kiểm tra
            var taken = await Store.TakenSeatsAsync(showtimeId);
            var clash = seats.Where(taken.Contains).ToList();
            if (clash.Count > 0) throw new ApiException(409, "SEAT_TAKEN", $"Ghế đã có người đặt: {string.Join(", ", clash)}");
            pending = await Store.InsertPendingAsync(movieId, showtimeId, username, seats, total);
        }
        finally { SeatLock.Release(); }

        if (!payNow)   // chỉ giữ ghế: trả đơn PENDING kèm expiresAt, chưa gọi Payment
        {
            await Ok(ctx, Result(pending, null, "SKIPPED"), 201);
            return;
        }

        // 3) Thanh toán qua Payment Service (lỗi -> hủy đơn, nhả ghế)
        var (payStatus, txId) = await Pay(pending, method);
        var finalStatus = payStatus == "PAID" ? BookingStatus.Paid : BookingStatus.Cancelled;
        await Store.UpdateStatusAsync(pending.Id, finalStatus);

        // 4) Thông báo (best-effort): Notification lỗi KHÔNG làm hỏng đơn đã PAID
        var notification = finalStatus == BookingStatus.Paid ? await Notify(username, pending.Id) : "SKIPPED";
        await Ok(ctx, Result((await Store.GetAsync(pending.Id))!, new { status = payStatus, method, transactionId = txId }, notification), 201);
    }

    static object Result(Booking b, object? payment, string notification) => new
    {
        b.Id, b.MovieId, b.ShowtimeId, b.Username, b.Seats, b.TotalPrice, b.Status, b.CreatedAt, b.ExpiresAt,
        payment, notification,
    };

    // ------------------------------------------------------------------ POST /api/booking/{id}/pay
    /// <summary>
    /// Thanh toán một đơn đang giữ ghế. Khác luồng đặt-và-trả-ngay: thanh toán thất bại hoặc Payment tạm sập
    /// thì đơn VẪN PENDING để người dùng thử lại / đổi phương thức cho tới khi hết hạn giữ ghế.
    /// </summary>
    static async Task PayBooking(HttpListenerContext ctx, int id)
    {
        var body = await ReadJson(ctx);
        var method = (Str(body, "paymentMethod") ?? Str(body, "method") ?? "").Trim().ToUpperInvariant();
        if (method.Length == 0) throw Bad("paymentMethod là bắt buộc");
        await ExpireHolds();
        var b = await Owned(id, Str(body, "username"));
        if (b.Status == BookingStatus.Paid) throw new ApiException(409, "ALREADY_PAID", $"Đơn #{id} đã được thanh toán");
        if (b.Status == BookingStatus.Cancelled) throw new ApiException(409, "BOOKING_CANCELLED", $"Đơn #{id} đã hết hạn giữ ghế hoặc đã bị hủy");

        var (payStatus, txId) = await Charge(b, method);
        var notification = "SKIPPED";
        if (payStatus == "PAID")
        {
            // Tiền đã nhận: chốt PAID kể cả khi đơn vừa bị quét hết hạn trong lúc chờ Payment (nếu ghế chưa ai lấy)
            if (!await Store.TryUpdateStatusAsync(id, BookingStatus.Pending, BookingStatus.Paid))
            {
                await SeatLock.WaitAsync();
                try
                {
                    if ((await Store.TakenSeatsAsync(b.ShowtimeId)).Overlaps(b.Seats))
                        Console.Error.WriteLine($"[booking] đơn #{id} thanh toán sau khi hết hạn và ghế đã bị lấy — cần hoàn tiền thủ công");
                    else await Store.UpdateStatusAsync(id, BookingStatus.Paid);
                }
                finally { SeatLock.Release(); }
            }
            notification = await Notify(b.Username, id);
        }
        await Ok(ctx, Result((await Store.GetAsync(id))!, new { status = payStatus, method, transactionId = txId }, notification));
    }

    // ------------------------------------------------------------------ POST /api/booking/{id}/cancel
    static async Task CancelBooking(HttpListenerContext ctx, int id)
    {
        var body = await ReadJson(ctx);
        await ExpireHolds();
        var b = await Owned(id, Str(body, "username"));
        if (b.Status == BookingStatus.Paid)
            throw new ApiException(409, "PAID_NOT_CANCELLABLE", "Vé đã thanh toán không thể hủy trực tuyến, vui lòng liên hệ quầy vé");
        if (b.Status == BookingStatus.Pending) await Store.TryUpdateStatusAsync(id, BookingStatus.Pending, BookingStatus.Cancelled);
        await Ok(ctx, Result((await Store.GetAsync(id))!, null, "SKIPPED"));
    }

    static async Task<Booking> Find(int id) =>
        await Store.GetAsync(id) ?? throw new ApiException(404, "NOT_FOUND", $"Không tìm thấy đơn đặt vé có id {id}");

    /// <summary>Baseline: chủ đơn xác định bằng username trong body (cuối kỳ: lấy từ JWT).</summary>
    static async Task<Booking> Owned(int id, string? username)
    {
        if (string.IsNullOrWhiteSpace(username)) throw Bad("username là bắt buộc");
        var b = await Find(id);
        if (!string.Equals(b.Username, username.Trim(), StringComparison.Ordinal))
            throw new ApiException(403, "FORBIDDEN", "Bạn không có quyền thao tác với đơn này");
        return b;
    }

    /// <summary>Gửi thông báo xác nhận (best-effort) -> SENT | FAILED.</summary>
    static async Task<string> Notify(string username, int bookingId)
    {
        string result;
        try
        {
            var n = await Upstream.SendAsync(HttpMethod.Post, $"{Config.NotificationUrl}/api/notify",
                new { username, bookingId, channel = "EMAIL" }, "Notification Service", "NOTIFICATION_SERVICE_UNAVAILABLE", 3);
            result = n.IsSuccess ? "SENT" : "FAILED";
        }
        catch (ApiException) { result = "FAILED"; }
        if (result == "FAILED") Console.Error.WriteLine($"[booking] không gửi được thông báo cho đơn #{bookingId} (đơn vẫn PAID)");
        return result;
    }

    /// <summary>Luồng đặt-và-trả-ngay: Payment lỗi / không với tới được -> hủy đơn (nhả ghế) rồi báo lỗi.</summary>
    static async Task<(string status, string? txId)> Pay(Booking b, string method)
    {
        try { return await Charge(b, method); }
        catch (ApiException e)
        {
            await Store.UpdateStatusAsync(b.Id, BookingStatus.Cancelled);
            throw new ApiException(e.Status, e.Code, $"{e.Message}. Đơn #{b.Id} đã bị hủy, ghế được nhả lại");
        }
    }

    /// <summary>Gọi Payment, trả (PAID|FAILED, mã giao dịch). Không đổi trạng thái đơn; lỗi -> ApiException.</summary>
    static async Task<(string status, string? txId)> Charge(Booking b, string method)
    {
        Reply r;
        try
        {
            r = await Upstream.SendAsync(HttpMethod.Post, $"{Config.PaymentUrl}/api/payment",
                new { bookingId = b.Id, amount = b.TotalPrice, method }, "Payment Service", "PAYMENT_SERVICE_UNAVAILABLE");
        }
        catch (ApiException)
        {
            // Có thể Payment đã ghi giao dịch nhưng phản hồi bị mất: hỏi lại bằng GET /api/payment?bookingId=
            var known = await TryReconcile(b.Id);
            if (known is not null) return known.Value;
            throw;
        }
        if (r.IsSuccess && r.Data is { ValueKind: JsonValueKind.Object } d && d.TryGetProperty("status", out var s))
            return (s.GetString() ?? "FAILED", d.TryGetProperty("id", out var id) ? id.GetString() : null);
        if (r.Status == 409 && await TryReconcile(b.Id) is { status: "PAID" } paid) return paid;   // ALREADY_PAID: đã trả trước đó

        throw new ApiException(502, "PAYMENT_SERVICE_ERROR", $"Payment Service từ chối giao dịch ({r.Message ?? "HTTP " + r.Status})");
    }

    /// <summary>Giao dịch đã ghi nhận của đơn: ưu tiên giao dịch PAID, nếu không có thì lấy giao dịch mới nhất.</summary>
    static async Task<(string status, string? txId)?> TryReconcile(int bookingId)
    {
        try
        {
            var r = await Upstream.SendAsync(HttpMethod.Get, $"{Config.PaymentUrl}/api/payment?bookingId={bookingId}", null, "Payment Service", "PAYMENT_SERVICE_UNAVAILABLE", 2);
            if (r.IsSuccess && r.Data is { ValueKind: JsonValueKind.Array } a && a.GetArrayLength() > 0)
            {
                var txs = a.EnumerateArray().ToList();
                var tx = txs.FirstOrDefault(t => t.TryGetProperty("status", out var st) && st.GetString() == "PAID");
                if (tx.ValueKind != JsonValueKind.Object) tx = txs[0];
                return (tx.GetProperty("status").GetString() ?? "FAILED", tx.TryGetProperty("id", out var id) ? id.GetString() : null);
            }
        }
        catch (ApiException) { }
        return null;
    }

    // ------------------------------------------------------------------ GET
    static async Task ListBookings(HttpListenerContext ctx)
    {
        var q = ctx.Request.QueryString;
        int? showtimeId = null;
        if (q["showtimeId"] is { Length: > 0 } sid)
        {
            if (!int.TryParse(sid, out var v) || v <= 0) throw Bad("showtimeId phải là số nguyên dương");
            showtimeId = v;
        }
        var status = q["status"]?.ToUpperInvariant();
        if (status is not null && status is not (BookingStatus.Pending or BookingStatus.Paid or BookingStatus.Cancelled))
            throw Bad("status chỉ nhận PENDING, PAID hoặc CANCELLED");
        await ExpireHolds();
        await Ok(ctx, await Store.ListAsync(string.IsNullOrWhiteSpace(q["username"]) ? null : q["username"], status, showtimeId));
    }

    static async Task TakenSeats(HttpListenerContext ctx)
    {
        if (!int.TryParse(ctx.Request.QueryString["showtimeId"], out var id) || id <= 0) throw Bad("showtimeId là bắt buộc (số nguyên dương)");
        await ExpireHolds();
        var taken = (await Store.TakenSeatsAsync(id)).OrderBy(s => s, StringComparer.Ordinal).ToList();
        await Ok(ctx, new { showtimeId = id, seats = taken });
    }

    static async Task Availability(HttpListenerContext ctx)
    {
        var ids = new List<int>();
        foreach (var part in (ctx.Request.QueryString["showtimeIds"] ?? "").Split(',', StringSplitOptions.RemoveEmptyEntries | StringSplitOptions.TrimEntries))
        {
            if (!int.TryParse(part, out var v) || v <= 0) throw Bad("showtimeIds là danh sách số nguyên dương, ví dụ 1,2,3");
            ids.Add(v);
        }
        if (ids.Count is 0 or > 500) throw Bad("showtimeIds cần từ 1 đến 500 suất chiếu");
        await ExpireHolds();
        var counts = await Store.TakenCountsAsync(ids);
        await Ok(ctx, counts.Select(kv => new { showtimeId = kv.Key, taken = kv.Value }).ToList());
    }

    // ------------------------------------------------------------------ helpers
    static ApiException Bad(string message) => new(400, "VALIDATION_ERROR", message);

    static async Task<JsonElement> ReadJson(HttpListenerContext ctx)
    {
        using var ms = new MemoryStream();
        await ctx.Request.InputStream.CopyToAsync(ms);
        if (ms.Length == 0) throw Bad("Body yêu cầu rỗng");
        if (ms.Length > 64 * 1024) throw new ApiException(413, "PAYLOAD_TOO_LARGE", "Body quá lớn");
        try
        {
            var root = JsonDocument.Parse(ms.ToArray()).RootElement.Clone();
            if (root.ValueKind != JsonValueKind.Object) throw Bad("Body phải là một đối tượng JSON");
            return root;
        }
        catch (JsonException) { throw Bad("JSON không hợp lệ"); }
    }

    static string? Str(JsonElement o, string key) =>
        o.TryGetProperty(key, out var v) && v.ValueKind == JsonValueKind.String ? v.GetString() : null;

    static int PositiveInt(JsonElement o, string key)
    {
        if (o.TryGetProperty(key, out var v) && v.ValueKind == JsonValueKind.Number && v.TryGetInt32(out var n) && n > 0) return n;
        throw Bad($"{key} là bắt buộc và phải là số nguyên dương");
    }

    static List<string> ParseSeats(JsonElement o)
    {
        if (!o.TryGetProperty("seats", out var v) || v.ValueKind != JsonValueKind.Array) throw Bad("seats là bắt buộc, ví dụ [\"A1\",\"A2\"]");
        var seats = new List<string>();
        foreach (var e in v.EnumerateArray())
        {
            var s = e.ValueKind == JsonValueKind.String ? e.GetString()!.Trim().ToUpperInvariant() : "";
            if (!SeatRe.IsMatch(s)) throw Bad("Mã ghế không hợp lệ (ví dụ A1, B12)");
            seats.Add(s);
        }
        if (seats.Count is 0 or > 10) throw Bad("Mỗi đơn đặt từ 1 đến 10 ghế");
        if (seats.Distinct().Count() != seats.Count) throw Bad("Danh sách ghế bị trùng");
        return seats;
    }

    static void Cors(HttpListenerContext ctx)
    {
        var h = ctx.Response.Headers;
        h["Access-Control-Allow-Origin"] = "*";
        h["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS";
        h["Access-Control-Allow-Headers"] = "Content-Type, Authorization";
        h["Access-Control-Max-Age"] = "3600";
    }

    static async Task Send(HttpListenerContext ctx, int status, object payload)
    {
        var bytes = Encoding.UTF8.GetBytes(JsonSerializer.Serialize(payload, Json.Options));
        Cors(ctx);
        ctx.Response.StatusCode = status;
        ctx.Response.ContentType = "application/json; charset=utf-8";
        ctx.Response.ContentLength64 = bytes.Length;
        await ctx.Response.OutputStream.WriteAsync(bytes);
        ctx.Response.Close();
    }

    static Task Ok(HttpListenerContext ctx, object data, int status = 200) =>
        Send(ctx, status, new Dictionary<string, object?> { ["status"] = "success", ["data"] = data });

    static Task Fail(HttpListenerContext ctx, int status, string code, string message) =>
        Send(ctx, status, new Dictionary<string, object?> { ["status"] = "error", ["code"] = code, ["message"] = message });

    static async Task MethodNotAllowed(HttpListenerContext ctx, string allow)
    {
        ctx.Response.Headers["Allow"] = allow + ", OPTIONS";
        await Fail(ctx, 405, "METHOD_NOT_ALLOWED", "Phương thức không được hỗ trợ trên endpoint này");
    }
}
