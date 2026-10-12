/* Client đặt vé — HTML/CSS/JS thuần, gọi trực tiếp các service qua REST (envelope {"status","data"}). */
(function () {
  var $ = function (s) { return document.querySelector(s); };
  var esc = function (v) { return String(v == null ? "" : v).replace(/[&<>"']/g, function (c) { return ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]; }); };
  var money = function (n) { return Number(n || 0).toLocaleString("vi-VN") + " đ"; };
  var NAMES = { movie: "Movie", showtime: "Showtime", user: "User", booking: "Booking" };
  var user = null; try { user = JSON.parse(sessionStorage.getItem("soa.user") || "null"); } catch (e) {}
  var ROWS = "ABCDE", COLS = 8;

  async function call(svc, method, path, body) {
    var res, json;
    try { res = await fetch(API[svc] + path, { method: method, headers: body ? { "Content-Type": "application/json" } : {}, body: body ? JSON.stringify(body) : undefined }); }
    catch (e) { throw new Error(NAMES[svc] + " Service đang không hoạt động. Vui lòng thử lại sau."); }
    try { json = await res.json(); } catch (e) { json = null; }
    if (!res.ok || !json || json.status !== "success") { var err = new Error((json && json.message) || "Lỗi " + res.status); err.code = json && json.code; throw err; }
    return json.data;
  }

  function nav() {
    $("#nav").innerHTML = '<a href="#/">Phim</a>' + (user ? '<a href="#/my">Vé của tôi</a><span class="muted">' + esc(user.username) + '</span><a class="link" id="logout">Đăng xuất</a>' : '<a href="#/login">Đăng nhập</a>');
    var lo = $("#logout"); if (lo) lo.onclick = function () { user = null; sessionStorage.removeItem("soa.user"); nav(); location.hash = "#/"; };
  }
  function show(html) { $("#view").innerHTML = html; }
  function fail(e) { return '<div class="msg">' + esc(e.message) + "</div>"; }

  async function home() {
    show('<h2>Phim đang chiếu</h2><div class="muted">Đang tải...</div>');
    try {
      var ms = await call("movie", "GET", "/api/movies");
      show("<h2>Phim đang chiếu</h2>" + (ms.length ? '<div class="grid">' + ms.map(function (m) {
        return '<div class="movie" data-id="' + m.id + '"><div class="poster">🎬</div><div class="info"><b>' + esc(m.title) + '</b><span class="muted">' + esc(m.genre) + " · " + m.duration + " phút</span></div></div>";
      }).join("") + "</div>" : '<div class="panel muted">Chưa có phim.</div>'));
      document.querySelectorAll(".movie").forEach(function (el) { el.onclick = function () { location.hash = "#/movie/" + el.dataset.id; }; });
    } catch (e) { show("<h2>Phim đang chiếu</h2>" + fail(e)); }
  }

  async function movie(id) {
    show('<div class="muted">Đang tải...</div>');
    try {
      var m = await call("movie", "GET", "/api/movies/" + id);
      var sts = []; var stErr = "";
      try { sts = await call("showtime", "GET", "/api/showtimes?movieId=" + id); } catch (e) { stErr = fail(e); }
      show('<a href="#/">← Quay lại</a><div class="panel" style="margin-top:12px"><h2>' + esc(m.title) + '</h2><span class="muted">' + esc(m.genre) + " · " + m.duration + " phút</span></div>" +
        "<h2>Suất chiếu</h2>" + stErr + (sts.length ? '<div class="showtimes">' + sts.map(function (s) {
          return '<div class="st"><span><b>' + esc(s.time.slice(0, 16)) + "</b> · " + esc(s.cinema) + " · " + esc(s.room) + '</span><span>' + money(s.price) + ' <button data-st="' + s.id + '">Chọn ghế</button></span></div>';
        }).join("") + "</div>" : (stErr ? "" : '<div class="panel muted">Phim chưa có suất chiếu.</div>')));
      document.querySelectorAll("[data-st]").forEach(function (b) { b.onclick = function () { location.hash = "#/book/" + id + "/" + b.dataset.st; }; });
    } catch (e) { show('<a href="#/">← Quay lại</a>' + fail(e)); }
  }

  async function book(movieId, stId) {
    if (!user) { sessionStorage.setItem("soa.next", location.hash); location.hash = "#/login"; return; }
    show('<div class="muted">Đang tải sơ đồ ghế...</div>');
    try {
      var st = await call("showtime", "GET", "/api/showtimes/" + stId);
      var taken = (await call("booking", "GET", "/api/booking/seats?showtimeId=" + stId)).seats;
      var picked = [];
      var grid = "";
      ROWS.split("").forEach(function (r) { for (var c = 1; c <= COLS; c++) { var code = r + c, t = taken.indexOf(code) >= 0; grid += '<button class="seat' + (t ? " taken" : "") + '" data-seat="' + code + '"' + (t ? " disabled" : "") + ">" + code + "</button>"; } });
      show('<a href="#/movie/' + movieId + '">← Quay lại</a><div class="panel" style="margin-top:12px"><b>' + esc(st.cinema) + " · " + esc(st.room) + '</b><div class="muted">' + esc(st.time) + " · " + money(st.price) + "/ghế</div></div>" +
        '<div class="panel"><div class="screen"></div><div class="seats">' + grid + '</div><div class="legend"><span>⬜ Trống</span><span style="color:#f59e0b">🟧 Đang chọn</span><span style="color:#fca5a5">🟥 Đã đặt</span></div></div>' +
        '<div class="panel"><div id="err"></div><label class="muted">Phương thức thanh toán</label><select id="method"><option>MOMO</option><option>VNPAY</option><option>CASH</option></select>' +
        '<div style="display:flex;justify-content:space-between;align-items:center"><div><b id="sum">Chưa chọn ghế</b></div><button id="pay" disabled>Đặt vé &amp; thanh toán</button></div></div>');
      function refresh() { $("#sum").textContent = picked.length ? picked.join(", ") + " — " + money(picked.length * st.price) : "Chưa chọn ghế"; $("#pay").disabled = !picked.length; }
      document.querySelectorAll(".seat:not(.taken)").forEach(function (b) {
        b.onclick = function () { var c = b.dataset.seat, i = picked.indexOf(c); if (i >= 0) { picked.splice(i, 1); b.classList.remove("sel"); } else if (picked.length < 10) { picked.push(c); b.classList.add("sel"); } refresh(); };
      });
      $("#pay").onclick = async function () {
        var btn = $("#pay"); btn.disabled = true; btn.textContent = "Đang xử lý...";
        try {
          var r = await call("booking", "POST", "/api/booking", { username: user.username, movieId: Number(movieId), showtimeId: Number(stId), seats: picked, paymentMethod: $("#method").value });
          sessionStorage.setItem("soa.last", JSON.stringify(r)); location.hash = "#/result";
        } catch (e) { $("#err").innerHTML = fail(e); btn.textContent = "Đặt vé & thanh toán"; btn.disabled = false; if (e.code === "SEAT_TAKEN") book(movieId, stId); }
      };
    } catch (e) { show('<a href="#/movie/' + movieId + '">← Quay lại</a>' + fail(e)); }
  }

  function result() {
    var r = null; try { r = JSON.parse(sessionStorage.getItem("soa.last") || "null"); } catch (e) {}
    if (!r) { location.hash = "#/"; return; }
    var ok = r.status === "PAID";
    show('<div class="panel"><h2>' + (ok ? "✅ Đặt vé thành công" : "❌ Thanh toán thất bại — đơn đã hủy") + '</h2>' +
      '<p>Mã đơn <b>#' + r.id + "</b> · Ghế <b>" + esc(r.seats.join(", ")) + "</b> · Tổng <b>" + money(r.totalPrice) + '</b></p><p>Trạng thái: <span class="badge ' + esc(r.status) + '">' + esc(r.status) + "</span></p>" +
      (ok ? '<p class="muted">' + (r.notification === "SENT" ? "Thông báo xác nhận đã được gửi." : "Đơn hợp lệ, nhưng chưa gửi được thông báo xác nhận.") + "</p>" : '<p class="muted">Ghế đã được nhả lại, bạn có thể thử đặt lại.</p>') +
      '<a href="#/my">Xem vé của tôi</a></div>');
  }

  async function my() {
    if (!user) { location.hash = "#/login"; return; }
    show("<h2>Vé của tôi</h2>");
    try {
      var rows = await call("booking", "GET", "/api/booking?username=" + encodeURIComponent(user.username));
      show("<h2>Vé của tôi</h2>" + (rows.length ? '<div class="panel"><table><tr><th>Mã đơn</th><th>Ghế</th><th>Tổng</th><th>Trạng thái</th><th>Ngày đặt</th></tr>' + rows.map(function (b) {
        return "<tr><td>#" + b.id + "</td><td>" + esc(b.seats.join(", ")) + "</td><td>" + money(b.totalPrice) + '</td><td><span class="badge ' + esc(b.status) + '">' + esc(b.status) + "</span></td><td>" + esc(b.createdAt) + "</td></tr>";
      }).join("") + "</table></div>" : '<div class="panel muted">Bạn chưa có đơn đặt vé nào.</div>'));
    } catch (e) { show("<h2>Vé của tôi</h2>" + fail(e)); }
  }

  function login(mode) {
    var reg = mode === "register";
    show('<div class="panel" style="max-width:380px;margin:0 auto"><h2>' + (reg ? "Đăng ký" : "Đăng nhập") + '</h2><div id="err"></div>' +
      '<label class="muted">Tên đăng nhập</label><input id="u" autocomplete="username">' + (reg ? '<label class="muted">Email</label><input id="e" type="email">' : "") +
      '<label class="muted">Mật khẩu</label><input id="p" type="password" autocomplete="' + (reg ? "new-password" : "current-password") + '">' +
      '<button id="go" style="width:100%">' + (reg ? "Tạo tài khoản" : "Đăng nhập") + '</button><p class="muted" style="text-align:center">' +
      (reg ? '<a href="#/login">Đã có tài khoản? Đăng nhập</a>' : '<a href="#/register">Chưa có tài khoản? Đăng ký</a>') + "</p></div>");
    $("#go").onclick = async function () {
      var u = $("#u").value.trim(), p = $("#p").value;
      try {
        if (reg) { await call("user", "POST", "/api/register", { username: u, password: p, email: $("#e").value.trim() }); }
        var r = await call("user", "POST", "/api/login", { username: u, password: p });
        user = { id: r.id, username: r.username, role: r.role, token: r.token }; sessionStorage.setItem("soa.user", JSON.stringify(user)); nav();
        var next = sessionStorage.getItem("soa.next"); sessionStorage.removeItem("soa.next"); location.hash = next || "#/";
      } catch (e) { $("#err").innerHTML = fail(e); }
    };
  }

  function route() {
    var h = location.hash || "#/", p = h.split("/");
    if (h === "#/" || h === "#") return home();
    if (p[1] === "movie") return movie(p[2]);
    if (p[1] === "book") return book(p[2], p[3]);
    if (p[1] === "result") return result();
    if (p[1] === "my") return my();
    if (p[1] === "login") return login();
    if (p[1] === "register") return login("register");
    return home();
  }
  window.addEventListener("hashchange", route);
  document.addEventListener("DOMContentLoaded", function () { nav(); route(); $("#title").onclick = function () { location.hash = "#/"; }; });
})();
