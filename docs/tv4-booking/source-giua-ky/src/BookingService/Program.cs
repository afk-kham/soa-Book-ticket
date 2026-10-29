using System.Net;
using System.Text;
using BookingService.Config;
using BookingService.Data;
using BookingService.Http;
using BookingService.Services;

namespace BookingService;

public static class Program
{
    public static async Task<int> Main()
    {
        Console.OutputEncoding = Encoding.UTF8; // hiển thị tiếng Việt trên console Windows

        AppConfig config;
        try
        {
            config = AppConfig.Load();
        }
        catch (InvalidOperationException ex)
        {
            Console.Error.WriteLine("Cấu hình sai: " + ex.Message);
            return 1;
        }

        var db = new Database(config);
        Console.WriteLine("=== Booking Service (TV4 - C# HttpListener + ADO.NET) ===");
        Console.WriteLine($"Cấu hình : {config.EnvFile ?? "(không có file .env, dùng biến môi trường / mặc định)"}");
        Console.WriteLine($"CSDL     : {db.Description}");

        // Kiểm tra kết nối CSDL trước khi nhận request (thử lại vài lần vì Docker MySQL khởi động chậm).
        if (!await WaitForDatabaseAsync(db))
            return 1;

        var manager = new BookingManager(new BookingRepository(db));
        var server = new ApiServer(config, manager);

        using var cts = new CancellationTokenSource();
        Console.CancelKeyPress += (_, e) =>
        {
            e.Cancel = true; // để chương trình tự dừng gọn gàng
            cts.Cancel();
        };

        try
        {
            server.Start();
        }
        catch (HttpListenerException ex)
        {
            Console.Error.WriteLine($"Không mở được cổng {config.Port}: {ex.Message}");
            Console.Error.WriteLine("- Cổng đang bị chương trình khác dùng: tắt chương trình đó hoặc đổi PORT trong .env.");
            Console.Error.WriteLine("- Dùng prefix http://+:PORT/ trên Windows cần chạy 1 lần (quyền Admin):");
            Console.Error.WriteLine($"    netsh http add urlacl url=http://+:{config.Port}/ user=Everyone");
            return 1;
        }

        foreach (var prefix in config.ListenPrefixes)
            Console.WriteLine($"Lắng nghe: {prefix}  (API: {prefix}api/booking)");
        Console.WriteLine("Nhấn Ctrl+C để dừng.");
        await server.RunAsync(cts.Token);

        Console.WriteLine("Booking Service đã dừng.");
        return 0;
    }

    private static async Task<bool> WaitForDatabaseAsync(Database db)
    {
        const int attempts = 5;
        for (var i = 1; i <= attempts; i++)
        {
            try
            {
                var version = await db.GetServerVersionAsync();
                Console.WriteLine($"Kết nối CSDL thành công ({db.Dialect.Name} {version}).");
                return true;
            }
            catch (Exception ex)
            {
                Console.WriteLine($"Lần {i}/{attempts}: chưa kết nối được CSDL - {ex.Message}");
                if (i < attempts) await Task.Delay(TimeSpan.FromSeconds(2));
            }
        }

        Console.Error.WriteLine("Không kết nối được CSDL. Kiểm tra lại:");
        Console.Error.WriteLine("  1) MySQL/SQL Server đã chạy chưa (docker compose up -d)?");
        Console.Error.WriteLine("  2) Đã chạy db/schema.sql và db/seed.sql chưa?");
        Console.Error.WriteLine("  3) DB_HOST, DB_PORT, DB_USER, DB_PASSWORD trong file .env có đúng không?");
        return false;
    }
}
