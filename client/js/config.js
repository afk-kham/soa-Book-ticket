// Client chỉ gọi các service công khai: Movie, Showtime, User, Booking. Việc thanh toán/thông báo do Booking điều phối.
(function () {
  var host = location.hostname || "localhost";
  window.API = { movie: "http://" + host + ":5001", showtime: "http://" + host + ":5002", user: "http://" + host + ":5003", booking: "http://" + host + ":5004" };
  // Sơ đồ phòng chiếu dùng chung cho mọi phòng (Showtime chưa lưu kích thước phòng). Ghế dạng <hàng><số>: A1..F10.
  window.SEAT_MAP = { rows: "ABCDEF", cols: 10, aisleAfter: [5], maxSeats: 10 };
  // Ảnh poster: trường "poster" của phim là URL, hoặc tên file trong thư mục này (thiếu .jpg/.png thì thử bản .svg cùng tên).
  window.POSTER_DIR = "img/posters/";
  window.PAYMENT_METHODS = [
    { value: "BANK_TRANSFER", label: "Chuyển khoản ngân hàng", hint: "Quét mã VietQR bằng app ngân hàng bất kỳ", logo: "VietQR" },
    { value: "MOMO", label: "Ví MoMo", hint: "Quét mã bằng ứng dụng MoMo", logo: "MoMo" },
    { value: "VNPAY", label: "VNPAY-QR", hint: "Quét mã bằng app ngân hàng hoặc ví VNPAY", logo: "VNPAY" }
  ];
  // Tài khoản nhận chuyển khoản (mã VietQR sinh từ đây). ĐÂY LÀ TÀI KHOẢN MẪU — thay bằng tài khoản thật của rạp khi triển khai.
  // bin: mã ngân hàng theo NAPAS (970436 = Vietcombank, 970422 = MB, 970407 = Techcombank, 970415 = VietinBank...).
  window.BANK_ACCOUNT = { bin: "970436", bank: "Vietcombank", account: "0000000000", holder: "CONG TY SOA CINEMA" };
  // true: môi trường thử nghiệm — chưa nối cổng thanh toán thật, người dùng bấm "Tôi đã thanh toán" để mô phỏng xác nhận.
  window.PAYMENT_SANDBOX = true;
})();
