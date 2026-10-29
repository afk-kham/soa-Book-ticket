using System.Text.RegularExpressions;

namespace BookingService.Domain;

/// <summary>
/// Quy tắc về ghế. Ghế gồm 1 chữ cái hàng (A-Z) + số ghế 1-99, ví dụ A1, C12.
/// Trong CSDL, ghế của một đơn lưu thành chuỗi "A1,A2".
/// </summary>
public static partial class SeatRules
{
    [GeneratedRegex(@"^[A-Z][1-9][0-9]?$")]
    private static partial Regex SeatPattern();

    public static string Normalize(string seat) => seat.Trim().ToUpperInvariant();

    public static bool IsValid(string normalizedSeat) => SeatPattern().IsMatch(normalizedSeat);

    /// <summary>Ghép danh sách ghế thành chuỗi lưu CSDL: ["A1","A2"] -> "A1,A2".</summary>
    public static string Join(IEnumerable<string> seats) => string.Join(",", seats);

    /// <summary>Tách chuỗi trong CSDL: "A1, a2" -> ["A1","A2"].</summary>
    public static IReadOnlyList<string> Split(string? stored) =>
        string.IsNullOrWhiteSpace(stored)
            ? Array.Empty<string>()
            : stored.Split(',', StringSplitOptions.RemoveEmptyEntries | StringSplitOptions.TrimEntries)
                    .Select(Normalize)
                    .ToArray();

    /// <summary>
    /// Trả về các ghế trong <paramref name="requested"/> đã nằm trong các đơn còn hiệu lực
    /// (PENDING hoặc PAID) của cùng suất chiếu.
    /// So khớp theo từng ghế sau khi tách chuỗi, không dùng LIKE, để "A1" không bị nhầm với "A10".
    /// </summary>
    public static IReadOnlyList<string> FindConflicts(IReadOnlyList<string> requested, IEnumerable<string> activeSeatStrings)
    {
        var taken = new HashSet<string>(StringComparer.Ordinal);
        foreach (var stored in activeSeatStrings)
            foreach (var seat in Split(stored))
                taken.Add(seat);

        return requested.Where(taken.Contains).ToArray();
    }
}
