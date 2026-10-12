using System.Net;
using System.Text;
using System.Text.Encodings.Web;
using System.Text.Json;
using BookingService.Domain;

namespace BookingService.Http;

/// <summary>Đơn đặt vé ở dạng JSON trả cho client (camelCase theo hợp đồng API chung).</summary>
public sealed record BookingJson(
    int Id,
    int MovieId,
    int ShowtimeId,
    string Username,
    IReadOnlyList<string> Seats,
    int TotalPrice,
    string Status,
    string CreatedAt)
{
    public static BookingJson From(Booking b) => new(
        b.Id, b.MovieId, b.ShowtimeId, b.Username, b.Seats, b.TotalPrice, b.Status,
        b.CreatedAt.ToString("yyyy-MM-dd'T'HH:mm:ss"));
}

/// <summary>Lỗi khi đọc body (413 quá lớn, 400 rỗng / sai JSON).</summary>
public sealed class BadRequestBodyException(int statusCode, string message) : Exception(message)
{
    public int StatusCode { get; } = statusCode;
}

public static class HttpHelpers
{
    private static readonly JsonSerializerOptions JsonOptions = new()
    {
        PropertyNamingPolicy = JsonNamingPolicy.CamelCase,
        WriteIndented = true,
        // Giữ nguyên tiếng Việt và các ký tự ' + < > thay vì \u0027, \u002B...
        // An toàn vì client (trang admin) chỉ hiển thị dữ liệu bằng textContent, không dùng innerHTML.
        Encoder = JavaScriptEncoder.UnsafeRelaxedJsonEscaping,
    };

    private static readonly UTF8Encoding Utf8NoBom = new(encoderShouldEmitUTF8Identifier: false);

    /// <summary>Header CORS theo hợp đồng API chung của nhóm.</summary>
    public static void AddCorsHeaders(HttpListenerResponse res)
    {
        res.Headers["Access-Control-Allow-Origin"] = "*";
        res.Headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS";
        res.Headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization";
        res.Headers["Access-Control-Max-Age"] = "600";
    }

    /// <summary>{"status":"success","data":...}</summary>
    public static Task<int> WriteSuccessAsync(HttpListenerResponse res, int statusCode, object data) =>
        WriteJsonAsync(res, statusCode, new { status = "success", data });

    /// <summary>{"status":"error","message":"..."}</summary>
    public static Task<int> WriteErrorAsync(HttpListenerResponse res, int statusCode, string message) =>
        WriteJsonAsync(res, statusCode, new { status = "error", message });

    public static int WriteNoContent(HttpListenerResponse res)
    {
        res.StatusCode = 204;
        res.ContentLength64 = 0;
        return 204;
    }

    private static async Task<int> WriteJsonAsync(HttpListenerResponse res, int statusCode, object payload)
    {
        var bytes = Utf8NoBom.GetBytes(JsonSerializer.Serialize(payload, JsonOptions));
        res.StatusCode = statusCode;
        res.ContentType = "application/json; charset=utf-8";
        res.ContentLength64 = bytes.Length;
        await res.OutputStream.WriteAsync(bytes);
        return statusCode;
    }

    /// <summary>Đọc body tối đa <paramref name="maxBytes"/> byte rồi phân tích JSON.</summary>
    public static async Task<JsonDocument> ReadJsonBodyAsync(HttpListenerRequest req, int maxBytes, CancellationToken ct)
    {
        if (req.ContentLength64 > maxBytes)
            throw new BadRequestBodyException(413, $"Body vượt quá giới hạn {maxBytes / 1024} KiB");

        using var buffer = new MemoryStream();
        var chunk = new byte[4096];
        int read;
        while ((read = await req.InputStream.ReadAsync(chunk, ct)) > 0)
        {
            if (buffer.Length + read > maxBytes)
                throw new BadRequestBodyException(413, $"Body vượt quá giới hạn {maxBytes / 1024} KiB");
            buffer.Write(chunk, 0, read);
        }

        var bytes = buffer.ToArray().AsMemory();
        // Bỏ BOM UTF-8 nếu client gửi kèm (một số bản PowerShell làm vậy)
        if (bytes.Length >= 3 && bytes.Span[0] == 0xEF && bytes.Span[1] == 0xBB && bytes.Span[2] == 0xBF)
            bytes = bytes[3..];

        if (IsBlank(bytes.Span))
            throw new BadRequestBodyException(400, "Body rỗng, cần gửi JSON");

        try
        {
            return JsonDocument.Parse(bytes, new JsonDocumentOptions { MaxDepth = 16 });
        }
        catch (JsonException ex)
        {
            var where = ex.LineNumber is { } line
                ? $" (dòng {line + 1}, vị trí {ex.BytePositionInLine + 1})"
                : "";
            throw new BadRequestBodyException(400, "JSON không hợp lệ" + where);
        }
    }

    private static bool IsBlank(ReadOnlySpan<byte> data)
    {
        foreach (var b in data)
            if (b is not ((byte)' ' or (byte)'\t' or (byte)'\r' or (byte)'\n')) return false;
        return true;
    }
}
