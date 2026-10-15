/* Client đặt vé — HTML/CSS/JS thuần, gọi trực tiếp các service qua REST (envelope {"status","data"}).
   Định tuyến bằng hash: #/ · #/movie/{id} · #/book/{movieId}/{showtimeId} · #/pay/{bookingId} · #/ticket/{bookingId} · #/my · #/login · #/register
   Luồng đặt vé: chọn ghế -> Booking giữ ghế (PENDING, có hạn) -> trang thanh toán -> Booking gọi Payment -> vé điện tử. */
(function () {
  var $ = function (s, root) { return (root || document).querySelector(s); };
  var $$ = function (s, root) { return Array.prototype.slice.call((root || document).querySelectorAll(s)); };
  var esc = function (v) { return String(v == null ? "" : v).replace(/[&<>"']/g, function (c) { return ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]; }); };
  var money = function (n) { return Number(n || 0).toLocaleString("vi-VN") + " đ"; };
  var STATUS = { PAID: "Đã thanh toán", PENDING: "Chờ thanh toán", CANCELLED: "Đã hủy" };
  var DOW = ["Chủ nhật", "Thứ hai", "Thứ ba", "Thứ tư", "Thứ năm", "Thứ sáu", "Thứ bảy"];
  var MAP = window.SEAT_MAP, METHODS = window.PAYMENT_METHODS, BANK = window.BANK_ACCOUNT;
  var TOTAL_SEATS = MAP.rows.length * MAP.cols;
  var user = null; try { user = JSON.parse(sessionStorage.getItem("soa.user") || "null"); } catch (e) {}
  var ICON_SEARCH = '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round"><circle cx="11" cy="11" r="7"/><path d="m20 20-3.5-3.5"/></svg>';
  var ICON_COPY = '<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="9" y="9" width="12" height="12" rx="2"/><path d="M5 15V5a2 2 0 0 1 2-2h10"/></svg>';

  /* ---------- Vòng đời trang: hẹn giờ cập nhật trực tiếp được dọn khi chuyển trang ---------- */
  var timers = [], page = 0;
  function every(fn, ms) { timers.push(setInterval(fn, ms)); }
  function leave() { timers.forEach(clearInterval); timers = []; page++; }
  function current() { var p = page; return function () { return p === page; }; }   // async: còn ở trang này không?

  /* ---------- Gọi API + thông báo lỗi thân thiện (không lộ tên service, mã kỹ thuật) ---------- */
  var DOWN = {
    movie: "Không tải được danh sách phim lúc này. Vui lòng thử lại sau ít phút.",
    showtime: "Không tải được lịch chiếu lúc này. Vui lòng thử lại sau ít phút.",
    user: "Hệ thống tài khoản đang tạm gián đoạn. Vui lòng thử lại sau ít phút.",
    booking: "Hệ thống đặt vé đang tạm gián đoạn. Vui lòng thử lại sau ít phút."
  };
  var FRIENDLY = {
    PAYMENT_SERVICE_UNAVAILABLE: "Cổng thanh toán đang tạm gián đoạn. Ghế của bạn vẫn được giữ — vui lòng thử lại sau ít phút.",
    PAYMENT_SERVICE_ERROR: "Giao dịch bị từ chối. Vui lòng thử lại hoặc chọn phương thức khác.",
    USER_NOT_FOUND: "Tài khoản không tồn tại. Vui lòng đăng nhập lại.",
    MOVIE_NOT_FOUND: "Phim này không còn tồn tại.",
    SHOWTIME_NOT_FOUND: "Suất chiếu không còn tồn tại, vui lòng chọn suất khác.",
    BOOKING_CANCELLED: "Đơn đã hết thời gian giữ ghế hoặc đã bị hủy.",
    ALREADY_PAID: "Đơn này đã được thanh toán.",
    FORBIDDEN: "Bạn không có quyền xem đơn đặt vé này.",
    NOT_FOUND: "Không tìm thấy thông tin yêu cầu.",
    INTERNAL_ERROR: "Hệ thống gặp sự cố. Vui lòng thử lại sau."
  };
  var TECHNICAL = /service|sql|http|json|endpoint|exception|null|\b[a-z]+Id\b/i;
  function friendly(code, message) {
    if (FRIENDLY[code]) return FRIENDLY[code];
    if (/_SERVICE_(UNAVAILABLE|ERROR)$/.test(code || "")) return "Hệ thống đang bận. Vui lòng thử lại sau ít phút.";
    return message && !TECHNICAL.test(message) ? message : "Đã có lỗi xảy ra. Vui lòng thử lại.";
  }
  async function call(svc, method, path, body) {
    var res, json;
    try { res = await fetch(API[svc] + path, { method: method, headers: body ? { "Content-Type": "application/json" } : {}, body: body ? JSON.stringify(body) : undefined, cache: "no-store" }); }
    catch (e) { var down = new Error(DOWN[svc]); down.code = "SERVICE_DOWN"; throw down; }
    try { json = await res.json(); } catch (e) { json = null; }
    if (!res.ok || !json || json.status !== "success") {
      var code = json && json.code, err = new Error(friendly(code, json && json.message));
      err.code = code; err.httpStatus = res.status; throw err;
    }
    return json.data;
  }
  // Dữ liệu phụ (tên phim, suất chiếu) để làm giàu hiển thị — lỗi thì trả giá trị dự phòng, không chặn trang.
  async function soft(svc, path, fallback) { try { return await call(svc, "GET", path); } catch (e) { return fallback; } }
  function byId(list) { var o = {}; (list || []).forEach(function (x) { o[x.id] = x; }); return o; }

  /* ---------- Thời gian ---------- */
  // "2026-10-10 18:00:00" hoặc ISO -> Date theo giờ địa phương (không đổi múi giờ)
  function toDate(t) { var m = String(t || "").match(/^(\d{4})-(\d{2})-(\d{2})[T ](\d{2}):(\d{2})(?::(\d{2}))?/); return m ? new Date(+m[1], +m[2] - 1, +m[3], +m[4], +m[5], +(m[6] || 0)) : null; }
  function ymd(d) { return d.getFullYear() + "-" + ("0" + (d.getMonth() + 1)).slice(-2) + "-" + ("0" + d.getDate()).slice(-2); }
  function when(t) {
    var d = toDate(t);
    if (!d) return { date: "", hm: String(t || ""), dm: "", dow: "", full: String(t || "") };
    var hm = ("0" + d.getHours()).slice(-2) + ":" + ("0" + d.getMinutes()).slice(-2), dm = ("0" + d.getDate()).slice(-2) + "/" + ("0" + (d.getMonth() + 1)).slice(-2);
    return { date: ymd(d), hm: hm, dm: dm, dow: DOW[d.getDay()], full: hm + " · " + DOW[d.getDay()] + ", " + dm + "/" + d.getFullYear() };
  }
  function dayLabel(dateStr) {
    var today = ymd(new Date()), t = new Date(); t.setDate(t.getDate() + 1);
    return dateStr === today ? "Hôm nay" : dateStr === ymd(t) ? "Ngày mai" : when(dateStr + " 00:00").dow;
  }
  function upcoming(s) { var d = toDate(s.time); return d && d > new Date(); }
  function mmss(ms) { var s = Math.max(0, Math.ceil(ms / 1000)); return ("0" + Math.floor(s / 60)).slice(-2) + ":" + ("0" + s % 60).slice(-2); }
  function duration(min) { min = Number(min) || 0; var h = Math.floor(min / 60), m = min % 60; return h ? h + " giờ" + (m ? " " + m + " phút" : "") : m + " phút"; }
  function nowHMS() { return new Date().toLocaleTimeString("vi-VN"); }

  function badge(s) { return '<span class="badge ' + esc(s) + '">' + esc(STATUS[s] || s) + "</span>"; }
  function code(b) { return "SOA" + ("00000" + b.id).slice(-6); }       // mã đặt vé — cũng là nội dung chuyển khoản
  function methodOf(v) { return METHODS.filter(function (p) { return p.value === v; })[0]; }

  /* ---------- Poster: ảnh thật trong img/posters (hoặc URL); không có ảnh thì dùng ảnh bìa tự sinh ---------- */
  var PAL = [["#7c2d12", "#f97316"], ["#1e3a8a", "#6366f1"], ["#4c1d95", "#db2777"], ["#064e3b", "#14b8a6"], ["#7f1d1d", "#f43f5e"], ["#713f12", "#eab308"], ["#0c4a6e", "#06b6d4"], ["#3b0764", "#a855f7"]];
  var GENRE_ICON = [[/hành động|action/i, "💥"], [/viễn tưởng|sci/i, "🚀"], [/hoạt hình|anim/i, "🎨"], [/kinh dị|horror/i, "👻"], [/hài|comedy/i, "😂"], [/tình cảm|lãng mạn|romance/i, "💕"], [/tâm lý|drama/i, "🎭"], [/phiêu lưu/i, "🧭"]];
  function hash(s) { var h = 0; s = String(s || ""); for (var i = 0; i < s.length; i++) h = (h * 31 + s.charCodeAt(i)) | 0; return Math.abs(h); }
  function palette(m) { var p = PAL[hash(m && m.title) % PAL.length]; return "--p1:" + p[0] + ";--p2:" + p[1]; }
  function genreIcon(g) { for (var i = 0; i < GENRE_ICON.length; i++) if (GENRE_ICON[i][0].test(g || "")) return GENRE_ICON[i][1]; return "🎬"; }
  function posterSrcs(p) {
    p = String(p || "").trim();
    if (!p) return [];
    if (/^(https?:)?\/\//.test(p)) return [p];
    var f = p.replace(/^.*[\\/]/, "");
    if (!/^[\w.-]+$/.test(f)) return [];
    var a = window.POSTER_DIR + f, b = a.replace(/\.(jpe?g|png|webp)$/i, ".svg");
    return b === a ? [a] : [a, b];
  }
  window.SOA_posterFail = function (img) {
    var rest = (img.getAttribute("data-alt") || "").split("|").filter(Boolean);
    if (rest.length) { img.setAttribute("data-alt", rest.slice(1).join("|")); img.src = rest[0]; } else img.remove();
  };
  function poster(m, cls) {
    m = m || { title: "Phim" };
    var srcs = posterSrcs(m.poster);
    var img = srcs.length ? '<img src="' + esc(srcs[0]) + '" data-alt="' + esc(srcs.slice(1).join("|")) + '" alt="Poster phim ' + esc(m.title) +
      '" loading="lazy" onload="this.parentNode.classList.add(\'has-img\')" onerror="SOA_posterFail(this)">' : "";
    return '<div class="poster ' + (cls || "") + '" style="' + palette(m) + '">' + img + '<span class="poster-emoji">' + genreIcon(m.genre) + '</span><span class="poster-title">' + esc(m.title) + "</span></div>";
  }
  // Nền mờ phía sau (hero/chi tiết): lớp ảnh poster nằm trên lớp màu; ảnh thiếu thì chỉ còn màu
  function backdrop(m) {
    var layers = posterSrcs(m.poster).map(function (s) { return "url('" + s.replace(/'/g, "%27") + "')"; });
    return '<div class="hero-bg" style="' + palette(m) + (layers.length ? ";background-image:" + esc(layers.join(",")) + ",linear-gradient(120deg,var(--p1),var(--p2))" : "") + '"></div>';
  }

  /* ---------- Khung chung ---------- */
  function show(html) { $("#view").innerHTML = html; }
  function toast(msg, type) {
    var t = document.createElement("div"); t.className = "toast " + (type || "ok");
    t.innerHTML = '<span class="ic">' + (type === "err" ? "⚠️" : type === "info" ? "ℹ️" : "✅") + "</span><span>" + esc(msg) + "</span>";
    $("#toasts").appendChild(t); setTimeout(function () { t.remove(); }, 4500);
  }
  function stateBox(icon, title, text, action) { return '<div class="state"><div class="big">' + icon + "</div><h3>" + esc(title) + "</h3><p>" + esc(text) + "</p>" + (action || "") + "</div>"; }
  function errorBox(e, retry) {
    return stateBox(e.code === "SERVICE_DOWN" ? "🔌" : "⚠️", e.code === "SERVICE_DOWN" ? "Mất kết nối tới hệ thống" : "Đã xảy ra lỗi", e.message,
      retry === false ? "" : '<button class="btn btn-ghost" data-retry>Thử lại</button>');
  }
  function bindRetry(fn) { var b = $("[data-retry]"); if (b) b.onclick = fn; }
  function back(href, label) { return '<a class="back" href="' + href + '">← ' + esc(label) + "</a>"; }
  function live(id) { return '<span class="live" id="' + id + '" title="Dữ liệu tự cập nhật"><i></i>Cập nhật trực tiếp</span>'; }
  function liveTick(id, ok) { var el = $("#" + id); if (el) { el.classList.toggle("off", !ok); el.lastChild.textContent = ok ? "Cập nhật lúc " + nowHMS() : "Mất kết nối, đang thử lại..."; } }
  function steps(active) {
    var names = ["Chọn suất chiếu", "Chọn ghế", "Thanh toán", "Nhận vé"];
    return '<div class="steps">' + names.map(function (n, i) {
      var cls = i < active ? "done" : i === active ? "on" : "";
      return (i ? '<span class="sep"></span>' : "") + '<span class="step ' + cls + '"><i>' + (i < active ? "✓" : i + 1) + "</i>" + n + "</span>";
    }).join("") + "</div>";
  }
  function needLogin(next) {
    if (user) return false;
    sessionStorage.setItem("soa.next", next || location.hash); toast("Vui lòng đăng nhập để tiếp tục", "info"); location.hash = "#/login";
    return true;
  }
  async function copy(text, label) {
    try { await navigator.clipboard.writeText(text); toast("Đã sao chép " + label); }
    catch (e) { toast("Không sao chép được, vui lòng chép thủ công", "err"); }
  }

  function nav() {
    var h = location.hash || "#/";
    var mine = /^#\/(my|ticket|pay|result)/.test(h), auth = /^#\/(login|register)/.test(h);
    var links = [["#/", "Phim", !mine && !auth], ["#/my", "Vé của tôi", mine]];
    $("#mainnav").innerHTML = links.map(function (l) { return '<a href="' + l[0] + '" class="' + (l[2] ? "active" : "") + '">' + l[1] + "</a>"; }).join("");
    $("#account").innerHTML = user
      ? '<span class="user-chip" title="' + esc(user.username) + '"><span class="avatar">' + esc(user.username.charAt(0).toUpperCase()) + '</span><span class="name">' + esc(user.username) + '</span></span><button class="btn btn-text btn-sm" id="logout">Đăng xuất</button>'
      : '<a class="btn btn-ghost btn-sm" href="#/login">Đăng nhập</a><a class="btn btn-primary btn-sm" href="#/register">Đăng ký</a>';
    var lo = $("#logout"); if (lo) lo.onclick = function () { user = null; sessionStorage.removeItem("soa.user"); toast("Đã đăng xuất"); location.hash = "#/"; nav(); };
  }

  /* ---------- Trang chủ ---------- */
  async function home() {
    var alive = current();
    show('<div class="skel" style="height:300px;border-radius:22px;margin-bottom:40px"></div><div class="grid">' +
      Array(5).join('<div><div class="skel" style="aspect-ratio:2/3"></div><div class="skel" style="height:16px;margin-top:12px;width:70%"></div></div>') + "</div>");
    var movies, sts;
    try { movies = await call("movie", "GET", "/api/movies"); } catch (e) { if (alive()) { show(errorBox(e)); bindRetry(home); } return; }
    sts = await soft("showtime", "/api/showtimes?upcoming=1", null);
    if (!alive()) return;
    if (sts) sts = sts.filter(upcoming);
    if (!movies.length) { show(stateBox("🎞️", "Chưa có phim nào", "Rạp đang cập nhật lịch chiếu. Vui lòng quay lại sau.")); return; }
    var count = {}, today = {}, todayStr = ymd(new Date());
    (sts || []).forEach(function (s) { count[s.movieId] = (count[s.movieId] || 0) + 1; if (when(s.time).date === todayStr) today[s.movieId] = (today[s.movieId] || 0) + 1; });
    var featured = movies.slice().sort(function (a, b) { return (count[b.id] || 0) - (count[a.id] || 0); })[0];
    var genres = []; movies.forEach(function (m) { if (m.genre && genres.indexOf(m.genre) < 0) genres.push(m.genre); });
    var state = { q: "", g: "" };

    show('<section class="hero" style="' + palette(featured) + '">' + backdrop(featured) + '<div class="hero-in"><div>' +
      '<span class="eyebrow">★ Phim nổi bật</span><h1>' + esc(featured.title) + '</h1><div class="meta"><span class="chip">' + genreIcon(featured.genre) + " " + esc(featured.genre) +
      '</span><span class="chip">⏱ ' + duration(featured.duration) + "</span>" + (today[featured.id] ? '<span class="chip">🎫 Hôm nay còn ' + today[featured.id] + " suất</span>" : "") + "</div>" +
      '<div class="actions"><a class="btn btn-primary btn-lg" href="#/movie/' + featured.id + '">Đặt vé ngay</a><a class="btn btn-ghost btn-lg" href="#movies" id="to-list">Xem tất cả phim</a></div></div>' +
      poster(featured) + "</div></section>" +
      '<section id="movies"><div class="section-head"><div><h2>Phim đang chiếu</h2><div class="muted small" id="m-count"></div></div></div>' +
      '<div class="filters"><label class="search">' + ICON_SEARCH + '<input class="input" id="q" placeholder="Tìm tên phim..." aria-label="Tìm phim"></label>' +
      '<div class="genres" id="genres">' + ['<button class="genre on" data-g="">Tất cả</button>'].concat(genres.map(function (g) { return '<button class="genre" data-g="' + esc(g) + '">' + esc(g) + "</button>"; })).join("") + "</div></div>" +
      '<div id="grid"></div></section>');

    function render() {
      var q = state.q.toLowerCase();
      var list = movies.filter(function (m) { return (!state.g || m.genre === state.g) && (!q || String(m.title).toLowerCase().indexOf(q) >= 0); });
      $("#m-count").textContent = list.length + " phim" + (sts ? "" : " · lịch chiếu đang được cập nhật");
      $("#grid").innerHTML = list.length ? '<div class="grid">' + list.map(function (m) {
        var tag = !sts ? "" : today[m.id] ? "Hôm nay " + today[m.id] + " suất" : count[m.id] ? count[m.id] + " suất sắp tới" : "Sắp chiếu";
        return '<a class="mcard" href="#/movie/' + m.id + '"><div style="position:relative">' + poster(m) + (tag ? '<span class="tag">' + tag + "</span>" : "") +
          "</div><h3>" + esc(m.title) + '</h3><div class="sub">' + esc(m.genre) + " · " + duration(m.duration) + "</div></a>";
      }).join("") + "</div>" : stateBox("🔍", "Không tìm thấy phim", "Thử từ khóa khác hoặc chọn thể loại khác.");
    }
    $("#q").oninput = function () { state.q = this.value.trim(); render(); };
    $$("#genres .genre").forEach(function (b) { b.onclick = function () { state.g = b.dataset.g; $$("#genres .genre").forEach(function (x) { x.classList.toggle("on", x === b); }); render(); }; });
    $("#to-list").onclick = function (ev) { ev.preventDefault(); $("#movies").scrollIntoView(); };
    render();
  }

  /* ---------- Chi tiết phim + lịch chiếu (tự cập nhật: suất đã bắt đầu biến mất, số ghế trống thay đổi) ---------- */
  async function movie(id) {
    var alive = current();
    show(back("#/", "Danh sách phim") + '<div class="skel" style="height:320px;border-radius:22px"></div>');
    var m;
    try { m = await call("movie", "GET", "/api/movies/" + encodeURIComponent(id)); }
    catch (e) { if (alive()) { show(back("#/", "Danh sách phim") + errorBox(e)); bindRetry(function () { movie(id); }); } return; }
    if (!alive()) return;
    var sts = [], free = null, stErr = null, cur = null;

    show(back("#/", "Danh sách phim") +
      '<section class="detail" style="' + palette(m) + '">' + backdrop(m) + '<div class="detail-in">' + poster(m) +
      '<div><span class="eyebrow">' + genreIcon(m.genre) + " " + esc(m.genre) + "</span><h1>" + esc(m.title) + "</h1>" +
      '<div class="facts" id="facts"></div><a class="btn btn-primary" href="#showtimes" id="to-st">Chọn suất chiếu</a></div></div></section>' +
      '<section id="showtimes"><div class="section-head"><h2>Lịch chiếu</h2>' + live("st-live") + '</div><div id="st-body"><div class="skel" style="height:160px"></div></div></section>');
    $("#to-st").onclick = function (ev) { ev.preventDefault(); $("#showtimes").scrollIntoView(); };

    async function load() {
      try { sts = (await call("showtime", "GET", "/api/showtimes?upcoming=1&movieId=" + encodeURIComponent(id))).filter(upcoming); stErr = null; }
      catch (e) { stErr = e; }
      if (!stErr && sts.length) {
        var av = await soft("booking", "/api/booking/availability?showtimeIds=" + sts.map(function (s) { return s.id; }).join(","), null);
        free = av ? {} : null; (av || []).forEach(function (a) { free[a.showtimeId] = TOTAL_SEATS - a.taken; });
      }
      if (!alive()) return;
      liveTick("st-live", !stErr);
      render();
    }
    function render() {
      sts.sort(function (a, b) { return String(a.time).localeCompare(String(b.time)); });
      var minPrice = sts.length ? Math.min.apply(null, sts.map(function (s) { return s.price; })) : 0;
      $("#facts").innerHTML = "<div><span>Thời lượng</span><b>" + duration(m.duration) + "</b></div><div><span>Suất sắp chiếu</span><b>" + (stErr ? "—" : sts.length) + "</b></div>" +
        (minPrice ? "<div><span>Giá từ</span><b>" + money(minPrice) + "</b></div>" : "");
      var body = $("#st-body");
      if (stErr && !sts.length) { body.innerHTML = errorBox(stErr); bindRetry(load); return; }
      if (!sts.length) { body.innerHTML = stateBox("🗓️", "Chưa có suất chiếu", "Phim này chưa có suất chiếu sắp tới. Hãy quay lại sau nhé."); return; }
      var dates = []; sts.forEach(function (s) { var d = when(s.time).date; if (dates.indexOf(d) < 0) dates.push(d); });
      if (dates.indexOf(cur) < 0) cur = dates[0];
      var day = sts.filter(function (s) { return when(s.time).date === cur; }), groups = {}, order = [];
      day.forEach(function (s) { if (!groups[s.cinema]) { groups[s.cinema] = []; order.push(s.cinema); } groups[s.cinema].push(s); });
      body.innerHTML = '<div class="dates" role="tablist">' + dates.map(function (d) {
        var w = when(d + " 00:00");
        return '<button class="date' + (d === cur ? " on" : "") + '" data-d="' + d + '" role="tab" aria-selected="' + (d === cur) + '"><small>' + dayLabel(d) + "</small><b>" + w.dm + "</b></button>";
      }).join("") + "</div>" + order.map(function (c) {
        return '<div class="cinema"><h3><span class="pin">📍</span>' + esc(c) + '</h3><div class="times">' + groups[c].map(function (s) {
          var f = free ? free[s.id] : null, out = f === 0;
          var seat = f == null ? "" : out ? '<em class="seats out">Hết vé</em>' : '<em class="seats' + (f <= 10 ? " low" : "") + '">Còn ' + f + " ghế</em>";
          return '<button class="time" data-st="' + s.id + '"' + (out ? " disabled" : "") + "><b>" + when(s.time).hm + "</b><span>Phòng " + esc(s.room) + " · " + money(s.price) + "</span>" + seat + "</button>";
        }).join("") + "</div></div>";
      }).join("");
      $$("#st-body .date").forEach(function (b) { b.onclick = function () { cur = b.dataset.d; render(); }; });
      $$("#st-body [data-st]").forEach(function (b) { b.onclick = function () { location.hash = "#/book/" + id + "/" + b.dataset.st; }; });
    }
    await load();
    every(load, 30000);
  }

  /* ---------- Chọn ghế (sơ đồ tự cập nhật mỗi 5 giây) ---------- */
  async function book(movieId, stId, notice) {
    if (needLogin()) return;
    var alive = current(), backLink = back("#/movie/" + movieId, "Đổi suất chiếu");
    show(backLink + steps(1) + '<div class="book"><div class="skel" style="height:420px"></div><div class="skel" style="height:420px"></div></div>');
    var st, taken, m, mine;
    try {
      st = await call("showtime", "GET", "/api/showtimes/" + encodeURIComponent(stId));
      taken = (await call("booking", "GET", "/api/booking/seats?showtimeId=" + encodeURIComponent(stId))).seats || [];
    } catch (e) { if (alive()) { show(backLink + errorBox(e)); bindRetry(function () { book(movieId, stId); }); } return; }
    var extra = await Promise.all([soft("movie", "/api/movies/" + encodeURIComponent(movieId), null),
      soft("booking", "/api/booking?status=PENDING&username=" + encodeURIComponent(user.username), [])]);
    if (!alive()) return;
    m = extra[0] || { id: movieId, title: "Phim", genre: "" };
    mine = extra[1].filter(function (b) { return String(b.showtimeId) === String(stId); })[0];
    if (!upcoming(st)) {
      show(backLink + stateBox("⏰", "Suất chiếu đã bắt đầu", "Suất " + when(st.time).full + " không còn nhận đặt vé. Vui lòng chọn suất khác.",
        '<a class="btn btn-primary" href="#/movie/' + movieId + '">Chọn suất khác</a>'));
      return;
    }
    var picked = [], w = when(st.time);

    var hall = "";
    MAP.rows.split("").forEach(function (r) {
      hall += '<div class="srow"><span class="rl">' + r + "</span>";
      for (var c = 1; c <= MAP.cols; c++) {
        hall += '<button class="seat" data-seat="' + r + c + '" aria-pressed="false">' + c + "</button>";
        if (MAP.aisleAfter.indexOf(c) >= 0) hall += '<span class="aisle"></span>';
      }
      hall += '<span class="rl">' + r + "</span></div>";
    });

    show(backLink + steps(1) +
      (mine ? '<div class="alert info">⏳ Bạn đang giữ ghế ' + esc(mine.seats.join(", ")) + ' cho suất này (đơn ' + code(mine) + ') nhưng chưa thanh toán.<a class="btn btn-primary btn-sm" style="margin-left:auto" href="#/pay/' + mine.id + '">Tiếp tục thanh toán</a></div>' : "") +
      '<div class="book"><div class="panel"><div class="panel-head"><b>Sơ đồ ghế · Phòng ' + esc(st.room) + "</b>" + live("seat-live") + "</div>" +
      '<div class="hall"><div class="hall-in"><div class="screen"><span>MÀN HÌNH</span></div>' + hall + "</div></div>" +
      '<div class="legend"><span><i></i>Ghế trống</span><span><i class="sel"></i>Đang chọn</span><span><i class="taken"></i>Đã có người đặt</span></div></div>' +
      '<aside class="panel summary"><div class="sum-movie">' + poster(m, "sm") + "<div><h3>" + esc(m.title) + '</h3><div class="muted small">' + esc(st.cinema) + "</div></div></div>" +
      '<div class="kv"><span>Suất chiếu</span><b>' + w.hm + " · " + dayLabel(w.date) + " " + w.dm + '</b></div><div class="kv"><span>Phòng</span><b>' + esc(st.room) + '</b></div><div class="kv"><span>Giá vé</span><b>' + money(st.price) + " / ghế</b></div>" +
      '<div class="kv"><span>Ghế đã chọn</span><b id="cnt">0 / ' + MAP.maxSeats + '</b></div><div class="seat-chips" id="chips"></div>' +
      '<div class="total"><span class="muted">Tổng cộng</span><b id="sum">0 đ</b></div>' +
      '<div id="err">' + (notice ? '<div class="alert">⚠ ' + esc(notice) + "</div>" : "") + '</div><button class="btn btn-primary btn-lg btn-block" id="hold" disabled>Giữ ghế &amp; thanh toán</button>' +
      '<p class="muted small" style="text-align:center;margin:10px 0 0">Ghế được giữ trong 10 phút để bạn hoàn tất thanh toán.</p></aside></div>');

    function paint() {
      $$(".seat").forEach(function (b) {
        var c = b.dataset.seat, t = taken.indexOf(c) >= 0, sel = picked.indexOf(c) >= 0;
        b.classList.toggle("taken", t); b.classList.toggle("sel", sel); b.disabled = t;
        b.setAttribute("aria-pressed", String(sel)); b.setAttribute("aria-label", c + (t ? " đã có người đặt" : sel ? " đang chọn" : " trống"));
      });
      $("#cnt").textContent = picked.length + " / " + MAP.maxSeats;
      $("#chips").innerHTML = picked.length ? picked.map(function (c) { return '<span class="c">' + c + "</span>"; }).join("") : '<span class="muted small">Chọn ghế trên sơ đồ</span>';
      $("#sum").textContent = money(picked.length * st.price);
      $("#hold").disabled = !picked.length;
    }
    $$(".seat").forEach(function (b) {
      b.onclick = function () {
        var c = b.dataset.seat, i = picked.indexOf(c);
        if (i >= 0) picked.splice(i, 1);
        else if (picked.length >= MAP.maxSeats) { toast("Mỗi đơn đặt tối đa " + MAP.maxSeats + " ghế", "err"); return; }
        else picked.push(c);
        picked.sort(function (a, z) { return a.charCodeAt(0) - z.charCodeAt(0) || parseInt(a.slice(1)) - parseInt(z.slice(1)); });
        paint();
      };
    });
    async function refreshSeats() {
      var r = await soft("booking", "/api/booking/seats?showtimeId=" + encodeURIComponent(stId), null);
      if (!alive()) return;
      liveTick("seat-live", !!r);
      if (!r) return;
      taken = r.seats || [];
      var lost = picked.filter(function (c) { return taken.indexOf(c) >= 0; });
      if (lost.length) { picked = picked.filter(function (c) { return lost.indexOf(c) < 0; }); toast("Ghế " + lost.join(", ") + " vừa được người khác đặt", "err"); }
      if (!upcoming(st)) { book(movieId, stId); return; }
      paint();
    }
    $("#hold").onclick = async function () {
      var btn = this;
      btn.disabled = true; btn.innerHTML = '<span class="spinner"></span> Đang giữ ghế...'; $("#err").innerHTML = "";
      try {
        var r = await call("booking", "POST", "/api/booking", { username: user.username, movieId: Number(movieId), showtimeId: Number(stId), seats: picked, payNow: false });
        location.hash = "#/pay/" + r.id;
      } catch (e) {
        if (e.code === "SEAT_TAKEN") { book(movieId, stId, e.message + ". Sơ đồ ghế đã được cập nhật, vui lòng chọn lại."); return; }
        if (e.code === "SHOWTIME_CLOSED") { book(movieId, stId); return; }
        $("#err").innerHTML = '<div class="alert">⚠ ' + esc(e.message) + "</div>"; btn.innerHTML = "Giữ ghế &amp; thanh toán"; btn.disabled = false;
      }
    };
    paint(); liveTick("seat-live", true);
    every(refreshSeats, 5000);
  }

  /* ---------- Dữ liệu một đơn của người đang đăng nhập (kèm phim, suất chiếu) ---------- */
  async function loadOrder(id) {
    var b = await call("booking", "GET", "/api/booking/" + encodeURIComponent(id));
    if (b.username !== user.username) { var e = new Error(FRIENDLY.FORBIDDEN); e.code = "FORBIDDEN"; throw e; }
    var r = await Promise.all([soft("movie", "/api/movies/" + b.movieId, null), soft("showtime", "/api/showtimes/" + b.showtimeId, null)]);
    return { b: b, m: r[0] || { id: b.movieId, title: "Phim", genre: "" }, st: r[1] };
  }
  function orderSummary(o, extra) {
    var b = o.b, st = o.st, w = st ? when(st.time) : null;
    return '<div class="sum-movie">' + poster(o.m, "sm") + "<div><h3>" + esc(o.m.title) + '</h3><div class="muted small">' + esc(st ? st.cinema : "") + "</div></div></div>" +
      (w ? '<div class="kv"><span>Suất chiếu</span><b>' + w.hm + " · " + dayLabel(w.date) + " " + w.dm + '</b></div><div class="kv"><span>Phòng</span><b>' + esc(st.room) + "</b></div>" : "") +
      '<div class="kv"><span>Ghế</span><b>' + esc(b.seats.join(", ")) + '</b></div><div class="kv"><span>Mã đặt vé</span><b>' + code(b) + "</b></div>" +
      '<div class="total"><span class="muted">Tổng thanh toán</span><b>' + money(b.totalPrice) + "</b></div>" + (extra || "");
  }

  /* ---------- Thanh toán đơn đang giữ ghế ---------- */
  async function pay(id) {
    if (needLogin()) return;
    var alive = current();
    show(steps(2) + '<div class="book"><div class="skel" style="height:520px"></div><div class="skel" style="height:420px"></div></div>');
    var o;
    try { o = await loadOrder(id); } catch (e) { if (alive()) { show(back("#/my", "Vé của tôi") + errorBox(e, e.code !== "FORBIDDEN" && e.code !== "NOT_FOUND")); bindRetry(function () { pay(id); }); } return; }
    if (!alive()) return;
    if (o.b.status === "PAID") { location.hash = "#/ticket/" + id; return; }
    if (o.b.status === "CANCELLED") { expired(o); return; }

    var b = o.b, deadline = toDate(b.expiresAt), method = sessionStorage.getItem("soa.method") || METHODS[0].value, busy = false;
    if (!methodOf(method)) method = METHODS[0].value;
    show(back("#/my", "Vé của tôi") + steps(2) + '<div class="book pay">' +
      '<div class="panel"><div class="panel-head"><b>Chọn phương thức thanh toán</b><span class="hold-mini" id="left2"></span></div><div class="methods" id="methods">' + METHODS.map(function (p) {
        return '<label class="method"><input type="radio" name="method" value="' + p.value + '"' + (p.value === method ? " checked" : "") + "><span><b>" + esc(p.label) + "</b><small>" + esc(p.hint) +
          '</small></span><span class="logo ' + p.value + '">' + esc(p.logo) + "</span></label>";
      }).join("") + '</div><div id="pay-box"></div></div>' +
      '<aside class="panel summary"><div class="hold" id="hold"><span>Thời gian giữ ghế</span><b id="left">--:--</b><div class="bar"><i id="bar"></i></div></div>' +
      orderSummary(o) + '<div id="err"></div><button class="btn btn-primary btn-lg btn-block" id="paid">Tôi đã thanh toán</button>' +
      '<button class="btn btn-text btn-block" id="cancel" style="margin-top:8px">Hủy đơn &amp; nhả ghế</button></aside></div>');

    function box() {
      var p = methodOf(method), amount = b.totalPrice, ref = code(b), qr, info;
      if (method === "BANK_TRANSFER") {
        qr = QR.vietQR({ bin: BANK.bin, account: BANK.account, amount: amount, content: ref });
        info = row("Ngân hàng", esc(BANK.bank)) + row("Số tài khoản", esc(BANK.account), BANK.account, "số tài khoản") + row("Chủ tài khoản", esc(BANK.holder)) +
          row("Số tiền", money(amount), String(amount), "số tiền") + row("Nội dung chuyển khoản", '<b class="ref">' + ref + "</b>", ref, "nội dung");
      } else {
        qr = "SOACINEMA|" + method + "|" + ref + "|" + amount;
        info = row("Đơn vị nhận", "SOA Cinema") + row("Mã đơn hàng", '<b class="ref">' + ref + "</b>", ref, "mã đơn hàng") + row("Số tiền", money(amount), String(amount), "số tiền");
      }
      var stepsTxt = method === "BANK_TRANSFER"
        ? ["Mở ứng dụng ngân hàng, chọn <b>Quét mã QR</b>.", "Kiểm tra đúng số tiền và nội dung <b>" + ref + "</b> (đã điền sẵn).", "Xác nhận chuyển tiền, sau đó bấm <b>Tôi đã thanh toán</b>."]
        : method === "MOMO"
          ? ["Mở ứng dụng <b>MoMo</b>, chọn biểu tượng <b>Quét mã</b>.", "Quét mã QR bên cạnh và kiểm tra số tiền.", "Xác nhận thanh toán, sau đó bấm <b>Tôi đã thanh toán</b>."]
          : ["Mở app ngân hàng hoặc ví hỗ trợ <b>VNPAY-QR</b>.", "Quét mã QR bên cạnh và kiểm tra số tiền.", "Xác nhận thanh toán, sau đó bấm <b>Tôi đã thanh toán</b>."];
      $("#pay-box").innerHTML = '<div class="paybox ' + method + '"><div class="qr-wrap"><div class="qr">' + QR.svg(qr, { label: "Mã QR thanh toán " + p.label }) + '</div><span class="qr-cap">' + esc(p.logo) + " · " + money(amount) + "</span></div>" +
        '<div class="pay-info">' + info + '<ol class="howto">' + stepsTxt.map(function (s) { return "<li>" + s + "</li>"; }).join("") + "</ol></div></div>" +
        (window.PAYMENT_SANDBOX ? '<div class="alert info sandbox"><span>ⓘ</span><span>Môi trường thử nghiệm: hệ thống chưa kết nối cổng thanh toán thật, vui lòng <b>không chuyển tiền thật</b>. Bấm <b>Tôi đã thanh toán</b> để mô phỏng ngân hàng xác nhận giao dịch.</span></div>' : "");
      $$("#pay-box [data-copy]").forEach(function (el) { el.onclick = function () { copy(el.dataset.copy, el.dataset.label); }; });
    }
    function row(k, v, copyVal, label) {
      return '<div class="kv"><span>' + k + "</span><b>" + v + (copyVal ? ' <button class="copy" type="button" data-copy="' + esc(copyVal) + '" data-label="' + esc(label) + '" aria-label="Sao chép ' + esc(label) + '">' + ICON_COPY + "</button>" : "") + "</b></div>";
    }
    function tick() {
      var left = deadline ? deadline - new Date() : 0, total = 10 * 60 * 1000;
      $("#left").textContent = mmss(left);
      $("#left2").textContent = "Giữ ghế còn " + mmss(left);
      $("#left2").classList.toggle("urgent", left < 60000);
      $("#bar").style.width = Math.max(0, Math.min(100, left / total * 100)) + "%";
      $("#hold").classList.toggle("urgent", left < 60000);
      if (deadline && left <= 0 && !busy) { busy = true; recheck(); }
    }
    async function recheck() {   // hỏi lại trạng thái đơn: hết hạn / đã thanh toán ở nơi khác
      var nb = await soft("booking", "/api/booking/" + id, null);
      if (!alive() || !nb) { busy = false; return; }
      if (nb.status === "PAID") { location.hash = "#/ticket/" + id; return; }
      if (nb.status === "CANCELLED") { o.b = nb; leave(); expired(o); return; }
      busy = false;
    }
    $$("#methods input").forEach(function (r) { r.onchange = function () { method = r.value; sessionStorage.setItem("soa.method", method); box(); }; });
    $("#paid").onclick = async function () {
      var btn = this; if (busy) return;
      busy = true; btn.disabled = true; btn.innerHTML = '<span class="spinner"></span> Đang xác nhận giao dịch...'; $("#err").innerHTML = "";
      try {
        var r = await call("booking", "POST", "/api/booking/" + id + "/pay", { username: user.username, paymentMethod: method });
        if (r.status === "PAID") {
          sessionStorage.setItem("soa.paid." + id, JSON.stringify({ method: method, transactionId: r.payment && r.payment.transactionId, notification: r.notification }));
          location.hash = "#/ticket/" + id + "/new"; return;
        }
        $("#err").innerHTML = '<div class="alert">⚠ Giao dịch chưa thành công. Ghế vẫn được giữ — vui lòng thử lại hoặc chọn phương thức khác.</div>';
      } catch (e) {
        if (e.code === "ALREADY_PAID") { location.hash = "#/ticket/" + id; return; }
        if (e.code === "BOOKING_CANCELLED") { recheck(); return; }
        $("#err").innerHTML = '<div class="alert">⚠ ' + esc(e.message) + "</div>";
      }
      busy = false; btn.disabled = false; btn.textContent = "Tôi đã thanh toán";
    };
    var armed = false;
    $("#cancel").onclick = async function () {
      var btn = this;
      if (!armed) { armed = true; btn.textContent = "Bấm lần nữa để xác nhận hủy đơn"; btn.classList.add("danger"); setTimeout(function () { armed = false; btn.innerHTML = "Hủy đơn &amp; nhả ghế"; btn.classList.remove("danger"); }, 4000); return; }
      btn.disabled = true;
      try { await call("booking", "POST", "/api/booking/" + id + "/cancel", { username: user.username }); toast("Đã hủy đơn " + code(b) + ", ghế đã được nhả"); location.hash = "#/my"; }
      catch (e) { toast(e.message, "err"); btn.disabled = false; }
    };
    box(); tick();
    every(tick, 1000);
    every(function () { if (!busy) { busy = true; recheck(); } }, 5000);
  }
  function expired(o) {
    show(back("#/my", "Vé của tôi") + stateBox("⌛", "Đơn đã hết thời gian giữ ghế", "Đơn " + code(o.b) + " chưa được thanh toán trong thời gian giữ chỗ nên đã tự hủy và ghế đã được nhả. Bạn có thể đặt lại nếu suất chiếu vẫn còn.",
      '<a class="btn btn-primary" href="#/book/' + o.b.movieId + "/" + o.b.showtimeId + '">Chọn lại ghế</a> <a class="btn btn-ghost" href="#/my">Vé của tôi</a>'));
  }

  /* ---------- Vé điện tử ---------- */
  async function ticket(id, fresh) {
    if (needLogin()) return;
    var alive = current();
    show('<div class="skel" style="height:360px;max-width:880px;margin:0 auto;border-radius:20px"></div>');
    var o;
    try { o = await loadOrder(id); } catch (e) { if (alive()) { show(back("#/my", "Vé của tôi") + errorBox(e, e.code !== "FORBIDDEN" && e.code !== "NOT_FOUND")); bindRetry(function () { ticket(id, fresh); }); } return; }
    if (!alive()) return;
    var b = o.b, m = o.m, st = o.st || {}, w = when(st.time);
    if (b.status === "PENDING") { location.hash = "#/pay/" + id; return; }
    if (b.status === "CANCELLED") { expired(o); return; }
    var paid = null; try { paid = JSON.parse(sessionStorage.getItem("soa.paid." + id) || "null"); } catch (e) {}
    var pm = paid && methodOf(paid.method), started = st.time && !upcoming(st);
    var note = fresh ? (paid && paid.notification === "FAILED" ? "Vé đã được xác nhận. Email xác nhận sẽ được gửi lại sau ít phút." : "Email xác nhận đã được gửi tới tài khoản của bạn.") : "";
    var qrText = "SOACINEMA|" + code(b) + "|" + b.username + "|" + b.showtimeId + "|" + b.seats.join(",");
    show((fresh ? steps(3) : back("#/my", "Vé của tôi")) + '<div class="ticket"><div class="ticket-main">' + poster(m) + "<div>" +
      '<div class="status-head"><span class="status-ic ok">✓</span><div><h2>' + (fresh ? "Thanh toán thành công!" : "Vé xem phim") + "</h2></div></div>" +
      (note ? '<p class="muted" style="margin:4px 0 0">' + note + "</p>" : "") +
      '<div class="tgrid"><div><span>Phim</span><b>' + esc(m.title) + "</b></div><div><span>Rạp</span><b>" + esc(st.cinema || "—") + "</b></div>" +
      "<div><span>Suất chiếu</span><b>" + esc(st.time ? w.full : "—") + "</b></div><div><span>Phòng</span><b>" + esc(st.room || "—") + "</b></div>" +
      "<div><span>Ghế (" + b.seats.length + " vé)</span><b>" + esc(b.seats.join(", ")) + "</b></div><div><span>Tổng tiền</span><b>" + money(b.totalPrice) + "</b></div>" +
      (pm ? "<div><span>Thanh toán</span><b>" + esc(pm.label) + "</b></div>" : "") + "<div><span>Đặt lúc</span><b>" + esc(when(b.createdAt).full) + "</b></div></div></div></div>" +
      '<div class="ticket-stub"><div><div class="muted small">Mã đặt vé</div><div class="code">' + code(b) + "</div></div>" +
      '<div class="tqr">' + QR.svg(qrText, { label: "Mã QR soát vé" }) + "</div>" + (started ? '<span class="badge CANCELLED">Suất chiếu đã diễn ra</span>' : badge(b.status)) +
      '<div class="muted small">Đưa mã này cho nhân viên soát vé tại rạp</div></div></div>' +
      '<div class="ticket-actions"><button class="btn btn-ghost" id="print">In / lưu vé</button><a class="btn btn-primary" href="#/my">Vé của tôi</a><a class="btn btn-ghost" href="#/">Đặt thêm vé</a></div>');
    $("#print").onclick = function () { window.print(); };
  }

  /* ---------- Vé của tôi ---------- */
  async function my() {
    if (needLogin("#/my")) return;
    var alive = current(), cur = sessionStorage.getItem("soa.tab") || "";
    var head = '<div class="section-head"><div><h2>Vé của tôi</h2><div class="muted small">Các đơn đặt vé của tài khoản ' + esc(user.username) + "</div></div>" + live("my-live") + "</div>";
    show(head + '<div class="tlist">' + Array(4).join('<div class="skel" style="height:100px"></div>') + "</div>");
    var rows, movies = {}, shows = {};
    async function load(first) {
      try { rows = await call("booking", "GET", "/api/booking?username=" + encodeURIComponent(user.username)); }
      catch (e) { if (!alive()) return; if (first) { show(head + errorBox(e)); bindRetry(my); } else liveTick("my-live", false); return false; }
      if (first) {
        var info = await Promise.all([soft("movie", "/api/movies", []), soft("showtime", "/api/showtimes", [])]);
        movies = byId(info[0]); shows = byId(info[1]);
      }
      if (!alive()) return false;
      rows.sort(function (a, b) { return b.id - a.id; });
      return true;
    }
    if (!await load(true)) return;
    if (!rows.length) { show(head + stateBox("🎟️", "Bạn chưa có vé nào", "Chọn một bộ phim và đặt vé đầu tiên của bạn.", '<a class="btn btn-primary" href="#/">Khám phá phim</a>')); return; }

    var tabs = [["", "Tất cả"], ["PENDING", "Chờ thanh toán"], ["PAID", "Đã thanh toán"], ["CANCELLED", "Đã hủy"]];
    show(head + '<div id="pending-note"></div><div class="tabs" id="tabs" role="tablist"></div><div id="list"></div>');
    function render() {
      var pending = rows.filter(function (b) { return b.status === "PENDING"; });
      $("#pending-note").innerHTML = pending.length ? '<div class="alert info">⏳ Bạn có ' + pending.length + " đơn đang giữ ghế chờ thanh toán. Hoàn tất trước khi hết thời gian giữ chỗ để không mất ghế.</div>" : "";
      $("#tabs").innerHTML = tabs.map(function (t) {
        var n = rows.filter(function (b) { return !t[0] || b.status === t[0]; }).length;
        return '<button class="tab' + (t[0] === cur ? " on" : "") + '" data-t="' + t[0] + '">' + t[1] + "<em>" + n + "</em></button>";
      }).join("");
      var list = rows.filter(function (b) { return !cur || b.status === cur; });
      $("#list").innerHTML = list.length ? '<div class="tlist">' + list.map(function (b) {
        var mv = movies[b.movieId] || { title: "Phim", genre: "" }, s = shows[b.showtimeId], w = s ? when(s.time) : null, right;
        if (b.status === "PENDING") right = '<span class="price">' + money(b.totalPrice) + '</span><span class="countdown" data-exp="' + esc(b.expiresAt || "") + '">Giữ ghế còn --:--</span>' +
          '<div class="row-actions"><button class="btn btn-text btn-sm" data-cancel="' + b.id + '">Hủy</button><a class="btn btn-primary btn-sm" href="#/pay/' + b.id + '">Thanh toán</a></div>';
        else if (b.status === "PAID") right = '<span class="price">' + money(b.totalPrice) + "</span>" + badge(b.status) + '<a class="btn btn-ghost btn-sm" href="#/ticket/' + b.id + '">Xem vé →</a>';
        else right = '<span class="price">' + money(b.totalPrice) + "</span>" + badge(b.status) + (s && upcoming(s) ? '<a class="btn btn-text btn-sm" href="#/book/' + b.movieId + "/" + b.showtimeId + '">Đặt lại</a>' : "");
        return '<article class="trow ' + esc(b.status) + '">' + poster(mv, "sm") + "<div><h3>" + esc(mv.title) + '</h3><div class="line">' +
          (s ? "<span>📍 " + esc(s.cinema) + " · " + esc(s.room) + "</span><span>🕒 " + w.hm + " · " + w.dm + "/" + s.time.slice(0, 4) + "</span>" : "") +
          "<span>💺 " + esc(b.seats.join(", ")) + '</span></div><div class="muted small" style="margin-top:4px">Mã đặt vé ' + code(b) + " · đặt lúc " + esc(when(b.createdAt).full) + "</div></div>" +
          '<div class="right">' + right + "</div></article>";
      }).join("") + "</div>" : stateBox("🗂️", "Không có đơn nào", "Không có đơn đặt vé ở trạng thái này.");
      $$("#tabs .tab").forEach(function (t) { t.onclick = function () { cur = t.dataset.t; sessionStorage.setItem("soa.tab", cur); render(); }; });
      $$("[data-cancel]").forEach(function (btn) {
        btn.onclick = async function () {
          if (btn.dataset.armed !== "1") { btn.dataset.armed = "1"; btn.textContent = "Xác nhận hủy?"; btn.classList.add("danger"); return; }
          btn.disabled = true;
          try { await call("booking", "POST", "/api/booking/" + btn.dataset.cancel + "/cancel", { username: user.username }); toast("Đã hủy đơn và nhả ghế"); refresh(); }
          catch (e) { toast(e.message, "err"); btn.disabled = false; }
        };
      });
      countdown(); liveTick("my-live", true);
    }
    function countdown() {
      var expiredNow = false;
      $$(".countdown").forEach(function (el) {
        var d = toDate(el.dataset.exp), left = d ? d - new Date() : 0;
        el.textContent = left > 0 ? "Giữ ghế còn " + mmss(left) : "Đã hết thời gian giữ ghế";
        el.classList.toggle("urgent", left < 60000);
        if (left <= 0) expiredNow = true;
      });
      if (expiredNow && !countdown.busy) { countdown.busy = true; setTimeout(function () { refresh().then(function () { countdown.busy = false; }); }, 1500); }
    }
    async function refresh() { if (await load(false)) render(); }
    render();
    every(countdown, 1000);
    every(refresh, 20000);
  }

  /* ---------- Đăng nhập / đăng ký ---------- */
  function login(mode) {
    if (user) { location.hash = "#/"; return; }
    var reg = mode === "register";
    show('<div class="auth"><div class="auth-art"><div><span class="eyebrow">SOA Cinema</span><h2 style="margin-top:12px">Đặt vé xem phim<br>chỉ trong vài bước.</h2></div>' +
      "<ul><li><i>🎬</i>Lịch chiếu 7 ngày tới, cập nhật liên tục</li><li><i>💺</i>Chọn ghế trực tiếp trên sơ đồ phòng</li><li><i>💳</i>Chuyển khoản VietQR, MoMo hoặc VNPAY</li><li><i>🎟️</i>Vé điện tử có mã QR, xem lại bất cứ lúc nào</li></ul>" +
      '<span class="muted small">Ghế được giữ 10 phút trong lúc bạn thanh toán.</span></div>' +
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
    if (h === "#movies" || h === "#showtimes") return;   // neo cuộn trong trang
    leave(); nav(); window.scrollTo(0, 0);
    if (p[1] === "movie" && p[2]) return movie(p[2]);
    if (p[1] === "book" && p[3]) return book(p[2], p[3]);
    if (p[1] === "pay" && p[2]) return pay(p[2]);
    if (p[1] === "ticket" && p[2]) return ticket(p[2], p[3] === "new");
    if (p[1] === "result" || p[1] === "my") { if (p[1] === "result") { location.replace("#/my"); return; } return my(); }
    if (p[1] === "login") return login();
    if (p[1] === "register") return login("register");
    return home();
  }
  window.addEventListener("hashchange", route);
  document.addEventListener("DOMContentLoaded", route);
})();
