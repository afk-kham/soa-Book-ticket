/* Thư viện dùng chung cho mọi trang Admin: khung giao diện, gọi API theo hợp đồng chung, bảng, form, thông báo. */
(function () {
  var S = window.SOA.services;
  var NAV = [["index", "Tổng quan"], ["movie", "Phim"], ["showtime", "Suất chiếu"], ["user", "Người dùng"],
             ["booking", "Đặt vé"], ["payment", "Thanh toán"], ["notification", "Thông báo"]];
  var IN_PAGES = /\/pages\/[^/]*$/.test(location.pathname);
  function href(key) { return key === "index" ? (IN_PAGES ? "../index.html" : "index.html") : (IN_PAGES ? "" : "pages/") + key + ".html"; }

  function esc(v) { return String(v == null ? "" : v).replace(/[&<>"']/g, function (c) { return ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]; }); }
  function money(n) { return Number(n || 0).toLocaleString("vi-VN") + " đ"; }
  function badge(v) { return '<span class="badge ' + esc(v) + '">' + esc(v) + "</span>"; }

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

  function toast(msg, type) {
    var box = document.getElementById("toasts"), t = document.createElement("div");
    t.className = "toast" + (type === "error" ? " error" : ""); t.textContent = msg; box.appendChild(t);
    setTimeout(function () { t.remove(); }, 4200);
  }

  /** Dựng khung (sidebar + tiêu đề). Mọi trang gọi hàm này đầu tiên -> giao diện đồng nhất. */
  function shell(active, title, subtitle) {
    var links = NAV.map(function (n) {
      var svc = S[n[0]];
      return '<a class="' + (n[0] === active ? "active" : "") + '" href="' + href(n[0]) + '"><span>' + n[1] + "</span>" + (svc ? "<small>:" + svc.port + "</small>" : "") + "</a>";
    }).join("");
    var app = document.getElementById("app"), content = app.innerHTML;
    app.outerHTML = '<div class="layout"><nav class="sidebar"><h1>🎬 SOA Đặt vé phim</h1>' + links + '</nav><main class="main">' +
      '<div class="page-title"><div><h2>' + esc(title) + '</h2><div class="sub">' + esc(subtitle || "") + '</div></div><div id="page-actions"></div></div>' +
      '<div id="page-error"></div><div id="content">' + content + '</div></main></div><div id="toasts"></div>' +
      '<div class="modal-bg" id="modal-bg"><div class="modal" id="modal"></div></div>';
  }

  function showError(e) { document.getElementById("page-error").innerHTML = '<div class="alert">⚠ ' + esc(e.message) + "</div>"; }
  function clearError() { document.getElementById("page-error").innerHTML = ""; }

  /** columns: [{label, key|render(row)}] */
  function table(el, columns, rows, actions) {
    if (!rows.length) { el.innerHTML = '<div class="empty">Chưa có dữ liệu</div>'; return; }
    var head = columns.map(function (c) { return "<th>" + esc(c.label) + "</th>"; }).join("") + (actions ? "<th></th>" : "");
    var body = rows.map(function (r, i) {
      var tds = columns.map(function (c) { return "<td>" + (c.render ? c.render(r) : esc(r[c.key])) + "</td>"; }).join("");
      return "<tr>" + tds + (actions ? "<td>" + actions(r, i) + "</td>" : "") + "</tr>";
    }).join("");
    el.innerHTML = '<div class="table-wrap"><table><thead><tr>' + head + "</tr></thead><tbody>" + body + "</tbody></table></div>";
  }

  /** Form dạng hộp thoại. fields: [{name,label,type,options,required,value,placeholder}] */
  function openForm(opts) {
    var bg = document.getElementById("modal-bg"), m = document.getElementById("modal");
    var html = "<h3>" + esc(opts.title) + '</h3><form id="modal-form" onsubmit="return false">' + opts.fields.map(function (f) {
      var v = (opts.values && opts.values[f.name] != null) ? opts.values[f.name] : (f.value != null ? f.value : "");
      var input = f.type === "select"
        ? "<select name=\"" + f.name + "\">" + f.options.map(function (o) { var ov = o.value != null ? o.value : o; var ol = o.label != null ? o.label : o; return '<option value="' + esc(ov) + '"' + (String(ov) === String(v) ? " selected" : "") + ">" + esc(ol) + "</option>"; }).join("") + "</select>"
        : '<input name="' + f.name + '" type="' + (f.type || "text") + '" value="' + esc(v) + '" placeholder="' + esc(f.placeholder || "") + '"' + (f.required ? " required" : "") + (f.min != null ? ' min="' + f.min + '"' : "") + ">";
      return '<div class="field"><label>' + esc(f.label) + (f.required ? " *" : "") + "</label>" + input + "</div>";
    }).join("") + '<div class="actions"><button type="button" class="secondary" id="m-cancel">Hủy</button><button type="submit" id="m-ok">' + esc(opts.submitLabel || "Lưu") + "</button></div></form>";
    m.innerHTML = html; bg.classList.add("open");
    var form = document.getElementById("modal-form");
    document.getElementById("m-cancel").onclick = closeForm;
    form.onsubmit = async function (ev) {
      ev.preventDefault();
      if (!form.reportValidity()) return;
      var data = {}; opts.fields.forEach(function (f) { data[f.name] = form.elements[f.name].value; });
      var btn = document.getElementById("m-ok"); btn.disabled = true;
      try { await opts.onSubmit(data); closeForm(); } catch (e) { toast(e.message, "error"); btn.disabled = false; }
    };
  }
  function closeForm() { document.getElementById("modal-bg").classList.remove("open"); }

  function confirmBox(msg) { return window.confirm(msg); }
  function fmtTime(t) { return esc(String(t || "").replace("T", " ").replace(/\.\d+Z?$/, "").replace(/Z$/, "")); }

  /** Trang CRUD chuẩn (dùng cho Movie, Showtime): list + thêm + sửa + xóa */
  function crudPage(cfg) {
    var rows = [];
    async function load() {
      clearError();
      try {
        if (cfg.beforeLoad) await cfg.beforeLoad();
        rows = await api(cfg.service, "GET", cfg.listPath ? cfg.listPath() : cfg.path);
        table(document.getElementById("list"), cfg.columns, rows, function (r) {
          return '<button class="small secondary" data-edit="' + r.id + '">Sửa</button> <button class="small danger" data-del="' + r.id + '">Xóa</button>';
        });
      } catch (e) { showError(e); document.getElementById("list").innerHTML = ""; }
    }
    function form(row) {
      openForm({
        title: row ? "Sửa " + cfg.noun + " #" + row.id : "Thêm " + cfg.noun, fields: cfg.fields(), values: row ? cfg.toForm(row) : {},
        onSubmit: async function (data) {
          var payload = cfg.toPayload(data);
          if (row) await api(cfg.service, "PUT", cfg.path + "/" + row.id, payload); else await api(cfg.service, "POST", cfg.path, payload);
          toast("Đã lưu"); load();
        }
      });
    }
    document.getElementById("page-actions").innerHTML = '<button id="btn-add">+ Thêm ' + esc(cfg.noun) + "</button>";
    document.getElementById("btn-add").onclick = function () { form(null); };
    document.getElementById("list").addEventListener("click", async function (ev) {
      var id = ev.target.getAttribute("data-edit"), del = ev.target.getAttribute("data-del");
      if (id) form(rows.filter(function (r) { return String(r.id) === id; })[0]);
      if (del && confirmBox("Xóa " + cfg.noun + " #" + del + "?")) {
        try { await api(cfg.service, "DELETE", cfg.path + "/" + del); toast("Đã xóa"); load(); } catch (e) { toast(e.message, "error"); }
      }
    });
    load();
    return { reload: load };
  }

  window.Admin = { api: api, toast: toast, shell: shell, table: table, openForm: openForm, closeForm: closeForm, crudPage: crudPage,
                   esc: esc, money: money, badge: badge, fmtTime: fmtTime, showError: showError, clearError: clearError };
})();
