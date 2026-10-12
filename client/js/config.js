// Client chỉ gọi các service công khai: Movie, Showtime, User, Booking. Việc thanh toán/thông báo do Booking điều phối.
(function () {
  var host = location.hostname || "localhost";
  window.API = { movie: "http://" + host + ":5001", showtime: "http://" + host + ":5002", user: "http://" + host + ":5003", booking: "http://" + host + ":5004" };
})();
