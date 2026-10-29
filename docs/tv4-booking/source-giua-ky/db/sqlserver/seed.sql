-- =====================================================================
-- Booking Service (TV4 - C#) - P1: Dữ liệu mẫu cho SQL Server
-- Chạy SAU schema.sql. Khớp Phụ lục A.4 (id 1-3 giữ nguyên giá trị).
-- MERGE: dòng chưa có thì thêm, dòng đã có thì đưa về giá trị chuẩn.
-- =====================================================================

USE booking_db;
GO

SET IDENTITY_INSERT dbo.bookings ON;

MERGE dbo.bookings AS t
USING (VALUES
    (1, 1, 1, N'user1', N'A1,A2', 180000, N'PAID',      CAST('2026-10-01T10:00:00' AS DATETIME2(0))),
    (2, 2, 3, N'user2', N'B5',     85000, N'CANCELLED', CAST('2026-10-01T11:00:00' AS DATETIME2(0))),
    (3, 4, 5, N'user1', N'C3,C4', 180000, N'PENDING',   CAST('2026-10-02T09:30:00' AS DATETIME2(0)))
) AS s (id, movie_id, showtime_id, username, seats, total_price, [status], created_at)
ON t.id = s.id
WHEN MATCHED THEN UPDATE SET
    t.movie_id = s.movie_id, t.showtime_id = s.showtime_id, t.username = s.username,
    t.seats = s.seats, t.total_price = s.total_price, t.[status] = s.[status], t.created_at = s.created_at
WHEN NOT MATCHED THEN
    INSERT (id, movie_id, showtime_id, username, seats, total_price, [status], created_at)
    VALUES (s.id, s.movie_id, s.showtime_id, s.username, s.seats, s.total_price, s.[status], s.created_at);

SET IDENTITY_INSERT dbo.bookings OFF;
GO

SELECT id, movie_id, showtime_id, username, seats, total_price, [status], created_at
FROM dbo.bookings ORDER BY id;
GO
