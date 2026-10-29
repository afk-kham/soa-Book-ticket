# Review — Cải tiến poster, thanh toán, đơn chờ, vé điện tử và lịch chiếu

Tài liệu này ghi lại những gì đã sửa theo 6 góp ý về bản thử nghiệm, lý do chọn cách làm, cách kiểm tra và những điểm còn hạn chế.

| # | Góp ý | Trạng thái |
|---|---|---|
| 1 | Giao diện chưa có file poster | Đã sửa |
| 2 | Thanh toán chuyển khoản chưa hoạt động rõ ràng | Đã sửa (mô phỏng, chưa nối cổng thật) |
| 3 | Mỗi phim chỉ có 1 suất chiếu, dữ liệu không cập nhật | Đã sửa |
| 4 | Giao diện hiện từ kỹ thuật (SQL, cổng…) | Đã sửa (Client + Admin) |
| 5 | Đơn "Chờ thanh toán" không có cách xử lý | Đã sửa |
| 6 | Đơn đã thanh toán không xem được vé | Đã sửa |

---

## 1. Poster phim

**Trước:** CSDL lưu `poster1.jpg` … `poster5.jpg` nhưng không có file ảnh nào. Client chỉ hiện ảnh khi `poster` là URL, còn lại dùng nền màu tự sinh.

**Đã làm**
- Thêm 5 poster vẽ bằng SVG trong `client/img/posters/` (Avengers: Endgame, Inception, Parasite, Mai, Coco), có tên phim, câu giới thiệu và nhãn độ tuổi (T13/T18/P). Đây là ảnh **tự thiết kế**, không dùng poster bản quyền.
- Client tìm ảnh theo thứ tự: `img/posters/poster1.jpg` → không có thì `poster1.svg` → không có nữa thì dùng nền màu như cũ. **Không phải sửa CSDL**: giá trị `poster1.jpg` giữ nguyên.
- Muốn dùng poster chính thức: chép file `poster1.jpg` (…) vào `client/img/posters/`, file `.jpg` sẽ được ưu tiên hơn `.svg`. Trường `poster` vẫn nhận URL đầy đủ như trước.
- Poster hiện ở trang chủ, nền mờ phía sau phần phim nổi bật, trang chi tiết, trang chọn ghế, trang thanh toán, vé điện tử, "Vé của tôi" và trang **Phim** của Admin.

## 2. Thanh toán chuyển khoản

**Trước:** chọn MoMo/VNPAY/Tại quầy rồi bấm một nút là đơn thành "Đã thanh toán" ngay. Người dùng không thấy mã QR, số tài khoản hay nội dung chuyển khoản nào.

**Đã làm:** tách thành một **trang thanh toán riêng** (`#/pay/{mã đơn}`), giống các ứng dụng đặt vé thật.

- **Chuyển khoản ngân hàng (VietQR):** mã QR theo chuẩn **VietQR/NAPAS 247**: app ngân hàng quét là tự điền người nhận, số tiền và nội dung. Bên cạnh có ngân hàng, số tài khoản, chủ tài khoản, số tiền và nội dung chuyển khoản `SOA000017` (chính là mã đặt vé); mỗi dòng có nút sao chép. Kèm 3 bước hướng dẫn.
- **Ví MoMo** và **VNPAY-QR:** khung QR riêng theo màu từng ví, có mã đơn hàng, số tiền và hướng dẫn.
- Có thể đổi phương thức ngay trên trang; trang nhớ lựa chọn lần trước.
- Bấm **"Tôi đã thanh toán"** → *Đang xác nhận giao dịch…* → Booking gọi Payment → sang vé điện tử. Nếu giao dịch thất bại, **ghế vẫn được giữ**, khách thử lại hoặc đổi phương thức.
- Bỏ "Tại quầy" khỏi trang khách: bản cũ đánh dấu *đã thanh toán* trong khi khách chưa trả đồng nào. Thanh toán tiền mặt chuyển sang Admin (nút **"Bán vé tại quầy"**), nơi nhân viên thu tiền thật.
- Payment Service nhận thêm phương thức `BANK_TRANSFER`.

