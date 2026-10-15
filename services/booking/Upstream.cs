using System.Net;
using System.Net.Sockets;
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
    // timeout đặt theo từng request. Kết nối thử IPv4 trước: "localhost" trên Windows phân giải ra ::1 trước,
    // mà Movie/Showtime/Payment chỉ nghe 0.0.0.0 (IPv4) nên mỗi lời gọi phải chờ ~1 giây mới chuyển sang 127.0.0.1.
    static readonly HttpClient Http = new(new SocketsHttpHandler { ConnectCallback = ConnectIPv4FirstAsync }) { Timeout = Timeout.InfiniteTimeSpan };

    static async ValueTask<Stream> ConnectIPv4FirstAsync(SocketsHttpConnectionContext ctx, CancellationToken ct)
    {
        var addresses = await Dns.GetHostAddressesAsync(ctx.DnsEndPoint.Host, ct);
        Exception? last = null;
        foreach (var a in addresses.OrderBy(a => a.AddressFamily == AddressFamily.InterNetworkV6))
        {
            var socket = new Socket(a.AddressFamily, SocketType.Stream, ProtocolType.Tcp) { NoDelay = true };
            try
            {
                await socket.ConnectAsync(new IPEndPoint(a, ctx.DnsEndPoint.Port), ct);
                return new NetworkStream(socket, ownsSocket: true);
            }
            catch (SocketException e) { socket.Dispose(); last = e; }
        }
        throw last ?? new SocketException((int)SocketError.HostNotFound);
    }

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
