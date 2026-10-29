using System.Data.Common;

namespace BookingService.Data;

/// <summary>
/// Những chỗ cú pháp SQL khác nhau giữa MySQL và SQL Server.
/// Mọi câu lệnh còn lại dùng chung và đều có tham số (@ten_tham_so).
/// </summary>
public interface ISqlDialect
{
    string Name { get; }

    /// <summary>Đặt tên cột trong dấu trích dẫn (status là từ khóa): `status` / [status].</summary>
    string Q(string identifier);

    /// <summary>Câu INSERT trả về id vừa tạo khi gọi ExecuteScalar.</summary>
    string InsertReturningId(string table, IReadOnlyList<string> columns);

    /// <summary>Lệnh lấy phiên bản máy chủ CSDL (dùng khi khởi động để kiểm tra kết nối).</summary>
    string VersionQuery { get; }

    /// <summary>
    /// Khóa theo tên (named lock) để hai request đặt cùng một suất chiếu không chạy chồng lên nhau.
    /// Trả về false nếu chờ quá thời gian.
    /// </summary>
    Task<bool> TryAcquireLockAsync(DbConnection conn, DbTransaction tx, string lockName, int timeoutSeconds, CancellationToken ct);

    /// <summary>Nhả khóa (MySQL cần nhả tay; SQL Server tự nhả khi kết thúc transaction).</summary>
    Task ReleaseLockAsync(DbConnection conn, string lockName);
}

public sealed class MySqlDialect : ISqlDialect
{
    public string Name => "MySQL";
    public string Q(string identifier) => $"`{identifier}`";
    public string VersionQuery => "SELECT VERSION()";

    public string InsertReturningId(string table, IReadOnlyList<string> columns) =>
        $"INSERT INTO {table} ({string.Join(", ", columns.Select(Q))}) " +
        $"VALUES ({string.Join(", ", columns.Select(c => "@" + c))}); " +
        "SELECT LAST_INSERT_ID();";

    public async Task<bool> TryAcquireLockAsync(DbConnection conn, DbTransaction tx, string lockName, int timeoutSeconds, CancellationToken ct)
    {
        await using var cmd = conn.CreateCommand();
        cmd.Transaction = tx;
        cmd.CommandText = "SELECT GET_LOCK(@lockName, @timeout)";
        cmd.AddParameter("@lockName", lockName);
        cmd.AddParameter("@timeout", timeoutSeconds);
        var result = await cmd.ExecuteScalarAsync(ct);
        return result is not null and not DBNull && Convert.ToInt32(result) == 1;
    }

    public async Task ReleaseLockAsync(DbConnection conn, string lockName)
    {
        await using var cmd = conn.CreateCommand();
        cmd.CommandText = "DO RELEASE_LOCK(@lockName)";
        cmd.AddParameter("@lockName", lockName);
        await cmd.ExecuteNonQueryAsync();
    }
}

public sealed class SqlServerDialect : ISqlDialect
{
    public string Name => "SQL Server";
    public string Q(string identifier) => $"[{identifier}]";
    public string VersionQuery => "SELECT CAST(SERVERPROPERTY('ProductVersion') AS NVARCHAR(128))";

    public string InsertReturningId(string table, IReadOnlyList<string> columns) =>
        $"INSERT INTO {table} ({string.Join(", ", columns.Select(Q))}) " +
        "OUTPUT INSERTED.id " +
        $"VALUES ({string.Join(", ", columns.Select(c => "@" + c))});";

    public async Task<bool> TryAcquireLockAsync(DbConnection conn, DbTransaction tx, string lockName, int timeoutSeconds, CancellationToken ct)
    {
        await using var cmd = conn.CreateCommand();
        cmd.Transaction = tx;
        cmd.CommandText =
            "DECLARE @r INT; " +
            "EXEC @r = sp_getapplock @Resource = @lockName, @LockMode = 'Exclusive', " +
            "@LockOwner = 'Transaction', @LockTimeout = @timeoutMs; " +
            "SELECT @r;";
        cmd.AddParameter("@lockName", lockName);
        cmd.AddParameter("@timeoutMs", timeoutSeconds * 1000);
        var result = await cmd.ExecuteScalarAsync(ct);
        return result is not null and not DBNull && Convert.ToInt32(result) >= 0;
    }

    // sp_getapplock với @LockOwner = 'Transaction' tự nhả khi COMMIT/ROLLBACK.
    public Task ReleaseLockAsync(DbConnection conn, string lockName) => Task.CompletedTask;
}

internal static class DbCommandExtensions
{
    /// <summary>Thêm tham số cho câu lệnh (prepared statement), không nối chuỗi dữ liệu người dùng.</summary>
    public static void AddParameter(this DbCommand cmd, string name, object? value)
    {
        var p = cmd.CreateParameter();
        p.ParameterName = name;
        p.Value = value ?? DBNull.Value;
        cmd.Parameters.Add(p);
    }
}
