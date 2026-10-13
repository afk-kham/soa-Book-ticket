/* Client đặt vé — HTML/CSS/JS thuần, gọi trực tiếp các service qua REST (envelope {"status","data"}).
   Định tuyến bằng hash: #/ · #/movie/{id} · #/book/{movieId}/{showtimeId} · #/result · #/my · #/login · #/register */
(function () {
  var $ = function (s, root) { return (root || document).querySelector(s); };
  var $$ = function (s, root) { return Array.prototype.slice.call((root || document).querySelectorAll(s)); };
  var esc = function (v) { return String(v == null ? "" : v).replace(/[&<>"']/g, function (c) { return ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]; }); };
  var money = function (n) { return Number(n || 0).toLocaleString("vi-VN") + " đ"; };
  var NAMES = { movie: "Movie", showtime: "Showtime", user: "User", booking: "Booking" };
  var STATUS = { PAID: "Đã thanh toán", PENDING: "Chờ thanh toán", CANCELLED: "Đã hủy" };
  var DOW = ["Chủ nhật", "Thứ hai", "Thứ ba", "Thứ tư", "Thứ năm", "Thứ sáu", "Thứ bảy"];
  var MAP = window.SEAT_MAP, METHODS = window.PAYMENT_METHODS;
  var user = null; try { user = JSON.parse(sessionStorage.getItem("soa.user") || "null"); } catch (e) {}
  var ICON_SEARCH = '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round"><circle cx="11" cy="11" r="7"/><path d="m20 20-3.5-3.5"/></svg>';

  /* ---------- Gọi API ---------- */
  async function call(svc, method, path, body) {
    var res, json;
    try { res = await fetch(API[svc] + path, { method: method, headers: body ? { "Content-Type": "application/json" } : {}, body: body ? JSON.stringify(body) : undefined }); }
    catch (e) { var down = new Error(NAMES[svc] + " Service đang không hoạt động. Vui lòng thử lại sau."); down.code = "SERVICE_DOWN"; throw down; }
    try { json = await res.json(); } catch (e) { json = null; }
    if (!res.ok || !json || json.status !== "success") { var err = new Error((json && json.message) || "Lỗi " + res.status); err.code = json && json.code; err.httpStatus = res.status; throw err; }
    return json.data;
  }
  // Dữ liệu phụ (tên phim, suất chiếu) để làm giàu hiển thị — lỗi thì trả rỗng, không chặn trang.
  async function soft(svc, path, fallback) { try { return await call(svc, "GET", path); } catch (e) { return fallback; } }
  function byId(list) { var o = {}; (list || []).forEach(function (x) { o[x.id] = x; }); return o; }

  /* ---------- Định dạng ---------- */
  // "2026-10-10 18:00:00" hoặc ISO → các mảnh để hiển thị; không đổi múi giờ.
  function when(t) {
    var m = String(t || "").match(/^(\d{4})-(\d{2})-(\d{2})[T ](\d{2}):(\d{2})/);
    if (!m) return { date: "", hm: String(t || ""), dm: "", dow: "", full: String(t || "") };
    var d = new Date(+m[1], +m[2] - 1, +m[3]);
    return { date: m[1] + "-" + m[2] + "-" + m[3], hm: m[4] + ":" + m[5], dm: m[3] + "/" + m[2], dow: DOW[d.getDay()], full: m[4] + ":" + m[5] + " · " + DOW[d.getDay()] + ", " + m[3] + "/" + m[2] + "/" + m[1] };
  }
  function duration(min) { min = Number(min) || 0; var h = Math.floor(min / 60), m = min % 60; return h ? h + " giờ" + (m ? " " + m + " phút" : "") : m + " phút"; }
  function badge(s) { return '<span class="badge ' + esc(s) + '">' + esc(STATUS[s] || s) + "</span>"; }

  /* ---------- Poster: dùng ảnh nếu poster là URL, ngược lại sinh nền màu theo tên phim ---------- */
  var PAL = [["#7c2d12", "#f97316"], ["#1e3a8a", "#6366f1"], ["#4c1d95", "#db2777"], ["#064e3b", "#14b8a6"], ["#7f1d1d", "#f43f5e"], ["#713f12", "#eab308"], ["#0c4a6e", "#06b6d4"], ["#3b0764", "#a855f7"]];
  var GENRE_ICON = [[/hành động|action/i, "💥"], [/viễn tưởng|sci/i, "🚀"], [/hoạt hình|anim/i, "🎨"], [/kinh dị|horror/i, "👻"], [/hài|comedy/i, "😂"], [/tình cảm|lãng mạn|romance/i, "💕"], [/tâm lý|drama/i, "🎭"], [/phiêu lưu/i, "🧭"]];
  function hash(s) { var h = 0; s = String(s || ""); for (var i = 0; i < s.length; i++) h = (h * 31 + s.charCodeAt(i)) | 0; return Math.abs(h); }
  function palette(m) { var p = PAL[hash(m && m.title) % PAL.length]; return "--p1:" + p[0] + ";--p2:" + p[1]; }
  function genreIcon(g) { for (var i = 0; i < GENRE_ICON.length; i++) if (GENRE_ICON[i][0].test(g || "")) return GENRE_ICON[i][1]; return "🎬"; }
  function poster(m, cls) {
    m = m || { title: "Phim" };
    var img = /^(https?:)?\/\//.test(m.poster || "") ? '<img src="' + esc(m.poster) + '" alt="" loading="lazy" onerror="this.remove()">' : "";
    return '<div class="poster ' + (cls || "") + '" style="' + palette(m) + '">' + img + '<span class="poster-emoji">' + genreIcon(m.genre) + '</span><span class="poster-title">' + esc(m.title) + "</span></div>";
  }

  /* ---------- Khung chung ---------- */
  function show(html) { $("#view").innerHTML = html; }
  function toast(msg, type) {
    var t = document.createElement("div"); t.className = "toast " + (type || "ok");
    t.innerHTML = '<span class="ic">' + (type === "err" ? "⚠️" : "✅") + "</span><span>" + esc(msg) + "</span>";
    $("#toasts").appendChild(t); setTimeout(function () { t.remove(); }, 4500);
  }
  function stateBox(icon, title, text, action) { return '<div class="state"><div class="big">' + icon + "</div><h3>" + esc(title) + "</h3><p>" + esc(text) + "</p>" + (action || "") + "</div>"; }
  function errorBox(e, retry) {
    return stateBox(e.code === "SERVICE_DOWN" ? "🔌" : "⚠️", e.code === "SERVICE_DOWN" ? "Không kết nối được dịch vụ" : "Đã xảy ra lỗi", e.message,
      retry === false ? "" : '<button class="btn btn-ghost" data-retry>Thử lại</button>');
  }
  function bindRetry(fn) { var b = $("[data-retry]"); if (b) b.onclick = fn; }
  function back(href, label) { return '<a class="back" href="' + href + '">← ' + esc(label) + "</a>"; }
  function steps(active) {
    var names = ["Chọn suất chiếu", "Chọn ghế & thanh toán", "Hoàn tất"];
    return '<div class="steps">' + names.map(function (n, i) {
      var cls = i < active ? "done" : i === active ? "on" : "";
      return (i ? '<span class="sep"></span>' : "") + '<span class="step ' + cls + '"><i>' + (i < active ? "✓" : i + 1) + "</i>" + n + "</span>";
    }).join("") + "</div>";
  }

  function nav() {
    var h = location.hash || "#/";
    var mine = /^#\/(my|result)/.test(h), auth = /^#\/(login|register)/.test(h);
    var links = [["#/", "Phim", !mine && !auth], ["#/my", "Vé của tôi", mine]];
    $("#mainnav").innerHTML = links.map(function (l) {
      var on = l[2];
      return '<a href="' + l[0] + '" class="' + (on ? "active" : "") + '">' + l[1] + "</a>";
    }).join("");
    $("#account").innerHTML = user
      ? '<span class="user-chip" title="' + esc(user.username) + '"><span class="avatar">' + esc(user.username.charAt(0).toUpperCase()) + '</span><span class="name">' + esc(user.username) + '</span></span><button class="btn btn-text btn-sm" id="logout">Đăng xuất</button>'
      : '<a class="btn btn-ghost btn-sm" href="#/login">Đăng nhập</a><a class="btn btn-primary btn-sm" href="#/register">Đăng ký</a>';
    var lo = $("#logout"); if (lo) lo.onclick = function () { user = null; sessionStorage.removeItem("soa.user"); toast("Đã đăng xuất"); location.hash = "#/"; nav(); };
  }

  /* ---------- Trang chủ ---------- */
  async function home() {
    show('<div class="skel" style="height:300px;border-radius:22px;margin-bottom:40px"></div><div class="grid">' +
      Array(5).join('<div><div class="skel" style="aspect-ratio:2/3"></div><div class="skel" style="height:16px;margin-top:12px;width:70%"></div></div>') + "</div>");
    var movies, sts;
    try { movies = await call("movie", "GET", "/api/movies"); } catch (e) { show(errorBox(e)); bindRetry(home); return; }
    sts = await soft("showtime", "/api/showtimes", null);
    if (!movies.length) { show(stateBox("🎞️", "Chưa có phim nào", "Rạp đang cập nhật lịch chiếu. Vui lòng quay lại sau.")); return; }
    var count = {}; (sts || []).forEach(function (s) { count[s.movieId] = (count[s.movieId] || 0) + 1; });
    var featured = movies.filter(function (m) { return count[m.id]; })[0] || movies[0];
    var genres = []; movies.forEach(function (m) { if (m.genre && genres.indexOf(m.genre) < 0) genres.push(m.genre); });
    var state = { q: "", g: "" };

    show('<section class="hero" style="' + palette(featured) + '"><div class="hero-bg"></div><div class="hero-in"><div>' +
      '<span class="eyebrow">★ Phim nổi bật</span><h1>' + esc(featured.title) + '</h1><div class="meta"><span class="chip">' + genreIcon(featured.genre) + " " + esc(featured.genre) +
      '</span><span class="chip">⏱ ' + duration(featured.duration) + "</span>" + (count[featured.id] ? '<span class="chip">🎟 ' + count[featured.id] + " suất chiếu</span>" : "") + "</div>" +
      '<div class="actions"><a class="btn btn-primary btn-lg" href="#/movie/' + featured.id + '">Đặt vé ngay</a><a class="btn btn-ghost btn-lg" href="#movies" id="to-list">Xem tất cả phim</a></div></div>' +
      poster(featured) + "</div></section>" +
      '<section id="movies"><div class="section-head"><div><h2>Phim đang chiếu</h2><div class="muted small" id="m-count"></div></div></div>' +
      '<div class="filters"><label class="search">' + ICON_SEARCH + '<input class="input" id="q" placeholder="Tìm tên phim..." aria-label="Tìm phim"></label>' +
      '<div class="genres" id="genres">' + ['<button class="genre on" data-g="">Tất cả</button>'].concat(genres.map(function (g) { return '<button class="genre" data-g="' + esc(g) + '">' + esc(g) + "</button>"; })).join("") + "</div></div>" +
      '<div id="grid"></div></section>');

    function render() {
      var q = state.q.toLowerCase();
      var list = movies.filter(function (m) { return (!state.g || m.genre === state.g) && (!q || String(m.title).toLowerCase().indexOf(q) >= 0); });
      $("#m-count").textContent = list.length + " phim" + (sts ? "" : " · chưa lấy được lịch chiếu");
      $("#grid").innerHTML = list.length ? '<div class="grid">' + list.map(function (m) {
        var n = count[m.id];
        return '<a class="mcard" href="#/movie/' + m.id + '"><div style="position:relative">' + poster(m) + (sts ? '<span class="tag">' + (n ? n + " suất" : "Sắp chiếu") + "</span>" : "") +
          "</div><h3>" + esc(m.title) + '</h3><div class="sub">' + esc(m.genre) + " · " + duration(m.duration) + "</div></a>";
      }).join("") + "</div>" : stateBox("🔍", "Không tìm thấy phim", "Thử từ khóa khác hoặc chọn thể loại khác.");
    }
    $("#q").oninput = function () { state.q = this.value.trim(); render(); };
    $$("#genres .genre").forEach(function (b) { b.onclick = function () { state.g = b.dataset.g; $$("#genres .genre").forEach(function (x) { x.classList.toggle("on", x === b); }); render(); }; });
    $("#to-list").onclick = function (ev) { ev.preventDefault(); $("#movies").scrollIntoView(); };
    render();
  }

  /* ---------- Chi tiết phim + suất chiếu ---------- */
  async function movie(id) {
    show(back("#/", "Danh sách phim") + '<div class="skel" style="height:320px;border-radius:22px"></div>');
    var m;
    try { m = await call("movie", "GET", "/api/movies/" + encodeURIComponent(id)); }
    catch (e) { show(back("#/", "Danh sách phim") + errorBox(e)); bindRetry(function () { movie(id); }); return; }
    var sts = [], stErr = null;
    try { sts = await call("showtime", "GET", "/api/showtimes?movieId=" + encodeURIComponent(id)); } catch (e) { stErr = e; }
    sts.sort(function (a, b) { return String(a.time).localeCompare(String(b.time)); });
    var dates = []; sts.forEach(function (s) { var d = when(s.time).date; if (dates.indexOf(d) < 0) dates.push(d); });
    var minPrice = sts.length ? Math.min.apply(null, sts.map(function (s) { return s.price; })) : 0;

    show(back("#/", "Danh sách phim") +
      '<section class="detail" style="' + palette(m) + '"><div class="hero-bg"></div><div class="detail-in">' + poster(m) +
      '<div><span class="eyebrow">' + genreIcon(m.genre) + " " + esc(m.genre) + "</span><h1>" + esc(m.title) + "</h1>" +
      '<div class="facts"><div><span>Thời lượng</span><b>' + duration(m.duration) + '</b></div><div><span>Suất chiếu</span><b>' + (stErr ? "—" : sts.length) + "</b></div>" +
      (minPrice ? "<div><span>Giá từ</span><b>" + money(minPrice) + "</b></div>" : "") + "</div>" +
      (sts.length ? '<a class="btn btn-primary" href="#showtimes" id="to-st">Chọn suất chiếu</a>' : "") + "</div></div></section>" +
      '<section id="showtimes"><div class="section-head"><h2>Lịch chiếu</h2></div><div id="st-body"></div></section>');
    var toSt = $("#to-st"); if (toSt) toSt.onclick = function (ev) { ev.preventDefault(); $("#showtimes").scrollIntoView(); };

    if (stErr) { $("#st-body").innerHTML = errorBox(stErr); bindRetry(function () { movie(id); }); return; }
    if (!sts.length) { $("#st-body").innerHTML = stateBox("🗓️", "Chưa có suất chiếu", "Phim này chưa được xếp lịch. Hãy quay lại sau nhé."); return; }

    var cur = dates[0];
    function render() {
      var day = sts.filter(function (s) { return when(s.time).date === cur; }), groups = {}, order = [];
      day.forEach(function (s) { if (!groups[s.cinema]) { groups[s.cinema] = []; order.push(s.cinema); } groups[s.cinema].push(s); });
      $("#st-body").innerHTML = '<div class="dates" role="tablist">' + dates.map(function (d) {
        var w = when(d + " 00:00"); return '<button class="date' + (d === cur ? " on" : "") + '" data-d="' + d + '" role="tab" aria-selected="' + (d === cur) + '"><small>' + w.dow + "</small><b>" + w.dm + "</b></button>";
      }).join("") + "</div>" + order.map(function (c) {
        return '<div class="cinema"><h3><span class="pin">📍</span>' + esc(c) + '</h3><div class="times">' + groups[c].map(function (s) {
          return '<button class="time" data-st="' + s.id + '"><b>' + when(s.time).hm + "</b><span>Phòng " + esc(s.room) + " · " + money(s.price) + "</span></button>";
        }).join("") + "</div></div>";
      }).join("");
      $$("#st-body .date").forEach(function (b) { b.onclick = function () { cur = b.dataset.d; render(); }; });
      $$("#st-body [data-st]").forEach(function (b) { b.onclick = function () { location.hash = "#/book/" + id + "/" + b.dataset.st; }; });
    }
    render();
  }

  /* ---------- Chọn ghế + thanh toán ---------- */
  async function book(movieId, stId, notice) {
    if (!user) { sessionStorage.setItem("soa.next", location.hash); toast("Vui lòng đăng nhập để đặt vé", "err"); location.hash = "#/login"; return; }
    var backLink = back("#/movie/" + movieId, "Đổi suất chiếu");
    show(backLink + steps(1) + '<div class="book"><div class="skel" style="height:420px"></div><div class="skel" style="height:420px"></div></div>');
    var st, taken, m;
    try {
      st = await call("showtime", "GET", "/api/showtimes/" + encodeURIComponent(stId));
      taken = (await call("booking", "GET", "/api/booking/seats?showtimeId=" + encodeURIComponent(stId))).seats || [];
    } catch (e) { show(backLink + errorBox(e)); bindRetry(function () { book(movieId, stId); }); return; }
    m = await soft("movie", "/api/movies/" + encodeURIComponent(movieId), { id: movieId, title: "Phim #" + movieId, genre: "" });
    var picked = [], w = when(st.time);

    var hall = "";
    MAP.rows.split("").forEach(function (r) {
      hall += '<div class="srow"><span class="rl">' + r + "</span>";
      for (var c = 1; c <= MAP.cols; c++) {
        var code = r + c, t = taken.indexOf(code) >= 0;
        hall += '<button class="seat' + (t ? " taken" : "") + '" data-seat="' + code + '"' + (t ? ' disabled aria-label="' + code + ' đã có người đặt"' : ' aria-pressed="false"') + ">" + c + "</button>";
        if (MAP.aisleAfter.indexOf(c) >= 0) hall += '<span class="aisle"></span>';
      }
      hall += '<span class="rl">' + r + "</span></div>";
    });

    show(backLink + steps(1) + '<div class="book">' +
      '<div class="panel"><div class="hall"><div class="hall-in"><div class="screen"><span>MÀN HÌNH</span></div>' + hall + "</div></div>" +
      '<div class="legend"><span><i></i>Ghế trống</span><span><i class="sel"></i>Đang chọn</span><span><i class="taken"></i>Đã có người đặt</span></div></div>' +
      '<aside class="panel summary"><div class="sum-movie">' + poster(m, "sm") + "<div><h3>" + esc(m.title) + '</h3><div class="muted small">' + esc(st.cinema) + "</div></div></div>" +
      '<div class="kv"><span>Suất chiếu</span><b>' + w.hm + " · " + w.dm + '</b></div><div class="kv"><span>Phòng</span><b>' + esc(st.room) + '</b></div><div class="kv"><span>Giá vé</span><b>' + money(st.price) + " / ghế</b></div>" +
      '<div class="kv"><span>Ghế đã chọn</span><b id="cnt">0 / ' + MAP.maxSeats + '</b></div><div class="seat-chips" id="chips"><span class="muted small">Chọn ghế trên sơ đồ</span></div>' +
      '<div class="total"><span class="muted">Tổng cộng</span><b id="sum">0 đ</b></div>' +
      '<label class="lbl">Phương thức thanh toán</label><div class="methods">' + METHODS.map(function (p, i) {
        return '<label class="method"><input type="radio" name="method" value="' + p.value + '"' + (i ? "" : " checked") + "><span><b>" + esc(p.label) + "</b><small>" + esc(p.hint) + '</small></span><span class="logo ' + p.value + '">' + p.value + "</span></label>";
      }).join("") + '</div><div id="err">' + (notice ? '<div class="alert">⚠ ' + esc(notice) + "</div>" : "") + '</div><button class="btn btn-primary btn-lg btn-block" id="pay" disabled>Đặt vé &amp; thanh toán</button>' +
      '<p class="muted small" style="text-align:center;margin:10px 0 0">Giá vé do hệ thống tính theo suất chiếu.</p></aside></div>');

    function refresh() {
      $("#cnt").textContent = picked.length + " / " + MAP.maxSeats;
      $("#chips").innerHTML = picked.length ? picked.map(function (c) { return '<span class="c">' + c + "</span>"; }).join("") : '<span class="muted small">Chọn ghế trên sơ đồ</span>';
      $("#sum").textContent = money(picked.length * st.price);
      $("#pay").disabled = !picked.length;
    }
    $$(".seat:not(.taken)").forEach(function (b) {
      b.onclick = function () {
        var c = b.dataset.seat, i = picked.indexOf(c);
        if (i >= 0) picked.splice(i, 1);
        else if (picked.length >= MAP.maxSeats) { toast("Mỗi đơn đặt tối đa " + MAP.maxSeats + " ghế", "err"); return; }
        else picked.push(c);
        picked.sort(function (a, z) { return a.charCodeAt(0) - z.charCodeAt(0) || parseInt(a.slice(1)) - parseInt(z.slice(1)); });
        b.classList.toggle("sel", i < 0); b.setAttribute("aria-pressed", String(i < 0)); refresh();
      };
    });
    $("#pay").onclick = async function () {
      var btn = this, method = ($("input[name=method]:checked") || {}).value || "MOMO";
      btn.disabled = true; btn.innerHTML = '<span class="spinner"></span> Đang xử lý...'; $("#err").innerHTML = "";
      try {
        var r = await call("booking", "POST", "/api/booking", { username: user.username, movieId: Number(movieId), showtimeId: Number(stId), seats: picked, paymentMethod: method });
        sessionStorage.setItem("soa.last", JSON.stringify({ booking: r, movie: m, showtime: st }));
        location.hash = "#/result";
      } catch (e) {
        if (e.code === "SEAT_TAKEN") { book(movieId, stId, e.message + ". Sơ đồ ghế đã được cập nhật, vui lòng chọn lại."); return; }
        $("#err").innerHTML = '<div class="alert">⚠ ' + esc(e.message) + "</div>"; btn.innerHTML = "Đặt vé &amp; thanh toán"; btn.disabled = false;
      }
    };
  }

  /* ---------- Kết quả đặt vé ---------- */
  function result() {
    var last = null; try { last = JSON.parse(sessionStorage.getItem("soa.last") || "null"); } catch (e) {}
    if (!last || !last.booking) { location.hash = "#/my"; return; }
    var r = last.booking, m = last.movie || { title: "Phim #" + r.movieId }, st = last.showtime || {}, ok = r.status === "PAID", w = when(st.time), pay = r.payment || {};
    var method = METHODS.filter(function (p) { return p.value === pay.method; })[0];
    var note = ok ? (r.notification === "SENT" ? "Thông báo xác nhận đã được gửi tới bạn." : "Đơn hợp lệ, nhưng hệ thống chưa gửi được thông báo xác nhận.")
                  : "Thanh toán không thành công nên đơn đã được hủy và ghế đã được nhả lại.";
    show(steps(2) + '<div class="ticket"><div class="ticket-main">' + poster(m) + "<div>" +
      '<div class="status-head"><span class="status-ic ' + (ok ? "ok" : "bad") + '">' + (ok ? "✓" : "✕") + "</span><div><h2>" + (ok ? "Đặt vé thành công!" : "Thanh toán thất bại") + "</h2></div></div>" +
      '<p class="muted" style="margin:4px 0 0">' + note + "</p>" +
      '<div class="tgrid"><div><span>Phim</span><b>' + esc(m.title) + "</b></div><div><span>Rạp</span><b>" + esc(st.cinema || "—") + "</b></div>" +
      "<div><span>Suất chiếu</span><b>" + esc(st.time ? w.full : "—") + "</b></div><div><span>Phòng</span><b>" + esc(st.room || "—") + "</b></div>" +
      "<div><span>Ghế</span><b>" + esc(r.seats.join(", ")) + "</b></div><div><span>Tổng tiền</span><b>" + money(r.totalPrice) + "</b></div>" +
      "<div><span>Thanh toán</span><b>" + esc(method ? method.label : pay.method || "—") + "</b></div><div><span>Mã giao dịch</span><b>" + esc(pay.transactionId || "—") + "</b></div></div></div></div>" +
      '<div class="ticket-stub"><div><div class="muted small">Mã đơn</div><div class="code">#' + esc(r.id) + "</div></div>" + badge(r.status) + '<div class="barcode" aria-hidden="true"></div></div></div>' +
      '<div class="ticket-actions">' + (ok ? "" : '<a class="btn btn-primary" href="#/book/' + r.movieId + "/" + r.showtimeId + '">Chọn lại ghế</a>') +
      '<a class="btn ' + (ok ? "btn-primary" : "btn-ghost") + '" href="#/my">Xem vé của tôi</a><a class="btn btn-ghost" href="#/">Về trang chủ</a></div>');
  }

  /* ---------- Vé của tôi ---------- */
  async function my() {
    if (!user) { sessionStorage.setItem("soa.next", "#/my"); location.hash = "#/login"; return; }
    var head = '<div class="section-head"><div><h2>Vé của tôi</h2><div class="muted small">Các đơn đặt vé của tài khoản ' + esc(user.username) + "</div></div></div>";
    show(head + '<div class="tlist">' + Array(4).join('<div class="skel" style="height:100px"></div>') + "</div>");
    var rows;
    try { rows = await call("booking", "GET", "/api/booking?username=" + encodeURIComponent(user.username)); }
    catch (e) { show(head + errorBox(e)); bindRetry(my); return; }
    var info = await Promise.all([soft("movie", "/api/movies", []), soft("showtime", "/api/showtimes", [])]);
    var movies = byId(info[0]), shows = byId(info[1]);
    rows.sort(function (a, b) { return b.id - a.id; });
    if (!rows.length) { show(head + stateBox("🎟️", "Bạn chưa có vé nào", "Chọn một bộ phim và đặt vé đầu tiên của bạn.", '<a class="btn btn-primary" href="#/">Khám phá phim</a>')); return; }

    var tabs = [["", "Tất cả"], ["PAID", "Đã thanh toán"], ["PENDING", "Chờ thanh toán"], ["CANCELLED", "Đã hủy"]], cur = "";
    function render() {
      var list = rows.filter(function (b) { return !cur || b.status === cur; });
      $("#tabs").innerHTML = tabs.map(function (t) {
        var n = rows.filter(function (b) { return !t[0] || b.status === t[0]; }).length;
        return '<button class="tab' + (t[0] === cur ? " on" : "") + '" data-t="' + t[0] + '">' + t[1] + "<em>" + n + "</em></button>";
      }).join("");
      $("#list").innerHTML = list.length ? '<div class="tlist">' + list.map(function (b) {
        var mv = movies[b.movieId] || { title: "Phim #" + b.movieId }, s = shows[b.showtimeId], w = s ? when(s.time) : null;
        return '<article class="trow ' + esc(b.status) + '">' + poster(mv, "sm") + "<div><h3>" + esc(mv.title) + '</h3><div class="line">' +
          (s ? "<span>📍 " + esc(s.cinema) + " · " + esc(s.room) + "</span><span>🕒 " + w.hm + " · " + w.dm + "</span>" : "<span>Suất #" + esc(b.showtimeId) + "</span>") +
          "<span>💺 " + esc(b.seats.join(", ")) + '</span></div><div class="muted small" style="margin-top:4px">Đơn #' + esc(b.id) + " · đặt lúc " + esc(when(b.createdAt).full) + "</div></div>" +
          '<div class="right"><span class="price">' + money(b.totalPrice) + "</span>" + badge(b.status) + "</div></article>";
      }).join("") + "</div>" : stateBox("🗂️", "Không có đơn nào", "Không có đơn đặt vé ở trạng thái này.");
      $$("#tabs .tab").forEach(function (b) { b.onclick = function () { cur = b.dataset.t; render(); }; });
    }
    show(head + '<div class="tabs" id="tabs" role="tablist"></div><div id="list"></div>');
    render();
  }

  /* ---------- Đăng nhập / đăng ký ---------- */
  function login(mode) {
    if (user) { location.hash = "#/"; return; }
    var reg = mode === "register";
    show('<div class="auth"><div class="auth-art"><div><span class="eyebrow">SOA Cinema</span><h2 style="margin-top:12px">Đặt vé xem phim<br>chỉ trong vài bước.</h2></div>' +
      "<ul><li><i>🎬</i>Xem lịch chiếu theo ngày và theo rạp</li><li><i>💺</i>Chọn ghế trực tiếp trên sơ đồ phòng</li><li><i>💳</i>Thanh toán MoMo, VNPAY hoặc tại quầy</li><li><i>🎟️</i>Quản lý toàn bộ vé đã đặt</li></ul>" +
      '<span class="muted small">Mỗi chức năng là một service độc lập, giao tiếp qua HTTP + JSON.</span></div>' +
      '<form class="auth-form" id="auth" novalidate><h1>' + (reg ? "Tạo tài khoản" : "Chào mừng trở lại") + '</h1><p class="lead">' + (reg ? "Đăng ký miễn phí để bắt đầu đặt vé." : "Đăng nhập để tiếp tục đặt vé.") + "</p>" +
      (reg ? "" : '<div class="demo"><span>Tài khoản thử: <code>user1</code> / <code>User@123</code></span><button type="button" class="btn btn-text btn-sm" id="fill">Điền nhanh</button></div>') +
      '<div id="err"></div><div class="field"><label class="lbl" for="u">Tên đăng nhập</label><input class="input" id="u" autocomplete="username" required></div>' +
      (reg ? '<div class="field"><label class="lbl" for="e">Email <span class="muted">(không bắt buộc)</span></label><input class="input" id="e" type="email" autocomplete="email"></div>' : "") +
      '<div class="field"><label class="lbl" for="p">Mật khẩu</label><div class="pw"><input class="input" id="p" type="password" autocomplete="' + (reg ? "new-password" : "current-password") + '" required' + (reg ? ' minlength="6" placeholder="Ít nhất 6 ký tự"' : "") + '><button type="button" class="btn btn-text btn-sm" id="eye">Hiện</button></div></div>' +
      '<button class="btn btn-primary btn-lg btn-block" id="go" type="submit">' + (reg ? "Tạo tài khoản" : "Đăng nhập") + "</button>" +
      '<p class="switch">' + (reg ? 'Đã có tài khoản? <a href="#/login">Đăng nhập</a>' : 'Chưa có tài khoản? <a href="#/register">Đăng ký ngay</a>') + "</p></form></div>");
    $("#u").focus();
    $("#eye").onclick = function () { var p = $("#p"), hidden = p.type === "password"; p.type = hidden ? "text" : "password"; this.textContent = hidden ? "Ẩn" : "Hiện"; };
    var fill = $("#fill"); if (fill) fill.onclick = function () { $("#u").value = "user1"; $("#p").value = "User@123"; $("#go").focus(); };
    $("#auth").onsubmit = async function (ev) {
      ev.preventDefault();
      var u = $("#u").value.trim(), p = $("#p").value, err = $("#err"), btn = $("#go"), label = btn.textContent;
      var problem = !u ? "Vui lòng nhập tên đăng nhập." : !p ? "Vui lòng nhập mật khẩu." : reg && p.length < 6 ? "Mật khẩu cần ít nhất 6 ký tự." : "";
      if (problem) { err.innerHTML = '<div class="alert">⚠ ' + problem + "</div>"; return; }
      err.innerHTML = ""; btn.disabled = true; btn.innerHTML = '<span class="spinner"></span> Đang xử lý...';
      try {
        if (reg) await call("user", "POST", "/api/register", { username: u, password: p, email: $("#e").value.trim() });
        var r = await call("user", "POST", "/api/login", { username: u, password: p });
        user = { id: r.id, username: r.username, role: r.role, token: r.token }; sessionStorage.setItem("soa.user", JSON.stringify(user));
        toast(reg ? "Tạo tài khoản thành công. Xin chào " + r.username + "!" : "Xin chào " + r.username + "!");
        var next = sessionStorage.getItem("soa.next"); sessionStorage.removeItem("soa.next"); location.hash = next || "#/"; nav();
      } catch (e) { err.innerHTML = '<div class="alert">⚠ ' + esc(e.message) + "</div>"; btn.disabled = false; btn.textContent = label; }
    };
  }

  /* ---------- Định tuyến ---------- */
  function route() {
    var h = location.hash || "#/", p = h.split("/");
    if (h === "#movies") return;   // neo cuộn trong trang chủ
    nav(); window.scrollTo(0, 0);
    if (p[1] === "movie" && p[2]) return movie(p[2]);
    if (p[1] === "book" && p[3]) return book(p[2], p[3]);
    if (p[1] === "result") return result();
    if (p[1] === "my") return my();
    if (p[1] === "login") return login();
    if (p[1] === "register") return login("register");
    return home();
  }
  window.addEventListener("hashchange", route);
  document.addEventListener("DOMContentLoaded", route);
})();
