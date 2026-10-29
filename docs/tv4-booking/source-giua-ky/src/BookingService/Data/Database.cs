using System.Data.Common;
using BookingService.Config;

namespace BookingService.Data;

/// <summary>
/// Mở kết nối ADO.NET tới booking_db. Dùng DbProviderFactory nên phần còn lại của code
/// chỉ làm việc với DbConnection / DbCommand chung, đổi MySQL <-> SQL Server chỉ bằng DB_PROVIDER.
/// </summary>
public sealed class Database
{
    private readonly DbProviderFactory _factory;
    private readonly string _connectionString;

    public ISqlDialect Dialect { get; }

    /// <summary>Mô tả để in ra màn hình (không chứa mật khẩu).</summary>
    public string Description { get; }

    public Database(AppConfig config)
    {
        var builder = new DbConnectionStringBuilder();

        if (config.DbProvider == "sqlserver")
        {
            _factory = Microsoft.Data.SqlClient.SqlClientFactory.Instance;
            Dialect = new SqlServerDialect();

            // Hỗ trợ cả "localhost\SQLEXPRESS" (instance có tên) lẫn "localhost" + cổng.
            var server = config.DbHost.Contains('\\') || config.DbPort is null
                ? config.DbHost
                : $"{config.DbHost},{config.DbPort}";
            builder["Server"] = server;
            builder["Database"] = config.DbName;
            if (string.IsNullOrEmpty(config.DbUser))
            {
                builder["Integrated Security"] = "true"; // đăng nhập bằng tài khoản Windows
            }
            else
            {
                builder["User ID"] = config.DbUser;
                builder["Password"] = config.DbPassword;
            }
            builder["TrustServerCertificate"] = "true";
            builder["Connect Timeout"] = "5";
            Description = $"SQL Server {server}/{config.DbName}";
        }
        else
        {
            _factory = MySqlConnector.MySqlConnectorFactory.Instance;
            Dialect = new MySqlDialect();

            var port = config.DbPort ?? 3306;
            builder["Server"] = config.DbHost;
            builder["Port"] = port.ToString();
            builder["Database"] = config.DbName;
            builder["User ID"] = config.DbUser;
            builder["Password"] = config.DbPassword;
            builder["Character Set"] = "utf8mb4";
            builder["SslMode"] = "Preferred";
            builder["AllowPublicKeyRetrieval"] = "true"; // cần cho MySQL 8 khi không dùng SSL
            builder["Connection Timeout"] = "5";
            builder["Default Command Timeout"] = "15";
            Description = $"MySQL {config.DbHost}:{port}/{config.DbName}";
        }

        _connectionString = builder.ConnectionString;
    }

    public async Task<DbConnection> OpenAsync(CancellationToken ct = default)
    {
        var conn = _factory.CreateConnection()
                   ?? throw new InvalidOperationException("Không tạo được kết nối CSDL.");
        conn.ConnectionString = _connectionString;
        try
        {
            await conn.OpenAsync(ct);
            return conn;
        }
        catch
        {
            await conn.DisposeAsync();
            throw;
        }
    }

    /// <summary>Kiểm tra kết nối khi khởi động, trả về phiên bản máy chủ CSDL.</summary>
    public async Task<string> GetServerVersionAsync(CancellationToken ct = default)
    {
        await using var conn = await OpenAsync(ct);
        await using var cmd = conn.CreateCommand();
        cmd.CommandText = Dialect.VersionQuery;
        return Convert.ToString(await cmd.ExecuteScalarAsync(ct)) ?? "?";
    }
}
