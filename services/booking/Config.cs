namespace BookingService;

/// <summary>Cấu hình từ biến môi trường hoặc file .env (KHÔNG hard-code, KHÔNG commit .env).</summary>
public static class Config
{
    static Config() => LoadDotEnv(".env");

    static void LoadDotEnv(string path)
    {
        if (!File.Exists(path)) return;
        foreach (var raw in File.ReadAllLines(path))
        {
            var line = raw.Trim();
            if (line.Length == 0 || line[0] == '#' || !line.Contains('=')) continue;
            var i = line.IndexOf('=');
            var key = line[..i].Trim();
            var val = line[(i + 1)..].Trim().Trim('"', '\'');
            if (Environment.GetEnvironmentVariable(key) is null) Environment.SetEnvironmentVariable(key, val);
        }
    }

    public static string Get(string key, string def) =>
        string.IsNullOrWhiteSpace(Environment.GetEnvironmentVariable(key)) ? def : Environment.GetEnvironmentVariable(key)!;

    public static int Port => int.Parse(Get("PORT", "5004"));

    // Windows: http://localhost:5004/ (không cần quyền Administrator). Linux/macOS: http://*:5004/ (nghe mọi giao diện).
    public static string Prefix => Get("BOOKING_PREFIX",
        OperatingSystem.IsWindows() ? $"http://localhost:{Port}/" : $"http://*:{Port}/");

    public static string DbConnectionString =>
        $"Server={Get("DB_HOST", "localhost")};Port={Get("DB_PORT", "3306")};Database={Get("DB_NAME", "booking_db")};" +
        $"User ID={Get("DB_USER", "root")};Password={Get("DB_PASSWORD", "")};CharSet=utf8mb4";

    /// <summary>mysql (mặc định) | memory (CHỈ dùng khi test, không cần DB).</summary>
    public static string Store => Get("BOOKING_STORE", "mysql").ToLowerInvariant();

    // Địa chỉ các service mà Booking gọi qua HTTP (Booking không bao giờ đọc DB của họ)
    public static string UserUrl => Get("USER_SERVICE_URL", "http://localhost:5003").TrimEnd('/');
    public static string MovieUrl => Get("MOVIE_SERVICE_URL", "http://localhost:5001").TrimEnd('/');
    public static string ShowtimeUrl => Get("SHOWTIME_SERVICE_URL", "http://localhost:5002").TrimEnd('/');
    public static string PaymentUrl => Get("PAYMENT_SERVICE_URL", "http://localhost:5005").TrimEnd('/');
    public static string NotificationUrl => Get("NOTIFICATION_SERVICE_URL", "http://localhost:5006").TrimEnd('/');

    public static int UpstreamTimeoutSeconds => int.Parse(Get("UPSTREAM_TIMEOUT_SECONDS", "5"));
}
