// Cấu hình DUY NHẤT về địa chỉ các service. Sửa ở đây nếu đổi cổng/máy chạy — không sửa rải rác trong từng trang.
// Host lấy theo địa chỉ đang mở trang (localhost khi chạy cùng máy; IP máy chủ khi demo trong mạng LAN).
window.SOA = (function () {
  var host = location.hostname || "localhost";
  function s(key, name, port, owner, ping, tech, db) { return { key: key, name: name, port: port, owner: owner, ping: ping, tech: tech, db: db, base: "http://" + host + ":" + port }; }
  return {
    services: {
      movie:        s("movie", "Movie", 5001, "TV1", "/api/movies", "Python", "movie_db · MySQL"),
      showtime:     s("showtime", "Showtime", 5002, "TV2", "/api/showtimes", "PHP", "showtime_db · MySQL"),
      user:         s("user", "User", 5003, "TV3", "/api/users", "Java", "user_db · MySQL"),
      booking:      s("booking", "Booking", 5004, "TV4", "/health", "C# .NET 8", "booking_db · MySQL"),
      payment:      s("payment", "Payment", 5005, "TV5", "/api/payment", "Node.js", "payment_db · MongoDB"),
      notification: s("notification", "Notification", 5006, "TV6", "/api/notify/logs", "Go", "notification_db · MySQL")
    },
    paymentMethods: ["MOMO", "VNPAY", "CASH"]
  };
})();
