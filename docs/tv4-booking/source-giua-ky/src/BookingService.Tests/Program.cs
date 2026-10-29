using System.Net;
using System.Text;
using System.Text.Json;
using BookingService.Domain;

namespace BookingService.Tests;

/// <summary>
/// Bộ kiểm thử tự viết, không cần thư viện ngoài (xUnit/NUnit).
///   - Phần U: kiểm thử đơn vị cho quy tắc ghế và bộ đọc request (không cần CSDL).
///   - Phần A: kiểm thử tích hợp, gọi API thật đang chạy (cần MySQL + dotnet run).
/// Chạy: dotnet run --project src/BookingService.Tests [-- http://localhost:5004]
/// </summary>
public static class Program
{
    private static int _passed, _failed, _skipped;

    public static async Task<int> Main(string[] args)
    {
        Console.OutputEncoding = Encoding.UTF8;
        var baseUrl = (args.Length > 0 ? args[0] : Environment.GetEnvironmentVariable("BOOKING_API") ?? "http://localhost:5004").TrimEnd('/');

        Console.WriteLine("=== Kiểm thử Booking Service ===");
        Console.WriteLine("--- U. Kiểm thử đơn vị ---");
        RunUnitTests();

        Console.WriteLine($"--- A. Kiểm thử API thật tại {baseUrl} ---");
        await RunApiTestsAsync(baseUrl);

        Console.WriteLine();
        Console.WriteLine($"Kết quả: {_passed} PASS, {_failed} FAIL, {_skipped} SKIP");
        return _failed == 0 ? 0 : 1;
    }

    // ------------------------------------------------------------------ U
    private static void RunUnitTests()
    {
        Check("U01", "Chuẩn hóa ghế ' a1 ' -> 'A1'", () => Equal("A1", SeatRules.Normalize(" a1 ")));
        Check("U02", "Ghế hợp lệ A1, C12, Z99", () =>
            True(SeatRules.IsValid("A1") && SeatRules.IsValid("C12") && SeatRules.IsValid("Z99")));
        Check("U03", "Ghế sai A0, A100, AA1, 1A, rỗng", () =>
            True(!SeatRules.IsValid("A0") && !SeatRules.IsValid("A100") && !SeatRules.IsValid("AA1")
                 && !SeatRules.IsValid("1A") && !SeatRules.IsValid("")));
        Check("U04", "Tách chuỗi CSDL 'A1, a2,,' -> [A1,A2]", () =>
            Equal("A1|A2", string.Join("|", SeatRules.Split("A1, a2,,"))));
        Check("U05", "Ghế A1 không bị nhầm với A10 khi kiểm tra trùng", () =>
            Equal("A10", string.Join("|", SeatRules.FindConflicts(new[] { "A1", "A10" }, new[] { "A10,B2", "C3" }))));
        Check("U06", "Không trùng ghế khi suất chiếu còn trống", () =>
            Equal(0, SeatRules.FindConflicts(new[] { "A1" }, Array.Empty<string>()).Count));

        Check("U07", "Đọc request hợp lệ, chuẩn hóa ghế", () =>
        {
            var r = Parse("""{"movieId":1,"showtimeId":1,"seats":["a1"," A2 "],"pricePerSeat":90000,"username":"user1"}""");
            True(r.IsValid);
            Equal("A1|A2", string.Join("|", r.Request!.Seats));
            Equal(90000, r.Request.PricePerSeat);
        });
        Check("U08", "Thiếu trường -> báo đủ 5 lỗi", () =>
        {
            var r = Parse("{}");
            True(!r.IsValid);
            Equal(5, r.Errors.Count);
            True(r.Errors.Contains("Thiếu trường movieId") && r.Errors.Contains("Thiếu trường seats"));
        });
        Check("U09", "Ghế lặp ['A1','a1'] bị từ chối", () =>
            True(Parse("""{"movieId":1,"showtimeId":1,"seats":["A1","a1"],"pricePerSeat":1,"username":"u"}""")
                .Errors.Any(e => e.Contains("bị lặp"))));
        Check("U10", "Quá 10 ghế bị từ chối", () =>
        {
            var seats = string.Join(",", Enumerable.Range(1, 11).Select(i => $"\"A{i}\""));
            True(Parse($$"""{"movieId":1,"showtimeId":1,"seats":[{{seats}}],"pricePerSeat":1,"username":"u"}""")
                .Errors.Any(e => e.Contains("tối đa")));
        });
        Check("U11", "pricePerSeat = 0, movieId = \"1\", showtimeId = 1.5 bị từ chối", () =>
        {
            var r = Parse("""{"movieId":"1","showtimeId":1.5,"seats":["A1"],"pricePerSeat":0,"username":"u"}""");
            True(r.Errors.Contains("movieId phải là số nguyên"));
            True(r.Errors.Contains("showtimeId phải là số nguyên"));
            True(r.Errors.Contains("pricePerSeat phải lớn hơn 0"));
        });
        Check("U12", "Body không phải object bị từ chối", () => True(!Parse("[1,2]").IsValid));
    }

