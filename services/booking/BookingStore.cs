using System.Data;
using System.Data.Common;
using System.Globalization;
using MySqlConnector;

namespace BookingService;

public interface IBookingStore
{
    Task PingAsync();
    Task<List<Booking>> ListAsync(string? username, string? status, int? showtimeId);
    Task<Booking?> GetAsync(int id);
    /// <summary>Các ghế đã bị giữ (đơn PENDING/PAID) của một suất chiếu — đơn CANCELLED không giữ ghế.</summary>
    Task<HashSet<string>> TakenSeatsAsync(int showtimeId);
    Task<Booking> InsertPendingAsync(int movieId, int showtimeId, string username, List<string> seats, int totalPrice);
    Task UpdateStatusAsync(int id, string status);
}

/// <summary>Truy cập booking_db bằng ADO.NET + câu lệnh có tham số (chống SQL injection).</summary>
public class MySqlBookingStore : IBookingStore
{
    const string Cols = "id, movie_id, showtime_id, username, seats, total_price, status, created_at";

    static DbConnection NewConnection() => new MySqlConnection(Config.DbConnectionString);

    static async Task<DbConnection> OpenAsync()
    {
        var c = NewConnection();
        await c.OpenAsync();
        return c;
    }

    static void P(DbCommand cmd, string name, object? value)
    {
        var p = cmd.CreateParameter();
        p.ParameterName = name;
        p.Value = value ?? DBNull.Value;
        cmd.Parameters.Add(p);
    }

    static Booking Map(DbDataReader r) => new(
        r.GetInt32(0), r.GetInt32(1), r.GetInt32(2), r.GetString(3),
        r.GetString(4).Split(',', StringSplitOptions.RemoveEmptyEntries | StringSplitOptions.TrimEntries).ToList(),
        r.GetInt32(5), r.GetString(6),
        r.GetDateTime(7).ToString("yyyy-MM-dd HH:mm:ss", CultureInfo.InvariantCulture));

    public async Task PingAsync()
    {
        await using var c = await OpenAsync();
        await using var cmd = c.CreateCommand();
        cmd.CommandText = "SELECT 1";
        await cmd.ExecuteScalarAsync();
    }

    public async Task<List<Booking>> ListAsync(string? username, string? status, int? showtimeId)
    {
        await using var c = await OpenAsync();
        await using var cmd = c.CreateCommand();
        cmd.CommandText = $"SELECT {Cols} FROM bookings WHERE (@u IS NULL OR username = @u) AND (@s IS NULL OR status = @s) " +
                          "AND (@t IS NULL OR showtime_id = @t) ORDER BY id";
        P(cmd, "@u", username); P(cmd, "@s", status); P(cmd, "@t", showtimeId);
        var list = new List<Booking>();
        await using var r = await cmd.ExecuteReaderAsync();
        while (await r.ReadAsync()) list.Add(Map(r));
        return list;
    }

    public async Task<Booking?> GetAsync(int id)
    {
        await using var c = await OpenAsync();
        await using var cmd = c.CreateCommand();
        cmd.CommandText = $"SELECT {Cols} FROM bookings WHERE id = @id";
        P(cmd, "@id", id);
        await using var r = await cmd.ExecuteReaderAsync();
        return await r.ReadAsync() ? Map(r) : null;
    }

    public async Task<HashSet<string>> TakenSeatsAsync(int showtimeId)
    {
        await using var c = await OpenAsync();
        await using var cmd = c.CreateCommand();
        cmd.CommandText = "SELECT seats FROM bookings WHERE showtime_id = @t AND status <> 'CANCELLED'";
        P(cmd, "@t", showtimeId);
        var taken = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
        await using var r = await cmd.ExecuteReaderAsync();
        while (await r.ReadAsync())
            foreach (var s in r.GetString(0).Split(',', StringSplitOptions.RemoveEmptyEntries | StringSplitOptions.TrimEntries))
                taken.Add(s);
        return taken;
    }

    public async Task<Booking> InsertPendingAsync(int movieId, int showtimeId, string username, List<string> seats, int totalPrice)
    {
        await using var c = await OpenAsync();
        await using var cmd = c.CreateCommand();
        cmd.CommandText = "INSERT INTO bookings (movie_id, showtime_id, username, seats, total_price, status) " +
                          "VALUES (@m, @t, @u, @seats, @total, 'PENDING')";
        P(cmd, "@m", movieId); P(cmd, "@t", showtimeId); P(cmd, "@u", username);
        P(cmd, "@seats", string.Join(",", seats)); P(cmd, "@total", totalPrice);
        await cmd.ExecuteNonQueryAsync();
        await using var idCmd = c.CreateCommand();
        idCmd.CommandText = "SELECT LAST_INSERT_ID()";
        var id = Convert.ToInt32(await idCmd.ExecuteScalarAsync(), CultureInfo.InvariantCulture);
        return (await GetAsync(id))!;
    }

    public async Task UpdateStatusAsync(int id, string status)
    {
        await using var c = await OpenAsync();
        await using var cmd = c.CreateCommand();
        cmd.CommandText = "UPDATE bookings SET status = @s WHERE id = @id";
        P(cmd, "@s", status); P(cmd, "@id", id);
        await cmd.ExecuteNonQueryAsync();
    }
}

/// <summary>CHỈ để test tích hợp khi không có DB (BOOKING_STORE=memory). Dữ liệu khớp seed chung.</summary>
public class MemoryBookingStore : IBookingStore
{
    readonly List<Booking> _rows =
    [
        new(1, 1, 1, "user1", ["A1", "A2"], 180000, BookingStatus.Paid, "2026-10-01 10:00:00"),
        new(2, 2, 3, "user2", ["B5"], 85000, BookingStatus.Cancelled, "2026-10-01 11:00:00"),
        new(3, 4, 5, "user1", ["C3", "C4"], 180000, BookingStatus.Pending, "2026-10-02 09:30:00"),
    ];
    int _next = 4;
    readonly object _lock = new();

    public Task PingAsync() => Task.CompletedTask;

    public Task<List<Booking>> ListAsync(string? username, string? status, int? showtimeId)
    {
        lock (_lock)
            return Task.FromResult(_rows.Where(b => (username is null || b.Username == username)
                && (status is null || b.Status == status) && (showtimeId is null || b.ShowtimeId == showtimeId)).ToList());
    }

    public Task<Booking?> GetAsync(int id) { lock (_lock) return Task.FromResult(_rows.FirstOrDefault(b => b.Id == id)); }

    public Task<HashSet<string>> TakenSeatsAsync(int showtimeId)
    {
        lock (_lock)
            return Task.FromResult(_rows.Where(b => b.ShowtimeId == showtimeId && b.Status != BookingStatus.Cancelled)
                .SelectMany(b => b.Seats).ToHashSet(StringComparer.OrdinalIgnoreCase));
    }

    public Task<Booking> InsertPendingAsync(int movieId, int showtimeId, string username, List<string> seats, int totalPrice)
    {
        lock (_lock)
        {
            var b = new Booking(_next++, movieId, showtimeId, username, seats, totalPrice, BookingStatus.Pending,
                DateTime.Now.ToString("yyyy-MM-dd HH:mm:ss", CultureInfo.InvariantCulture));
            _rows.Add(b);
            return Task.FromResult(b);
        }
    }

    public Task UpdateStatusAsync(int id, string status)
    {
        lock (_lock)
        {
            var i = _rows.FindIndex(b => b.Id == id);
            if (i >= 0) _rows[i] = _rows[i] with { Status = status };
        }
        return Task.CompletedTask;
    }
}
