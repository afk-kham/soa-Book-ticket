using BookingService.Data;
using BookingService.Domain;

namespace BookingService.Services;

/// <summary>Kết quả tạo đơn: hoặc đã tạo, hoặc bị trùng ghế.</summary>
public sealed record CreateBookingResult(Booking? Booking, IReadOnlyList<string> TakenSeats)
{
    public bool Success => Booking is not null;
    public static CreateBookingResult Created(Booking b) => new(b, Array.Empty<string>());
    public static CreateBookingResult SeatsTaken(IReadOnlyList<string> seats) => new(null, seats);
}

/// <summary>Nghiệp vụ của Booking Service (giữa kỳ: chưa gọi Payment / Notification).</summary>
public sealed class BookingManager(BookingRepository repository)
{
    public Task<IReadOnlyList<Booking>> ListAsync(CancellationToken ct = default) =>
        repository.GetAllAsync(ct);

    public Task<Booking?> GetAsync(int id, CancellationToken ct = default) =>
        repository.GetByIdAsync(id, ct);

    /// <summary>Tiến trình 2.0 "Tạo đơn PENDING" (phân rã ở DFD mức 2).</summary>
    public async Task<CreateBookingResult> CreateAsync(CreateBookingRequest request, CancellationToken ct = default)
    {
        // 2.1 Tính tổng tiền = số ghế x giá vé (tối đa 10 x 1.000.000 nên không tràn int)
        var totalPrice = checked(request.Seats.Count * request.PricePerSeat);

        await using var session = await repository.BeginShowtimeSessionAsync(request.ShowtimeId, ct);

        // 2.2 Kiểm tra ghế đã bị đặt: các đơn cùng suất chiếu, trạng thái khác CANCELLED
        var activeSeats = await session.GetActiveSeatStringsAsync(request.ShowtimeId, ct);
        var conflicts = SeatRules.FindConflicts(request.Seats, activeSeats);
        if (conflicts.Count > 0)
            return CreateBookingResult.SeatsTaken(conflicts); // rollback + nhả khóa khi dispose

        // 2.3 Ghi đơn PENDING vào D1 | bookings
        var now = DateTime.Now;
        var createdAt = new DateTime(now.Year, now.Month, now.Day, now.Hour, now.Minute, now.Second, DateTimeKind.Unspecified);
        var booking = await session.InsertPendingAsync(new NewBooking(
            request.MovieId, request.ShowtimeId, request.Username, request.Seats, totalPrice, createdAt), ct);
        await session.CommitAsync(ct);

        // 2.4 Tạo phản hồi: do lớp HTTP chuyển Booking thành JSON 201
        return CreateBookingResult.Created(booking);
    }
}
