-- Dữ liệu DEMO để test thủ công (lọc, sắp xếp, sửa, xóa). KHÔNG phải seed chính thức: id từ 101, không đụng id cũ.
-- Idempotent: INSERT OR IGNORE theo id. Nạp bằng: python -m app.db.init_db --demo
INSERT OR IGNORE INTO notification_logs (id, booking_id, username, channel, message, sent_at) VALUES
 (101, 2,  'user1',  'SMS',   'Đặt vé thành công cho đơn #2',          '2026-10-02T09:15:00Z'),
 (102, 3,  'user2',  'EMAIL', 'Đặt vé thành công cho đơn #3',          '2026-10-03T14:30:00Z'),
 (103, 4,  'user2',  'SMS',   'Nhắc suất chiếu 19:00 hôm nay',         '2026-10-04T08:00:00Z'),
 (104, 5,  'Alice',  'EMAIL', 'Đặt vé thành công cho đơn #5',          '2026-10-05T20:45:00Z'),
 (105, 5,  'Alice',  'SMS',   'Thanh toán đơn #5 đã được xác nhận',    '2026-10-05T20:46:10Z'),
 (106, 12, 'bob',    'EMAIL', 'Đặt vé thành công cho đơn #12',         '2026-10-06T11:20:00Z');
