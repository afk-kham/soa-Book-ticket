/* Thư viện dùng chung cho mọi trang Admin: khung giao diện, gọi API theo hợp đồng chung, bảng, form, thông báo. */
(function () {
  var S = window.SOA.services;
  var NAV = [["index", "Tổng quan"], ["movie", "Phim"], ["showtime", "Suất chiếu"], ["user", "Người dùng"],
             ["booking", "Đặt vé"], ["payment", "Thanh toán"], ["notification", "Thông báo"]];
  var ICONS = {   // nét vẽ SVG 24×24 cho từng mục
    index: '<rect x="3" y="3" width="7" height="9" rx="1.5"/><rect x="14" y="3" width="7" height="5" rx="1.5"/><rect x="14" y="12" width="7" height="9" rx="1.5"/><rect x="3" y="16" width="7" height="5" rx="1.5"/>',
    movie: '<rect x="3" y="4" width="18" height="16" rx="2"/><path d="M7 4v16M17 4v16M3 9h4M3 15h4M17 9h4M17 15h4"/>',
    showtime: '<rect x="3" y="5" width="18" height="16" rx="2"/><path d="M8 3v4M16 3v4M3 10h18M12 14v3l2 1"/>',
    user: '<circle cx="9" cy="8" r="3.5"/><path d="M2.5 20a6.5 6.5 0 0 1 13 0M16 4.5a3.5 3.5 0 0 1 0 7M18 14.5a6.5 6.5 0 0 1 3.5 5.5"/>',
    booking: '<path d="M3 8a2 2 0 0 0 2-2h14a2 2 0 0 0 2 2v2a2 2 0 0 0 0 4v2a2 2 0 0 0-2 2H5a2 2 0 0 0-2-2v-2a2 2 0 0 0 0-4z"/><path d="M14 6v12" stroke-dasharray="2 2"/>',
    payment: '<rect x="2.5" y="5" width="19" height="14" rx="2"/><path d="M2.5 10h19M6.5 15h4"/>',
    notification: '<path d="M6 9a6 6 0 0 1 12 0c0 6 2.5 7.5 2.5 7.5h-17S6 15 6 9"/><path d="M10 20a2 2 0 0 0 4 0"/>',
    search: '<circle cx="11" cy="11" r="7"/><path d="m20 20-3.5-3.5"/>', menu: '<path d="M4 7h16M4 12h16M4 17h16"/>', close: '<path d="M6 6l12 12M18 6 6 18"/>'
  };
  var IN_PAGES = /\/pages\/[^/]*$/.test(location.pathname);
  function href(key) { return key === "index" ? (IN_PAGES ? "../index.html" : "index.html") : (IN_PAGES ? "" : "pages/") + key + ".html"; }
  function icon(name, size) { return '<svg width="' + (size || 18) + '" height="' + (size || 18) + '" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">' + (ICONS[name] || "") + "</svg>"; }

  function esc(v) { return String(v == null ? "" : v).replace(/[&<>"']/g, function (c) { return ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]; }); }
  function money(n) { return Number(n || 0).toLocaleString("vi-VN") + " đ"; }
  function badge(v, label) { return '<span class="badge ' + esc(v) + '">' + esc(label || v) + "</span>"; }
  function seats(list) { return (list || []).map(function (s) { return '<span class="seat-tag">' + esc(s) + "</span>"; }).join(""); }

  /** Ảnh đại diện phim sinh từ tên (poster trong CSDL chỉ là tên file, chưa có ảnh thật). */
  var PAL = [["#7c2d12", "#f97316"], ["#1e3a8a", "#6366f1"], ["#4c1d95", "#db2777"], ["#064e3b", "#14b8a6"], ["#7f1d1d", "#f43f5e"], ["#713f12", "#eab308"], ["#0c4a6e", "#06b6d4"], ["#3b0764", "#a855f7"]];
  function thumb(title, cls) {
    var h = 0, s = String(title || ""); for (var i = 0; i < s.length; i++) h = (h * 31 + s.charCodeAt(i)) | 0;
    var p = PAL[Math.abs(h) % PAL.length];
    return '<span class="thumb' + (cls ? " " + cls : "") + '" style="--p1:' + p[0] + ";--p2:" + p[1] + '">' + esc(s.charAt(0).toUpperCase()) + "</span>";
  }

  /** Gọi API: tự bóc envelope {"status","data"}; lỗi ném Error có .code/.httpStatus; service tắt -> thông báo rõ ràng. */
  async function api(service, method, path, body) {
    var svc = S[service], res, json;
    try {
      res = await fetch(svc.base + path, { method: method, headers: body ? { "Content-Type": "application/json" } : {}, body: body ? JSON.stringify(body) : undefined });
    } catch (e) {
      var err = new Error(svc.name + " Service đang không chạy hoặc không truy cập được (cổng " + svc.port + ")");
      err.code = "SERVICE_DOWN"; throw err;
    }
    try { json = await res.json(); } catch (e) { json = null; }
    if (!res.ok || !json || json.status !== "success") {
      var e2 = new Error((json && json.message) || ("Lỗi HTTP " + res.status));
      e2.code = json && json.code; e2.httpStatus = res.status; throw e2;
    }
    return json.data;
  }
  /** Như api() nhưng không ném lỗi: trả fallback khi service lỗi (dùng cho dữ liệu phụ). */
  async function tryApi(service, path, fallback) { try { return await api(service, "GET", path); } catch (e) { return fallback; } }

  /** Kiểm tra sống một service bằng GET nhẹ (đường dẫn ping trong config.js). */
  async function ping(key) {
    var t0 = performance.now();
    try { await api(key, "GET", S[key].ping); return { ok: true, ms: Math.round(performance.now() - t0) }; }
    catch (e) { return { ok: e.code !== "SERVICE_DOWN" && e.httpStatus < 500, ms: Math.round(performance.now() - t0), error: e.message }; }
  }
  // Chấm trạng thái ở thanh bên: lưu 20 giây trong sessionStorage để chuyển trang không ping lại liên tục.
  async function sidebarHealth(force) {
    var cache = null; try { cache = JSON.parse(sessionStorage.getItem("soa.health") || "null"); } catch (e) {}
    if (force || !cache || Date.now() - cache.at > 20000) {
      var keys = Object.keys(S), res = await Promise.all(keys.map(ping));
      cache = { at: Date.now(), up: {} }; keys.forEach(function (k, i) { cache.up[k] = res[i].ok; });
      try { sessionStorage.setItem("soa.health", JSON.stringify(cache)); } catch (e) {}
    }
    setHealthDots(cache.up);
  }
  function setHealthDots(up) {
    Object.keys(up).forEach(function (k) {
      var d = document.querySelector('[data-dot="' + k + '"]');
      if (d) { d.className = "dot " + (up[k] ? "up" : "down"); d.title = up[k] ? "Đang chạy" : "Không truy cập được"; }
    });
  }

  function toast(msg, type) {
    var box = document.getElementById("toasts"), t = document.createElement("div");
    t.className = "toast" + (type === "error" ? " error" : ""); t.setAttribute("role", "status");
    t.innerHTML = "<span>" + (type === "error" ? "⚠️" : "✅") + "</span><span>" + esc(msg) + "</span>"; box.appendChild(t);
    setTimeout(function () { t.remove(); }, 4500);
  }

  /** Dựng khung (sidebar + tiêu đề). Mọi trang gọi hàm này đầu tiên -> giao diện đồng nhất. */
  function shell(active, title, subtitle) {
    if (!document.querySelector('link[data-font]')) {
      document.head.insertAdjacentHTML("beforeend", '<link data-font rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Be+Vietnam+Pro:wght@400;500;600;700&display=swap">');
    }
    var links = NAV.map(function (n, i) {
      var svc = S[n[0]];
      return (i === 1 ? '<div class="group">Dịch vụ</div>' : "") +
        '<a class="' + (n[0] === active ? "active" : "") + '" href="' + href(n[0]) + '">' + icon(n[0]) + '<span class="lbl">' + n[1] + "</span>" +
        (svc ? "<small>:" + svc.port + '</small><span class="dot" data-dot="' + n[0] + '"></span>' : "") + "</a>";
    }).join("");
    var svc = S[active];
    var app = document.getElementById("app"), content = app.innerHTML;
    app.outerHTML = '<div class="layout"><div class="mobilebar"><b>🎬 Admin SOA</b><button class="small" id="nav-toggle" aria-label="Mở menu">' + icon("menu") + "</button></div>" +
      '<nav class="sidebar" id="sidebar"><h1><span class="logo">▶</span><span>SOA Đặt vé phim<small>Bảng quản trị</small></span></h1><div class="group">Hệ thống</div>' + links +
      '<div class="side-foot">6 service · 6 CSDL · HTTP + JSON<br><a href="http://' + (location.hostname || "localhost") + ':8080" target="_blank" rel="noopener">Mở trang Client ↗</a></div></nav>' +
      '<main class="main"><div class="page-title"><div>' + (svc ? '<div class="crumb">' + esc(svc.name) + " Service · " + esc(svc.owner) + "</div>" : '<div class="crumb">Admin</div>') +
      "<h2>" + esc(title) + '</h2><div class="sub">' + esc(subtitle || "") + '</div></div><div id="page-actions"></div></div>' +
      '<div id="page-error"></div><div id="content">' + content + '</div></main></div><div id="toasts"></div>' +
      '<div class="modal-bg" id="modal-bg"><div class="modal" id="modal" role="dialog" aria-modal="true"></div></div>' +
      '<div class="drawer-bg" id="drawer-bg"><aside class="drawer" role="dialog" aria-modal="true"><div class="drawer-head"><h3 id="drawer-title"></h3><button class="ghost small" id="drawer-close" aria-label="Đóng">' +
      icon("close") + '</button></div><div class="drawer-body" id="drawer-body"></div></aside></div>';
    var side = document.getElementById("sidebar");
    document.getElementById("nav-toggle").onclick = function (ev) { ev.stopPropagation(); side.classList.toggle("open"); };
    document.addEventListener("click", function (ev) { if (side.classList.contains("open") && !side.contains(ev.target)) side.classList.remove("open"); });
    document.getElementById("modal-bg").addEventListener("mousedown", function (ev) { if (ev.target.id === "modal-bg") closeForm(); });
    document.getElementById("drawer-bg").addEventListener("mousedown", function (ev) { if (ev.target.id === "drawer-bg") closeDrawer(); });
    document.getElementById("drawer-close").onclick = closeDrawer;
    document.addEventListener("keydown", function (ev) { if (ev.key === "Escape") { closeForm(); closeDrawer(); } });
    sidebarHealth(false);
  }

  function showError(e) {
    document.getElementById("page-error").innerHTML = '<div class="alert"><span>⚠</span><div><b>' + (e.code === "SERVICE_DOWN" ? "Không kết nối được service" : "Có lỗi xảy ra") + "</b>" + esc(e.message) + "</div></div>";
  }
  function clearError() { document.getElementById("page-error").innerHTML = ""; }
  /** Khung xương trong lúc tải dữ liệu. */
  function loading(el, rows) {
    el.innerHTML = '<div style="display:grid;gap:14px;padding:6px 0">' + Array((rows || 5) + 1).join('<div class="skel"></div>') + "</div>";
  }
  function emptyHtml(text) { return '<div class="empty"><span class="ic">🗂️</span>' + esc(text || "Chưa có dữ liệu") + "</div>"; }

  /** columns: [{label, key|render(row), align:"num", wrap:true}]
   *  opts (tùy chọn): {search: "placeholder" | true, onRowClick(row), empty: "text"} — tìm kiếm lọc theo nội dung hiển thị của từng dòng. */
  function table(el, columns, rows, actions, opts) {
    opts = opts || {};
    if (!rows.length) { el.innerHTML = emptyHtml(opts.empty); return; }
    var head = columns.map(function (c) { return '<th class="' + (c.align || "") + '">' + esc(c.label) + "</th>"; }).join("") + (actions ? "<th></th>" : "");
    var html = rows.map(function (r, i) {
      var tds = columns.map(function (c) { return '<td class="' + (c.align || "") + (c.wrap ? " wrap" : "") + '">' + (c.render ? c.render(r) : esc(r[c.key])) + "</td>"; }).join("");
      return '<tr data-i="' + i + '"' + (opts.onRowClick ? ' class="clickable"' : "") + ">" + tds + (actions ? '<td><div class="actions">' + actions(r, i) + "</div></td>" : "") + "</tr>";
    });
    var tools = opts.search ? '<div class="table-tools"><label class="search">' + icon("search", 15) + '<input type="search" placeholder="' + esc(opts.search === true ? "Tìm trong bảng..." : opts.search) + '"></label><span class="count"></span></div>' : "";
    el.innerHTML = tools + '<div class="table-wrap"><table><thead><tr>' + head + "</tr></thead><tbody>" + html.join("") + "</tbody></table></div>";
    var tbody = el.querySelector("tbody"), trs = Array.prototype.slice.call(tbody.children), count = el.querySelector(".count");
    function filter(q) {
      var n = 0; q = q.toLowerCase();
      trs.forEach(function (tr) { var hit = !q || tr.textContent.toLowerCase().indexOf(q) >= 0; tr.style.display = hit ? "" : "none"; if (hit) n++; });
      if (count) count.textContent = (q ? n + " / " : "") + rows.length + " bản ghi";
    }
    if (opts.search) { var inp = el.querySelector(".table-tools input"); inp.oninput = function () { filter(inp.value.trim()); }; filter(""); }
    if (opts.onRowClick) tbody.addEventListener("click", function (ev) {
      if (ev.target.closest("button,a,input")) return;
      var tr = ev.target.closest("tr"); if (tr) opts.onRowClick(rows[+tr.dataset.i]);
    });
  }

  /** Form dạng hộp thoại. fields: [{name,label,type,options,required,value,placeholder,hint}] */
  function openForm(opts) {
    var bg = document.getElementById("modal-bg"), m = document.getElementById("modal");
    var html = "<h3>" + esc(opts.title) + "</h3>" + (opts.subtitle ? '<p class="modal-sub">' + esc(opts.subtitle) + "</p>" : "") + '<form id="modal-form" novalidate>' + opts.fields.map(function (f) {
      var v = (opts.values && opts.values[f.name] != null) ? opts.values[f.name] : (f.value != null ? f.value : "");
      var input = f.type === "select"
        ? "<select name=\"" + f.name + "\">" + f.options.map(function (o) { var ov = o.value != null ? o.value : o; var ol = o.label != null ? o.label : o; return '<option value="' + esc(ov) + '"' + (String(ov) === String(v) ? " selected" : "") + ">" + esc(ol) + "</option>"; }).join("") + "</select>"
        : '<input name="' + f.name + '" type="' + (f.type || "text") + '" value="' + esc(v) + '" placeholder="' + esc(f.placeholder || "") + '"' + (f.required ? " required" : "") + (f.min != null ? ' min="' + f.min + '"' : "") + ">";
      return '<div class="field"><label>' + esc(f.label) + (f.required ? ' <span style="color:var(--err)">*</span>' : "") + "</label>" + input + (f.hint ? '<div class="hint">' + esc(f.hint) + "</div>" : "") + "</div>";
    }).join("") + '<div class="actions"><button type="button" class="secondary" id="m-cancel">Hủy</button><button type="submit" id="m-ok">' + esc(opts.submitLabel || "Lưu") + "</button></div></form>";
    m.className = "modal"; m.innerHTML = html; bg.classList.add("open");
    var form = document.getElementById("modal-form"), first = form.querySelector("input,select");
    if (first) first.focus();
    document.getElementById("m-cancel").onclick = closeForm;
    form.onsubmit = async function (ev) {
      ev.preventDefault();
      if (!form.reportValidity()) return;
      var data = {}; opts.fields.forEach(function (f) { data[f.name] = form.elements[f.name].value; });
      var btn = document.getElementById("m-ok"), label = btn.innerHTML; btn.disabled = true; btn.innerHTML = '<span class="spinner"></span> Đang xử lý';
      try { await opts.onSubmit(data); closeForm(); } catch (e) { toast(e.message, "error"); btn.disabled = false; btn.innerHTML = label; }
    };
  }
  function closeForm() { var bg = document.getElementById("modal-bg"); if (bg) bg.classList.remove("open"); }

  /** Hộp xác nhận (Promise<boolean>) thay cho window.confirm. */
  function confirmBox(msg, okLabel) {
    return new Promise(function (resolve) {
      var bg = document.getElementById("modal-bg"), m = document.getElementById("modal");
      m.className = "modal confirm";
      m.innerHTML = '<div class="ic">!</div><h3>Xác nhận</h3><p class="modal-sub">' + esc(msg) + '</p><div class="actions"><button class="secondary" id="c-no">Hủy</button><button class="danger" id="c-yes">' + esc(okLabel || "Xóa") + "</button></div>";
      bg.classList.add("open"); document.getElementById("c-yes").focus();
      function done(v) { closeForm(); resolve(v); }
      document.getElementById("c-no").onclick = function () { done(false); };
      document.getElementById("c-yes").onclick = function () { done(true); };
    });
  }

  /** Ngăn kéo chi tiết bên phải. html có thể là chuỗi hoặc Promise<chuỗi>. */
  async function drawer(title, html) {
    document.getElementById("drawer-title").textContent = title;
    var body = document.getElementById("drawer-body");
    document.getElementById("drawer-bg").classList.add("open");
    if (html && typeof html.then === "function") { loading(body, 6); try { body.innerHTML = await html; } catch (e) { body.innerHTML = '<div class="alert">⚠ ' + esc(e.message) + "</div>"; } }
    else body.innerHTML = html;
  }
  function closeDrawer() { var d = document.getElementById("drawer-bg"); if (d) d.classList.remove("open"); }
  /** Danh sách cặp nhãn–giá trị: [[label, htmlValue]] */
  function dl(pairs) { return '<dl class="dl">' + pairs.map(function (p) { return "<dt>" + esc(p[0]) + "</dt><dd>" + (p[1] == null || p[1] === "" ? "—" : p[1]) + "</dd>"; }).join("") + "</dl>"; }

  /** Hàng ô số liệu: [{label, value, hint}] */
  function stats(el, items) {
    el.className = "stats";
    el.innerHTML = items.map(function (s) { return '<div class="stat"><div class="k">' + esc(s.label) + '</div><div class="v">' + s.value + '</div><div class="h">' + (s.hint || "&nbsp;") + "</div></div>"; }).join("");
  }

  function fmtTime(t) { return esc(String(t || "").replace("T", " ").replace(/\.\d+Z?$/, "").replace(/Z$/, "")); }

  /** Trang CRUD chuẩn (dùng cho Movie, Showtime): list + thêm + sửa + xóa */
  function crudPage(cfg) {
    var rows = [], list = document.getElementById("list");
    async function load() {
      clearError(); if (!rows.length) loading(list);
      try {
        if (cfg.beforeLoad) await cfg.beforeLoad();
        rows = await api(cfg.service, "GET", cfg.listPath ? cfg.listPath() : cfg.path);
        if (cfg.afterLoad) cfg.afterLoad(rows);
        table(list, cfg.columns, rows, function (r) {
          return '<button class="small secondary" data-edit="' + r.id + '">Sửa</button><button class="small ghost" data-del="' + r.id + '" style="color:var(--err)">Xóa</button>';
        }, { search: cfg.search || "Tìm " + cfg.noun + "...", empty: "Chưa có " + cfg.noun + " nào" });
      } catch (e) { showError(e); list.innerHTML = emptyHtml("Không tải được dữ liệu"); }
    }
    function form(row) {
      openForm({
        title: row ? "Sửa " + cfg.noun + " #" + row.id : "Thêm " + cfg.noun, subtitle: cfg.formHint, fields: cfg.fields(), values: row ? cfg.toForm(row) : {},
        submitLabel: row ? "Lưu thay đổi" : "Thêm " + cfg.noun,
        onSubmit: async function (data) {
          var payload = cfg.toPayload(data);
          if (row) await api(cfg.service, "PUT", cfg.path + "/" + row.id, payload); else await api(cfg.service, "POST", cfg.path, payload);
          toast(row ? "Đã cập nhật " + cfg.noun + " #" + row.id : "Đã thêm " + cfg.noun); load();
        }
      });
    }
    document.getElementById("page-actions").innerHTML = '<button class="secondary" id="btn-reload">Làm mới</button><button id="btn-add">+ Thêm ' + esc(cfg.noun) + "</button>";
    document.getElementById("btn-add").onclick = function () { form(null); };
    document.getElementById("btn-reload").onclick = load;
    list.addEventListener("click", async function (ev) {
      var eb = ev.target.closest("[data-edit]"), db = ev.target.closest("[data-del]");
      if (eb) form(rows.filter(function (r) { return String(r.id) === eb.dataset.edit; })[0]);
      if (db && await confirmBox("Xóa " + cfg.noun + " #" + db.dataset.del + "? Thao tác này không hoàn tác được.")) {
        try { await api(cfg.service, "DELETE", cfg.path + "/" + db.dataset.del); toast("Đã xóa " + cfg.noun + " #" + db.dataset.del); load(); } catch (e) { toast(e.message, "error"); }
      }
    });
    load();
    return { reload: load };
  }

  window.Admin = { api: api, tryApi: tryApi, ping: ping, sidebarHealth: sidebarHealth, setHealthDots: setHealthDots, toast: toast, shell: shell, table: table,
                   openForm: openForm, closeForm: closeForm, confirmBox: confirmBox, drawer: drawer, closeDrawer: closeDrawer, dl: dl, stats: stats,
                   loading: loading, crudPage: crudPage, icon: icon, thumb: thumb, seats: seats,
                   esc: esc, money: money, badge: badge, fmtTime: fmtTime, showError: showError, clearError: clearError };
})();
