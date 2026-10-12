using System.Diagnostics;
using System.Globalization;
using System.Net;
using System.Text.RegularExpressions;
using BookingService.Config;
using BookingService.Data;
using BookingService.Domain;
using BookingService.Services;

namespace BookingService.Http;

/// <summary>
/// Máy chủ HTTP viết bằng HttpListener (không dùng ASP.NET Core).
/// Tự định tuyến 3 endpoint:
///   GET  /api/booking        danh sách đơn
///   POST /api/booking        tạo đơn PENDING
///   GET  /api/booking/{id}   chi tiết một đơn
/// </summary>
public sealed partial class ApiServer(AppConfig config, BookingManager bookings)
{
    [GeneratedRegex(@"^/api/booking/?$")]
    private static partial Regex CollectionRoute();

    [GeneratedRegex(@"^/api/booking/([^/]+)/?$")]
    private static partial Regex ItemRoute();

    private readonly HttpListener _listener = new();

    /// <summary>Mở cổng. Ném HttpListenerException nếu cổng bận hoặc thiếu quyền.</summary>
    public void Start()
    {
        foreach (var prefix in config.ListenPrefixes)
            _listener.Prefixes.Add(prefix);
        _listener.Start();
    }

    /// <summary>Vòng lặp nhận request cho tới khi nhấn Ctrl+C.</summary>
    public async Task RunAsync(CancellationToken ct)
    {
        using var stopRegistration = ct.Register(() => _listener.Stop());

        while (!ct.IsCancellationRequested)
        {
            HttpListenerContext ctx;
            try
            {
                ctx = await _listener.GetContextAsync();
            }
            catch (Exception) when (ct.IsCancellationRequested)
            {
                break; // Ctrl+C: listener đã dừng
            }

            // Mỗi request xử lý trên một task riêng để các request không chờ nhau.
            _ = Task.Run(() => HandleAsync(ctx, ct), CancellationToken.None);
        }
        _listener.Close();
    }

    private async Task HandleAsync(HttpListenerContext ctx, CancellationToken ct)
    {
        var sw = Stopwatch.StartNew();
        var req = ctx.Request;
        var res = ctx.Response;
        var status = 500;
        try
        {
            HttpHelpers.AddCorsHeaders(res);
            status = await RouteAsync(req, res, ct);
        }
        catch (BadRequestBodyException ex)
        {
            status = await HttpHelpers.WriteErrorAsync(res, ex.StatusCode, ex.Message);
        }
        catch (ResourceBusyException ex)
        {
            status = await HttpHelpers.WriteErrorAsync(res, 503, ex.Message);
        }
        catch (Exception ex)
        {
            // Chi tiết lỗi chỉ in ở console, không trả ra ngoài.
            Log($"LỖI {req.HttpMethod} {req.Url?.AbsolutePath}: {ex.GetType().Name}: {ex.Message}");
            try
            {
                status = await HttpHelpers.WriteErrorAsync(res, 500, "Lỗi máy chủ, vui lòng thử lại sau");
            }
            catch
            {
                // Không ghi được phản hồi (client đã ngắt kết nối)
            }
        }
        finally
        {
            try { res.Close(); } catch { /* client đã ngắt */ }
            Log($"{req.HttpMethod,-7} {req.Url?.PathAndQuery} -> {status} ({sw.ElapsedMilliseconds} ms)");
        }
    }

    private async Task<int> RouteAsync(HttpListenerRequest req, HttpListenerResponse res, CancellationToken ct)
    {
        var path = req.Url?.AbsolutePath ?? "/";
        var method = req.HttpMethod.ToUpperInvariant();

        // /api/booking
        if (CollectionRoute().IsMatch(path))
        {
            return method switch
            {
                "OPTIONS" => HttpHelpers.WriteNoContent(res),
                "GET" => await ListAsync(res, ct),
                "POST" => await CreateAsync(req, res, ct),
                _ => await MethodNotAllowedAsync(res, "GET, POST, OPTIONS"),
            };
        }

        // /api/booking/{id}
        var item = ItemRoute().Match(path);
        if (item.Success)
        {
            return method switch
            {
                "OPTIONS" => HttpHelpers.WriteNoContent(res),
                "GET" => await GetByIdAsync(item.Groups[1].Value, res, ct),
                _ => await MethodNotAllowedAsync(res, "GET, OPTIONS"),
            };
        }

        return await HttpHelpers.WriteErrorAsync(res, 404, $"Không tìm thấy đường dẫn {path}");
    }

    private static Task<int> MethodNotAllowedAsync(HttpListenerResponse res, string allow)
    {
        res.Headers["Allow"] = allow;
        return HttpHelpers.WriteErrorAsync(res, 405, $"Phương thức không được hỗ trợ. Chỉ chấp nhận: {allow}");
    }

    // GET /api/booking
    private async Task<int> ListAsync(HttpListenerResponse res, CancellationToken ct)
    {
        var list = await bookings.ListAsync(ct);
        return await HttpHelpers.WriteSuccessAsync(res, 200, list.Select(BookingJson.From).ToArray());
    }

    // GET /api/booking/{id}
    private async Task<int> GetByIdAsync(string idText, HttpListenerResponse res, CancellationToken ct)
    {
        if (!int.TryParse(idText, NumberStyles.None, CultureInfo.InvariantCulture, out var id) || id <= 0)
            return await HttpHelpers.WriteErrorAsync(res, 400, "Mã đơn phải là số nguyên dương");

        var booking = await bookings.GetAsync(id, ct);
        return booking is null
            ? await HttpHelpers.WriteErrorAsync(res, 404, $"Không tìm thấy đơn #{id}")
            : await HttpHelpers.WriteSuccessAsync(res, 200, BookingJson.From(booking));
    }

    // POST /api/booking
    private async Task<int> CreateAsync(HttpListenerRequest req, HttpListenerResponse res, CancellationToken ct)
    {
        // 1.0 Tiếp nhận và kiểm tra yêu cầu
        using var doc = await HttpHelpers.ReadJsonBodyAsync(req, AppConfig.MaxBodyBytes, ct);
        var parsed = BookingRequestParser.Parse(doc.RootElement);
        if (!parsed.IsValid)
            return await HttpHelpers.WriteErrorAsync(res, 400, "Dữ liệu không hợp lệ: " + string.Join("; ", parsed.Errors));

        // 2.0 Tạo đơn PENDING
        var result = await bookings.CreateAsync(parsed.Request!, ct);
        if (!result.Success)
            return await HttpHelpers.WriteErrorAsync(res, 400,
                $"Ghế đã có người đặt trong suất chiếu #{parsed.Request!.ShowtimeId}: {string.Join(", ", result.TakenSeats)}");

        res.Headers["Location"] = $"/api/booking/{result.Booking!.Id}";
        return await HttpHelpers.WriteSuccessAsync(res, 201, BookingJson.From(result.Booking));
    }

    public static void Log(string message) =>
        Console.WriteLine($"[{DateTime.Now:yyyy-MM-dd HH:mm:ss}] {message}");
}