    private static ParseResult Parse(string json)
    {
        using var doc = JsonDocument.Parse(json);
        return BookingRequestParser.Parse(doc.RootElement);
    }

    // ------------------------------------------------------------------ A
    private static async Task RunApiTestsAsync(string baseUrl)
    {
        using var http = new HttpClient { BaseAddress = new Uri(baseUrl), Timeout = TimeSpan.FromSeconds(15) };

        try
        {
            using var ping = await http.GetAsync("/api/booking");
        }
        catch (Exception ex)
        {
            Skip("A00", $"Không gọi được API ({ex.Message}). Hãy chạy 'dotnet run' trước.");
            return;
        }

        await CheckAsync("A01", "OPTIONS /api/booking -> 204 + CORS", async () =>
        {
            using var res = await http.SendAsync(new HttpRequestMessage(HttpMethod.Options, "/api/booking"));
            Equal(204, (int)res.StatusCode);
            Equal("*", res.Headers.GetValues("Access-Control-Allow-Origin").First());
        });

        JsonElement list = default;
        await CheckAsync("A02", "GET /api/booking -> 200, có đơn mẫu 1-3", async () =>
        {
            var (status, body) = await SendAsync(http, HttpMethod.Get, "/api/booking");
            Equal(200, status);
            Equal("success", body.GetProperty("status").GetString());
            list = body.GetProperty("data").Clone();
            var ids = list.EnumerateArray().Select(b => b.GetProperty("id").GetInt32()).ToHashSet();
            True(ids.Contains(1) && ids.Contains(2) && ids.Contains(3));
        });

        await CheckAsync("A03", "GET /api/booking/1 -> 200, đúng dữ liệu mẫu", async () =>
        {
            var (status, body) = await SendAsync(http, HttpMethod.Get, "/api/booking/1");
            Equal(200, status);
            var d = body.GetProperty("data");
            Equal("user1", d.GetProperty("username").GetString());
            Equal("A1|A2", string.Join("|", d.GetProperty("seats").EnumerateArray().Select(s => s.GetString())));
            Equal(180000, d.GetProperty("totalPrice").GetInt32());
            Equal("PAID", d.GetProperty("status").GetString());
        });

        await CheckAsync("A04", "GET /api/booking/999999 -> 404", async () =>
            Equal(404, (await SendAsync(http, HttpMethod.Get, "/api/booking/999999")).Status));
        await CheckAsync("A05", "GET /api/booking/abc -> 400", async () =>
            Equal(400, (await SendAsync(http, HttpMethod.Get, "/api/booking/abc")).Status));

        // Chọn ghế còn trống ở hàng Z của suất 6 để chạy lặp lại nhiều lần vẫn đúng
        const int testShowtime = 6;
        var taken = list.ValueKind == JsonValueKind.Array
            ? list.EnumerateArray()
                .Where(b => b.GetProperty("showtimeId").GetInt32() == testShowtime && b.GetProperty("status").GetString() != "CANCELLED")
                .SelectMany(b => b.GetProperty("seats").EnumerateArray().Select(s => s.GetString()!))
                .ToHashSet()
            : new HashSet<string>();
        var free = Enumerable.Range(1, 99).Select(i => $"Z{i}").Where(s => !taken.Contains(s)).Take(3).ToArray();
        if (free.Length < 3)
        {
            Skip("A06", "Hàng Z của suất 6 đã hết ghế để test, hãy chạy lại db/seed.sql trên CSDL mới");
            return;
        }

        var newId = 0;
        await CheckAsync("A06", $"POST đặt {free[0]},{free[1]} -> 201, PENDING, tổng tiền = 2 x 75000", async () =>
        {
            var (status, body) = await SendAsync(http, HttpMethod.Post, "/api/booking",
                $$"""{"movieId":5,"showtimeId":{{testShowtime}},"seats":["{{free[0]}}","{{free[1]}}"],"pricePerSeat":75000,"username":"tester"}""");
            Equal(201, status);
            var d = body.GetProperty("data");
            newId = d.GetProperty("id").GetInt32();
            Equal(150000, d.GetProperty("totalPrice").GetInt32());
            Equal("PENDING", d.GetProperty("status").GetString());
        });

        await CheckAsync("A07", "GET đơn vừa tạo -> 200, dữ liệu đã lưu trong CSDL", async () =>
        {
            var (status, body) = await SendAsync(http, HttpMethod.Get, $"/api/booking/{newId}");
            Equal(200, status);
            Equal("tester", body.GetProperty("data").GetProperty("username").GetString());
        });

        await CheckAsync("A08", $"POST trùng ghế {free[1]} -> 400", async () =>
        {
            var (status, body) = await SendAsync(http, HttpMethod.Post, "/api/booking",
                $$"""{"movieId":5,"showtimeId":{{testShowtime}},"seats":["{{free[1]}}"],"pricePerSeat":75000,"username":"user2"}""");
            Equal(400, status);
            True(body.GetProperty("message").GetString()!.Contains(free[1]));
        });

        await CheckAsync("A09", "Ghế B5 của đơn #2 đã CANCELLED (suất 3) được đặt lại -> 201", async () =>
        {
            var b5Active = list.EnumerateArray().Any(b =>
                b.GetProperty("showtimeId").GetInt32() == 3 && b.GetProperty("status").GetString() != "CANCELLED"
                && b.GetProperty("seats").EnumerateArray().Any(s => s.GetString() == "B5"));
            if (b5Active)
                throw new SkipException("B5 đã được đặt lại ở lần chạy trước (chạy lại db/seed.sql trên CSDL mới để test lại)");
            var (status, _) = await SendAsync(http, HttpMethod.Post, "/api/booking",
                """{"movieId":2,"showtimeId":3,"seats":["B5"],"pricePerSeat":85000,"username":"tester"}""");
            Equal(201, status);
        });

        await CheckAsync("A10", "POST JSON sai cú pháp -> 400", async () =>
            Equal(400, (await SendAsync(http, HttpMethod.Post, "/api/booking", "{\"movieId\":1,")).Status));
        await CheckAsync("A11", "POST body rỗng -> 400", async () =>
            Equal(400, (await SendAsync(http, HttpMethod.Post, "/api/booking", "")).Status));
        await CheckAsync("A12", "POST thiếu trường -> 400 kèm thông báo", async () =>
        {
            var (status, body) = await SendAsync(http, HttpMethod.Post, "/api/booking", """{"movieId":1}""");
            Equal(400, status);
            True(body.GetProperty("message").GetString()!.Contains("Thiếu trường seats"));
        });
        await CheckAsync("A13", "PUT /api/booking -> 405 + header Allow", async () =>
        {
            using var res = await http.PutAsync("/api/booking", new StringContent("{}", Encoding.UTF8, "application/json"));
            Equal(405, (int)res.StatusCode);
            True(res.Content.Headers.Allow.Contains("POST") || res.Headers.Contains("Allow"));
        });
        await CheckAsync("A14", "DELETE /api/booking/1 -> 405", async () =>
            Equal(405, (await SendAsync(http, HttpMethod.Delete, "/api/booking/1")).Status));
        await CheckAsync("A15", "GET /api/khong-ton-tai -> 404", async () =>
            Equal(404, (await SendAsync(http, HttpMethod.Get, "/api/khong-ton-tai")).Status));
        await CheckAsync("A16", "POST body 20 KiB -> 413", async () =>
            Equal(413, (await SendAsync(http, HttpMethod.Post, "/api/booking", "{\"x\":\"" + new string('a', 20 * 1024) + "\"}")).Status));

        await CheckAsync("A17", $"8 request đặt cùng ghế {free[2]} cùng lúc -> đúng 1 thành công", async () =>
        {
            var body = $$"""{"movieId":5,"showtimeId":{{testShowtime}},"seats":["{{free[2]}}"],"pricePerSeat":75000,"username":"tester"}""";
            var tasks = Enumerable.Range(0, 8).Select(_ => SendAsync(http, HttpMethod.Post, "/api/booking", body));
            var results = await Task.WhenAll(tasks);
            Equal(1, results.Count(r => r.Status == 201));
            Equal(7, results.Count(r => r.Status == 400));
        });
    }

