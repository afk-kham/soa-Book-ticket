/* Thư viện dùng chung cho toàn bộ trang Admin: Dark Cinema + Bootstrap 5.3 + Count-up KPI + Poster thật */
(function () {
  "use strict";

  var S = window.SOA.services;
  var NAV = [
    ["index", "Tổng quan"],
    ["movie", "Phim"],
    ["showtime", "Suất chiếu"],
    ["user", "Người dùng"],
    ["booking", "Đặt vé"],
    ["payment", "Thanh toán"],
    ["notification", "Thông báo"]
  ];

  var ICONS = {
    index: '<rect x="3" y="3" width="7" height="9" rx="1.5"/><rect x="14" y="3" width="7" height="5" rx="1.5"/><rect x="14" y="12" width="7" height="9" rx="1.5"/><rect x="3" y="16" width="7" height="5" rx="1.5"/>',
    movie: '<rect x="3" y="4" width="18" height="16" rx="2"/><path d="M7 4v16M17 4v16M3 9h4M3 15h4M17 9h4M17 15h4"/>',
    showtime: '<rect x="3" y="5" width="18" height="16" rx="2"/><path d="M8 3v4M16 3v4M3 10h18M12 14v3l2 1"/>',
    user: '<circle cx="9" cy="8" r="3.5"/><path d="M2.5 20a6.5 6.5 0 0 1 13 0M16 4.5a3.5 3.5 0 0 1 0 7M18 14.5a6.5 6.5 0 0 1 3.5 5.5"/>',
    booking: '<path d="M3 8a2 2 0 0 0 2-2h14a2 2 0 0 0 2 2v2a2 2 0 0 0 0 4v2a2 2 0 0 0-2 2H5a2 2 0 0 0-2-2v-2a2 2 0 0 0 0-4z"/><path d="M14 6v12" stroke-dasharray="2 2"/>',
    payment: '<rect x="2.5" y="5" width="19" height="14" rx="2"/><path d="M2.5 10h19M6.5 15h4"/>',
    notification: '<path d="M6 9a6 6 0 0 1 12 0c0 6 2.5 7.5 2.5 7.5h-17S6 15 6 9"/><path d="M10 20a2 2 0 0 0 4 0"/>',
    search: '<circle cx="11" cy="11" r="7"/><path d="m20 20-3.5-3.5"/>',
    menu: '<path d="M4 7h16M4 12h16M4 17h16"/>',
    close: '<path d="M6 6l12 12M18 6 6 18"/>',
    collapse: '<path d="M11 19l-7-7 7-7m8 14l-7-7 7-7"/>'
  };

  var IN_PAGES = /\/pages\/[^/]*$/.test(location.pathname);
  function href(key) {
    return key === "index" ? (IN_PAGES ? "../index.html" : "index.html") : (IN_PAGES ? "" : "pages/") + key + ".html";
  }
  function icon(name, size) {
    return '<svg width="' + (size || 18) + '" height="' + (size || 18) + '" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">' + (ICONS[name] || "") + "</svg>";
  }

  function esc(v) {
    return String(v == null ? "" : v).replace(/[&<>"']/g, function (c) {
      return ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c];
    });
  }
  function money(n) { return Number(n || 0).toLocaleString("vi-VN") + " đ"; }
  function badge(v, label) { return '<span class="badge ' + esc(v) + '">' + esc(label || v) + "</span>"; }
  function methodLabel(v) {
    var m = (window.SOA.paymentMethods || []).filter(function (x) { return x.value === v; })[0];
    return m ? m.label : v;
  }
  var PAY_ST = { PAID: "Thành công", FAILED: "Thất bại" };
  function payStatus(v) { return badge(v, PAY_ST[v] || v); }

  /* ---------- Poster thật & Thumbnail ---------- */
  var PAL = [
    ["#7c2d12", "#f97316"], ["#1e3a8a", "#6366f1"], ["#4c1d95", "#db2777"],
    ["#064e3b", "#14b8a6"], ["#7f1d1d", "#f43f5e"], ["#713f12", "#eab308"],
    ["#0c4a6e", "#06b6d4"], ["#3b0764", "#a855f7"]
  ];
  function thumb(title, cls) {
    var h = 0, s = String(title || "");
    for (var i = 0; i < s.length; i++) h = (h * 31 + s.charCodeAt(i)) | 0;
    var p = PAL[Math.abs(h) % PAL.length];
    return '<span class="thumb' + (cls ? " " + cls : "") + '" style="--p1:' + p[0] + ";--p2:" + p[1] + '">' + esc(s.charAt(0).toUpperCase()) + "</span>";
  }

  function poster(m) {
    if (!m) return thumb("?");
    var extra = window.mergeMovieExtras ? window.mergeMovieExtras(m) : null;
    var basePath = IN_PAGES ? "../" : "";
    var srcs = [];

    if (extra && extra.posterUrl) {
      srcs.push(basePath + extra.posterUrl);
    }
    if (m.poster) {
      var p = String(m.poster).trim();
      if (/^(https?:)?\/\//.test(p)) srcs.push(p);
      else {
        var f = p.replace(/^.*[\\/]/, "");
        if (/^[\w.-]+$/.test(f)) {
          srcs.push(basePath + "assets/posters/" + f);
          srcs.push(window.SOA.clientBase + "/assets/posters/" + f);
        }
      }
    }
    if (extra && extra.remotePosterUrl) {
      srcs.push(extra.remotePosterUrl);
    }

    var t = thumb(m.title);
    if (!srcs.length) return t;

    var first = srcs[0];
    var rest = srcs.slice(1).join("|");
    return t.replace('class="thumb"', 'class="thumb poster-thumb"').replace(
      /<\/span>$/,
      '<img src="' + esc(first) + '" data-alt="' + esc(rest) + '" alt="" loading="lazy" onerror="Admin.posterFail(this)"></span>'
    );
  }

  function posterFail(img) {
    var a = (img.getAttribute("data-alt") || "").split("|").filter(Boolean);
    if (a.length) {
      img.setAttribute("data-alt", a.slice(1).join("|"));
      img.src = a[0];
    } else {
      img.remove();
    }
  }

  function seats(list) {
    return (list || []).map(function (s) { return '<span class="seat-tag">' + esc(s) + "</span>"; }).join("");
  }

  /* ---------- Gọi API ---------- */
  async function api(service, method, path, body) {
    var svc = S[service], res, json;
    try {
      res = await fetch(svc.base + path, {
        method: method,
        headers: body ? { "Content-Type": "application/json" } : {},
        body: body ? JSON.stringify(body) : undefined
      });
    } catch (e) {
      var err = new Error("Hệ thống " + svc.label.toLowerCase() + " đang tạm ngưng hoặc không truy cập được. Vui lòng kiểm tra lại service.");
      err.code = "SERVICE_DOWN";
      throw err;
    }
    try { json = await res.json(); } catch (e) { json = null; }
    if (!res.ok || !json || json.status !== "success") {
      var e2 = new Error((json && json.message) || ("Lỗi HTTP " + res.status));
      e2.code = json && json.code;
      e2.httpStatus = res.status;
      throw e2;
    }
    return json.data;
  }

  async function tryApi(service, path, fallback) {
    try { return await api(service, "GET", path); } catch (e) { return fallback; }
  }

  async function ping(key) {
    var t0 = performance.now();
    try {
      await api(key, "GET", S[key].ping);
      return { ok: true, ms: Math.round(performance.now() - t0) };
    } catch (e) {
      return { ok: e.code !== "SERVICE_DOWN" && e.httpStatus < 500, ms: Math.round(performance.now() - t0), error: e.message };
    }
  }

  async function sidebarHealth(force) {
    var cache = null;
    try { cache = JSON.parse(sessionStorage.getItem("soa.health") || "null"); } catch (e) {}
    if (force || !cache || Date.now() - cache.at > 20000) {
      var keys = Object.keys(S), res = await Promise.all(keys.map(ping));
      cache = { at: Date.now(), up: {} };
      keys.forEach(function (k, i) { cache.up[k] = res[i].ok; });
      try { sessionStorage.setItem("soa.health", JSON.stringify(cache)); } catch (e) {}
    }
    setHealthDots(cache.up);
  }

  function setHealthDots(up) {
    Object.keys(up).forEach(function (k) {
      var d = document.querySelector('[data-dot="' + k + '"]');
      if (d) {
        d.className = "dot " + (up[k] ? "up" : "down");
        d.title = up[k] ? "Đang chạy bình thường" : "Không truy cập được";
      }
    });
  }

  function toast(msg, type) {
    var box = document.getElementById("toasts");
    if (!box) return;
    var t = document.createElement("div");
    t.className = "toast" + (type === "error" ? " error" : "");
    t.setAttribute("role", "status");
    t.innerHTML = "<span>" + (type === "error" ? "⚠️" : "✅") + "</span><span>" + esc(msg) + "</span>";
    box.appendChild(t);
    setTimeout(function () { t.remove(); }, 4500);
  }

  /* ---------- Modal Xem Trailer trong Admin ---------- */
  var adminTrailerModalInstance = null;
  function openTrailer(title, youtubeId) {
    if (!youtubeId) return;
    var el = document.getElementById("adminTrailerModal");
    var iframe = document.getElementById("adminTrailerIframe");
    var titleEl = document.getElementById("adminTrailerTitle");
    if (!el || !iframe) return;

    if (titleEl) titleEl.textContent = title + " — Trailer chính thức";
    iframe.src = "https://www.youtube-nocookie.com/embed/" + encodeURIComponent(youtubeId) + "?autoplay=1&rel=0";
    if (window.bootstrap) {
      if (!adminTrailerModalInstance) {
        adminTrailerModalInstance = new bootstrap.Modal(el);
        el.addEventListener("hidden.bs.modal", function () {
          if (iframe) iframe.src = "";
        });
      }
      adminTrailerModalInstance.show();
    } else {
      el.classList.add("open");
    }
  }

  /* ---------- Khung Shell của Admin ---------- */
  function shell(active, title, subtitle) {
    document.documentElement.setAttribute("data-bs-theme", "dark");

    var links = NAV.map(function (n, i) {
      var svc = S[n[0]];
      return (i === 1 ? '<div class="group">Quản lý</div>' : "") +
        '<a class="' + (n[0] === active ? "active" : "") + '" href="' + href(n[0]) + '" title="' + esc(n[1]) + '">' +
          icon(n[0]) + '<span class="lbl">' + n[1] + "</span>" +
          (svc ? '<span class="dot" data-dot="' + n[0] + '"></span>' : "") +
        "</a>";
    }).join("");

    var svc = S[active];
    var app = document.getElementById("app"), content = app.innerHTML;

    var isCollapsed = localStorage.getItem("soa.admin.sidebar") === "collapsed";

    app.outerHTML =
      '<div class="layout">' +
        '<div class="mobilebar">' +
          '<b>🎬 Admin SOA Cinema</b>' +
          '<button class="small btn-outline-light" id="nav-toggle" aria-label="Mở menu">' + icon("menu") + "</button>" +
        "</div>" +

        '<nav class="sidebar ' + (isCollapsed ? "collapsed" : "") + '" id="sidebar">' +
          '<div class="sidebar-header">' +
            '<h1><span class="logo">▶</span><span>SOA<b>Cinema</b><small>Bảng quản trị</small></span></h1>' +
            '<button class="sidebar-toggle-btn d-none d-md-grid" id="sidebar-toggle" title="Thu gọn / Mở rộng">' + icon("collapse", 14) + "</button>" +
          "</div>" +
          '<div class="sidebar-nav">' +
            '<div class="group">Hệ thống</div>' +
            links +
          "</div>" +
          '<div class="side-foot">' +
            'SOA Cinema · Quản trị rạp<br>' +
            '<a href="' + window.SOA.clientBase + '" target="_blank" rel="noopener">Mở trang đặt vé ↗</a>' +
          "</div>" +
        "</nav>" +

        '<main class="main">' +
          '<div class="page-title">' +
            '<div>' +
              '<div class="crumb">' + (svc ? "Quản lý · " + esc(svc.label) : "Quản trị") + "</div>" +
              "<h2>" + esc(title) + "</h2>" +
              '<div class="sub">' + esc(subtitle || "") + "</div>" +
            "</div>" +
            '<div id="page-actions"></div>' +
          "</div>" +
          '<div id="page-error"></div>' +
          '<div id="content">' + content + "</div>" +
        "</main>" +
      "</div>" +

      '<div id="toasts"></div>' +

      '<!-- Modal CRUD -->' +
      '<div class="modal-bg" id="modal-bg"><div class="modal" id="modal" role="dialog" aria-modal="true"></div></div>' +

      '<!-- Drawer chi tiết đơn hàng -->' +
      '<div class="drawer-bg" id="drawer-bg">' +
        '<aside class="drawer" role="dialog" aria-modal="true">' +
          '<div class="drawer-head">' +
            '<h3 id="drawer-title"></h3>' +
            '<button class="ghost small" id="drawer-close" aria-label="Đóng">' + icon("close") + "</button>" +
          "</div>" +
          '<div class="drawer-body" id="drawer-body"></div>' +
        "</aside>" +
      "</div>" +

      '<!-- Modal xem trailer YouTube trong Admin -->' +
      '<div class="modal fade" id="adminTrailerModal" tabindex="-1" aria-hidden="true">' +
        '<div class="modal-dialog modal-dialog-centered modal-lg">' +
          '<div class="modal-content bg-dark border-secondary">' +
            '<div class="modal-header border-secondary py-2">' +
              '<h5 class="modal-title fs-6 text-truncate d-flex align-items-center gap-2" id="adminTrailerTitle">' +
                '<span class="text-danger">▶</span> Trailer' +
              "</h5>" +
              '<button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal" aria-label="Đóng"></button>' +
            "</div>" +
            '<div class="modal-body p-0 ratio ratio-16x9 bg-black">' +
              '<iframe id="adminTrailerIframe" src="" title="Trailer" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture" allowfullscreen></iframe>' +
            "</div>" +
          "</div>" +
        "</div>" +
      "</div>";

    var side = document.getElementById("sidebar");
    var toggleBtn = document.getElementById("sidebar-toggle");
    if (toggleBtn) {
      toggleBtn.onclick = function () {
        side.classList.toggle("collapsed");
        localStorage.setItem("soa.admin.sidebar", side.classList.contains("collapsed") ? "collapsed" : "expanded");
      };
    }

    var navToggle = document.getElementById("nav-toggle");
    if (navToggle) {
      navToggle.onclick = function (ev) {
        ev.stopPropagation();
        side.classList.toggle("open");
      };
    }

    document.addEventListener("click", function (ev) {
      if (side.classList.contains("open") && !side.contains(ev.target)) side.classList.remove("open");
    });
    document.getElementById("modal-bg").addEventListener("mousedown", function (ev) { if (ev.target.id === "modal-bg") closeForm(); });
    document.getElementById("drawer-bg").addEventListener("mousedown", function (ev) { if (ev.target.id === "drawer-bg") closeDrawer(); });
    document.getElementById("drawer-close").onclick = closeDrawer;

    // Reset iframe khi đóng trailer modal
    var trModal = document.getElementById("adminTrailerModal");
    if (trModal) {
      trModal.addEventListener("hidden.bs.modal", function () {
        var ifr = document.getElementById("adminTrailerIframe");
        if (ifr) ifr.src = "";
      });
    }

    document.addEventListener("keydown", function (ev) {
      if (ev.key === "Escape") { closeForm(); closeDrawer(); }
    });

    sidebarHealth(false);
  }

  function showError(e) {
    document.getElementById("page-error").innerHTML =
      '<div class="alert"><span>⚠</span><div><b>' +
      (e.code === "SERVICE_DOWN" ? "Mất kết nối hệ thống" : "Đã có lỗi xảy ra") +
      "</b>" + esc(e.message) + "</div></div>";
  }
  function clearError() {
    var el = document.getElementById("page-error");
    if (el) el.innerHTML = "";
  }
  function loading(el, rows) {
    el.innerHTML = '<div style="display:grid;gap:14px;padding:6px 0">' + Array((rows || 5) + 1).join('<div class="skel"></div>') + "</div>";
  }
  function emptyHtml(text) {
    return '<div class="empty"><span class="ic">🗂️</span>' + esc(text || "Chưa có dữ liệu") + "</div>";
  }

  /* ---------- Hiệu ứng Count-Up Animation cho KPI ---------- */
  function countUp(el, target, suffix, isCurrency) {
    var duration = 750;
    var startTime = null;
    function step(timestamp) {
      if (!startTime) startTime = timestamp;
      var progress = Math.min((timestamp - startTime) / duration, 1);
      var easeOut = 1 - Math.pow(1 - progress, 3);
      var current = Math.floor(easeOut * target);
      el.textContent = isCurrency ? (current.toLocaleString("vi-VN") + " " + suffix) : (current.toLocaleString("vi-VN") + (suffix || ""));
      if (progress < 1) {
        window.requestAnimationFrame(step);
      } else {
        el.textContent = isCurrency ? (target.toLocaleString("vi-VN") + " " + suffix) : (target.toLocaleString("vi-VN") + (suffix || ""));
      }
    }
    window.requestAnimationFrame(step);
  }

  function stats(el, items) {
    el.className = "stats";
    el.innerHTML = items.map(function (s, idx) {
      return '<div class="stat">' +
        '<div class="k">' + esc(s.label) + "</div>" +
        '<div class="v" id="kpi-val-' + idx + '">' + s.value + "</div>" +
        '<div class="h">' + (s.hint || "&nbsp;") + "</div>" +
      "</div>";
    }).join("");

    // Trigger count-up animation cho các giá trị là số
    items.forEach(function (s, idx) {
      var valEl = document.getElementById("kpi-val-" + idx);
      if (!valEl) return;
      var raw = String(s.value || "").trim();
      if (/^[\d,.]+$/.test(raw)) {
        var num = parseInt(raw.replace(/[.,]/g, ""), 10);
        if (!isNaN(num) && num > 0) countUp(valEl, num, "", false);
      } else if (/^[\d,.]+\s*đ$/.test(raw)) {
        var moneyNum = parseInt(raw.replace(/[^\d]/g, ""), 10);
        if (!isNaN(moneyNum) && moneyNum > 0) countUp(valEl, moneyNum, "đ", true);
      }
    });
  }

  function table(el, columns, rows, actions, opts) {
    opts = opts || {};
    if (!rows.length) { el.innerHTML = emptyHtml(opts.empty); return; }
    var head = columns.map(function (c) { return '<th class="' + (c.align || "") + '">' + esc(c.label) + "</th>"; }).join("") + (actions ? "<th></th>" : "");
    var html = rows.map(function (r, i) {
      var tds = columns.map(function (c) {
        return '<td class="' + (c.align || "") + (c.wrap ? " wrap" : "") + '">' + (c.render ? c.render(r) : esc(r[c.key])) + "</td>";
      }).join("");
      return '<tr data-i="' + i + '"' + (opts.onRowClick ? ' class="clickable"' : "") + ">" + tds + (actions ? '<td><div class="actions">' + actions(r, i) + "</div></td>" : "") + "</tr>";
    });
    var tools = opts.search
      ? '<div class="table-tools">' +
          '<div class="soa-search">' +
            '<i class="bi bi-search soa-search-icon"></i>' +
            '<input type="search" class="soa-search-input" placeholder="' + esc(opts.search === true ? "Tìm kiếm…" : opts.search) + '" aria-label="Tìm kiếm">' +
            '<button type="button" class="soa-search-clear" aria-label="Xóa tìm kiếm">&times;</button>' +
          '</div>' +
          '<span class="count"></span>' +
        '</div>'
      : "";
    el.innerHTML = tools + '<div class="table-wrap"><table><thead><tr>' + head + "</tr></thead><tbody>" + html.join("") + "</tbody></table></div>";

    var tbody = el.querySelector("tbody"), trs = Array.prototype.slice.call(tbody.children), count = el.querySelector(".count");
    function filter(q) {
      var n = 0; q = q.toLowerCase();
      trs.forEach(function (tr) {
        var hit = !q || tr.textContent.toLowerCase().indexOf(q) >= 0;
        tr.style.display = hit ? "" : "none";
        if (hit) n++;
      });
      if (count) count.textContent = (q ? n + " / " : "") + rows.length + " bản ghi";
    }
    if (opts.search) {
      var searchWrap = el.querySelector(".table-tools .soa-search");
      var inp = searchWrap ? searchWrap.querySelector(".soa-search-input") : el.querySelector(".table-tools input");
      var clearBtn = searchWrap ? searchWrap.querySelector(".soa-search-clear") : null;
      var debounceTimer = null;
      function updateClear() {
        if (clearBtn) clearBtn.classList.toggle("visible", !!inp.value);
      }
      inp.oninput = function () {
        updateClear();
        if (debounceTimer) clearTimeout(debounceTimer);
        debounceTimer = setTimeout(function () { filter(inp.value.trim()); }, 220);
      };
      inp.onkeydown = function (e) {
        if (e.key === "Escape") {
          inp.value = "";
          updateClear();
          filter("");
        }
      };
      if (clearBtn) {
        clearBtn.onclick = function () {
          inp.value = "";
          updateClear();
          filter("");
          inp.focus();
        };
      }
      filter("");
    }
    if (opts.onRowClick) tbody.addEventListener("click", function (ev) {
      if (ev.target.closest("button,a,input")) return;
      var tr = ev.target.closest("tr");
      if (tr) opts.onRowClick(rows[+tr.dataset.i]);
    });
  }

  function openForm(opts) {
    var bg = document.getElementById("modal-bg"), m = document.getElementById("modal");
    var html = "<h3>" + esc(opts.title) + "</h3>" +
      (opts.subtitle ? '<p class="modal-sub">' + esc(opts.subtitle) + "</p>" : "") +
      '<form id="modal-form" novalidate>' + opts.fields.map(function (f) {
        var v = (opts.values && opts.values[f.name] != null) ? opts.values[f.name] : (f.value != null ? f.value : "");
        var input = f.type === "select"
          ? '<select name="' + f.name + '">' + f.options.map(function (o) {
              var ov = o.value != null ? o.value : o;
              var ol = o.label != null ? o.label : o;
              return '<option value="' + esc(ov) + '"' + (String(ov) === String(v) ? " selected" : "") + ">" + esc(ol) + "</option>";
            }).join("") + "</select>"
          : '<input name="' + f.name + '" type="' + (f.type || "text") + '" value="' + esc(v) + '" placeholder="' + esc(f.placeholder || "") + '"' + (f.required ? " required" : "") + (f.min != null ? ' min="' + f.min + '"' : "") + ">";
        return '<div class="field"><label>' + esc(f.label) + (f.required ? ' <span style="color:var(--cinema-red)">*</span>' : "") + "</label>" + input + (f.hint ? '<div class="hint">' + esc(f.hint) + "</div>" : "") + "</div>";
      }).join("") +
      '<div class="actions"><button type="button" class="secondary" id="m-cancel">Hủy</button><button type="submit" id="m-ok">' + esc(opts.submitLabel || "Lưu") + "</button></div></form>";

    m.className = "modal";
    m.innerHTML = html;
    bg.classList.add("open");
    var form = document.getElementById("modal-form"), first = form.querySelector("input,select");
    if (first) first.focus();
    if (opts.onRender) opts.onRender(form);
    document.getElementById("m-cancel").onclick = closeForm;
    form.onsubmit = async function (ev) {
      ev.preventDefault();
      if (!form.reportValidity()) return;
      var data = {};
      opts.fields.forEach(function (f) { data[f.name] = form.elements[f.name].value; });
      var btn = document.getElementById("m-ok"), label = btn.innerHTML;
      btn.disabled = true;
      btn.innerHTML = '<span class="spinner"></span> Đang xử lý...';
      try {
        await opts.onSubmit(data);
        closeForm();
      } catch (e) {
        toast(e.message, "error");
        btn.disabled = false;
        btn.innerHTML = label;
      }
    };
  }

  function closeForm() {
    var bg = document.getElementById("modal-bg");
    if (bg) bg.classList.remove("open");
  }

  function confirmBox(msg, okLabel) {
    return new Promise(function (resolve) {
      var bg = document.getElementById("modal-bg"), m = document.getElementById("modal");
      m.className = "modal confirm";
      m.innerHTML = '<div class="ic" style="width:44px;height:44px;border-radius:50%;display:grid;place-items:center;background:var(--cinema-err-soft);color:var(--cinema-err);font-size:22px;margin-bottom:12px">!</div>' +
        "<h3>Xác nhận thao tác</h3>" +
        '<p class="modal-sub">' + esc(msg) + "</p>" +
        '<div class="actions"><button class="secondary" id="c-no">Hủy</button><button class="danger" id="c-yes">' + esc(okLabel || "Đồng ý") + "</button></div>";
      bg.classList.add("open");
      document.getElementById("c-yes").focus();
      function done(v) { closeForm(); resolve(v); }
      document.getElementById("c-no").onclick = function () { done(false); };
      document.getElementById("c-yes").onclick = function () { done(true); };
    });
  }

  async function drawer(title, html) {
    document.getElementById("drawer-title").textContent = title;
    var body = document.getElementById("drawer-body");
    document.getElementById("drawer-bg").classList.add("open");
    if (html && typeof html.then === "function") {
      loading(body, 6);
      try { body.innerHTML = await html; }
      catch (e) { body.innerHTML = '<div class="alert">⚠ ' + esc(e.message) + "</div>"; }
    } else {
      body.innerHTML = html;
    }
  }

  function closeDrawer() {
    var d = document.getElementById("drawer-bg");
    if (d) d.classList.remove("open");
  }

  function dl(pairs) {
    return '<dl class="dl">' + pairs.map(function (p) {
      return "<dt>" + esc(p[0]) + "</dt><dd>" + (p[1] == null || p[1] === "" ? "—" : p[1]) + "</dd>";
    }).join("") + "</dl>";
  }

  function fmtTime(t) {
    return esc(String(t || "").replace("T", " ").replace(/\.\d+Z?$/, "").replace(/Z$/, ""));
  }

  function crudPage(cfg) {
    var rows = [], list = document.getElementById("list");
    async function load() {
      clearError();
      if (!rows.length) loading(list);
      try {
        if (cfg.beforeLoad) await cfg.beforeLoad();
        rows = await api(cfg.service, "GET", cfg.listPath ? cfg.listPath() : cfg.path);
        if (cfg.afterLoad) cfg.afterLoad(rows);
        table(list, cfg.columns, rows, function (r) {
          return '<button class="small secondary" data-edit="' + r.id + '">Sửa</button>' +
            '<button class="small ghost" data-del="' + r.id + '" style="color:var(--cinema-red)">Xóa</button>';
        }, { search: cfg.search || "Tìm " + cfg.noun + "...", empty: "Chưa có " + cfg.noun + " nào" });
      } catch (e) {
        showError(e);
        list.innerHTML = emptyHtml("Không tải được dữ liệu");
      }
    }

    function form(row) {
      openForm({
        title: row ? "Sửa " + cfg.noun + " #" + row.id : "Thêm " + cfg.noun,
        subtitle: cfg.formHint,
        fields: cfg.fields(row),
        values: row ? cfg.toForm(row) : {},
        submitLabel: row ? "Lưu thay đổi" : "Thêm " + cfg.noun,
        onRender: cfg.onRender ? function (formEl) { cfg.onRender(formEl, row, rows); } : null,
        onSubmit: async function (data) {
          var payload = await cfg.toPayload(data, row, rows);
          if (row) await api(cfg.service, "PUT", cfg.path + "/" + row.id, payload);
          else await api(cfg.service, "POST", cfg.path, payload);
          toast(row ? "Đã cập nhật " + cfg.noun + " #" + row.id : "Đã thêm " + cfg.noun);
          load();
        }
      });
    }

    var actionsEl = document.getElementById("page-actions");
    if (actionsEl) {
      actionsEl.innerHTML = '<button class="secondary" id="btn-reload">Làm mới</button><button id="btn-add">+ Thêm ' + esc(cfg.noun) + "</button>";
      document.getElementById("btn-add").onclick = function () { form(null); };
      document.getElementById("btn-reload").onclick = load;
    }

    list.addEventListener("click", async function (ev) {
      var eb = ev.target.closest("[data-edit]"), db = ev.target.closest("[data-del]");
      if (eb) form(rows.filter(function (r) { return String(r.id) === eb.dataset.edit; })[0]);
      if (db && await confirmBox("Xóa " + cfg.noun + " #" + db.dataset.del + "? Thao tác này không hoàn tác được.", "Xóa ngay")) {
        try {
          await api(cfg.service, "DELETE", cfg.path + "/" + db.dataset.del);
          toast("Đã xóa " + cfg.noun + " #" + db.dataset.del);
          load();
        } catch (e) {
          if (e.code === "CONFLICT" || e.status === 409 || (e.message && (e.message.indexOf("foreign") >= 0 || e.message.indexOf("ràng buộc") >= 0 || e.message.indexOf("khóa ngoại") >= 0))) {
            toast("Không thể xóa " + cfg.noun + " này vì đang có dữ liệu ràng buộc (suất chiếu hoặc vé đã bán). Vui lòng xóa các mục liên quan trước.", "error");
          } else {
            toast(e.message, "error");
          }
        }
      }
    });

    load();
    return { reload: load };
  }

  window.Admin = {
    api: api,
    tryApi: tryApi,
    ping: ping,
    sidebarHealth: sidebarHealth,
    setHealthDots: setHealthDots,
    toast: toast,
    shell: shell,
    table: table,
    openForm: openForm,
    closeForm: closeForm,
    confirmBox: confirmBox,
    drawer: drawer,
    closeDrawer: closeDrawer,
    dl: dl,
    stats: stats,
    loading: loading,
    crudPage: crudPage,
    icon: icon,
    thumb: thumb,
    poster: poster,
    posterFail: posterFail,
    seats: seats,
    methodLabel: methodLabel,
    payStatus: payStatus,
    esc: esc,
    money: money,
    badge: badge,
    fmtTime: fmtTime,
    showError: showError,
    clearError: clearError,
    openTrailer: openTrailer
  };
})();
