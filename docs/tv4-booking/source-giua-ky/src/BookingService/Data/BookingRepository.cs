using System.Data;
using System.Data.Common;
using BookingService.Domain;

namespace BookingService.Data;

/// <summary>Báo hiệu đang có request khác giữ khóa của suất chiếu quá lâu.</summary>
public sealed class ResourceBusyException(string message) : Exception(message);

/// <summary>Đọc / ghi bảng bookings (kho dữ liệu D1 | bookings trong DFD).</summary>
public sealed class BookingRepository(Database db)
{
    private const int LockTimeoutSeconds = 5;

    private ISqlDialect D => db.Dialect;

    private string SelectColumns =>
        $"id, movie_id, showtime_id, username, seats, total_price, {D.Q("status")}, created_at";

    /// <summary>Tiến trình 3.0: danh sách đơn, mới nhất trước.</summary>
    public async Task<IReadOnlyList<Booking>> GetAllAsync(CancellationToken ct = default)
    {
        await using var conn = await db.OpenAsync(ct);
        await using var cmd = conn.CreateCommand();
        cmd.CommandText = $"SELECT {SelectColumns} FROM bookings ORDER BY id DESC";

        var list = new List<Booking>();
        await using var reader = await cmd.ExecuteReaderAsync(ct);
        while (await reader.ReadAsync(ct))
            list.Add(Map(reader));
        return list;
    }

    /// <summary>Tiến trình 3.0: chi tiết một đơn theo id (null nếu không có).</summary>
    public async Task<Booking?> GetByIdAsync(int id, CancellationToken ct = default)
    {
        await using var conn = await db.OpenAsync(ct);
        await using var cmd = conn.CreateCommand();
        cmd.CommandText = $"SELECT {SelectColumns} FROM bookings WHERE id = @id";
        cmd.AddParameter("@id", id);

        await using var reader = await cmd.ExecuteReaderAsync(CommandBehavior.SingleRow, ct);
        return await reader.ReadAsync(ct) ? Map(reader) : null;
    }

    /// <summary>
    /// Mở một phiên làm việc riêng cho một suất chiếu: mở kết nối, bắt đầu transaction
    /// và giữ khóa theo tên "booking_showtime_{id}" cho tới khi phiên kết thúc.
    /// Nhờ vậy hai request đặt cùng ghế cùng lúc không thể cùng vượt qua bước kiểm tra ghế.
    /// </summary>
    public async Task<ShowtimeBookingSession> BeginShowtimeSessionAsync(int showtimeId, CancellationToken ct = default)
    {
        var lockName = $"booking_showtime_{showtimeId}";
        var conn = await db.OpenAsync(ct);
        DbTransaction? tx = null;
        try
        {
            tx = await conn.BeginTransactionAsync(IsolationLevel.ReadCommitted, ct);
            if (!await D.TryAcquireLockAsync(conn, tx, lockName, LockTimeoutSeconds, ct))
                throw new ResourceBusyException("Suất chiếu đang được nhiều người đặt cùng lúc, vui lòng thử lại.");
            return new ShowtimeBookingSession(conn, tx, D, lockName);
        }
        catch
        {
            if (tx is not null) await tx.DisposeAsync();
            await conn.DisposeAsync();
            throw;
        }
    }

    internal static Booking Map(DbDataReader r) => new(
        Id: r.GetInt32(0),
        MovieId: r.GetInt32(1),
        ShowtimeId: r.GetInt32(2),
        Username: r.GetString(3),
        Seats: SeatRules.Split(r.GetString(4)),
        TotalPrice: r.GetInt32(5),
        Status: r.GetString(6),
        CreatedAt: r.IsDBNull(7) ? DateTime.MinValue : r.GetDateTime(7));
}

/// <summary>Một transaction đặt vé cho một suất chiếu (đang giữ khóa của suất đó).</summary>
public sealed class ShowtimeBookingSession : IAsyncDisposable
{
    private static readonly string[] InsertColumns =
        { "movie_id", "showtime_id", "username", "seats", "total_price", "status", "created_at" };

    private readonly DbConnection _conn;
    private readonly DbTransaction _tx;
    private readonly ISqlDialect _dialect;
    private readonly string _lockName;
    private bool _committed;

    internal ShowtimeBookingSession(DbConnection conn, DbTransaction tx, ISqlDialect dialect, string lockName)
    {
        _conn = conn;
        _tx = tx;
        _dialect = dialect;
        _lockName = lockName;
    }

    /// <summary>Lấy chuỗi ghế của các đơn còn hiệu lực (khác CANCELLED) trong suất chiếu.</summary>
    public async Task<IReadOnlyList<string>> GetActiveSeatStringsAsync(int showtimeId, CancellationToken ct = default)
    {
        await using var cmd = _conn.CreateCommand();
        cmd.Transaction = _tx;
        cmd.CommandText =
            $"SELECT seats FROM bookings WHERE showtime_id = @showtimeId AND {_dialect.Q("status")} <> @cancelled";
        cmd.AddParameter("@showtimeId", showtimeId);
        cmd.AddParameter("@cancelled", BookingStatus.Cancelled);

        var result = new List<string>();
        await using var reader = await cmd.ExecuteReaderAsync(ct);
        while (await reader.ReadAsync(ct))
            result.Add(reader.GetString(0));
        return result;
    }

    /// <summary>Ghi đơn mới với trạng thái PENDING, trả về đơn kèm id do CSDL cấp.</summary>
    public async Task<Booking> InsertPendingAsync(NewBooking b, CancellationToken ct = default)
    {
        await using var cmd = _conn.CreateCommand();
        cmd.Transaction = _tx;
        cmd.CommandText = _dialect.InsertReturningId("bookings", InsertColumns);
        cmd.AddParameter("@movie_id", b.MovieId);
        cmd.AddParameter("@showtime_id", b.ShowtimeId);
        cmd.AddParameter("@username", b.Username);
        cmd.AddParameter("@seats", SeatRules.Join(b.Seats));
        cmd.AddParameter("@total_price", b.TotalPrice);
        cmd.AddParameter("@status", BookingStatus.Pending);
        cmd.AddParameter("@created_at", b.CreatedAt);

        var id = Convert.ToInt32(await cmd.ExecuteScalarAsync(ct));
        return new Booking(id, b.MovieId, b.ShowtimeId, b.Username, b.Seats, b.TotalPrice,
            BookingStatus.Pending, b.CreatedAt);
    }

    public async Task CommitAsync(CancellationToken ct = default)
    {
        await _tx.CommitAsync(ct);
        _committed = true;
    }

    public async ValueTask DisposeAsync()
    {
        try
        {
            if (!_committed) await _tx.RollbackAsync();
        }
        catch
        {
            // Kết nối có thể đã đứt; bỏ qua để vẫn đóng kết nối bên dưới.
        }
        try
        {
            await _dialect.ReleaseLockAsync(_conn, _lockName);
        }
        catch
        {
            // Đóng kết nối MySQL cũng tự nhả khóa GET_LOCK.
        }
        await _tx.DisposeAsync();
        await _conn.DisposeAsync();
    }
}
