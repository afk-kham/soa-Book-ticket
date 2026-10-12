using System.Text.Json;
using System.Text.Json.Serialization;

namespace BookingService;

/// <summary>Trạng thái đơn đặt vé — dùng đúng 3 giá trị này ở mọi nơi (DB, API, Admin, Client).</summary>
public static class BookingStatus
{
    public const string Pending = "PENDING";
    public const string Paid = "PAID";
    public const string Cancelled = "CANCELLED";
}

public record Booking(
    int Id, int MovieId, int ShowtimeId, string Username,
    List<string> Seats, int TotalPrice, string Status, string CreatedAt);

public static class Json
{
    public static readonly JsonSerializerOptions Options = new()
    {
        PropertyNamingPolicy = JsonNamingPolicy.CamelCase,      // API dùng camelCase
        DictionaryKeyPolicy = JsonNamingPolicy.CamelCase,
        Encoder = System.Text.Encodings.Web.JavaScriptEncoder.UnsafeRelaxedJsonEscaping,   // giữ nguyên tiếng Việt
        DefaultIgnoreCondition = JsonIgnoreCondition.Never,
    };
}

/// <summary>Lỗi nghiệp vụ -> được chuyển thành {"status":"error","code":...,"message":...}.</summary>
public class ApiException : Exception
{
    public int Status { get; }
    public string Code { get; }
    public ApiException(int status, string code, string message) : base(message) { Status = status; Code = code; }
}
