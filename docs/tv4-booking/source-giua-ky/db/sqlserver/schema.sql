-- =====================================================================
-- Booking Service (TV4 - C#) - P1: Lược đồ booking_db cho SQL Server
-- Chạy bằng SSMS hoặc: sqlcmd -S localhost -E -i schema.sql
-- Chạy lặp lại được (không DROP bảng).
-- movie_id, showtime_id, username là khóa ngoại LOGIC, không tạo FOREIGN KEY.
-- =====================================================================

IF DB_ID(N'booking_db') IS NULL
    CREATE DATABASE booking_db;
GO

USE booking_db;
GO

IF OBJECT_ID(N'dbo.bookings', N'U') IS NULL
BEGIN
    CREATE TABLE dbo.bookings (
        id          INT IDENTITY(1,1) NOT NULL CONSTRAINT PK_bookings PRIMARY KEY,
        movie_id    INT           NOT NULL,   -- FK logic -> Movie.movies.id
        showtime_id INT           NOT NULL,   -- FK logic -> Showtime.showtimes.id
        username    NVARCHAR(50)  NOT NULL,   -- FK logic -> User.users.username
        seats       NVARCHAR(100) NOT NULL,   -- ví dụ 'A1,A2'
        total_price INT           NOT NULL,
        [status]    NVARCHAR(10)  NOT NULL CONSTRAINT DF_bookings_status DEFAULT N'PENDING',
        created_at  DATETIME2(0)  NOT NULL CONSTRAINT DF_bookings_created_at DEFAULT SYSDATETIME(),
        CONSTRAINT CK_bookings_status CHECK ([status] IN (N'PENDING', N'PAID', N'CANCELLED')),
        CONSTRAINT CK_bookings_total  CHECK (total_price >= 0)
    );

    CREATE INDEX IX_bookings_showtime_status ON dbo.bookings (showtime_id, [status]);
    CREATE INDEX IX_bookings_username        ON dbo.bookings (username);
END
GO