**Cần lưu ý (trung thực về phạm vi)**
- Hệ thống **chưa nối cổng thanh toán thật**. Trang có ghi rõ *"Môi trường thử nghiệm… vui lòng không chuyển tiền thật"*; nút "Tôi đã thanh toán" **mô phỏng** việc ngân hàng xác nhận. Tắt dòng này bằng `PAYMENT_SANDBOX = false` trong `client/js/config.js`.
- Tài khoản nhận tiền trong `client/js/config.js` (`BANK_ACCOUNT`) là **tài khoản mẫu** `0000000000`. Muốn quét ra người nhận thật thì thay bằng tài khoản của rạp/nhóm.
- Khi triển khai thật: chuyển khoản thường được xác nhận tự động qua webhook của dịch vụ đối soát (SePay, Casso…), MoMo/VNPAY qua IPN của cổng. Khi đó chỉ cần webhook gọi `POST /api/booking/{id}/pay` thay cho nút bấm.
- Mã QR MoMo/VNPAY chỉ mang thông tin đơn hàng (không phải QR do cổng cấp), nên quét bằng app MoMo sẽ báo không hợp lệ. Mã VietQR thì đúng chuẩn.
- Mã QR được sinh **ngay trên trình duyệt** (`client/js/qr.js`, không dùng thư viện ngoài, không cần Internet). Bộ sinh mã đã qua các kiểm tra: mã sửa lỗi Reed–Solomon khớp ví dụ chuẩn "HELLO WORLD" 1-M, CRC16 khớp vector chuẩn, và giải mã ngược ra đúng nội dung ở các phiên bản 1, 3, 7, 11. **Chưa quét thử bằng điện thoại thật**: nên quét một lần trước buổi demo.

## 3. Suất chiếu nhiều hơn và luôn cập nhật

**Trước:** 6 suất trong 3 ngày 10–12/10/2026, **đều đã qua** so với hôm nay (15/10). Client vẫn hiện và vẫn cho đặt các suất đó.

**Đã làm**
- **Lịch chiếu tự xếp** (`services/showtime/src/schedule.php`): mỗi lần có người xem lịch chiếu, Showtime kiểm tra 7 ngày tới; ngày nào **chưa có suất nào** thì tự xếp lịch: mỗi phim chiếu ở 3 rạp, 2 suất/rạp, 6 khung giờ 09:30–22:45, mỗi phim một phòng riêng nên không trùng phòng. Giá theo khung giờ và ngày: 75.000đ, trước 12h −10.000đ, từ 17h +10.000đ, thứ 7 và CN +15.000đ.
  - Kết quả hiện tại: **30 suất/ngày, 210 suất/7 ngày**, mỗi phim 38 suất sắp chiếu.
  - Không đụng suất đã có hoặc đã có người đặt; Admin xóa lẻ một suất thì suất đó không bị sinh lại. Phim mới thêm ở Admin sẽ tự có lịch cho các ngày tiếp theo.
  - Danh sách phim lấy qua API của Movie (đúng nguyên tắc SOA); Movie sập thì dùng các phim đã có lịch.
  - Có khóa trong CSDL nên hai yêu cầu cùng lúc không sinh lịch hai lần. Tắt bằng `AUTO_SCHEDULE_DAYS=0`.
