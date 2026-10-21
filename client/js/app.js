/**
 * SOA Cinema — Client Application (Bootstrap 5.3 + Dark Cinema Theme)
 * Đầy đủ logic nghiệp vụ:
 * - Định tuyến URL Hash (#/, #/movie/:id, #/book/:mid/:sid, #/pay/:id, #/ticket/:id, #/my, #/login, #/register)
 * - Hero Carousel tự chuyển 6s, 4-6 phim nổi bật, thanh tiến độ, tạm dừng hover/touch, swipe mobile
 * - Poster thật 2:3, ảnh backdrop, Modal xem YouTube trailer chính thức (tắt video khi đóng modal)
 * - Vé điện tử Code 128 mã vạch 1D thuần JS SVG, thiết kế vé răng cưa đục lỗ, in ấn tối ưu
 * - Giữ ghế 10 phút, đếm ngược MM:SS, cảnh báo đỏ khi <60s
 * - Cập nhật sơ đồ ghế 5s/lần, tự bỏ chọn ghế nếu bị người khác đặt
 * - Toàn bộ thông báo tiếng Việt thân thiện, che giấu chi tiết kỹ thuật
 */
(function () {
  "use strict";

  var $ = function (s, root) { return (root || document).querySelector(s); };
  var $$ = function (s, root) { return Array.prototype.slice.call((root || document).querySelectorAll(s)); };
  var esc = function (v) {
    return String(v == null ? "" : v).replace(/[&<>"']/g, function (c) {
      return ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c];
    });
  };
  var money = function (n) { return Number(n || 0).toLocaleString("vi-VN") + " đ"; };
  var STATUS = { PAID: "Đã thanh toán", PENDING: "Chờ thanh toán", CANCELLED: "Đã hủy" };
  var DOW = ["Chủ nhật", "Thứ hai", "Thứ ba", "Thứ tư", "Thứ năm", "Thứ sáu", "Thứ bảy"];
  var MAP = window.SEAT_MAP || { rows: "ABCDEF", cols: 10, aisleAfter: [5], maxSeats: 8 };
  var METHODS = window.PAYMENT_METHODS || [];
  var BANK = window.BANK_ACCOUNT || {};
  var TOTAL_SEATS = MAP.rows.length * MAP.cols;

  var user = null;
  try { user = JSON.parse(sessionStorage.getItem("soa.user") || "null"); } catch (e) {}

  var ICON_SEARCH = '<i class="bi bi-search"></i>';
  var ICON_COPY = '<i class="bi bi-clipboard"></i>';
  var ICON_PLAY = '<i class="bi bi-play-circle-fill"></i>';

  /* ---------- Quản lý vòng đời trang & hẹn giờ ---------- */
  var timers = [], page = 0;
  function every(fn, ms) { timers.push(setInterval(fn, ms)); }
  function leave() { timers.forEach(clearInterval); timers = []; page++; }
  function current() {
    var p = page;
    return function () { return p === page; };
  }

  /* ---------- Thông báo lỗi thân thiện ---------- */
  var DOWN = {
    movie: "Không tải được danh mục phim lúc này. Vui lòng thử lại sau ít phút.",
    showtime: "Không tải được lịch chiếu lúc này. Vui lòng thử lại sau ít phút.",
    user: "Hệ thống tài khoản đang tạm gián đoạn. Vui lòng thử lại sau ít phút.",
    booking: "Hệ thống đặt vé đang tạm gián đoạn. Vui lòng thử lại sau ít phút."
  };
  var FRIENDLY = {
    PAYMENT_SERVICE_UNAVAILABLE: "Cổng thanh toán đang tạm gián đoạn. Ghế của bạn vẫn được giữ — vui lòng thử lại sau ít phút.",
    PAYMENT_SERVICE_ERROR: "Giao dịch chưa hoàn tất. Vui lòng kiểm tra lại hoặc chọn phương thức khác.",
    USER_NOT_FOUND: "Tài khoản không tồn tại. Vui lòng đăng nhập lại.",
    MOVIE_NOT_FOUND: "Phim này không còn tồn tại.",
    SHOWTIME_NOT_FOUND: "Suất chiếu không còn tồn tại, vui lòng chọn suất khác.",
    BOOKING_CANCELLED: "Đơn đã hết thời gian giữ ghế hoặc đã bị hủy.",
    ALREADY_PAID: "Đơn này đã được thanh toán.",
    FORBIDDEN: "Bạn không có quyền xem đơn đặt vé này.",
    NOT_FOUND: "Không tìm thấy thông tin yêu cầu.",
    INTERNAL_ERROR: "Hệ thống đang bận. Vui lòng thử lại sau ít phút."
  };
  var TECHNICAL = /service|sql|http|json|endpoint|exception|null|\b[a-z]+Id\b/i;

  function friendly(code, message) {
    if (FRIENDLY[code]) return FRIENDLY[code];
    if (/_SERVICE_(UNAVAILABLE|ERROR)$/.test(code || "")) return "Hệ thống đang bận. Vui lòng thử lại sau ít phút.";
    return message && !TECHNICAL.test(message) ? message : "Đã có lỗi xảy ra. Vui lòng thử lại sau.";
  }

  async function call(svc, method, path, body) {
    var res, json;
    try {
      res = await fetch(API[svc] + path, {
        method: method,
        headers: body ? { "Content-Type": "application/json" } : {},
        body: body ? JSON.stringify(body) : undefined,
        cache: "no-store"
      });
    } catch (e) {
      var down = new Error(DOWN[svc] || "Không kết nối được dịch vụ.");
      down.code = "SERVICE_DOWN";
      throw down;
    }
    try { json = await res.json(); } catch (e) { json = null; }
    if (!res.ok || !json || json.status !== "success") {
      var code = json && json.code;
      var err = new Error(friendly(code, json && json.message));
      err.code = code;
      err.httpStatus = res.status;
      throw err;
    }
    return json.data;
  }

  async function soft(svc, path, fallback) {
    try { return await call(svc, "GET", path); } catch (e) { return fallback; }
  }

  function byId(list) {
    var o = {};
    (list || []).forEach(function (x) { o[x.id] = x; });
    return o;
  }

  /* ---------- Xử lý dữ liệu phim mở rộng (movie-extras) ---------- */
  function enrichMovie(m) {
    if (!m) return m;
    if (window.mergeMovieExtras) return window.mergeMovieExtras(m);
    return m;
  }

  function enrichMovies(list) {
    return (list || []).map(enrichMovie);
  }

  /* ---------- Thời gian & định dạng ---------- */
  function toDate(t) {
    var m = String(t || "").match(/^(\d{4})-(\d{2})-(\d{2})[T ](\d{2}):(\d{2})(?::(\d{2}))?/);
    return m ? new Date(+m[1], +m[2] - 1, +m[3], +m[4], +m[5], +(m[6] || 0)) : null;
  }
  function ymd(d) {
    return d.getFullYear() + "-" + ("0" + (d.getMonth() + 1)).slice(-2) + "-" + ("0" + d.getDate()).slice(-2);
  }
  function when(t) {
    var d = toDate(t);
    if (!d) return { date: "", hm: String(t || ""), dm: "", dow: "", full: String(t || "") };
    var hm = ("0" + d.getHours()).slice(-2) + ":" + ("0" + d.getMinutes()).slice(-2);
    var dm = ("0" + d.getDate()).slice(-2) + "/" + ("0" + (d.getMonth() + 1)).slice(-2);
    return { date: ymd(d), hm: hm, dm: dm, dow: DOW[d.getDay()], full: hm + " · " + DOW[d.getDay()] + ", " + dm + "/" + d.getFullYear() };
  }
  function dayLabel(dateStr) {
    var today = ymd(new Date()), t = new Date(); t.setDate(t.getDate() + 1);
    return dateStr === today ? "Hôm nay" : dateStr === ymd(t) ? "Ngày mai" : when(dateStr + " 00:00").dow;
  }
  function upcoming(s) { var d = toDate(s.time); return d && d > new Date(); }
  function mmss(ms) {
    var s = Math.max(0, Math.ceil(ms / 1000));
    return ("0" + Math.floor(s / 60)).slice(-2) + ":" + ("0" + s % 60).slice(-2);
  }
  function duration(min) {
    min = Number(min) || 0;
    var h = Math.floor(min / 60), m = min % 60;
    return h ? h + " giờ" + (m ? " " + m + " phút" : "") : m + " phút";
  }
  function shortDuration(min) {
    min = Number(min) || 0;
    var h = Math.floor(min / 60), m = min % 60;
    if (!h) return m + "p";
    return m ? h + "h" + (m < 10 ? "0" + m : m) : h + "h";
  }
  function nowHMS() { return new Date().toLocaleTimeString("vi-VN"); }

  function badge(s) {
    return '<span class="badge status-' + esc(s) + '">' + esc(STATUS[s] || s) + "</span>";
  }
  function code(b) {
    return "SOA" + ("00000" + b.id).slice(-6);
  }
  function methodOf(v) {
    return METHODS.filter(function (p) { return p.value === v; })[0];
  }

  /* ---------- Poster & Backdrop ---------- */
  var PAL = [
    ["#7c2d12", "#f97316"], ["#1e3a8a", "#6366f1"], ["#4c1d95", "#db2777"],
    ["#064e3b", "#14b8a6"], ["#7f1d1d", "#f43f5e"], ["#713f12", "#eab308"],
    ["#0c4a6e", "#06b6d4"], ["#3b0764", "#a855f7"]
  ];
  var GENRE_ICON = [
    [/hành động|action/i, "💥"], [/viễn tưởng|sci/i, "🚀"], [/hoạt hình|anim/i, "🎨"],
    [/kinh dị|horror/i, "👻"], [/hài|comedy/i, "😂"], [/tình cảm|lãng mạn|romance/i, "💕"],
    [/tâm lý|drama/i, "🎭"], [/phiêu lưu/i, "🧭"], [/hình sự|crime/i, "🕵️"], [/gia đình/i, "👨‍👩‍👧"]
  ];
  function hash(s) {
    var h = 0; s = String(s || "");
    for (var i = 0; i < s.length; i++) h = (h * 31 + s.charCodeAt(i)) | 0;
    return Math.abs(h);
  }
  function palette(m) {
    var p = PAL[hash(m && m.title) % PAL.length];
    return "--p1:" + p[0] + ";--p2:" + p[1];
  }
  function genreIcon(g) {
    for (var i = 0; i < GENRE_ICON.length; i++) {
      if (GENRE_ICON[i][0].test(g || "")) return GENRE_ICON[i][1];
    }
    return "🎬";
  }

  function getPosterSources(m) {
    m = m || {};
    var list = [];
    if (m.posterUrl) list.push(m.posterUrl);
    if (m.poster) {
      var p = String(m.poster).trim();
      if (/^(https?:)?\/\//.test(p)) list.push(p);
      else {
        var fn = p.replace(/^.*[\\/]/, "");
        if (/^[\w.-]+$/.test(fn)) {
          list.push((window.POSTER_DIR || "assets/posters/") + fn);
          list.push("img/posters/" + fn);
          list.push("assets/posters/" + fn.replace(/\.(jpe?g|png|webp)$/i, ".svg"));
        }
      }
    }
    if (m.remotePosterUrl) list.push(m.remotePosterUrl);
    return list.filter(function (v, idx, arr) { return arr.indexOf(v) === idx; });
  }

  window.SOA_posterFail = function (img) {
    var alts = (img.getAttribute("data-alt") || "").split("|").filter(Boolean);
    if (alts.length) {
      img.setAttribute("data-alt", alts.slice(1).join("|"));
      img.src = alts[0];
    } else {
      img.style.display = "none";
      if (img.parentNode) img.parentNode.classList.add("poster-fallback");
    }
  };

  function ageBadge(age) {
    if (!age) return "";
    var cls = age === "P" ? "age-p" : age === "T13" ? "age-t13" : age === "T16" ? "age-t16" : "age-t18";
    return '<span class="age-badge ' + cls + '">' + esc(age) + "</span>";
  }

  function poster(m, cls) {
    m = enrichMovie(m) || { title: "Phim" };
    var srcs = getPosterSources(m);
    var age = m.ageRating ? ageBadge(m.ageRating) : "";
    var imgTag = srcs.length
      ? '<img src="' + esc(srcs[0]) + '" data-alt="' + esc(srcs.slice(1).join("|")) + '" alt="Poster phim ' + esc(m.title) +
        '" loading="lazy" onload="this.parentNode.classList.add(\'has-img\')" onerror="SOA_posterFail(this)">'
      : "";

    return '<div class="poster ' + (cls || "") + '" style="' + palette(m) + '">' +
      imgTag +
      age +
      '<div class="poster-fallback-info">' +
        '<span class="poster-emoji">' + genreIcon(m.genre) + "</span>" +
        '<span class="poster-title">' + esc(m.title) + "</span>" +
      "</div>" +
    "</div>";
  }

  function backdrop(m) {
    m = enrichMovie(m) || {};
    var bg = m.backdropUrl || m.remoteBackdropUrl || m.posterUrl;
    var style = palette(m);
    if (bg) {
      style += ";background-image:linear-gradient(to right, rgba(10,12,19,0.92) 20%, rgba(10,12,19,0.6) 60%, rgba(10,12,19,0.85) 100%), url('" + esc(bg) + "')";
    }
    return '<div class="hero-bg" style="' + style + '"></div>';
  }

  /* ---------- Modal Trailer YouTube Chuyên Nghiệp (M4) ---------- */
  var trailerModalInstance = null;
  var ytPlayer = null;
  var ytWatchdogTimer = null;
  var currentTrailerQueue = [];
  var currentTrailerIndex = 0;
  var currentTrailerTitle = "";
  var currentTrailerBackdrop = "";

  function loadYouTubeIframeApi() {
    if (window.YT && window.YT.Player) return;
    if (document.getElementById("yt-iframe-api-script")) return;
    var tag = document.createElement("script");
    tag.id = "yt-iframe-api-script";
    tag.src = "https://www.youtube.com/iframe_api";
    var firstScriptTag = document.getElementsByTagName("script")[0];
    if (firstScriptTag && firstScriptTag.parentNode) {
      firstScriptTag.parentNode.insertBefore(tag, firstScriptTag);
    } else {
      document.head.appendChild(tag);
    }
  }

  function stopAndCleanTrailer() {
    if (ytWatchdogTimer) {
      clearTimeout(ytWatchdogTimer);
      ytWatchdogTimer = null;
    }
    if (ytPlayer) {
      try {
        if (ytPlayer.stopVideo) ytPlayer.stopVideo();
        if (ytPlayer.destroy) ytPlayer.destroy();
      } catch (e) {}
      ytPlayer = null;
    }
    var modalBody = document.getElementById("trailerModalBody");
    if (modalBody) {
      modalBody.innerHTML = '<div id="trailerPlayerHost" class="w-100 h-100 ratio ratio-16x9"></div>';
    }
  }

  function initTrailerModal() {
    loadYouTubeIframeApi();
    var el = document.getElementById("trailerModal");
    if (!el || !window.bootstrap) return;
    trailerModalInstance = new bootstrap.Modal(el);
    el.addEventListener("hidden.bs.modal", stopAndCleanTrailer);
  }

  function renderTrailerFallback(title, youtubeId, backdropUrl) {
    if (ytWatchdogTimer) { clearTimeout(ytWatchdogTimer); ytWatchdogTimer = null; }
    var modalBody = document.getElementById("trailerModalBody");
    if (!modalBody) return;
    var bgStyle = backdropUrl
      ? 'background: linear-gradient(rgba(10,12,19,0.88), rgba(10,12,19,0.96)), url(\'' + esc(backdropUrl) + '\') center/cover;'
      : 'background: var(--cinema-surface-1);';
    modalBody.innerHTML =
      '<div class="d-flex flex-column align-items-center justify-content-center p-4 text-center w-100 h-100" style="' + bgStyle + '">' +
        '<i class="bi bi-shield-lock-fill text-warning fs-1 mb-2"></i>' +
        '<h5 class="text-white mb-2">' + esc(title) + '</h5>' +
        '<p class="text-secondary small mb-4" style="max-width: 440px;">' +
          'Không thể phát trực tiếp trailer phim này do cài đặt bản quyền hoặc giới hạn nhúng của nhà phát hành.' +
        '</p>' +
        '<div class="d-flex gap-2 flex-wrap justify-content-center">' +
          '<a href="https://www.youtube.com/watch?v=' + encodeURIComponent(youtubeId) + '" target="_blank" rel="noopener noreferrer" class="btn btn-danger px-4 py-2">' +
            '<i class="bi bi-youtube me-2"></i>Mở xem trên YouTube ↗' +
          '</a>' +
          '<a href="https://www.youtube.com/results?search_query=' + encodeURIComponent(title + ' trailer chính thức') + '" target="_blank" rel="noopener noreferrer" class="btn btn-outline-light px-4 py-2">' +
            '<i class="bi bi-search me-2"></i>Tìm trailer trên YouTube ↗' +
          '</a>' +
        '</div>' +
      '</div>';
  }

  function playNextTrailerId() {
    if (ytWatchdogTimer) {
      clearTimeout(ytWatchdogTimer);
      ytWatchdogTimer = null;
    }
    if (currentTrailerIndex >= currentTrailerQueue.length) {
      renderTrailerFallback(currentTrailerTitle, currentTrailerQueue[0] || "", currentTrailerBackdrop);
      return;
    }

    var nextId = currentTrailerQueue[currentTrailerIndex];
    currentTrailerIndex++;

    var modalBody = document.getElementById("trailerModalBody");
    if (!modalBody) return;

    modalBody.innerHTML = '<iframe id="trailerIframe" src="https://www.youtube-nocookie.com/embed/' + encodeURIComponent(nextId) + '?autoplay=1&enablejsapi=1&rel=0&playsinline=1" title="' + esc(currentTrailerTitle) + '" class="w-100 h-100 border-0" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share" referrerpolicy="strict-origin-when-cross-origin" allowfullscreen></iframe>';

    // Watchdog timer 8s tự động chuyển sang video dự phòng tiếp theo nếu chưa chạy hoặc bị chặn
    ytWatchdogTimer = setTimeout(function () {
      if (currentTrailerIndex < currentTrailerQueue.length) {
        playNextTrailerId();
      } else {
        renderTrailerFallback(currentTrailerTitle, currentTrailerQueue[0] || "", currentTrailerBackdrop);
      }
    }, 8000);

    // Bắt sự kiện thông qua YT.Player nếu API đã sẵn sàng
    if (window.YT && window.YT.Player) {
      try {
        if (ytPlayer && ytPlayer.destroy) ytPlayer.destroy();
        ytPlayer = new YT.Player("trailerIframe", {
          events: {
            onStateChange: function (event) {
              if (event.data === 1) { // 1 = PLAYING
                if (ytWatchdogTimer) {
                  clearTimeout(ytWatchdogTimer);
                  ytWatchdogTimer = null;
                }
              }
            },
            onError: function (event) {
              // Lỗi mã 2, 5, 100, 101, 150, 153 -> tự động chuyển backup
              playNextTrailerId();
            }
          }
        });
      } catch (err) {}
    }
  }

  function openTrailer(title, youtubeId, backupYoutubeId) {
    if (!youtubeId && (!window.MOVIE_EXTRAS || !title)) return;
    var el = document.getElementById("trailerModal");
    var titleEl = document.getElementById("trailerTitle");
    if (!el) return;

    stopAndCleanTrailer();

    var extra = null;
    if (window.MOVIE_EXTRAS) {
      var norm = String(title || "").trim().toLowerCase().normalize("NFD").replace(/[\u0300-\u036f]/g, "").replace(/[^a-z0-9]/g, "");
      extra = window.MOVIE_EXTRAS[norm] || null;
    }

    var queue = [];
    if (extra && Array.isArray(extra.youtubeIds) && extra.youtubeIds.length) {
      queue = extra.youtubeIds.slice();
    } else {
      if (youtubeId) queue.push(youtubeId);
      if (backupYoutubeId && queue.indexOf(backupYoutubeId) < 0) queue.push(backupYoutubeId);
      if (extra && extra.youtubeId && queue.indexOf(extra.youtubeId) < 0) queue.push(extra.youtubeId);
    }

    if (!queue.length) return;

    currentTrailerQueue = queue;
    currentTrailerIndex = 0;
    currentTrailerTitle = title || "Trailer";
    currentTrailerBackdrop = (extra && (extra.backdropUrl || extra.remoteBackdropUrl || extra.posterUrl)) || "";

    if (titleEl) titleEl.textContent = currentTrailerTitle + " — Trailer chính thức";

    if (!trailerModalInstance && window.bootstrap) {
      trailerModalInstance = new bootstrap.Modal(el);
    }
    if (trailerModalInstance) trailerModalInstance.show();

    playNextTrailerId();
  }

  /* ---------- Modal xác nhận (Confirm Dialog) ---------- */
  var confirmModalInstance = null;
  function confirmDialog(title, message, onOk) {
    var el = document.getElementById("confirmModal");
    if (!el || !window.bootstrap) {
      if (window.confirm(message)) onOk();
      return;
    }
    var titleEl = document.getElementById("confirmTitle");
    var msgEl = document.getElementById("confirmMessage");
    var okBtn = document.getElementById("confirmOkBtn");
    if (titleEl) titleEl.textContent = title;
    if (msgEl) msgEl.textContent = message;

    if (!confirmModalInstance) {
      confirmModalInstance = new bootstrap.Modal(el);
    }

    okBtn.onclick = function () {
      confirmModalInstance.hide();
      if (typeof onOk === "function") onOk();
    };

    confirmModalInstance.show();
  }

  /* ---------- Khung chung & Toasts ---------- */
  function show(html) {
    var v = $("#view");
    v.innerHTML = html;
    v.focus();
  }

  function toast(msg, type) {
    var container = $("#toastContainer") || $("#toasts");
    var t = document.createElement("div");
    t.className = "toast align-items-center text-white bg-" + (type === "err" ? "danger" : type === "info" ? "info" : "success") + " border-0 show mb-2 shadow";
    t.setAttribute("role", "alert");
    t.setAttribute("aria-live", "assertive");
    t.setAttribute("aria-atomic", "true");
    t.innerHTML = '<div class="d-flex"><div class="toast-body d-flex align-items-center gap-2">' +
      '<i class="bi ' + (type === "err" ? "bi-exclamation-triangle-fill" : type === "info" ? "bi-info-circle-fill" : "bi-check-circle-fill") + '"></i>' +
      '<span>' + esc(msg) + '</span></div>' +
      '<button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast" aria-label="Đóng"></button></div>';

    container.appendChild(t);
    setTimeout(function () {
      t.classList.remove("show");
      setTimeout(function () { t.remove(); }, 300);
    }, 4500);

    var closeBtn = t.querySelector("[data-bs-dismiss='toast']");
    if (closeBtn) closeBtn.onclick = function () { t.remove(); };
  }

  function stateBox(icon, title, text, action) {
    return '<div class="state"><div class="big">' + icon + "</div><h3>" + esc(title) + "</h3><p>" + esc(text) + "</p>" + (action || "") + "</div>";
  }

  function errorBox(e, retry) {
    return stateBox(
      e.code === "SERVICE_DOWN" ? "🔌" : "⚠️",
      e.code === "SERVICE_DOWN" ? "Mất kết nối tới hệ thống" : "Đã xảy ra lỗi",
      e.message,
      retry === false ? "" : '<button class="btn btn-outline-warning mt-3 px-4" data-retry>Thử lại</button>'
    );
  }

  function bindRetry(fn) {
    var b = $("[data-retry]");
    if (b) b.onclick = fn;
  }

  function back(href, label) {
    return '<a class="back d-inline-flex align-items-center gap-2 mb-3" href="' + href + '"><i class="bi bi-arrow-left"></i><span>' + esc(label) + "</span></a>";
  }

  function live(id) {
    return '<span class="live" id="' + id + '" title="Dữ liệu tự động cập nhật"><i class="pulse-dot"></i>Cập nhật trực tiếp</span>';
  }

  function liveTick(id, ok) {
    var el = $("#" + id);
    if (el) {
      el.classList.toggle("off", !ok);
      el.lastChild.textContent = ok ? "Cập nhật lúc " + nowHMS() : "Mất kết nối, đang thử lại...";
    }
  }

  function steps(active) {
    var names = ["Chọn suất chiếu", "Chọn ghế", "Thanh toán", "Nhận vé"];
    return '<nav class="soa-stepper" aria-label="Tiến trình đặt vé">' +
      '<ol class="soa-stepper-list">' +
      names.map(function (n, i) {
        var isDone = i < active;
        var isCurrent = i === active;
        var cls = isDone ? "done" : isCurrent ? "active" : "";
        var aria = isCurrent ? ' aria-current="step"' : "";
        var icon = isDone ? '<i class="bi bi-check-lg" aria-hidden="true"></i>' : (i + 1);
        var item = '<li class="soa-step ' + cls + '"' + aria + '>' +
          '<span class="soa-step-num">' + icon + '</span>' +
          '<span class="soa-step-label">' + n + '</span>' +
          '</li>';
        var line = (i < names.length - 1) ? '<li class="soa-step-line ' + (i < active ? "done" : "") + '" aria-hidden="true"></li>' : "";
        return item + line;
      }).join("") +
      '</ol>' +
      '</nav>';
  }

  function needLogin(next) {
    if (user) return false;
    sessionStorage.setItem("soa.next", next || location.hash);
    toast("Vui lòng đăng nhập để tiếp tục", "info");
    location.hash = "#/login";
    return true;
  }

  async function copy(text, label) {
    try {
      await navigator.clipboard.writeText(text);
      toast("Đã sao chép " + label);
    } catch (e) {
      toast("Không thể sao chép tự động, vui lòng chọn thủ công", "err");
    }
  }

  /* ---------- Thanh điều hướng Topbar ---------- */
  function nav() {
    var h = location.hash || "#/";
    var mine = /^#\/(my|ticket|pay|result)/.test(h);
    var auth = /^#\/(login|register)/.test(h);
    var links = [["#/", "Phim", !mine && !auth], ["#/my", "Vé của tôi", mine]];

    $("#mainnav").innerHTML = links.map(function (l) {
      return '<a href="' + l[0] + '" class="' + (l[2] ? "active" : "") + '">' + l[1] + "</a>";
    }).join("");

    $("#account").innerHTML = user
      ? '<div class="dropdown">' +
          '<button class="user-chip dropdown-toggle btn btn-link text-decoration-none p-0" id="userMenuBtn" data-bs-toggle="dropdown" aria-expanded="false">' +
            '<span class="avatar">' + esc(user.username.charAt(0).toUpperCase()) + "</span>" +
            '<span class="name text-light">' + esc(user.username) + "</span>" +
          "</button>" +
          '<ul class="dropdown-menu dropdown-menu-dark dropdown-menu-end shadow" aria-labelledby="userMenuBtn">' +
            '<li><a class="dropdown-item" href="#/my"><i class="bi bi-ticket-perforated me-2 text-warning"></i>Vé của tôi</a></li>' +
            '<li><hr class="dropdown-divider border-secondary"></li>' +
            '<li><button class="dropdown-item text-danger" id="logout"><i class="bi bi-box-arrow-right me-2"></i>Đăng xuất</button></li>' +
          "</ul>" +
        "</div>"
      : '<div class="d-flex align-items-center gap-2">' +
          '<a class="btn btn-outline-light btn-sm px-3" href="#/login">Đăng nhập</a>' +
          '<a class="btn btn-primary btn-sm px-3" href="#/register">Đăng ký</a>' +
        "</div>";

    var lo = $("#logout");
    if (lo) {
      lo.onclick = function () {
        user = null;
        sessionStorage.removeItem("soa.user");
        toast("Đã đăng xuất thành công");
        location.hash = "#/";
        nav();
      };
    }
  }

  /* =============================================================================
     TRANG CHỦ — CAROUSEL 6S + LƯỚI PHIM ĐẦY ĐỦ
  ============================================================================= */
  async function home() {
    var alive = current();
    show(
      '<div class="skel" style="height:440px;border-radius:24px;margin-bottom:40px"></div>' +
      '<div class="grid">' + Array(6).join('<div><div class="skel" style="aspect-ratio:2/3;border-radius:16px"></div><div class="skel" style="height:18px;margin-top:12px;width:75%"></div></div>') + "</div>"
    );

    var rawMovies, sts;
    try {
      rawMovies = await call("movie", "GET", "/api/movies");
    } catch (e) {
      if (alive()) { show(errorBox(e)); bindRetry(home); }
      return;
    }
    sts = await soft("showtime", "/api/showtimes?upcoming=1", null);
    if (!alive()) return;

    var movies = enrichMovies(rawMovies);
    if (sts) sts = sts.filter(upcoming);

    if (!movies.length) {
      show(stateBox("🎞️", "Chưa có phim nào", "Rạp đang cập nhật lịch chiếu. Vui lòng quay lại sau ít phút."));
      return;
    }

    var count = {}, today = {}, todayStr = ymd(new Date());
    (sts || []).forEach(function (s) {
      count[s.movieId] = (count[s.movieId] || 0) + 1;
      if (when(s.time).date === todayStr) today[s.movieId] = (today[s.movieId] || 0) + 1;
    });

    // Chọn danh sách phim cho Carousel (4 - 6 phim nổi bật)
    var carouselMovies = movies.filter(function (m) { return m.featured; });
    if (carouselMovies.length < 4) {
      var sortedBySt = movies.slice().sort(function (a, b) { return (count[b.id] || 0) - (count[a.id] || 0); });
      sortedBySt.forEach(function (m) {
        if (carouselMovies.indexOf(m) < 0 && carouselMovies.length < 6) carouselMovies.push(m);
      });
    }
    if (carouselMovies.length > 6) carouselMovies = carouselMovies.slice(0, 6);

    // Lọc thể loại phong phú
    var genres = [];
    movies.forEach(function (m) {
      var gList = m.genres && m.genres.length ? m.genres : [m.genre];
      gList.forEach(function (g) {
        if (g && genres.indexOf(g) < 0) genres.push(g);
      });
    });

    var state = { q: "", g: "" };

    // Xây dựng Carousel HTML
    var slidesHtml = carouselMovies.map(function (m, idx) {
      var age = m.ageRating ? ageBadge(m.ageRating) : "";
      var trailerBtn = m.youtubeId
        ? '<button type="button" class="btn btn-outline-light btn-lg hero-trailer-btn" data-trailer-title="' + esc(m.title) + '" data-trailer-id="' + esc(m.youtubeId) + '">' +
            ICON_PLAY + ' Xem trailer</button>'
        : "";
      var todayTag = today[m.id] ? '<span class="chip"><i class="bi bi-ticket-perforated"></i> Hôm nay còn ' + today[m.id] + " suất</span>" : "";
      var desc = m.description || "Thưởng thức siêu phẩm điện ảnh với hình ảnh sắc nét và âm thanh vòm sống động tại SOA Cinema.";

      return '<div class="carousel-slide ' + (idx === 0 ? "active" : "") + '" data-slide-index="' + idx + '" style="' + palette(m) + '">' +
        backdrop(m) +
        '<div class="hero-slide-in">' +
          '<div class="slide-content">' +
            '<div class="slide-tags d-flex align-items-center gap-2 flex-wrap mb-2">' +
              '<span class="badge bg-warning text-dark px-2 py-1"><i class="bi bi-star-fill"></i> Phim nổi bật</span>' +
              age +
            '</div>' +
            '<h1 class="slide-title">' + esc(m.title) + "</h1>" +
            (m.titleVi && m.titleVi !== m.title ? '<p class="slide-subtitle text-secondary mb-2">' + esc(m.titleVi) + "</p>" : "") +
            '<div class="slide-meta mb-3">' +
              '<span class="chip">' + genreIcon(m.genre) + " " + esc(m.genre) + "</span>" +
              '<span class="chip"><i class="bi bi-clock"></i> ' + duration(m.duration) + "</span>" +
              todayTag +
            "</div>" +
            '<p class="slide-desc text-light-50 mb-4">' + esc(desc) + "</p>" +
            '<div class="slide-actions d-flex flex-wrap gap-3">' +
              '<a class="btn btn-primary btn-lg px-4" href="#/movie/' + m.id + '"><i class="bi bi-lightning-charge-fill me-1"></i> Đặt vé ngay</a>' +
              trailerBtn +
              '<a class="btn btn-ghost btn-lg" href="#movies" data-scroll-movies>Tất cả phim</a>' +
            "</div>" +
          "</div>" +
          '<div class="slide-poster-wrap d-none d-md-block">' +
            poster(m, "hero-poster shadow-lg") +
          "</div>" +
        "</div>" +
      "</div>";
    }).join("");

    var indicatorsHtml = carouselMovies.map(function (_, idx) {
      return '<button class="indicator-bar ' + (idx === 0 ? "active" : "") + '" data-to="' + idx + '" aria-label="Slide ' + (idx + 1) + '">' +
        '<span class="indicator-progress"></span>' +
      "</button>";
    }).join("");

    show(
      '<section class="hero-carousel-wrapper" id="heroCarousel" aria-label="Phim nổi bật">' +
        '<div class="carousel-track">' + slidesHtml + "</div>" +
        '<div class="carousel-indicators-bar">' + indicatorsHtml + "</div>" +
        '<button class="carousel-nav-btn prev" id="carouselPrev" aria-label="Phim trước"><i class="bi bi-chevron-left"></i></button>' +
        '<button class="carousel-nav-btn next" id="carouselNext" aria-label="Phim tiếp theo"><i class="bi bi-chevron-right"></i></button>' +
      "</section>" +

      '<section id="movies" class="mt-5">' +
        '<div class="section-head mb-4 d-flex justify-content-between align-items-end flex-wrap gap-3">' +
          '<div>' +
            '<h2 class="section-title mb-1">Phim đang chiếu</h2>' +
            '<div class="text-secondary small" id="m-count">Đang tải lịch chiếu...</div>' +
          "</div>" +
          '<div class="filters-search">' +
            '<div class="soa-search">' +
              '<i class="bi bi-search soa-search-icon"></i>' +
              '<input class="soa-search-input" id="q" placeholder="Tìm phim…" aria-label="Tìm phim">' +
              '<button type="button" class="soa-search-clear" id="q-clear" aria-label="Xóa">&times;</button>' +
            '</div>' +
          '</div>' +
        "</div>" +

        '<div class="genres-wrapper mb-4">' +
          '<div class="genres-scroll-container">' +
            '<button type="button" class="genre-arrow-btn prev" id="genrePrev" aria-label="Cuộn trái"><i class="bi bi-chevron-left"></i></button>' +
            '<div class="genres-scroll" id="genres">' +
              '<button type="button" class="genre on" data-g="">Tất cả</button>' +
              genres.map(function (g) {
                return '<button type="button" class="genre" data-g="' + esc(g) + '">' + esc(g) + "</button>";
              }).join("") +
            '</div>' +
            '<button type="button" class="genre-arrow-btn next" id="genreNext" aria-label="Cuộn phải"><i class="bi bi-chevron-right"></i></button>' +
          '</div>' +
        '</div>' +

        '<div id="grid"></div>' +
      "</section>"
    );

    // Xử lý logic Carousel (6 giây, tạm dừng khi hover/touch, phím mũi tên, swipe)
    initHeroCarousel(carouselMovies.length);

    // Gắn sự kiện mở trailer từ hero
    $$(".hero-trailer-btn").forEach(function (btn) {
      btn.onclick = function (ev) {
        ev.preventDefault();
        openTrailer(btn.getAttribute("data-trailer-title"), btn.getAttribute("data-trailer-id"));
      };
    });

    // Cuộn mượt xuống lưới phim
    $$("[data-scroll-movies]").forEach(function (btn) {
      btn.onclick = function (ev) {
        ev.preventDefault();
        var el = document.getElementById("movies");
        if (el) el.scrollIntoView({ behavior: "smooth" });
      };
    });

    // Render lưới phim
    function render() {
      var q = state.q.toLowerCase();
      var list = movies.filter(function (m) {
        var matchGenre = !state.g || (m.genres && m.genres.indexOf(state.g) >= 0) || m.genre === state.g;
        var matchTitle = !q || String(m.title).toLowerCase().indexOf(q) >= 0 || (m.titleVi && String(m.titleVi).toLowerCase().indexOf(q) >= 0);
        return matchGenre && matchTitle;
      });

      var countEl = $("#m-count");
      if (countEl) countEl.textContent = list.length + " bộ phim" + (sts ? "" : " · lịch chiếu đang được cập nhật");

      var gridEl = $("#grid");
      if (!gridEl) return;

      if (!list.length) {
        gridEl.innerHTML = stateBox("🔍", "Không tìm thấy phim phù hợp", "Thử tìm với từ khóa khác hoặc chọn thể loại khác.");
        return;
      }

      gridEl.innerHTML = '<div class="grid movies-grid">' + list.map(function (m) {
        var showtimeText = !sts ? "Đang cập nhật" : today[m.id] ? "● " + today[m.id] + " suất hôm nay" : count[m.id] ? "● " + count[m.id] + " suất sắp tới" : "● Sắp chiếu";
        var showtimeClass = !sts ? "none" : today[m.id] ? "today" : count[m.id] ? "soon" : "none";

        return '<a class="mcard" href="#/movie/' + m.id + '">' +
          '<div class="mcard-poster-wrap">' +
            poster(m) +
            '<div class="mcard-hover-overlay">' +
              (m.youtubeId ? '<button type="button" class="btn btn-outline-light btn-sm rounded-pill px-3 mcard-trailer-btn" data-trailer-id="' + esc(m.youtubeId) + '" data-trailer-title="' + esc(m.title) + '"><i class="bi bi-play-circle-fill text-danger me-1"></i>Xem trailer</button>' : "") +
              '<span class="btn btn-primary btn-sm rounded-pill px-3 shadow">Chi tiết & Đặt vé</span>' +
            '</div>' +
          '</div>' +
          '<div class="mcard-info">' +
            '<h3 class="mcard-title" title="' + esc(m.title) + '">' + esc(m.title) + '</h3>' +
            '<div class="mcard-sub">' +
              '<span>' + esc(m.genre) + '</span> · <span>' + shortDuration(m.duration) + '</span>' +
            '</div>' +
            '<div class="mcard-showtimes ' + showtimeClass + '">' +
              '<span class="showtime-dot"></span>' +
              '<span class="showtime-text">' + showtimeText.replace("● ", "") + '</span>' +
            '</div>' +
            '<div class="mcard-footer">' +
              '<span class="btn btn-primary btn-sm w-100 mcard-btn">Đặt vé</span>' +
            '</div>' +
          '</div>' +
        '</a>';
      }).join("") + '</div>';

      $$(".mcard-trailer-btn").forEach(function (btn) {
        btn.onclick = function (ev) {
          ev.preventDefault();
          ev.stopPropagation();
          openTrailer(btn.getAttribute("data-trailer-title"), btn.getAttribute("data-trailer-id"));
        };
      });
    }

    var qInp = $("#q");
    var qClr = $("#q-clear");
    var qDebounceTimer = null;
    function updateQClear() {
      if (qClr) qClr.classList.toggle("visible", !!qInp.value);
    }
    if (qInp) {
      qInp.oninput = function () {
        updateQClear();
        if (qDebounceTimer) clearTimeout(qDebounceTimer);
        qDebounceTimer = setTimeout(function () {
          state.q = qInp.value.trim();
          render();
        }, 220);
      };
      qInp.onkeydown = function (e) {
        if (e.key === "Escape") {
          qInp.value = "";
          updateQClear();
          state.q = "";
          render();
        }
      };
    }
    if (qClr) {
      qClr.onclick = function (e) {
        e.preventDefault();
        qInp.value = "";
        updateQClear();
        state.q = "";
        render();
        qInp.focus();
      };
    }
    $$("#genres .genre").forEach(function (b) {
      b.onclick = function () {
        state.g = b.dataset.g;
        $$("#genres .genre").forEach(function (x) { x.classList.toggle("on", x === b); });
        render();
      };
    });

    var gp = $("#genrePrev"), gn = $("#genreNext"), gs = $("#genres");
    if (gp && gs) gp.onclick = function () { gs.scrollBy({ left: -240, behavior: "smooth" }); };
    if (gn && gs) gn.onclick = function () { gs.scrollBy({ left: 240, behavior: "smooth" }); };

    render();
  }

  function initHeroCarousel(slideCount) {
    if (slideCount <= 1) return;
    var currentIdx = 0;
    var isPaused = false;
    var intervalMs = 6000;
    var carouselEl = document.getElementById("heroCarousel");
    if (!carouselEl) return;

    var slides = $$(".carousel-slide", carouselEl);
    var indicators = $$(".indicator-bar", carouselEl);

    function goToSlide(idx) {
      if (idx < 0) idx = slideCount - 1;
      if (idx >= slideCount) idx = 0;
      currentIdx = idx;

      slides.forEach(function (s, i) {
        s.classList.toggle("active", i === idx);
      });
      indicators.forEach(function (bar, i) {
        bar.classList.toggle("active", i === idx);
        var p = bar.querySelector(".indicator-progress");
        if (p) {
          p.style.animation = "none";
          p.offsetHeight; // trigger reflow
          if (i === idx && !isPaused) {
            p.style.animation = "fillProgress " + intervalMs + "ms linear";
          }
        }
      });
    }

    function nextSlide() { goToSlide(currentIdx + 1); }
    function prevSlide() { goToSlide(currentIdx - 1); }

    var timer = setInterval(function () {
      if (!isPaused) nextSlide();
    }, intervalMs);

    timers.push(timer);

    var prevBtn = document.getElementById("carouselPrev");
    var nextBtn = document.getElementById("carouselNext");
    if (prevBtn) prevBtn.onclick = function () { prevSlide(); };
    if (nextBtn) nextBtn.onclick = function () { nextSlide(); };

    indicators.forEach(function (bar) {
      bar.onclick = function () {
        var to = parseInt(bar.getAttribute("data-to"), 10);
        if (!isNaN(to)) goToSlide(to);
      };
    });

    // Pause on hover
    carouselEl.addEventListener("mouseenter", function () { isPaused = true; });
    carouselEl.addEventListener("mouseleave", function () { isPaused = false; });

    // Keyboard navigation
    function handleKey(e) {
      if (location.hash && location.hash !== "#/" && location.hash !== "") return;
      if (e.key === "ArrowLeft") prevSlide();
      else if (e.key === "ArrowRight") nextSlide();
    }
    window.addEventListener("keydown", handleKey);

    // Touch swipe navigation for mobile
    var touchStartX = 0, touchEndX = 0;
    carouselEl.addEventListener("touchstart", function (e) {
      isPaused = true;
      touchStartX = e.changedTouches[0].screenX;
    }, { passive: true });
    carouselEl.addEventListener("touchend", function (e) {
      isPaused = false;
      touchEndX = e.changedTouches[0].screenX;
      if (touchStartX - touchEndX > 50) nextSlide();
      else if (touchEndX - touchStartX > 50) prevSlide();
    }, { passive: true });

    goToSlide(0);
  }

  /* =============================================================================
     CHI TIẾT PHIM + LỊCH CHIẾU
  ============================================================================= */
  async function movie(id) {
    var alive = current();
    show(back("#/", "Danh sách phim") + '<div class="skel" style="height:360px;border-radius:24px"></div>');

    var rawM;
    try {
      rawM = await call("movie", "GET", "/api/movies/" + encodeURIComponent(id));
    } catch (e) {
      if (alive()) { show(back("#/", "Danh sách phim") + errorBox(e)); bindRetry(function () { movie(id); }); }
      return;
    }
    if (!alive()) return;

    var m = enrichMovie(rawM);
    var sts = [], free = null, stErr = null, cur = null;

    var trailerBtnHtml = m.youtubeId
      ? '<button type="button" class="btn btn-outline-danger btn-lg d-inline-flex align-items-center gap-2" id="detailTrailerBtn">' +
          ICON_PLAY + ' Xem trailer</button>'
      : "";

    var genresList = m.genres && m.genres.length ? m.genres.join(" · ") : m.genre;
    var descText = m.description || "Bộ phim hấp dẫn mang lại trải nghiệm cảm xúc đa tầng và góc nhìn điện ảnh đặc sắc tại SOA Cinema.";

    show(
      back("#/", "Danh sách phim") +
      '<section class="detail detail-hero" style="' + palette(m) + '">' +
        backdrop(m) +
        '<div class="detail-in detail-hero-in">' +
          poster(m, "detail-poster shadow-lg") +
          '<div class="detail-content">' +
            '<div class="d-flex align-items-center gap-2 mb-2">' +
              '<span class="badge bg-secondary-subtle text-secondary px-3 py-1 rounded-pill">' + genreIcon(m.genre) + " " + esc(genresList) + "</span>" +
              (m.ageRating ? ageBadge(m.ageRating) : "") +
            "</div>" +
            '<h1 class="detail-title">' + esc(m.title) + "</h1>" +
            (m.titleVi && m.titleVi !== m.title ? '<h2 class="fs-5 text-secondary mb-3">' + esc(m.titleVi) + "</h2>" : "") +
            '<p class="detail-desc text-light-50 mb-4">' + esc(descText) + "</p>" +
            '<div class="facts" id="facts"></div>' +
            '<div class="d-flex flex-wrap gap-3 mt-4">' +
              '<a class="btn btn-primary btn-lg px-4" href="#showtimes" id="to-st"><i class="bi bi-calendar2-week me-2"></i>Chọn suất chiếu</a>' +
              trailerBtnHtml +
            "</div>" +
          "</div>" +
        "</div>" +
      "</section>" +

      '<section id="showtimes" class="mt-5">' +
        '<div class="section-head mb-4 d-flex justify-content-between align-items-center">' +
          '<div>' +
            '<h2 class="section-title mb-1">Lịch chiếu phim</h2>' +
            '<div class="text-secondary small">Chọn ngày và khung giờ bạn muốn xem</div>' +
          "</div>" +
          live("st-live") +
        "</div>" +
        '<div id="st-body"><div class="skel" style="height:180px;border-radius:16px"></div></div>' +
      "</section>"
    );

    var trBtn = $("#detailTrailerBtn");
    if (trBtn && m.youtubeId) {
      trBtn.onclick = function () { openTrailer(m.title, m.youtubeId); };
    }

    $("#to-st").onclick = function (ev) {
      ev.preventDefault();
      var el = document.getElementById("showtimes");
      if (el) el.scrollIntoView({ behavior: "smooth" });
    };

    async function load() {
      try {
        sts = (await call("showtime", "GET", "/api/showtimes?upcoming=1&movieId=" + encodeURIComponent(id))).filter(upcoming);
        stErr = null;
      } catch (e) {
        stErr = e;
      }

      if (!stErr && sts.length) {
        var av = await soft("booking", "/api/booking/availability?showtimeIds=" + sts.map(function (s) { return s.id; }).join(","), null);
        free = av ? {} : null;
        (av || []).forEach(function (a) { free[a.showtimeId] = TOTAL_SEATS - a.taken; });
      }

      if (!alive()) return;
      liveTick("st-live", !stErr);
      render();
    }

    function render() {
      sts.sort(function (a, b) { return String(a.time).localeCompare(String(b.time)); });
      var minPrice = sts.length ? Math.min.apply(null, sts.map(function (s) { return s.price; })) : 0;

      $("#facts").innerHTML =
        '<div class="fact-item"><span class="fact-label">Thời lượng</span><b class="fact-val">' + duration(m.duration) + "</b></div>" +
        '<div class="fact-item"><span class="fact-label">Suất sắp tới</span><b class="fact-val">' + (stErr ? "—" : sts.length) + "</b></div>" +
        (minPrice ? '<div class="fact-item"><span class="fact-label">Giá vé từ</span><b class="fact-val text-warning">' + money(minPrice) + "</b></div>" : "");

      var body = $("#st-body");
      if (stErr && !sts.length) { body.innerHTML = errorBox(stErr); bindRetry(load); return; }
      if (!sts.length) {
        body.innerHTML = stateBox("🗓️", "Chưa có suất chiếu", "Phim này hiện chưa có suất chiếu sắp tới. Quý khách vui lòng chọn phim khác nhé.");
        return;
      }

      var dates = [];
      sts.forEach(function (s) {
        var d = when(s.time).date;
        if (dates.indexOf(d) < 0) dates.push(d);
      });
      if (dates.indexOf(cur) < 0) cur = dates[0];

      var daySts = sts.filter(function (s) { return when(s.time).date === cur; });
      var groups = {}, order = [];
      daySts.forEach(function (s) {
        if (!groups[s.cinema]) { groups[s.cinema] = []; order.push(s.cinema); }
        groups[s.cinema].push(s);
      });

      body.innerHTML =
        '<div class="soa-date-tabs mb-4" role="tablist" aria-label="Chọn ngày chiếu">' +
          dates.map(function (d) {
            var w = when(d + " 00:00");
            return '<button type="button" class="soa-date-tab' + (d === cur ? " active" : "") + '" data-d="' + d + '" role="tab" aria-selected="' + (d === cur) + '">' +
              '<small>' + dayLabel(d) + "</small><b>" + w.dm + "</b></button>";
          }).join("") +
        "</div>" +
        order.map(function (c) {
          return '<div class="cinema-card mb-4">' +
            '<h3 class="cinema-name"><i class="bi bi-geo-alt-fill text-danger me-2"></i>' + esc(c) + "</h3>" +
            '<div class="times-grid">' + groups[c].map(function (s) {
              var f = free ? free[s.id] : null, out = f === 0;
              var seat = f == null ? "" : out ? '<em class="seats out">Hết vé</em>' : '<em class="seats' + (f <= 10 ? " low" : "") + '">Còn ' + f + " ghế</em>";
              return '<button class="time-btn" data-st="' + s.id + '"' + (out ? " disabled" : "") + ">" +
                '<b class="show-hm">' + when(s.time).hm + "</b>" +
                '<span class="show-sub">Phòng ' + esc(s.room) + " · " + money(s.price) + "</span>" +
                seat +
              "</button>";
            }).join("") + "</div>" +
          "</div>";
        }).join("");

      $$("#st-body .soa-date-tab").forEach(function (b) {
        b.onclick = function () { cur = b.dataset.d; render(); };
      });
      $$("#st-body [data-st]").forEach(function (b) {
        b.onclick = function () { location.hash = "#/book/" + id + "/" + b.dataset.st; };
      });
    }

    await load();
    every(load, 30000);
  }

  /* =============================================================================
     CHỌN GHẾ (SƠ ĐỒ 6 HÀNG X 10 CỘT, LIVE UPDATE 5S, TỰ BỎ CHỌN NẾU BỊ ĐẶT)
  ============================================================================= */
  async function book(movieId, stId, notice) {
    if (needLogin()) return;
    var alive = current();
    var backLink = back("#/movie/" + movieId, "Đổi suất chiếu");

    show(
      backLink + steps(1) +
      '<div class="book booking-layout">' +
        '<div class="skel" style="height:440px;border-radius:20px"></div>' +
        '<div class="skel" style="height:440px;border-radius:20px"></div>' +
      "</div>"
    );

    var st, taken, rawM, mine;
    try {
      st = await call("showtime", "GET", "/api/showtimes/" + encodeURIComponent(stId));
      taken = (await call("booking", "GET", "/api/booking/seats?showtimeId=" + encodeURIComponent(stId))).seats || [];
    } catch (e) {
      if (alive()) { show(backLink + errorBox(e)); bindRetry(function () { book(movieId, stId); }); }
      return;
    }

    var extra = await Promise.all([
      soft("movie", "/api/movies/" + encodeURIComponent(movieId), null),
      soft("booking", "/api/booking?status=PENDING&username=" + encodeURIComponent(user.username), [])
    ]);

    if (!alive()) return;
    rawM = extra[0] || { id: movieId, title: "Phim", genre: "" };
    var m = enrichMovie(rawM);
    mine = extra[1].filter(function (b) { return String(b.showtimeId) === String(stId); })[0];

    if (!upcoming(st)) {
      show(backLink + stateBox("⏰", "Suất chiếu đã bắt đầu", "Suất chiếu " + when(st.time).full + " đã đóng cổng đặt vé.",
        '<a class="btn btn-primary mt-3" href="#/movie/' + movieId + '">Chọn suất khác</a>'));
      return;
    }

    var picked = [], w = when(st.time);

    // Sơ đồ phòng chiếu
    var hall = "";
    MAP.rows.split("").forEach(function (r) {
      hall += '<div class="srow seat-row"><span class="rl row-label">' + r + "</span>";
      for (var c = 1; c <= MAP.cols; c++) {
        hall += '<button class="seat seat-btn" data-seat="' + r + c + '" aria-pressed="false">' + c + "</button>";
        if (MAP.aisleAfter.indexOf(c) >= 0) hall += '<span class="aisle"></span>';
      }
      hall += '<span class="rl row-label">' + r + "</span></div>";
    });

    show(
      backLink + steps(1) +
      (mine ? '<div class="alert alert-warning d-flex align-items-center gap-3 mb-4"><i class="bi bi-hourglass-split fs-4"></i><div>' +
        'Bạn đang giữ ghế <b>' + esc(mine.seats.join(", ")) + '</b> cho suất này (đơn ' + code(mine) + ') nhưng chưa thanh toán. ' +
        '<a class="btn btn-warning btn-sm ms-2" href="#/pay/' + mine.id + '">Tiếp tục thanh toán</a></div></div>' : "") +

      '<div class="book booking-layout">' +
        '<div class="panel seat-panel">' +
          '<div class="panel-head d-flex justify-content-between align-items-center">' +
            '<div><b class="fs-5">Sơ đồ ghế</b> · Phòng ' + esc(st.room) + "</div>" +
            live("seat-live") +
          "</div>" +

          '<div class="hall">' +
            '<div class="hall-in">' +
              '<div class="screen-box"><div class="screen-curve"></div><span class="screen-label">MÀN HÌNH</span></div>' +
              hall +
            "</div>" +
          "</div>" +

          '<div class="legend seat-legend d-flex justify-content-center gap-4 flex-wrap mt-4">' +
            '<span><i class="seat-dot available"></i>Ghế trống</span>' +
            '<span><i class="seat-dot sel"></i>Đang chọn</span>' +
            '<span><i class="seat-dot taken"></i>Đã có người đặt</span>' +
          "</div>" +
        "</div>" +

        '<aside class="panel summary order-summary-panel">' +
          '<div class="sum-movie d-flex gap-3 align-items-center mb-3">' +
            poster(m, "sm") +
            '<div>' +
              '<h3 class="fs-5 mb-1 text-truncate">' + esc(m.title) + "</h3>" +
              '<div class="text-secondary small">' + esc(st.cinema) + "</div>" +
            "</div>" +
          "</div>" +

          '<div class="soa-info-row"><span class="soa-info-label">Suất chiếu</span><b class="soa-info-value">' + w.hm + " · " + dayLabel(w.date) + " " + w.dm + "</b></div>" +
          '<div class="soa-info-row"><span class="soa-info-label">Phòng chiếu</span><b class="soa-info-value">Phòng ' + esc(st.room) + "</b></div>" +
          '<div class="soa-info-row"><span class="soa-info-label">Giá vé</span><b class="soa-info-value">' + money(st.price) + " / ghế</b></div>" +
          '<div class="soa-info-row"><span class="soa-info-label">Số lượng</span><b class="soa-info-value" id="cnt">0 / ' + MAP.maxSeats + "</b></div>" +

          '<div class="seat-chips-container my-3">' +
            '<label class="text-secondary small d-block mb-1">Ghế đã chọn:</label>' +
            '<div class="seat-chips d-flex flex-wrap gap-2" id="chips"></div>' +
          "</div>" +

          '<div class="total-box d-flex justify-content-between align-items-baseline pt-3 border-top border-secondary mb-3">' +
            '<span class="text-secondary">Tổng cộng</span>' +
            '<b class="total-price text-warning fs-4" id="sum">0 đ</b>' +
          "</div>" +

          '<div id="err">' + (notice ? '<div class="alert alert-danger py-2 px-3 small mb-3">⚠ ' + esc(notice) + "</div>" : "") + "</div>" +

          '<button class="btn btn-primary btn-lg w-100 py-3 font-weight-bold" id="hold" disabled>' +
            '<i class="bi bi-lock-fill me-1"></i> Giữ ghế &amp; thanh toán' +
          "</button>" +
          '<p class="text-secondary small text-center mt-2 mb-0">Ghế được giữ 10 phút để bạn hoàn tất thanh toán.</p>' +
        "</aside>" +
      "</div>"
    );

    function paint() {
      $$(".seat").forEach(function (b) {
        var c = b.dataset.seat;
        var t = taken.indexOf(c) >= 0;
        var sel = picked.indexOf(c) >= 0;
        b.classList.toggle("taken", t);
        b.classList.toggle("sel", sel);
        b.disabled = t;
        b.setAttribute("aria-pressed", String(sel));
        b.setAttribute("aria-label", c + (t ? " đã có người đặt" : sel ? " đang chọn" : " còn trống"));
      });

      $("#cnt").textContent = picked.length + " / " + MAP.maxSeats;
      $("#chips").innerHTML = picked.length
        ? picked.map(function (c) { return '<span class="badge bg-warning text-dark px-2 py-1 fs-6">' + c + "</span>"; }).join("")
        : '<span class="text-secondary small">Vui lòng chọn ghế trên sơ đồ</span>';

      $("#sum").textContent = money(picked.length * st.price);
      $("#hold").disabled = !picked.length;
    }

    $$(".seat").forEach(function (b) {
      b.onclick = function () {
        var c = b.dataset.seat, i = picked.indexOf(c);
        if (i >= 0) {
          picked.splice(i, 1);
        } else if (picked.length >= MAP.maxSeats) {
          toast("Mỗi đơn đặt tối đa " + MAP.maxSeats + " ghế", "err");
          return;
        } else {
          picked.push(c);
        }
        picked.sort(function (a, z) {
          return a.charCodeAt(0) - z.charCodeAt(0) || parseInt(a.slice(1)) - parseInt(z.slice(1));
        });
        paint();
      };
    });

    // Cập nhật trực tiếp mỗi 5 giây
    async function refreshSeats() {
      var r = await soft("booking", "/api/booking/seats?showtimeId=" + encodeURIComponent(stId), null);
      if (!alive()) return;
      liveTick("seat-live", !!r);
      if (!r) return;

      taken = r.seats || [];
      var lost = picked.filter(function (c) { return taken.indexOf(c) >= 0; });
      if (lost.length) {
        picked = picked.filter(function (c) { return lost.indexOf(c) < 0; });
        toast("Ghế " + lost.join(", ") + " vừa có khách khác đặt trước", "err");
      }

      if (!upcoming(st)) { book(movieId, stId); return; }
      paint();
    }

    $("#hold").onclick = async function () {
      var btn = this;
      btn.disabled = true;
      btn.innerHTML = '<span class="spinner-border spinner-border-sm me-2" role="status"></span> Đang giữ ghế...';
      $("#err").innerHTML = "";

      try {
        var r = await call("booking", "POST", "/api/booking", {
          username: user.username,
          movieId: Number(movieId),
          showtimeId: Number(stId),
          seats: picked,
          payNow: false
        });
        location.hash = "#/pay/" + r.id;
      } catch (e) {
        if (e.code === "SEAT_TAKEN") {
          book(movieId, stId, e.message + ". Sơ đồ ghế đã được cập nhật, vui lòng chọn lại.");
          return;
        }
        if (e.code === "SHOWTIME_CLOSED") {
          book(movieId, stId);
          return;
        }
        $("#err").innerHTML = '<div class="alert alert-danger py-2 px-3 small mb-3">⚠ ' + esc(e.message) + "</div>";
        btn.innerHTML = '<i class="bi bi-lock-fill me-1"></i> Giữ ghế &amp; thanh toán';
        btn.disabled = false;
      }
    };

    paint();
    liveTick("seat-live", true);
    every(refreshSeats, 5000);
  }

  /* ---------- Tải thông tin đơn hàng đầy đủ ---------- */
  async function loadOrder(id) {
    var b = await call("booking", "GET", "/api/booking/" + encodeURIComponent(id));
    if (b.username !== user.username) {
      var e = new Error(FRIENDLY.FORBIDDEN);
      e.code = "FORBIDDEN";
      throw e;
    }
    var r = await Promise.all([
      soft("movie", "/api/movies/" + b.movieId, null),
      soft("showtime", "/api/showtimes/" + b.showtimeId, null)
    ]);
    return {
      b: b,
      m: enrichMovie(r[0] || { id: b.movieId, title: "Phim", genre: "" }),
      st: r[1]
    };
  }

  function orderSummary(o, extra) {
    var b = o.b, st = o.st, w = st ? when(st.time) : null;
    return '<div class="sum-movie d-flex gap-3 align-items-center mb-3">' +
      poster(o.m, "sm") +
      '<div>' +
        '<h3 class="fs-5 mb-1">' + esc(o.m.title) + "</h3>" +
        '<div class="text-secondary small">' + esc(st ? st.cinema : "") + "</div>" +
      "</div>" +
    "</div>" +
    (w ? '<div class="soa-info-row"><span class="soa-info-label">Suất chiếu</span><b class="soa-info-value">' + w.hm + " · " + dayLabel(w.date) + " " + w.dm + '</b></div><div class="soa-info-row"><span class="soa-info-label">Phòng chiếu</span><b class="soa-info-value">Phòng ' + esc(st.room) + "</b></div>" : "") +
    '<div class="soa-info-row"><span class="soa-info-label">Ghế đặt</span><b class="soa-info-value">' + esc(b.seats.join(", ")) + '</b></div>' +
    '<div class="soa-info-row"><span class="soa-info-label">Mã đặt vé</span><b class="soa-info-value text-warning font-monospace">' + code(b) + "</b></div>" +
    '<div class="total-box pt-3 border-top border-secondary border-opacity-50 mt-2 mb-3">' +
      '<span class="text-secondary">Tổng thanh toán</span>' +
      '<b class="total-price text-warning fs-4">' + money(b.totalPrice) + "</b>" +
    "</div>" +
    (extra || "");
  }

  /* =============================================================================
     THANH TOÁN (10 PHÚT GIỮ GHẾ, VIETQR, MOMO, VNPAY)
  ============================================================================= */
  async function pay(id) {
    if (needLogin()) return;
    var alive = current();
    show(
      steps(2) +
      '<div class="book pay booking-layout">' +
        '<div class="skel" style="height:520px;border-radius:20px"></div>' +
        '<div class="skel" style="height:440px;border-radius:20px"></div>' +
      "</div>"
    );

    var o;
    try {
      o = await loadOrder(id);
    } catch (e) {
      if (alive()) {
        show(back("#/my", "Vé của tôi") + errorBox(e, e.code !== "FORBIDDEN" && e.code !== "NOT_FOUND"));
        bindRetry(function () { pay(id); });
      }
      return;
    }
    if (!alive()) return;

    if (o.b.status === "PAID") { location.hash = "#/ticket/" + id; return; }
    if (o.b.status === "CANCELLED") { expired(o); return; }

    var b = o.b, deadline = toDate(b.expiresAt);
    var method = sessionStorage.getItem("soa.method") || METHODS[0].value;
    var qrMode = "BANK"; // "BANK" hoặc "SANDBOX"
    var busy = false;
    if (!methodOf(method)) method = METHODS[0].value;

    show(
      back("#/my", "Vé của tôi") + steps(2) +
      '<div class="book pay booking-layout">' +
        '<div class="panel">' +
          '<div class="panel-head d-flex justify-content-between align-items-center">' +
            '<div><b class="fs-5">Phương thức thanh toán</b></div>' +
            '<span class="hold-mini badge bg-warning text-dark px-3 py-2 fs-6" id="left2">Giữ ghế còn --:--</span>' +
          "</div>" +

          '<div class="methods-group my-3" id="methods">' +
            METHODS.map(function (p) {
              return '<label class="method-card d-flex align-items-center justify-content-between p-3 mb-2 rounded border border-secondary">' +
                '<div class="d-flex align-items-center gap-3">' +
                  '<input type="radio" name="method" class="form-check-input" value="' + p.value + '"' + (p.value === method ? " checked" : "") + ">" +
                  '<div>' +
                    '<b class="d-block">' + esc(p.label) + "</b>" +
                    '<small class="text-secondary">' + esc(p.hint) + "</small>" +
                  "</div>" +
                "</div>" +
                '<span class="method-badge ' + p.value + '">' + esc(p.logo) + "</span>" +
              "</label>";
            }).join("") +
          "</div>" +

          '<div id="pay-box"></div>' +
        "</div>" +

        '<aside class="panel summary order-summary-panel">' +
          '<div class="hold-countdown-card p-3 rounded mb-4" id="hold">' +
            '<div class="d-flex justify-content-between align-items-center mb-2">' +
              '<span class="text-secondary small"><i class="bi bi-clock-history me-1"></i> Thời gian giữ ghế</span>' +
              '<b class="fs-4 font-monospace" id="left">--:--</b>' +
            "</div>" +
            '<div class="progress" style="height: 8px;">' +
              '<div class="progress-bar bg-warning progress-bar-striped progress-bar-animated" id="bar" role="progressbar" style="width: 100%"></div>' +
            "</div>" +
          "</div>" +

          orderSummary(o) +

          '<div id="err"></div>' +

          '<button class="btn btn-primary btn-lg w-100 py-3 font-weight-bold" id="paid">' +
            '<i class="bi bi-check2-circle me-1"></i> Tôi đã thanh toán' +
          "</button>" +

          '<button class="btn btn-outline-danger w-100 mt-2 py-2" id="cancel">' +
            '<i class="bi bi-x-circle me-1"></i> Hủy đơn &amp; nhả ghế' +
          "</button>" +
        "</aside>" +
      "</div>"
    );

    function box() {
      var p = methodOf(method), amount = b.totalPrice, ref = code(b), qr, info;
      var sandboxUrl = (window.SANDBOX_BASE_URL || location.origin) + "/#/sandbox-pay/" + id;

      if (qrMode === "SANDBOX") {
        qr = sandboxUrl;
        info = row("Chế độ thử nghiệm", '<span class="badge bg-warning text-dark">Mobile Sandbox</span>') +
          row("Mã đơn hàng", '<b class="ref font-monospace text-warning">' + ref + "</b>", ref, "mã đơn hàng") +
          row("Số tiền thanh toán", money(amount), String(amount), "số tiền") +
          row("Liên kết thử", '<a href="' + sandboxUrl + '" class="text-warning small text-decoration-underline" target="_blank">Mở thanh toán thử ↗</a>');
      } else if (method === "BANK_TRANSFER") {
        qr = QR.vietQR({ bin: BANK.bin, account: BANK.account, amount: amount, content: ref });
        info = row("Ngân hàng nhận", esc(BANK.bank)) +
          row("Số tài khoản", esc(BANK.account), BANK.account, "số tài khoản") +
          row("Chủ tài khoản", esc(BANK.holder)) +
          row("Số tiền thanh toán", money(amount), String(amount), "số tiền") +
          row("Nội dung chuyển khoản", '<b class="ref font-monospace text-warning">' + ref + "</b>", ref, "nội dung");
      } else {
        qr = "SOACINEMA|" + method + "|" + ref + "|" + amount;
        info = row("Đơn vị thụ hưởng", "SOA Cinema") +
          row("Mã đơn hàng", '<b class="ref font-monospace text-warning">' + ref + "</b>", ref, "mã đơn hàng") +
          row("Số tiền thanh toán", money(amount), String(amount), "số tiền");
      }

      var stepsTxt = qrMode === "SANDBOX"
        ? ["Dùng <b>Camera điện thoại</b> quét mã QR bên cạnh.", "Trình duyệt trên điện thoại sẽ mở trang xác nhận thanh toán mô phỏng.", "Bấm nút <b>Xác nhận thanh toán thử</b> để hoàn tất ngay lập tức!"]
        : method === "BANK_TRANSFER"
          ? ["Mở ứng dụng ngân hàng, chọn <b>Quét mã QR</b>.", "Kiểm tra đúng số tiền và nội dung <b>" + ref + "</b> (đã điền sẵn).", "Xác nhận chuyển tiền, sau đó bấm <b>Tôi đã thanh toán</b>."]
          : method === "MOMO"
            ? ["Mở ứng dụng <b>MoMo</b>, chọn biểu tượng <b>Quét mã</b>.", "Quét mã QR bên cạnh và kiểm tra đúng số tiền.", "Xác nhận thanh toán, sau đó bấm <b>Tôi đã thanh toán</b>."]
            : ["Mở app ngân hàng hoặc ví hỗ trợ <b>VNPAY-QR</b>.", "Quét mã QR bên cạnh và kiểm tra đúng số tiền.", "Xác nhận thanh toán, sau đó bấm <b>Tôi đã thanh toán</b>."];

      var qrLabel = qrMode === "SANDBOX" ? "QR Thử nghiệm trên di động" : ("Mã QR thanh toán " + p.label);
      var qrCap = qrMode === "SANDBOX" ? "Quét thử bằng điện thoại" : (esc(p.logo) + " · " + money(amount));

      $("#pay-box").innerHTML =
        '<div class="paybox ' + method + ' p-3 rounded border border-secondary mt-3">' +
          '<div class="d-flex justify-content-center mb-3">' +
            '<div class="qr-mode-tabs">' +
              '<button type="button" class="qr-mode-btn ' + (qrMode === "BANK" ? "active" : "") + '" id="btnQrBank">Mã thanh toán ' + esc(p.logo) + '</button>' +
              '<button type="button" class="qr-mode-btn ' + (qrMode === "SANDBOX" ? "active" : "") + '" id="btnQrSandbox"><i class="bi bi-phone me-1"></i>Quét thử bằng điện thoại</button>' +
            '</div>' +
          '</div>' +
          '<div class="d-flex flex-column flex-md-row gap-4 align-items-center">' +
            '<div class="qr-wrap text-center">' +
              '<div class="qr p-2 bg-white rounded shadow-sm d-inline-block">' + QR.svg(qr, { label: qrLabel }) + "</div>" +
              '<div class="qr-cap mt-2 text-secondary small font-weight-bold">' + qrCap + "</div>" +
            "</div>" +
            '<div class="pay-info flex-grow-1">' +
              info +
              '<ol class="howto small text-secondary ps-3 mt-3 mb-0">' +
                stepsTxt.map(function (s) { return '<li class="mb-1">' + s + "</li>"; }).join("") +
              "</ol>" +
            "</div>" +
          "</div>" +
          '<div class="alert alert-secondary d-flex align-items-center gap-2 mt-3 mb-0 small border-secondary">' +
            '<i class="bi bi-info-circle-fill text-warning"></i>' +
            '<div>Mẹo thử nghiệm: Quý khách có thể quét mã thử bằng điện thoại hoặc bấm nút <b>Tôi đã thanh toán</b> bên dưới để hoàn tất đơn hàng.</div>' +
          '</div>' +
        "</div>";

      var btnBank = $("#btnQrBank");
      if (btnBank) btnBank.onclick = function () { qrMode = "BANK"; box(); };
      var btnSandbox = $("#btnQrSandbox");
      if (btnSandbox) btnSandbox.onclick = function () { qrMode = "SANDBOX"; box(); };

      $$("#pay-box [data-copy]").forEach(function (el) {
        el.onclick = function () { copy(el.dataset.copy, el.dataset.label); };
      });
    }

    function row(k, v, copyVal, label) {
      return '<div class="soa-info-row">' +
        '<span class="soa-info-label">' + k + "</span>" +
        '<b class="soa-info-value d-flex align-items-center gap-2">' + v +
          (copyVal ? ' <button class="btn btn-sm btn-outline-secondary p-1 lh-1" type="button" data-copy="' + esc(copyVal) + '" data-label="' + esc(label) + '" title="Sao chép ' + esc(label) + '">' + ICON_COPY + "</button>" : "") +
        "</b></div>";
    }

    function tick() {
      var left = deadline ? deadline - new Date() : 0, total = 10 * 60 * 1000;
      var mmssStr = mmss(left);
      var urgent = left < 60000;

      $("#left").textContent = mmssStr;
      var left2 = $("#left2");
      left2.textContent = "Giữ ghế còn " + mmssStr;
      left2.classList.toggle("bg-danger", urgent);
      left2.classList.toggle("bg-warning", !urgent);

      var bar = $("#bar");
      var pct = Math.max(0, Math.min(100, left / total * 100));
      bar.style.width = pct + "%";
      bar.classList.toggle("bg-danger", urgent);
      bar.classList.toggle("bg-warning", !urgent);

      var holdBox = $("#hold");
      holdBox.classList.toggle("border-danger", urgent);

      if (deadline && left <= 0 && !busy) {
        busy = true;
        recheck();
      }
    }

    async function recheck() {
      var nb = await soft("booking", "/api/booking/" + id, null);
      if (!alive() || !nb) { busy = false; return; }
      if (nb.status === "PAID") { location.hash = "#/ticket/" + id; return; }
      if (nb.status === "CANCELLED") { o.b = nb; leave(); expired(o); return; }
      busy = false;
    }

    $$("#methods input").forEach(function (r) {
      r.onchange = function () {
        method = r.value;
        sessionStorage.setItem("soa.method", method);
        box();
      };
    });

    $("#paid").onclick = async function () {
      var btn = this;
      if (busy) return;
      busy = true;
      btn.disabled = true;
      btn.innerHTML = '<span class="spinner-border spinner-border-sm me-2" role="status"></span> Đang xác nhận giao dịch...';
      $("#err").innerHTML = "";

      try {
        var r = await call("booking", "POST", "/api/booking/" + id + "/pay", {
          username: user.username,
          paymentMethod: method
        });
        if (r.status === "PAID") {
          sessionStorage.setItem("soa.paid." + id, JSON.stringify({
            method: method,
            transactionId: r.payment && r.payment.transactionId,
            notification: r.notification
          }));
          location.hash = "#/ticket/" + id + "/new";
          return;
        }
        $("#err").innerHTML = '<div class="alert alert-warning small mb-3">⚠ Giao dịch chưa được ghi nhận. Ghế vẫn được giữ — vui lòng thử lại hoặc chọn phương thức khác.</div>';
      } catch (e) {
        if (e.code === "ALREADY_PAID") { location.hash = "#/ticket/" + id; return; }
        if (e.code === "BOOKING_CANCELLED") { recheck(); return; }
        var userMsg = (e.message && e.message.indexOf("500") < 0 && e.message.indexOf("5005") < 0 && e.message.indexOf("ECONN") < 0)
          ? e.message
          : "Hệ thống thanh toán đang bảo trì tạm thời. Đơn đặt vé và chỗ ngồi của quý khách vẫn được giữ an toàn. Vui lòng thử lại sau ít phút hoặc chọn thanh toán tại quầy.";
        $("#err").innerHTML = '<div class="alert alert-danger small mb-3">⚠ ' + esc(userMsg) + "</div>";
      }
      busy = false;
      btn.disabled = false;
      btn.innerHTML = '<i class="bi bi-check2-circle me-1"></i> Tôi đã thanh toán';
    };

    $("#cancel").onclick = function () {
      confirmDialog(
        "Hủy đơn đặt vé",
        "Bạn có chắc muốn hủy đơn đặt vé này? Ghế đã chọn sẽ được nhả để khách hàng khác có thể đặt.",
        async function () {
          var btn = $("#cancel");
          if (btn) btn.disabled = true;
          try {
            await call("booking", "POST", "/api/booking/" + id + "/cancel", { username: user.username });
            toast("Đã hủy đơn " + code(b) + ", ghế đã được nhả");
            location.hash = "#/my";
          } catch (e) {
            toast(e.message, "err");
            if (btn) btn.disabled = false;
          }
        }
      );
    };

    box();
    tick();
    every(tick, 1000);
    every(function () { if (!busy) { busy = true; recheck(); } }, 5000);
  }

  function expired(o) {
    show(
      back("#/my", "Vé của tôi") +
      stateBox(
        "⌛",
        "Đơn đã hết thời gian giữ ghế",
        "Đơn " + code(o.b) + " chưa được thanh toán trong thời gian 10 phút giữ chỗ nên đã tự động hủy và ghế đã được nhả.",
        '<div class="d-flex justify-content-center gap-3 mt-4">' +
          '<a class="btn btn-primary" href="#/book/' + o.b.movieId + "/" + o.b.showtimeId + '">Chọn lại ghế</a>' +
          '<a class="btn btn-outline-light" href="#/my">Vé của tôi</a>' +
        "</div>"
      )
    );
  }

  /* =============================================================================
     THANH TOÁN THỬ NGHIỆM SANDBOX TRÊN DI ĐỘNG (YÊU CẦU L3)
  ============================================================================= */
  async function sandboxPay(id) {
    var alive = current();
    show(
      '<div class="container py-5" style="max-width: 520px;">' +
        '<div class="skel" style="height:440px;border-radius:20px"></div>' +
      '</div>'
    );

    var b;
    try {
      b = await call("booking", "GET", "/api/booking/" + encodeURIComponent(id));
    } catch (e) {
      if (alive()) show(stateBox("⚠️", "Không tìm thấy đơn", "Đơn đặt vé này không tồn tại hoặc đã hết hạn.", '<a href="#/" class="btn btn-primary mt-3">Về trang chủ</a>'));
      return;
    }
    if (!alive()) return;

    if (b.status === "PAID") {
      location.hash = "#/ticket/" + id;
      return;
    }
    if (b.status === "CANCELLED") {
      show(stateBox("⌛", "Đơn đã hết hạn", "Đơn đặt vé này đã hết thời gian giữ chỗ 10 phút.", '<a href="#/" class="btn btn-primary mt-3">Chọn suất khác</a>'));
      return;
    }

    var r = await Promise.all([
      soft("movie", "/api/movies/" + b.movieId, null),
      soft("showtime", "/api/showtimes/" + b.showtimeId, null)
    ]);
    var m = enrichMovie(r[0] || { title: "Phim #" + b.movieId });
    var st = r[1] || {};
    var w = when(st.time);

    show(
      '<div class="container py-4" style="max-width: 520px;">' +
        '<div class="card border-warning bg-dark p-4 shadow-lg text-center" style="border-radius: 20px;">' +
          '<div class="d-flex align-items-center justify-content-center gap-2 mb-3">' +
            '<span class="brand-mark">▶</span>' +
            '<span class="fs-4 fw-bold text-white">SOA<b>Cinema</b></span>' +
          '</div>' +
          '<div class="mb-3">' +
            '<span class="badge bg-warning text-dark px-3 py-1 fs-6 rounded-pill"><i class="bi bi-phone me-1"></i>Thanh toán di động mô phỏng</span>' +
          '</div>' +
          '<div class="d-flex gap-3 align-items-center text-start p-3 rounded bg-black bg-opacity-50 border border-secondary mb-3">' +
            poster(m, "sm") +
            '<div>' +
              '<h5 class="text-white mb-1">' + esc(m.title) + '</h5>' +
              '<div class="text-secondary small">' + (st.cinema ? esc(st.cinema) + " · Phòng " + esc(st.room) : "") + '</div>' +
              '<div class="text-warning small">' + (w ? w.hm + " · " + dayLabel(w.date) + " " + w.dm : "") + '</div>' +
            '</div>' +
          '</div>' +
          '<div class="soa-info-row"><span class="soa-info-label">Mã đặt vé</span><b class="soa-info-value text-warning font-monospace">' + code(b) + '</b></div>' +
          '<div class="soa-info-row"><span class="soa-info-label">Khách hàng</span><b class="soa-info-value">' + esc(b.username) + '</b></div>' +
          '<div class="soa-info-row"><span class="soa-info-label">Ghế đã chọn</span><b class="soa-info-value text-warning">' + esc(b.seats.join(", ")) + '</b></div>' +
          '<div class="soa-info-row"><span class="soa-info-label">Tổng tiền</span><b class="soa-info-value fs-4 text-warning">' + money(b.totalPrice) + '</b></div>' +
          '<div id="sandboxErr"></div>' +
          '<button type="button" class="btn btn-primary btn-lg w-100 py-3 mt-4 fw-bold shadow" id="btnConfirmSandbox">' +
            '<i class="bi bi-check-circle-fill me-2"></i> Xác nhận thanh toán thử' +
          '</button>' +
          '<a href="#/pay/' + b.id + '" class="btn btn-outline-secondary w-100 mt-2 py-2 small">Quay lại trang chi tiết thanh toán</a>' +
        '</div>' +
      '</div>'
    );

    var confirmBtn = $("#btnConfirmSandbox");
    if (confirmBtn) {
      confirmBtn.onclick = async function () {
        confirmBtn.disabled = true;
        confirmBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span> Đang xác nhận...';
        $("#sandboxErr").innerHTML = "";
        try {
          var res = await call("booking", "POST", "/api/booking/" + id + "/pay", {
            username: b.username,
            paymentMethod: "BANK_TRANSFER"
          });
          if (res.status === "PAID") {
            sessionStorage.setItem("soa.paid." + id, JSON.stringify({
              method: "BANK_TRANSFER",
              transactionId: res.payment && res.payment.transactionId,
              notification: res.notification
            }));
            toast("Thanh toán thành công!", "ok");
            location.hash = "#/ticket/" + id + "/new";
            return;
          }
          $("#sandboxErr").innerHTML = '<div class="alert alert-warning py-2 small mt-3">Giao dịch chưa hoàn tất. Vui lòng thử lại.</div>';
          confirmBtn.disabled = false;
          confirmBtn.innerHTML = '<i class="bi bi-check-circle-fill me-2"></i> Xác nhận thanh toán thử';
        } catch (e) {
          var errMsg = "Hệ thống thanh toán đang bảo trì tạm thời. Đơn đặt vé của bạn vẫn được giữ an toàn. Vui lòng thử lại sau.";
          $("#sandboxErr").innerHTML = '<div class="alert alert-danger py-2 small mt-3">⚠ ' + errMsg + '</div>';
          confirmBtn.disabled = false;
          confirmBtn.innerHTML = '<i class="bi bi-check-circle-fill me-2"></i> Xác nhận thanh toán thử';
        }
      };
    }
  }

  /* =============================================================================
     VÉ ĐIỆN TỬ (MÃ VẠCH 1D CODE 128, RĂNG CƯA ĐỤC LỖ, BẢN IN SẮC NÉT)
  ============================================================================= */
  async function ticket(id, fresh) {
    if (needLogin()) return;
    var alive = current();
    show('<div class="skel" style="height:380px;max-width:880px;margin:40px auto;border-radius:24px"></div>');

    var o;
    try {
      o = await loadOrder(id);
    } catch (e) {
      if (alive()) {
        show(back("#/my", "Vé của tôi") + errorBox(e, e.code !== "FORBIDDEN" && e.code !== "NOT_FOUND"));
        bindRetry(function () { ticket(id, fresh); });
      }
      return;
    }
    if (!alive()) return;

    var b = o.b, m = o.m, st = o.st || {}, w = when(st.time);
    if (b.status === "PENDING") { location.hash = "#/pay/" + id; return; }
    if (b.status === "CANCELLED") { expired(o); return; }

    var paid = null;
    try { paid = JSON.parse(sessionStorage.getItem("soa.paid." + id) || "null"); } catch (e) {}
    var pm = paid && methodOf(paid.method);
    var started = st.time && !upcoming(st);
    var note = fresh
      ? (paid && paid.notification === "FAILED"
          ? "Vé đã được xác nhận. Thông báo qua email sẽ được gửi bổ sung sau ít phút."
          : "Vé xem phim đã được tạo và gửi thông báo xác nhận tới tài khoản của bạn.")
      : "";

    var bookingCode = code(b);

    // Sinh mã vạch 1D Code 128 bằng thuần JS SVG (chạy 100% offline)
    var barcodeSvg = window.Barcode
      ? window.Barcode.svg(bookingCode, { height: 64, showText: false, barWidth: 2, quietZone: 12 })
      : '<div class="font-monospace fs-4 text-center">' + bookingCode + "</div>";

    show(
      (fresh ? steps(3) : back("#/my", "Vé của tôi")) +
      '<div class="eticket-wrapper my-4">' +
        '<div class="eticket-card ' + (fresh ? "fresh-reveal" : "") + '">' +
          // Khối thân vé chính (bên trái)
          '<div class="eticket-main">' +
            '<div class="eticket-header d-flex justify-content-between align-items-center mb-3">' +
              '<div class="d-flex align-items-center gap-2">' +
                '<span class="brand-mark">▶</span>' +
                '<span class="fw-bold fs-5">SOA<b>Cinema</b></span>' +
              "</div>" +
              '<span class="badge bg-success-subtle text-success px-3 py-1 rounded-pill">' +
                '<i class="bi bi-check-circle-fill me-1"></i> ' + (fresh ? "Thanh toán thành công" : "Vé hợp lệ") +
              "</span>" +
            "</div>" +

            '<div class="eticket-movie-info d-flex gap-3 align-items-start mb-4">' +
              poster(m, "ticket-poster") +
              '<div>' +
                '<h2 class="eticket-movie-title mb-1">' + esc(m.title) + "</h2>" +
                (m.titleVi && m.titleVi !== m.title ? '<div class="text-secondary small mb-2">' + esc(m.titleVi) + "</div>" : "") +
                '<div class="d-flex gap-2 flex-wrap mb-2">' +
                  '<span class="badge bg-secondary-subtle text-light small">' + esc(m.genre) + "</span>" +
                  (m.ageRating ? ageBadge(m.ageRating) : "") +
                  '<span class="badge bg-secondary-subtle text-light small">' + duration(m.duration) + "</span>" +
                "</div>" +
                (note ? '<p class="text-success small mb-0"><i class="bi bi-info-circle me-1"></i>' + note + "</p>" : "") +
              "</div>" +
            "</div>" +

            '<div class="eticket-grid">' +
              '<div class="soa-info-row"><span class="soa-info-label">Rạp chiếu</span><b class="soa-info-value">' + esc(st.cinema || "—") + "</b></div>" +
              '<div class="soa-info-row"><span class="soa-info-label">Phòng chiếu</span><b class="soa-info-value">Phòng ' + esc(st.room || "—") + "</b></div>" +
              '<div class="soa-info-row"><span class="soa-info-label">Suất chiếu</span><b class="soa-info-value text-warning">' + esc(st.time ? w.full : "—") + "</b></div>" +
              '<div class="soa-info-row"><span class="soa-info-label">Ghế (' + b.seats.length + ' vé)</span><b class="soa-info-value text-warning fs-5">' + esc(b.seats.join(", ")) + "</b></div>" +
              '<div class="soa-info-row"><span class="soa-info-label">Tổng thanh toán</span><b class="soa-info-value">' + money(b.totalPrice) + "</b></div>" +
              '<div class="soa-info-row"><span class="soa-info-label">Phương thức</span><b class="soa-info-value">' + esc(pm ? pm.label : "Chuyển khoản") + "</b></div>" +
            "</div>" +
          "</div>" +

          // Khối cuống vé kiểm soát (bên phải, đục lỗ hai bên)
          '<div class="eticket-stub text-center">' +
            '<div class="stub-brand mb-2 text-secondary small">MÃ SOÁT VÉ ĐIỆN TỬ</div>' +
            '<div class="stub-code font-monospace fs-4 text-warning mb-3">' + bookingCode + "</div>" +

            '<div class="eticket-barcode-box p-3 bg-white rounded shadow-sm mb-3">' +
              barcodeSvg +
              '<div class="barcode-text font-monospace text-dark small mt-1">' + bookingCode + "</div>" +
            "</div>" +

            (started ? '<span class="badge bg-danger mb-2">Suất chiếu đã diễn ra</span>' : badge(b.status)) +
            '<p class="text-secondary small mt-3 mb-0">Đưa mã vạch này cho nhân viên tại rạp để quét kiểm tra vào phòng chiếu.</p>' +
          "</div>" +
        "</div>" +
      "</div>" +

      '<div class="ticket-actions d-flex justify-content-center gap-3 flex-wrap mt-4">' +
        '<button class="btn btn-outline-light px-4 py-2" id="printTicket">' +
          '<i class="bi bi-printer-fill me-2"></i>In / Lưu PDF' +
        "</button>" +
        '<a class="btn btn-primary px-4 py-2" href="#/my">' +
          '<i class="bi bi-ticket-perforated me-2"></i>Vé của tôi' +
        "</a>" +
        '<a class="btn btn-ghost px-4 py-2" href="#/">' +
          '<i class="bi bi-film me-2"></i>Đặt thêm vé' +
        "</a>" +
      "</div>"
    );

    var printBtn = $("#printTicket");
    if (printBtn) {
      printBtn.onclick = function () { window.print(); };
    }
  }

  /* =============================================================================
     VÉ CỦA TÔI (4 TAB TRẠNG THÁI, LIVE UPDATE, COUNTDOWN CHO PENDING)
  ============================================================================= */
  async function my() {
    if (needLogin("#/my")) return;
    var alive = current();
    var cur = sessionStorage.getItem("soa.tab") || "";

    var head = '<div class="section-head mb-4 d-flex justify-content-between align-items-center flex-wrap gap-2">' +
      '<div>' +
        '<h2 class="section-title mb-1">Vé của tôi</h2>' +
        '<div class="text-secondary small">Quản lý lịch sử và trạng thái đơn vé của bạn</div>' +
      "</div>" +
      live("my-live") +
    "</div>";

    show(head + '<div class="tlist">' + Array(4).join('<div class="skel" style="height:110px;border-radius:16px;margin-bottom:12px"></div>') + "</div>");

    var rows, movies = {}, shows = {};

    async function load(first) {
      try {
        rows = await call("booking", "GET", "/api/booking?username=" + encodeURIComponent(user.username));
      } catch (e) {
        if (!alive()) return;
        if (first) { show(head + errorBox(e)); bindRetry(my); }
        else liveTick("my-live", false);
        return false;
      }

      if (first) {
        var info = await Promise.all([
          soft("movie", "/api/movies", []),
          soft("showtime", "/api/showtimes", [])
        ]);
        movies = byId(enrichMovies(info[0]));
        shows = byId(info[1]);
      }

      if (!alive()) return false;
      rows.sort(function (a, b) { return b.id - a.id; });
      return true;
    }

    if (!await load(true)) return;

    if (!rows.length) {
      show(head + stateBox("🎟️", "Bạn chưa có vé nào", "Hãy chọn một bộ phim yêu thích và trải nghiệm đặt vé tiện lợi tại SOA Cinema.",
        '<a class="btn btn-primary mt-3" href="#/">Khám phá phim ngay</a>'));
      return;
    }

    var tabs = [
      ["", "Tất cả"],
      ["PENDING", "Chờ thanh toán"],
      ["PAID", "Đã thanh toán"],
      ["CANCELLED", "Đã hủy"]
    ];

    show(head + '<div id="pending-note"></div><div class="soa-tabs mb-4" id="tabs" role="tablist" aria-label="Lọc đơn theo trạng thái"></div><div id="list"></div>');

    function render() {
      var pending = rows.filter(function (b) { return b.status === "PENDING"; });
      var noteEl = $("#pending-note");
      if (noteEl) {
        noteEl.innerHTML = pending.length
          ? '<div class="alert alert-warning d-flex align-items-center gap-3 mb-4"><i class="bi bi-clock-history fs-4"></i><div>' +
              'Bạn đang có <b>' + pending.length + ' đơn</b> giữ ghế chờ thanh toán. Vui lòng thanh toán trước khi hết giờ để không bị hủy vé.' +
            "</div></div>"
          : "";
      }

      var tabsEl = $("#tabs");
      if (tabsEl) {
        tabsEl.innerHTML = tabs.map(function (t) {
          var n = rows.filter(function (b) { return !t[0] || b.status === t[0]; }).length;
          var badgeClass = !t[0] ? "soa-tab-badge-all" : t[0] === "PENDING" ? "soa-tab-badge-pending" : t[0] === "PAID" ? "soa-tab-badge-paid" : "soa-tab-badge-cancelled";
          return '<button type="button" class="soa-tab' + (t[0] === cur ? " active" : "") + '" data-t="' + t[0] + '" role="tab" aria-selected="' + (t[0] === cur) + '">' +
            '<span>' + esc(t[1]) + '</span><span class="soa-tab-badge ' + badgeClass + '">' + n + "</span></button>";
        }).join("");
      }

      var list = rows.filter(function (b) { return !cur || b.status === cur; });
      var listEl = $("#list");
      if (!listEl) return;

      if (!list.length) {
        listEl.innerHTML = stateBox("🗂️", "Không có đơn nào", "Chưa có đơn đặt vé nào ở trạng thái này.");
        return;
      }

      listEl.innerHTML = '<div class="tlist">' + list.map(function (b) {
        var mv = movies[b.movieId] || { title: "Phim", genre: "" };
        var s = shows[b.showtimeId];
        var w = s ? when(s.time) : null;
        var right;

        if (b.status === "PENDING") {
          right = '<span class="price text-warning">' + money(b.totalPrice) + "</span>" +
            '<span class="countdown badge bg-warning text-dark py-2 px-3 my-2" data-exp="' + esc(b.expiresAt || "") + '">Giữ ghế còn --:--</span>' +
            '<div class="row-actions d-flex gap-2 justify-content-end">' +
              '<button class="btn btn-outline-danger btn-sm" data-cancel="' + b.id + '">Hủy đơn</button>' +
              '<a class="btn btn-primary btn-sm px-3" href="#/pay/' + b.id + '">Thanh toán ngay</a>' +
            "</div>";
        } else if (b.status === "PAID") {
          right = '<span class="price text-warning">' + money(b.totalPrice) + "</span>" +
            badge(b.status) +
            '<a class="btn btn-outline-light btn-sm mt-2" href="#/ticket/' + b.id + '"><i class="bi bi-ticket-perforated me-1"></i> Xem vé →</a>';
        } else {
          right = '<span class="price text-secondary">' + money(b.totalPrice) + "</span>" +
            badge(b.status) +
            (s && upcoming(s) ? '<a class="btn btn-ghost btn-sm mt-2" href="#/book/' + b.movieId + "/" + b.showtimeId + '">Đặt lại</a>' : "");
        }

        return '<article class="trow ticket-row ' + esc(b.status) + ' mb-3 p-3 rounded border border-secondary">' +
          poster(mv, "sm") +
          '<div class="trow-body flex-grow-1">' +
            '<h3 class="trow-title fs-5 mb-1">' + esc(mv.title) + "</h3>" +
            '<div class="trow-line text-secondary small d-flex flex-wrap gap-3 my-1">' +
              (s ? '<span><i class="bi bi-geo-alt-fill text-danger me-1"></i>' + esc(s.cinema) + " · Phòng " + esc(s.room) + "</span>" +
                   '<span><i class="bi bi-calendar3 me-1"></i>' + w.hm + " · " + w.dm + "/" + s.time.slice(0, 4) + "</span>" : "") +
              '<span><i class="bi bi-person-badge-fill me-1"></i>Ghế: ' + esc(b.seats.join(", ")) + "</span>" +
            "</div>" +
            '<div class="text-secondary small font-monospace mt-1">Mã đặt vé: <b class="text-warning">' + code(b) + "</b> · Đặt lúc: " + esc(when(b.createdAt).full) + "</div>" +
          "</div>" +
          '<div class="right trow-right text-end">' + right + "</div>" +
        "</article>";
      }).join("") + "</div>";

      $$("#tabs .soa-tab").forEach(function (t) {
        t.onclick = function () {
          cur = t.dataset.t;
          sessionStorage.setItem("soa.tab", cur);
          render();
        };
      });

      $$("[data-cancel]").forEach(function (btn) {
        btn.onclick = function () {
          var bookingId = btn.dataset.cancel;
          confirmDialog(
            "Hủy đơn đặt vé",
            "Bạn có chắc muốn hủy đơn đặt vé này không? Ghế sẽ được nhả ngay lập tức.",
            async function () {
              btn.disabled = true;
              try {
                await call("booking", "POST", "/api/booking/" + bookingId + "/cancel", { username: user.username });
                toast("Đã hủy đơn và nhả ghế thành công");
                refresh();
              } catch (e) {
                toast(e.message, "err");
                btn.disabled = false;
              }
            }
          );
        };
      });

      countdown();
      liveTick("my-live", true);
    }

    function countdown() {
      var expiredNow = false;
      $$(".countdown").forEach(function (el) {
        var d = toDate(el.dataset.exp), left = d ? d - new Date() : 0;
        var urgent = left < 60000;
        el.textContent = left > 0 ? "Giữ ghế còn " + mmss(left) : "Đã hết thời gian giữ ghế";
        el.classList.toggle("bg-danger", urgent);
        el.classList.toggle("bg-warning", !urgent);
        if (left <= 0) expiredNow = true;
      });

      if (expiredNow && !countdown.busy) {
        countdown.busy = true;
        setTimeout(function () {
          refresh().then(function () { countdown.busy = false; });
        }, 1500);
      }
    }

    async function refresh() {
      if (await load(false)) render();
    }

    render();
    every(countdown, 1000);
    every(refresh, 20000);
  }

  /* =============================================================================
     ĐĂNG NHẬP / ĐĂNG KÝ
  ============================================================================= */
  function login(mode) {
    if (user) { location.hash = "#/"; return; }
    var reg = mode === "register";

    show(
      '<div class="auth-wrapper d-flex justify-content-center align-items-center py-5">' +
        '<div class="auth-card d-flex flex-column flex-md-row rounded-4 overflow-hidden shadow-lg border border-secondary" style="max-width: 900px; width: 100%;">' +
          '<div class="auth-art p-4 p-md-5 bg-gradient d-flex flex-column justify-content-between" style="flex: 1.1; background: linear-gradient(135deg, #111520 0%, #1e2538 100%);">' +
            '<div>' +
              '<div class="d-flex align-items-center gap-2 mb-3">' +
                '<span class="brand-mark fs-4 text-warning">▶</span>' +
                '<span class="fs-4 fw-bold">SOA<b>Cinema</b></span>' +
              "</div>" +
              '<h2 class="fs-3 fw-bold mb-3">Trải nghiệm điện ảnh<br>đỉnh cao chỉ trong vài bước.</h2>' +
              '<ul class="list-unstyled text-secondary mb-4">' +
                '<li class="mb-2"><i class="bi bi-film text-warning me-2"></i>Cập nhật liên tục lịch chiếu 7 ngày tới</li>' +
                '<li class="mb-2"><i class="bi bi-grid-3x3-gap text-warning me-2"></i>Chọn ghế trực quan trên sơ đồ thời gian thực</li>' +
                '<li class="mb-2"><i class="bi bi-qr-code-scan text-warning me-2"></i>Thanh toán nhanh chóng qua VietQR, MoMo, VNPAY</li>' +
                '<li class="mb-2"><i class="bi bi-upc-scan text-warning me-2"></i>Vé điện tử mã vạch 1D tiện lợi, kiểm soát dễ dàng</li>' +
              "</ul>" +
            "</div>" +
            '<span class="text-secondary small">Ghế được giữ 10 phút để bạn an tâm hoàn tất thanh toán.</span>' +
          "</div>" +

          '<form class="auth-form p-4 p-md-5 bg-dark" id="auth" novalidate style="flex: 1;">' +
            '<h1 class="fs-3 fw-bold mb-2">' + (reg ? "Tạo tài khoản mới" : "Chào mừng trở lại") + "</h1>" +
            '<p class="text-secondary small mb-4">' + (reg ? "Đăng ký để nhận nhiều ưu đãi và quản lý vé tiện lợi." : "Đăng nhập để tiếp tục đặt vé của bạn.") + "</p>" +

            (reg ? "" : '<div class="alert alert-secondary d-flex justify-content-between align-items-center py-2 px-3 mb-3 small">' +
              '<span>Tài khoản thử: <code>user1</code> / <code>User@123</code></span>' +
              '<button type="button" class="btn btn-link btn-sm text-warning p-0" id="fill">Điền nhanh</button></div>') +

            '<div id="err"></div>' +

            '<div class="mb-3">' +
              '<label class="form-label small text-secondary" for="u">Tên đăng nhập</label>' +
              '<input class="form-control bg-secondary-subtle border-secondary text-light" id="u" autocomplete="username" required placeholder="Nhập tên tài khoản">' +
            "</div>" +

            (reg ? '<div class="mb-3">' +
              '<label class="form-label small text-secondary" for="e">Email <span class="text-muted">(không bắt buộc)</span></label>' +
              '<input class="form-control bg-secondary-subtle border-secondary text-light" id="e" type="email" autocomplete="email" placeholder="email@domain.com">' +
            "</div>" : "") +

            '<div class="mb-4">' +
              '<label class="form-label small text-secondary" for="p">Mật khẩu</label>' +
              '<div class="input-group">' +
                '<input class="form-control bg-secondary-subtle border-secondary text-light" id="p" type="password" autocomplete="' + (reg ? "new-password" : "current-password") + '" required' + (reg ? ' minlength="6" placeholder="Tối thiểu 6 ký tự"' : ' placeholder="Nhập mật khẩu"') + ">" +
                '<button type="button" class="btn btn-outline-secondary" id="eye"><i class="bi bi-eye"></i></button>' +
              "</div>" +
            "</div>" +

            '<button class="btn btn-primary w-100 py-2 mb-3 font-weight-bold" id="go" type="submit">' +
              (reg ? "Tạo tài khoản ngay" : "Đăng nhập") +
            "</button>" +

            '<p class="text-secondary text-center small mb-0">' +
              (reg ? 'Đã có tài khoản? <a href="#/login" class="text-warning">Đăng nhập ngay</a>' : 'Chưa có tài khoản? <a href="#/register" class="text-warning">Đăng ký mới</a>') +
            "</p>" +
          "</form>" +
        "</div>" +
      "</div>"
    );

    var uEl = $("#u");
    if (uEl) uEl.focus();

    var eyeBtn = $("#eye");
    if (eyeBtn) {
      eyeBtn.onclick = function () {
        var p = $("#p"), hidden = p.type === "password";
        p.type = hidden ? "text" : "password";
        this.innerHTML = hidden ? '<i class="bi bi-eye-slash"></i>' : '<i class="bi bi-eye"></i>';
      };
    }

    var fill = $("#fill");
    if (fill) {
      fill.onclick = function () {
        $("#u").value = "user1";
        $("#p").value = "User@123";
        $("#go").focus();
      };
    }

    $("#auth").onsubmit = async function (ev) {
      ev.preventDefault();
      var u = $("#u").value.trim(), p = $("#p").value, err = $("#err"), btn = $("#go"), label = btn.textContent;
      var problem = !u ? "Vui lòng nhập tên đăng nhập." : !p ? "Vui lòng nhập mật khẩu." : reg && p.length < 6 ? "Mật khẩu cần ít nhất 6 ký tự." : "";

      if (problem) {
        err.innerHTML = '<div class="alert alert-danger py-2 px-3 small mb-3">⚠ ' + problem + "</div>";
        return;
      }

      err.innerHTML = "";
      btn.disabled = true;
      btn.innerHTML = '<span class="spinner-border spinner-border-sm me-2" role="status"></span> Đang xử lý...';

      try {
        if (reg) {
          var emailVal = $("#e") ? $("#e").value.trim() : "";
          await call("user", "POST", "/api/register", { username: u, password: p, email: emailVal });
        }
        var r = await call("user", "POST", "/api/login", { username: u, password: p });
        user = { id: r.id, username: r.username, role: r.role, token: r.token };
        sessionStorage.setItem("soa.user", JSON.stringify(user));

        toast(reg ? "Tạo tài khoản thành công! Xin chào " + r.username : "Xin chào " + r.username + "!");
        var next = sessionStorage.getItem("soa.next");
        sessionStorage.removeItem("soa.next");
        location.hash = next || "#/";
        nav();
      } catch (e) {
        err.innerHTML = '<div class="alert alert-danger py-2 px-3 small mb-3">⚠ ' + esc(e.message) + "</div>";
        btn.disabled = false;
        btn.textContent = label;
      }
    };
  }

  /* =============================================================================
     ĐỊNH TUYẾN URL HASH
  ============================================================================= */
  function route() {
    var h = location.hash || "#/", p = h.split("/");
    if (h === "#movies" || h === "#showtimes") return;

    leave();
    nav();
    window.scrollTo(0, 0);

    if (p[1] === "movie" && p[2]) return movie(p[2]);
    if (p[1] === "book" && p[3]) return book(p[2], p[3]);
    if (p[1] === "pay" && p[2]) return pay(p[2]);
    if (p[1] === "sandbox-pay" && p[2]) return sandboxPay(p[2]);
    if (p[1] === "ticket" && p[2]) return ticket(p[2], p[3] === "new");
    if (p[1] === "result" || p[1] === "my") {
      if (p[1] === "result") { location.replace("#/my"); return; }
      return my();
    }
    if (p[1] === "login") return login();
    if (p[1] === "register") return login("register");

    return home();
  }

  window.addEventListener("hashchange", route);
  document.addEventListener("DOMContentLoaded", function () {
    initTrailerModal();
    route();
  });
})();
