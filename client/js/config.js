// Client chỉ gọi các service công khai: Movie, Showtime, User, Booking. Việc thanh toán/thông báo do Booking điều phối.
(function () {
  var host = location.hostname || "localhost";
  window.API = { movie: "http://" + host + ":5001", showtime: "http://" + host + ":5002", user: "http://" + host + ":5003", booking: "http://" + host + ":5004" };
  // Sơ đồ phòng chiếu dùng chung cho mọi phòng (Showtime chưa lưu kích thước phòng). Ghế dạng <hàng><số>: A1..F10.
  window.SEAT_MAP = { rows: "ABCDEF", cols: 10, aisleAfter: [5], maxSeats: 10 };
  window.PAYMENT_METHODS = [
    { value: "MOMO", label: "Ví MoMo", hint: "Thanh toán qua ví điện tử" },
    { value: "VNPAY", label: "VNPAY", hint: "Thẻ ATM / QR ngân hàng" },
    { value: "CASH", label: "Tại quầy", hint: "Trả tiền mặt khi nhận vé" }
  ];
})();
