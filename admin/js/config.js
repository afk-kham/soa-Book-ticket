// Cấu hình DUY NHẤT về địa chỉ các service. Sửa ở đây nếu đổi cổng/máy chạy — không sửa rải rác trong từng trang.
// Host lấy theo địa chỉ đang mở trang (localhost khi chạy cùng máy; IP máy chủ khi demo trong mạng LAN).
window.SOA = (function () {
  var host = location.hostname || "localhost";
  function s(key, name, port, owner, ping) { return { key: key, name: name, port: port, owner: owner, ping: ping, base: "http://" + host + ":" + port }; }
  return {
    services: {
      movie:        s("movie", "Movie", 5001, "TV1", "/api/movies"),
      showtime:     s("showtime", "Showtime", 5002, "TV2", "/api/showtimes"),
      user:         s("user", "User", 5003, "TV3", "/api/users"),
      booking:      s("booking", "Booking", 5004, "TV4", "/health"),
      payment:      s("payment", "Payment", 5005, "TV5", "/api/payment"),
      notification: s("notification", "Notification", 5006, "TV6", "/api/notify/logs")
    },
    paymentMethods: ["MOMO", "VNPAY", "CASH"]
  };
})();
