namespace BookingService.Domain;

/// <summary>Các trạng thái của một đơn đặt vé (cột status).</summary>
public static class BookingStatus
{
    public const string Pending = "PENDING";     // vừa tạo, chờ thanh toán
    public const string Paid = "PAID";           // đã thanh toán (cuối kỳ do luồng Payment cập nhật)
    public const string Cancelled = "CANCELLED"; // đã hủy, ghế được trả lại
}

/// <summary>Một dòng của bảng bookings.</summary>
public sealed record Booking(
    int Id,
    int MovieId,
    int ShowtimeId,
    string Username,
    IReadOnlyList<string> Seats,
    int TotalPrice,
    string Status,
    DateTime CreatedAt);

/// <summary>Dữ liệu để ghi một đơn mới (chưa có id).</summary>
public sealed record NewBooking(
    int MovieId,
    int ShowtimeId,
    string Username,
    IReadOnlyList<string> Seats,
    int TotalPrice,
    DateTime CreatedAt);

/// <summary>Yêu cầu đặt vé đã được kiểm tra hợp lệ (đầu ra của tiến trình 1.0).</summary>
public sealed record CreateBookingRequest(
    int MovieId,
    int ShowtimeId,
    IReadOnlyList<string> Seats,
    int PricePerSeat,
    string Username);