- **Chỉ hiện suất chưa chiếu:** Showtime có thêm `?upcoming=1`; Client và form "Bán vé tại quầy" dùng tham số này. Booking **từ chối** đặt suất đã bắt đầu (`SHOWTIME_CLOSED`).
- **Cập nhật trực tiếp** (có chấm xanh "Cập nhật lúc …"):
  - Trang lịch chiếu tự tải lại mỗi 30 giây: suất vừa bắt đầu tự biến mất; mỗi suất hiện **"Còn N ghế"**, sắp hết thì đổi màu, hết thì ghi "Hết vé" và khóa nút. Số ghế lấy từ endpoint mới `GET /api/booking/availability`.
  - Sơ đồ ghế tự cập nhật mỗi 5 giây. Ghế khách đang chọn mà người khác vừa đặt thì tự bỏ chọn và báo cho khách.
  - Tab ngày ghi "Hôm nay", "Ngày mai", "Thứ bảy"…
- Đặt múi giờ `Asia/Ho_Chi_Minh` cho Showtime (PHP mặc định UTC, sẽ so "đã chiếu chưa" lệch 7 tiếng).

## 4. Bỏ từ kỹ thuật khỏi giao diện

**Client**
- Chân trang không còn "Client gọi Movie · Showtime · User · Booking…"; trang đăng nhập không còn "service độc lập, HTTP + JSON".
- Thông báo lỗi được viết lại theo mã lỗi. Ví dụ "Movie Service đang không hoạt động" thành *"Không tải được danh sách phim lúc này…"*, `PAYMENT_SERVICE_UNAVAILABLE` thành *"Cổng thanh toán đang tạm gián đoạn. Ghế của bạn vẫn được giữ…"*. Thông báo nào còn chứa từ như *Service, SQL, HTTP, JSON, movieId* thì thay bằng câu chung.
- Không còn hiện "Phim #3", "Suất #5"; mã đơn hiện dạng **SOA000017**.

**Admin**
- Bỏ khỏi giao diện: cổng (`:5001`…), tên CSDL (`movie_db · MySQL`…), công nghệ (Python, PHP…), mã thành viên (TV1…TV6), "băm BCrypt", "POST /api/login".
- Phụ đề mỗi trang viết theo nghiệp vụ, ví dụ trang Đặt vé: *"Đơn đặt vé của khách: giữ ghế, thanh toán, hủy và hết hạn giữ chỗ"*.
- Ô sức khỏe hệ thống thành **"Tình trạng hệ thống"**: Phim / Lịch chiếu / Tài khoản / Đặt vé / Thanh toán / Thông báo, mỗi ô ghi *Hoạt động / Gián đoạn* và thời gian phản hồi.
- Sơ đồ luồng: *Chọn suất → Chọn ghế → Giữ ghế → Thanh toán → Xuất vé → Gửi xác nhận* thay cho tên service.
- Phương thức và kết quả thanh toán có nhãn tiếng Việt ("Chuyển khoản ngân hàng", "Thành công"…).
- Thông tin kỹ thuật (cổng, CSDL) vẫn còn trong `admin/js/config.js` và README cho nhóm phát triển, chỉ không hiện lên màn hình.

## 5. Đơn "Chờ thanh toán"

**Trước:** đơn PENDING chỉ hiện nhãn vàng, không có nút nào và cũng không bao giờ tự hết hạn, nên ghế bị giữ vĩnh viễn.

**Hướng xử lý theo thực tế:** rạp giữ ghế trong một khoảng ngắn (CGV, Lotte, Galaxy giữ 5–10 phút), khách thanh toán hoặc hủy, quá hạn thì tự nhả ghế.

- **Giữ ghế 10 phút** (`HOLD_MINUTES` trong `.env` của Booking). Mỗi đơn PENDING có `expiresAt`.
- **Trang thanh toán** có đồng hồ đếm ngược và thanh tiến độ; dưới 1 phút chuyển màu đỏ. Trên điện thoại có thêm đồng hồ nhỏ ở đầu trang. Trang tự kiểm tra trạng thái mỗi 5 giây: hết hạn thì báo *"Đơn đã hết thời gian giữ ghế"* kèm nút **Chọn lại ghế**; đơn đã thanh toán ở nơi khác thì tự sang vé.
- **"Vé của tôi"**:
  - Đơn chờ được tô nổi, có *"Giữ ghế còn 08:46"* đếm từng giây, nút **Thanh toán** (quay lại trang thanh toán) và **Hủy** (bấm hai lần để tránh bấm nhầm).
  - Đầu trang nhắc *"Bạn có 1 đơn đang giữ ghế chờ thanh toán"*. Danh sách tự làm mới mỗi 20 giây.
