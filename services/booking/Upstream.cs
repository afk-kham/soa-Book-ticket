using System.Text;
using System.Text.Json;

namespace BookingService;

/// <summary>Kết quả gọi một service khác (đã giải mã envelope {"status","data"|"message"}).</summary>
public record Reply(int Status, JsonElement? Data, string? Message)
{
    public bool IsSuccess => Status is >= 200 and < 300;
}

/// <summary>
/// Gọi service khác bằng HTTP + JSON. Đây là CÁCH DUY NHẤT Booking lấy dữ liệu của User/Movie/Showtime/Payment/Notification
/// (SOA: Booking không đọc movie_db, showtime_db, user_db, payment_db, notification_db).
/// </summary>
public static class Upstream
{
    static readonly HttpClient Http = new() { Timeout = Timeout.InfiniteTimeSpan };   // timeout đặt theo từng request

    public static async Task<Reply> SendAsync(HttpMethod method, string url, object? body, string serviceName,
        string unavailableCode, int? timeoutSeconds = null)
    {
        using var cts = new CancellationTokenSource(TimeSpan.FromSeconds(timeoutSeconds ?? Config.UpstreamTimeoutSeconds));
        using var req = new HttpRequestMessage(method, url);
        if (body is not null)
            req.Content = new StringContent(JsonSerializer.Serialize(body, Json.Options), Encoding.UTF8, "application/json");
        try
        {
            using var res = await Http.SendAsync(req, cts.Token);
            var text = await res.Content.ReadAsStringAsync(cts.Token);
            JsonElement? data = null; string? message = null;
            try
            {
                using var doc = JsonDocument.Parse(text);
                if (doc.RootElement.ValueKind == JsonValueKind.Object)
                {
                    if (doc.RootElement.TryGetProperty("data", out var d)) data = d.Clone();
                    if (doc.RootElement.TryGetProperty("message", out var m) && m.ValueKind == JsonValueKind.String) message = m.GetString();
                }
            }
            catch (JsonException) { /* không phải JSON: bỏ qua, chỉ dùng mã HTTP */ }
            return new Reply((int)res.StatusCode, data, message);
        }
        catch (Exception e) when (e is HttpRequestException or TaskCanceledException or OperationCanceledException)
        {
            Console.Error.WriteLine($"[booking] {serviceName} không phản hồi ({url}): {e.Message}");
            throw new ApiException(503, unavailableCode, $"{serviceName} đang không khả dụng, vui lòng thử lại sau");
        }
    }
}