    private static async Task<(int Status, JsonElement Body)> SendAsync(HttpClient http, HttpMethod method, string path, string? body = null)
    {
        using var req = new HttpRequestMessage(method, path);
        if (body is not null) req.Content = new StringContent(body, Encoding.UTF8, "application/json");
        using var res = await http.SendAsync(req);
        var text = await res.Content.ReadAsStringAsync();
        var json = text.Length == 0 ? default : JsonDocument.Parse(text).RootElement.Clone();
        return ((int)res.StatusCode, json);
    }

    // ------------------------------------------------------------------ mini framework
    private static void Check(string id, string name, Action test)
    {
        try { test(); Pass(id, name); }
        catch (Exception ex) { Fail(id, name, ex.Message); }
    }

    private static async Task CheckAsync(string id, string name, Func<Task> test)
    {
        try { await test(); Pass(id, name); }
        catch (SkipException ex) { Skip(id, $"{name}: {ex.Message}"); }
        catch (Exception ex) { Fail(id, name, ex.Message); }
    }

    private sealed class SkipException(string message) : Exception(message);

    private static void Pass(string id, string name) { _passed++; Console.WriteLine($"[PASS] {id} {name}"); }
    private static void Fail(string id, string name, string why) { _failed++; Console.WriteLine($"[FAIL] {id} {name} -> {why}"); }
    private static void Skip(string id, string why) { _skipped++; Console.WriteLine($"[SKIP] {id} {why}"); }

    private static void True(bool condition) { if (!condition) throw new Exception("điều kiện sai"); }
    private static void Equal<T>(T expected, T actual)
    {
        if (!EqualityComparer<T>.Default.Equals(expected, actual))
            throw new Exception($"mong đợi '{expected}', nhận '{actual}'");
    }
}
