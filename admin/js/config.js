// Cấu hình DUY NHẤT về địa chỉ các service. Sửa ở đây nếu đổi cổng/máy chạy — không sửa rải rác trong từng trang.
// Host lấy theo địa chỉ đang mở trang (localhost khi chạy cùng máy; IP máy chủ khi demo trong mạng LAN).
window.SOA = (function () {
  var host = location.hostname || "localhost";
  // label: tên hiển thị trên giao diện (không đưa cổng/CSDL/công nghệ lên màn hình quản trị — các thông tin đó ở README).
  function s(key, name, port, owner, ping, tech, db, label) { return { key: key, name: name, port: port, owner: owner, ping: ping, tech: tech, db: db, label: label, base: "http://" + host + ":" + port }; }
  return {
    services: {
      movie:        s("movie", "Movie", 5001, "TV1", "/api/movies", "Python", "movie_db · MySQL", "Phim"),
      showtime:     s("showtime", "Showtime", 5002, "TV2", "/api/showtimes", "PHP", "showtime_db · MySQL", "Lịch chiếu"),
      user:         s("user", "User", 5003, "TV3", "/api/users", "Java", "user_db · MySQL", "Tài khoản"),
      booking:      s("booking", "Booking", 5004, "TV4", "/health", "C# .NET 8", "booking_db · MySQL", "Đặt vé"),
      payment:      s("payment", "Payment", 5005, "TV5", "/api/payment", "Node.js", "payment_db · MongoDB", "Thanh toán"),
      notification: s("notification", "Notification", 5006, "TV6", "/api/notify/logs", "Go", "notification_db · MySQL", "Thông báo")
    },
    paymentMethods: [{value: "CASH", label: "Tiền mặt tại quầy"}, {value: "BANK_TRANSFER", label: "Chuyển khoản ngân hàng"}, {value: "MOMO", label: "Ví MoMo"}, {value: "VNPAY", label: "VNPAY-QR"}],
    // Trang đặt vé của khách (dùng để mở trang và lấy ảnh poster trong img/posters)
    clientBase: "http://" + host + ":8080"
  };
})();
