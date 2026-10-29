# Hợp đồng API Notification giữa kỳ

Base URL mặc định: `http://localhost:5006`. API công khai, REST/JSON, không cần JWT/X-Internal-Key. Không kiểm tra Booking hoặc gọi service khác.

Mọi response có body dùng `application/json; charset=utf-8`.
Success: `{"status":"success","data":...}`. Error: `{"status":"error","message":"..."}`; không lộ lỗi DB chi tiết.

## POST /api/notify

```json
{"username":"user1","bookingId":3,"channel":"EMAIL"}
```

Body phải là đúng một JSON object UTF-8, tối đa 16 KiB. Không nhận rỗng/null/array/JSON lỗi/trailing JSON/trường lạ (kể cả message). bookingId là số nguyên 1–2147483647, trong phạm vi INT MySQL. username trim, 1–50 ký tự Unicode. channel trim và uppercase, chỉ EMAIL/SMS. Nội dung do service soạn.

200 chỉ sau khi sender giả lập và INSERT thành công:

```json
{"status":"success","data":{"notificationId":2,"bookingId":3,"username":"user1","channel":"EMAIL","deliveryStatus":"SIMULATED","message":"Đặt vé thành công cho đơn #3","sentAt":"2026-10-03T05:00:00Z"}}
```

notificationId do MySQL cấp (không bảo đảm ID cụ thể như ví dụ). sentAt là thời điểm thực, UTC RFC3339 độ chính xác giây. deliveryStatus chỉ là DTO, không có cột tương ứng. EMAIL/SMS không gửi thật.

## GET /api/notify/logs

200 đọc MySQL, `ORDER BY sent_at DESC, id DESC`:

```json
{"status":"success","data":[{"id":1,"bookingId":1,"username":"user1","channel":"EMAIL","message":"Đặt vé thành công cho đơn #1","sentAt":"2026-01-01T00:00:00Z"}]}
```

Không có dữ liệu: `{"status":"success","data":[]}`. Không phân trang/lọc server; admin lọc dữ liệu đã tải. Không có endpoint sửa/xóa log.

## Mã lỗi, routing và CORS

| Mã | Tình huống |
|---|---|
| 400 | JSON hoặc dữ liệu không hợp lệ |
| 413 | Body quá 16384 byte |
| 404 | URL không tồn tại, kể cả đường dẫn có thêm slash/suffix |
| 405 | Sai method; Allow là POST, OPTIONS hoặc GET, OPTIONS |
| 500 | Sender hoặc MySQL lỗi |

Ví dụ `{"status":"error","message":"Không thể lưu nhật ký thông báo"}`.

OPTIONS trên đúng hai URL trả 204 không body, trước kiểm tra method. OPTIONS URL lạ trả JSON 404. Headers trên cả success và lỗi: Access-Control-Allow-Origin `*`, Allow-Methods `GET, POST, OPTIONS`, Allow-Headers `Content-Type, Authorization`. Không Allow-Credentials. Chưa thêm endpoint healthz.

## Lưu ý TV4 tích hợp cuối kỳ

Booking gọi POST sau khi đơn PAID, dùng timeout và không hủy đơn PAID khi Notification lỗi. Đây là quy ước tích hợp dự kiến, chưa triển khai trong workspace này. Body hiện chỉ cần username/bookingId/channel; không gửi message tùy ý. Console và MySQL không trong cùng transaction. Retry POST hiện có thể tạo trùng log; không tự retry vô hạn. X-Internal-Key/JWT/idempotency sẽ thay đổi theo hợp đồng cuối kỳ, chưa bật ở giữa kỳ.