- **Trang chọn ghế:** nếu khách đang giữ ghế cho chính suất đó thì có nhắc *"Bạn đang giữ ghế … — Tiếp tục thanh toán"*, tránh giữ trùng hai đơn.
- **Tự hủy:** Booking quét mỗi 30 giây và trước mỗi yêu cầu. Quá hạn → CANCELLED, ghế nhả ngay cho khách khác. Các đơn PENDING cũ trong CSDL (như đơn #3 từ 02/10) cũng tự được hủy theo quy tắc này.
- **API mới của Booking**:
  - `POST /api/booking` với `"payNow": false`: chỉ giữ ghế.
  - `POST /api/booking/{id}/pay`: thanh toán. Thất bại vẫn giữ ghế; Payment tạm sập cũng giữ ghế.
  - `POST /api/booking/{id}/cancel`: hủy, nhả ghế. Vé đã thanh toán không hủy online được (409).
  - Chỉ chủ đơn mới thanh toán/hủy được đơn của mình (403 với người khác).
  - Luồng cũ "đặt và trả ngay" **giữ nguyên** cho Admin và test cũ.

## 6. Xem vé đã thanh toán — vé điện tử

**Trước:** chỉ thấy thông tin một lần ngay sau khi đặt (lưu tạm trong trình duyệt); vào lại "Vé của tôi" thì không mở được vé nào.

**Đã làm:** trang **vé điện tử** `#/ticket/{mã đơn}`, mở được bất cứ lúc nào từ nút **"Xem vé →"** trong "Vé của tôi".
- Vé gồm: poster, phim, rạp, phòng, suất chiếu, ghế (số vé), tổng tiền, phương thức thanh toán, thời điểm đặt, **mã đặt vé** và **mã QR soát vé** kèm dòng *"Đưa mã này cho nhân viên soát vé tại rạp"*.
- Suất đã chiếu thì vé ghi *"Suất chiếu đã diễn ra"*.
- Nút **In / lưu vé**: bản in chỉ có tấm vé, nền trắng, có thể lưu thành PDF.
- Ngay sau khi trả tiền, vé hiện *"Thanh toán thành công! Email xác nhận đã được gửi…"*.
- Vé chỉ mở được với tài khoản đã đặt. Đơn chưa trả thì chuyển sang trang thanh toán; đơn đã hủy thì báo hết hạn và mời đặt lại.

---

## Lỗi phát hiện thêm khi chạy thử và đã sửa

1. **Hạn giữ ghế lệch 7 tiếng.** MySQL chạy trong Docker theo **giờ UTC**, còn giờ chiếu và trình duyệt theo giờ Việt Nam. Nếu để CSDL tự điền `created_at`, khách vừa giữ ghế đã thấy "hết hạn". Booking giờ ghi `created_at` và so hạn theo đồng hồ của chính nó.
2. **Đặt vé chậm 4 giây.** Booking gọi `localhost`; trên Windows .NET thử IPv6 (`::1`) trước, trong khi Movie, Showtime và Payment chỉ nghe IPv4, nên mỗi lời gọi chờ khoảng 1 giây. Booking giờ ưu tiên IPv4: thời gian giữ ghế giảm từ **4,08 giây xuống ~0,05 giây**. Thanh toán và luồng đặt vé cũ cũng nhanh hơn tương ứng.

## Kiểm tra đã chạy

Chạy thật cả 6 service cùng MySQL và MongoDB (Docker) trên máy phát triển.

| Kiểm tra | Kết quả |
|---|---|
| `python tests/integration/run_tests.py` | **54 đạt / 0 lỗi** (thêm 13 kiểm tra mới ở nhóm [7]: giữ ghế, `expiresAt`, availability, 403, thanh toán thất bại vẫn giữ ghế, chuyển khoản → PAID + thông báo, 409 trả lại, 409 hủy vé đã trả, hủy nhả ghế, 409 trả đơn đã hủy, `SHOWTIME_CLOSED`, `?upcoming=1`) |
| `node --test` (Payment) | **9 đạt / 0 lỗi** (thêm test `BANK_TRANSFER`) |
| Hết hạn giữ ghế | Lùi `created_at` một đơn giữ ghế 11 phút → đơn tự CANCELLED, ghế F9/F10 được nhả |
| Giao diện | Chụp bằng Chrome headless toàn bộ luồng: trang chủ → lịch chiếu → chọn ghế → thanh toán (VietQR, MoMo) → Vé của tôi → thanh toán → vé điện tử; Admin Tổng quan/Đặt vé/Phim; giao diện điện thoại 390px. Không có lỗi JavaScript trong console. |
| Build | `dotnet build` Booking: 0 cảnh báo; `php -l` các file Showtime: không lỗi |

Thay đổi trong bộ test: test cũ đặt vé vào `shows[0]` (suất 10/10 đã qua). Vì Booking giờ từ chối suất đã chiếu, test đổi sang chọn **suất sắp chiếu đầu tiên**; kịch bản `--expect-down` cũng vậy.

## Hạn chế còn lại / việc nên làm tiếp

- **Cổng thanh toán thật**: chưa có (xem mục 2). Đây là phần mô phỏng có chủ đích của bản thử nghiệm.
- **Xác thực:** thanh toán/hủy vẫn xác định chủ đơn bằng `username` trong body (giống luồng đặt vé hiện có). Cuối kỳ nên lấy từ JWT như kế hoạch trong `API_CONTRACT.md`.
- **Trùng thời điểm:** nếu khách bấm thanh toán đúng lúc hạn giữ ghế vừa hết và người khác đã lấy ghế, Booking ghi log *"cần hoàn tiền thủ công"*. Trường hợp rất hiếm; bản thật cần quy trình hoàn tiền.
- **Sơ đồ phòng** vẫn dùng chung 6×10 cho mọi phòng (Showtime chưa lưu kích thước phòng), nên "Còn N ghế" tính trên 60 ghế.
- **Dữ liệu thử:** trong lúc kiểm tra đã tạo thêm vài đơn của `user1` (đã thanh toán hoặc đã hủy) và tài khoản `it_<số>` do bộ test tích hợp sinh ra (vốn có từ trước). Muốn sạch thì chạy lại `scripts/init-db`.

## Danh sách file thay đổi

| Phần | File |
|---|---|
| Client | `client/index.html`, `client/js/app.js` (viết lại), `client/js/config.js`, `client/js/qr.js` (mới), `client/css/client.css`, `client/img/posters/poster1–5.svg` (mới) |
| Admin | `admin/index.html`, `admin/js/common.js`, `admin/js/config.js`, `admin/css/admin.css`, `admin/pages/*.html` |
| Booking | `Program.cs`, `BookingStore.cs`, `Models.cs`, `Config.cs`, `Upstream.cs`, `.env.example`, `README.md` |
| Showtime | `router.php`, `src/schedule.php` (mới), `src/db.php`, `src/config.php`, `.env.example`, `README.md` |
| Payment | `payment_service.js`, `test_payment_service.js` |
| Khác | `API_CONTRACT.md`, `CHANGELOG.md`, `database/showtime/seed.sql` (chỉ thêm chú thích), `tests/integration/run_tests.py` |

Không đổi schema CSDL nào; không đổi dữ liệu mẫu. Biến môi trường mới đều có giá trị mặc định, nên file `.env` hiện có của mọi người vẫn chạy được.
