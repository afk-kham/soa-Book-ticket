namespace BookingService.Config;

/// <summary>
/// Toàn bộ cấu hình của service nằm ở một chỗ (theo quy tắc P6 của phiếu giao việc).
/// Thứ tự ưu tiên: biến môi trường của hệ điều hành  >  file .env  >  giá trị mặc định.
/// </summary>
public sealed class AppConfig
{
    /// <summary>Giới hạn kích thước body của request (16 KiB).</summary>
    public const int MaxBodyBytes = 16 * 1024;

    public int Port { get; private init; } = 5004;

    /// <summary>
    /// Prefix cho HttpListener. Mặc định http://localhost:5004/ để không cần quyền Administrator.
    /// Khi ghép nhóm qua mạng LAN dùng http://+:5004/ (xem README).
    /// </summary>
    public IReadOnlyList<string> ListenPrefixes { get; private init; } = Array.Empty<string>();

    /// <summary>"mysql" (mặc định) hoặc "sqlserver".</summary>
    public string DbProvider { get; private init; } = "mysql";
    public string DbHost { get; private init; } = "127.0.0.1";
    public int? DbPort { get; private init; }
    public string DbName { get; private init; } = "booking_db";
    public string DbUser { get; private init; } = "root";
    public string DbPassword { get; private init; } = "";

    /// <summary>Đường dẫn file .env đã đọc (null nếu không có).</summary>
    public string? EnvFile { get; private init; }

    public static AppConfig Load()
    {
        var envFile = FindEnvFile();
        var fileValues = envFile is null ? new Dictionary<string, string>() : ReadEnvFile(envFile);

        string Get(string key, string defaultValue)
        {
            var fromOs = Environment.GetEnvironmentVariable(key);
            if (!string.IsNullOrEmpty(fromOs)) return fromOs.Trim();
            return fileValues.TryGetValue(key, out var v) && v.Length > 0 ? v : defaultValue;
        }

        var port = ParseInt(Get("PORT", "5004"), "PORT", 1, 65535);
        var prefixes = Get("LISTEN_PREFIXES", $"http://localhost:{port}/")
            .Split(',', StringSplitOptions.RemoveEmptyEntries | StringSplitOptions.TrimEntries)
            .Select(p => p.EndsWith('/') ? p : p + "/")
            .ToArray();

        var provider = Get("DB_PROVIDER", "mysql").ToLowerInvariant();
        if (provider is not ("mysql" or "sqlserver"))
            throw new InvalidOperationException($"DB_PROVIDER='{provider}' không hợp lệ (chỉ nhận mysql hoặc sqlserver).");

        var dbPortText = Get("DB_PORT", "");
        int? dbPort = dbPortText.Length == 0 ? null : ParseInt(dbPortText, "DB_PORT", 1, 65535);

        return new AppConfig
        {
            Port = port,
            ListenPrefixes = prefixes,
            DbProvider = provider,
            DbHost = Get("DB_HOST", "127.0.0.1"),
            DbPort = dbPort,
            DbName = Get("DB_NAME", "booking_db"),
            DbUser = Get("DB_USER", provider == "mysql" ? "root" : ""),
            DbPassword = Get("DB_PASSWORD", ""),
            EnvFile = envFile,
        };
    }

    private static int ParseInt(string text, string key, int min, int max)
    {
        if (int.TryParse(text, out var value) && value >= min && value <= max) return value;
        throw new InvalidOperationException($"{key}='{text}' không hợp lệ (phải là số từ {min} đến {max}).");
    }

    /// <summary>Tìm file .env ở thư mục hiện tại và tối đa 4 thư mục cha (để chạy được từ src/BookingService).</summary>
    private static string? FindEnvFile()
    {
        var dir = new DirectoryInfo(Directory.GetCurrentDirectory());
        for (var i = 0; i < 5 && dir is not null; i++, dir = dir.Parent)
        {
            var candidate = Path.Combine(dir.FullName, ".env");
            if (File.Exists(candidate)) return candidate;
        }
        return null;
    }

    /// <summary>Đọc file .env dạng KEY=VALUE, bỏ qua dòng trống và dòng bắt đầu bằng #.</summary>
    private static Dictionary<string, string> ReadEnvFile(string path)
    {
        var result = new Dictionary<string, string>(StringComparer.OrdinalIgnoreCase);
        foreach (var rawLine in File.ReadAllLines(path))
        {
            var line = rawLine.Trim();
            if (line.Length == 0 || line.StartsWith('#')) continue;
            var eq = line.IndexOf('=');
            if (eq <= 0) continue;
            var key = line[..eq].Trim();
            var value = line[(eq + 1)..].Trim();
            if (value.Length >= 2 && (value[0] == '"' && value[^1] == '"' || value[0] == '\'' && value[^1] == '\''))
                value = value[1..^1];
            result[key] = value;
        }
        return result;
    }
}
