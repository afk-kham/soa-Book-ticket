-- Dùng khi Booking chạy SQL Server (Windows)
IF DB_ID('booking_db') IS NULL CREATE DATABASE booking_db;
GO
USE booking_db;
GO
IF OBJECT_ID('bookings') IS NOT NULL DROP TABLE bookings;
CREATE TABLE bookings (
  id INT IDENTITY(1,1) PRIMARY KEY,
  movie_id INT NOT NULL,
  showtime_id INT NOT NULL,
  username NVARCHAR(50) NOT NULL,
  seats NVARCHAR(100) NOT NULL,
  total_price INT NOT NULL,
  status NVARCHAR(10) NOT NULL DEFAULT 'PENDING',
  created_at DATETIME2 DEFAULT SYSDATETIME()
);
GO
SET IDENTITY_INSERT bookings ON;
INSERT INTO bookings (id, movie_id, showtime_id, username, seats, total_price, status, created_at) VALUES
(1, 1, 1, N'user1', N'A1,A2', 180000, N'PAID',      '2026-10-01 10:00:00'),
(2, 2, 3, N'user2', N'B5',     85000, N'CANCELLED', '2026-10-01 11:00:00'),
(3, 4, 5, N'user1', N'C3,C4', 180000, N'PENDING',   '2026-10-02 09:30:00');
SET IDENTITY_INSERT bookings OFF;
GO
