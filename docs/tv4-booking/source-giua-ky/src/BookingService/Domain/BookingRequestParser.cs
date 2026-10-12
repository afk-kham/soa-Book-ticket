using System.Text.Json;
using System.Text.RegularExpressions;

namespace BookingService.Domain;

/// <summary>Kết quả đọc body: hoặc có Request hợp lệ, hoặc có danh sách lỗi.</summary>
public sealed record ParseResult(CreateBookingRequest? Request, IReadOnlyList<string> Errors)
{
    public bool IsValid => Request is not null && Errors.Count == 0;
}

/// <summary>
/// Tiến trình 1.0 "Tiếp nhận và kiểm tra yêu cầu": đọc JSON
/// { movieId, showtimeId, seats[], pricePerSeat, username } và kiểm tra từng trường.
/// Các trường khác client tự gửi (status, totalPrice...) bị bỏ qua: server tự quyết định.
/// </summary>
public static partial class BookingRequestParser
{
    public const int MaxSeatsPerBooking = 10;
    public const int MaxPricePerSeat = 1_000_000; // VND

    [GeneratedRegex(@"^[A-Za-z0-9_.\-]{1,50}$")]
    private static partial Regex UsernamePattern();

    public static ParseResult Parse(JsonElement root)
    {
        if (root.ValueKind != JsonValueKind.Object)
            return new ParseResult(null, new[] { "Body phải là một đối tượng JSON" });

        var errors = new List<string>();
        var movieId = ReadPositiveInt(root, "movieId", int.MaxValue, errors);
        var showtimeId = ReadPositiveInt(root, "showtimeId", int.MaxValue, errors);
        var seats = ReadSeats(root, errors);
        var pricePerSeat = ReadPositiveInt(root, "pricePerSeat", MaxPricePerSeat, errors);
        var username = ReadUsername(root, errors);

        return errors.Count > 0
            ? new ParseResult(null, errors)
            : new ParseResult(new CreateBookingRequest(movieId, showtimeId, seats, pricePerSeat, username), errors);
    }

    private static int ReadPositiveInt(JsonElement root, string name, int max, List<string> errors)
    {
        if (!root.TryGetProperty(name, out var el) || el.ValueKind == JsonValueKind.Null)
        {
            errors.Add($"Thiếu trường {name}");
            return 0;
        }
        if (el.ValueKind != JsonValueKind.Number || !el.TryGetInt32(out var value))
        {
            errors.Add($"{name} phải là số nguyên");
            return 0;
        }
        if (value <= 0)
        {
            errors.Add($"{name} phải lớn hơn 0");
            return 0;
        }
        if (value > max)
        {
            errors.Add($"{name} không được vượt quá {max}");
            return 0;
        }
        return value;
    }

    private static string ReadUsername(JsonElement root, List<string> errors)
    {
        if (!root.TryGetProperty("username", out var el) || el.ValueKind == JsonValueKind.Null)
        {
            errors.Add("Thiếu trường username");
            return "";
        }
        if (el.ValueKind != JsonValueKind.String)
        {
            errors.Add("username phải là chuỗi");
            return "";
        }
        var username = el.GetString()!.Trim();
        if (!UsernamePattern().IsMatch(username))
        {
            errors.Add("username phải dài 1-50 ký tự, chỉ gồm chữ, số và . _ -");
            return "";
        }
        return username;
    }

    private static IReadOnlyList<string> ReadSeats(JsonElement root, List<string> errors)
    {
        if (!root.TryGetProperty("seats", out var el) || el.ValueKind == JsonValueKind.Null)
        {
            errors.Add("Thiếu trường seats");
            return Array.Empty<string>();
        }
        if (el.ValueKind != JsonValueKind.Array)
        {
            errors.Add("seats phải là mảng, ví dụ [\"A1\",\"A2\"]");
            return Array.Empty<string>();
        }

        var count = el.GetArrayLength();
        if (count == 0)
        {
            errors.Add("Phải chọn ít nhất 1 ghế");
            return Array.Empty<string>();
        }
        if (count > MaxSeatsPerBooking)
        {
            errors.Add($"Mỗi đơn đặt tối đa {MaxSeatsPerBooking} ghế");
            return Array.Empty<string>();
        }

        var seats = new List<string>(count);
        var seen = new HashSet<string>(StringComparer.Ordinal);
        var index = 0;
        foreach (var item in el.EnumerateArray())
        {
            if (item.ValueKind != JsonValueKind.String)
            {
                errors.Add($"seats[{index}] phải là chuỗi");
            }
            else
            {
                var seat = SeatRules.Normalize(item.GetString()!);
                if (!SeatRules.IsValid(seat))
                    errors.Add($"Ghế '{item.GetString()}' không hợp lệ (dạng hàng A-Z + số 1-99, ví dụ A1)");
                else if (!seen.Add(seat))
                    errors.Add($"Ghế {seat} bị lặp trong yêu cầu");
                else
                    seats.Add(seat);
            }
            index++;
        }
        return seats;
    }
}
