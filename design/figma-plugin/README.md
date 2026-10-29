# SOA Cinema Builder (plugin Figma)

Plugin phát triển dùng để hoàn thiện file Figma **SOA Cinema — Giao diện chính thức**
(https://www.figma.com/design/aGFb4cT9qZhAvbx0e20uHP). Plugin chạy ngay trong Figma Desktop của bạn,
nên **không tốn lượt gọi Figma MCP** (gói Starter chỉ có 20 lượt mỗi tháng).

| Lệnh | Việc plugin làm |
|---|---|
| **1. Client — prototype + hoạt ảnh** | Nối luồng 6 màn hình Client: Trang chủ → Chi tiết phim → Đăng nhập → Chọn ghế → Kết quả → Vé của tôi. Đi tiếp thì màn hình đẩy sang trái, quay lại thì đẩy sang phải, đặt vé thành công thì trượt lên. Ghế, tab ngày, bộ lọc thể loại và phương thức thanh toán đổi trạng thái khi bấm (Smart Animate). Sửa luôn chữ poster bị ngắt giữa từ ở màn Kết quả. |
| **2. Admin — dựng 5 màn hình + prototype** | Dựng các màn hình A01 Tổng quan, A02 Quản lý đặt vé, A03 Đặt vé có ngăn chi tiết, A04 Quản lý phim, A05 Phim có form thêm phim. Menu bên chuyển trang bằng hiệu ứng mờ dần. Bấm một đơn thì ngăn chi tiết trượt vào từ phải; bấm "+ Thêm phim" thì form hiện lên (Smart Animate). |

## Cách chạy (khoảng 2 phút)
1. Mở **Figma Desktop**. Plugin phát triển không chạy được trên trình duyệt.
2. Mở file *SOA Cinema — Giao diện chính thức*.
3. Vào menu **Plugins → Development → Import plugin from manifest…** rồi chọn file `manifest.json` trong thư mục này.
4. Chạy **Plugins → Development → SOA Cinema Builder → 1. Client — prototype + hoạt ảnh**.
5. Chạy tiếp **… → 2. Admin — dựng 5 màn hình + prototype**. Chạy lại lệnh này nhiều lần cũng an toàn: plugin xóa các màn hình A0x cũ trước khi dựng lại.
6. Xem thử: chọn trang 📱 Client hoặc 🛠 Admin, rồi bấm nút **▶ Present** (luồng bắt đầu từ Trang chủ hoặc Tổng quan).

Khi chạy xong, góc dưới màn hình hiện thông báo `✅ Xong: N tương tác`. Nếu có dòng `⚠ … lỗi`, mở
**Plugins → Development → Show/Hide console** để xem chi tiết rồi gửi lại cho người hỗ trợ.

## Lưu ý
- Các node ID trong `code.js` là của đúng file Figma ở trên. Chạy trên file khác sẽ báo lỗi `Thiếu component …`.
- Hoạt ảnh ngăn chi tiết và form dùng Smart Animate. Hai màn hình trước và sau có cùng tên lớp
  (`Drawer`, `Scrim`, `Modal`); chỉ vị trí và độ mờ khác nhau. Nếu đổi tên các lớp này, hoạt ảnh sẽ mất.
