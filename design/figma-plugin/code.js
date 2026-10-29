// SOA Cinema Builder — plugin phát triển, chạy trong Figma Desktop trên file "SOA Cinema — Giao diện chính thức".
// Chạy cục bộ nên không tốn lượt gọi Figma MCP. Mọi node ID bên dưới là của file đó (fileKey aGFb4cT9qZhAvbx0e20uHP).
//   Lệnh "client": nối luồng prototype + hoạt ảnh cho 6 màn hình Client, biến ghế/tab/thanh toán thành component tương tác.
//   Lệnh "admin":  dựng 5 màn hình Admin (Tổng quan, Đặt vé, Đặt vé + ngăn chi tiết, Phim, Phim + form) và nối prototype.
// Chạy lại an toàn: lệnh "admin" xóa các màn hình A0x cũ trước khi dựng.

const PAGES = { client: '2:28', admin: '2:29' };
const FONT = 'Be Vietnam Pro';
const N = (id) => figma.getNodeByIdAsync(id);
let V = {}, TS = {}, ES = {};
const report = { ok: 0, fail: [] };

// ---------- Nền tảng ----------
async function setup() {
  const cols = await figma.variables.getLocalVariableCollectionsAsync();
  const cname = {};
  cols.forEach((c) => { cname[c.id] = c.name; });
  (await figma.variables.getLocalVariablesAsync('COLOR')).forEach((v) => { V[cname[v.variableCollectionId] + ':' + v.name] = v; });
  (await figma.getLocalTextStylesAsync()).forEach((s) => { TS[s.name] = s; });
  (await figma.getLocalEffectStylesAsync()).forEach((s) => { ES[s.name] = s; });
  await Promise.all(['Regular', 'Medium', 'SemiBold', 'Bold', 'ExtraBold'].map((s) => figma.loadFontAsync({ family: FONT, style: s }))
    .concat([figma.loadFontAsync({ family: 'IBM Plex Mono', style: 'Medium' }), figma.loadFontAsync({ family: 'Inter', style: 'Regular' })]));
}
function P(k) {
  if (!V[k]) throw new Error('Thiếu biến màu ' + k);
  return figma.variables.setBoundVariableForPaint({ type: 'SOLID', color: { r: 0, g: 0, b: 0 } }, 'color', V[k]);
}
async function T(str, style, color, name) {
  const t = figma.createText();
  await t.setTextStyleIdAsync(TS[style].id);
  t.characters = str;
  t.fills = [P(color)];
  t.name = name || str.slice(0, 24);
  return t;
}
function A(dir, props) {
  const f = figma.createFrame();
  f.layoutMode = dir;
  f.primaryAxisSizingMode = 'AUTO';
  f.counterAxisSizingMode = 'AUTO';
  f.fills = [];
  f.clipsContent = false;
  if (props) Object.assign(f, props);
  return f;
}
function pad(n, v, h) { n.paddingTop = v; n.paddingBottom = v; n.paddingLeft = h == null ? v : h; n.paddingRight = h == null ? v : h; }
function stroke(n, k, w) { n.strokes = [P(k)]; n.strokeWeight = w || 1; n.strokeAlign = 'INSIDE'; }
function sideStroke(n, k, side) {
  n.strokes = [P(k)]; n.strokeAlign = 'INSIDE';
  n.strokeTopWeight = side === 'top' ? 1 : 0; n.strokeBottomWeight = side === 'bottom' ? 1 : 0;
  n.strokeLeftWeight = side === 'left' ? 1 : 0; n.strokeRightWeight = side === 'right' ? 1 : 0;
}
function width(f, w) {
  f.resize(w, Math.max(f.height, 1));
  if (f.layoutMode === 'VERTICAL') { f.counterAxisSizingMode = 'FIXED'; f.primaryAxisSizingMode = 'AUTO'; }
  else { f.primaryAxisSizingMode = 'FIXED'; f.counterAxisSizingMode = 'AUTO'; }
}
function fillW(n) { n.layoutSizingHorizontal = 'FILL'; if (n.type === 'TEXT') n.textAutoResize = 'HEIGHT'; }
function gap(h, w) { const f = figma.createFrame(); f.resize(w || 1, h); f.fills = []; f.name = 'Gap'; return f; }

// Màu poster/thumb — cùng hàm băm với client/js/app.js và admin/js/common.js
const PAL = [['#7c2d12', '#f97316'], ['#1e3a8a', '#6366f1'], ['#4c1d95', '#db2777'], ['#064e3b', '#14b8a6'], ['#7f1d1d', '#f43f5e'], ['#713f12', '#eab308'], ['#0c4a6e', '#06b6d4'], ['#3b0764', '#a855f7']];
function hash(s) { let h = 0; for (let i = 0; i < s.length; i++) h = (h * 31 + s.charCodeAt(i)) | 0; return Math.abs(h); }
function hex(h) { return { r: parseInt(h.slice(1, 3), 16) / 255, g: parseInt(h.slice(3, 5), 16) / 255, b: parseInt(h.slice(5, 7), 16) / 255 }; }
function grad(title) {
  const p = PAL[hash(title) % PAL.length];
  return { type: 'GRADIENT_LINEAR', gradientTransform: [[0.6, 0.6, -0.1], [-0.6, 0.6, 0.5]], gradientStops: [{ position: 0, color: Object.assign(hex(p[0]), { a: 1 }) }, { position: 1, color: Object.assign(hex(p[1]), { a: 1 }) }] };
}

// ---------- Prototype ----------
const EASE = { type: 'EASE_IN_AND_OUT' };
const TR = {
  fwd: { type: 'PUSH', direction: 'LEFT', matchLayers: true, easing: EASE, duration: 0.4 },
  back: { type: 'PUSH', direction: 'RIGHT', matchLayers: true, easing: EASE, duration: 0.4 },
  fade: { type: 'DISSOLVE', easing: { type: 'EASE_OUT' }, duration: 0.25 },
  up: { type: 'SLIDE_IN', direction: 'TOP', matchLayers: false, easing: { type: 'EASE_OUT' }, duration: 0.45 },
  toggle: { type: 'SMART_ANIMATE', easing: { type: 'EASE_OUT' }, duration: 0.18 },
  open: { type: 'SMART_ANIMATE', easing: { type: 'EASE_OUT' }, duration: 0.35 },
  close: { type: 'SMART_ANIMATE', easing: EASE, duration: 0.3 },
  scroll: { type: 'SCROLL_ANIMATE', easing: EASE, duration: 0.5 }
};
async function click(node, destId, tr, navigation) {
  const nav = navigation || 'NAVIGATE';
  if (!node) { report.fail.push('Không tìm thấy nút → ' + destId); return; }
  try {
    const action = { type: 'NODE', destinationId: destId, navigation: nav, transition: TR[tr] };
    await node.setReactionsAsync([{ trigger: { type: 'ON_CLICK' }, actions: [action] }]);
    report.ok++;
  } catch (e) { report.fail.push(node.name + ': ' + String(e).slice(0, 140)); }
}
const byName = (root, name) => root.findOne((n) => n.name === name);
const textIs = (root, chars) => root.findOne((n) => n.type === 'TEXT' && n.characters === chars);
const btnLabel = (root, label) => root.findOne((n) => n.type === 'INSTANCE' && n.children.some((c) => c.type === 'TEXT' && c.characters === label));

// =====================================================================
// Lệnh 1 — Client: prototype + hoạt ảnh
// =====================================================================
async function client() {
  const page = await N(PAGES.client);
  await figma.setCurrentPageAsync(page);
  const S = { home: '8:83', detail: '8:201', login: '8:265', seat: '9:212', result: '9:492', my: '9:641' };
  const scr = {};
  for (const k in S) { scr[k] = await N(S[k]); if (!scr[k]) throw new Error('Không thấy màn hình ' + k + ' (' + S[k] + ')'); }

  // Thanh trên: Phim / logo → Trang chủ, Vé của tôi → Vé của tôi, Đăng nhập / Đăng ký → Đăng nhập
  for (const k in scr) {
    const tb = scr[k].children[0];
    if (k !== 'home') { await click(byName(tb, 'Nav / Phim'), S.home, 'back'); await click(byName(tb, 'Brand'), S.home, 'back'); }
    if (k !== 'my') await click(byName(tb, 'Nav / Vé của tôi'), S.my, 'fade');
    const acc = byName(tb, 'Account');
    if (acc && k !== 'login') for (const b of acc.children) if (b.type === 'INSTANCE' && b.children.some((c) => c.type === 'TEXT' && /Đăng (nhập|ký)/.test(c.characters))) await click(b, S.login, 'fade');
  }
  // Trang chủ
  const hero = byName(scr.home, 'Hero');
  await click(btnLabel(hero, 'Đặt vé ngay'), S.detail, 'fwd');
  await click(btnLabel(hero, 'Xem tất cả phim'), byName(scr.home, 'Phim đang chiếu').id, 'scroll', 'SCROLL_TO');
  for (const c of byName(scr.home, 'Grid').children) await click(c, S.detail, 'fwd');
  // Chi tiết phim
  await click(textIs(scr.detail, '← Danh sách phim'), S.home, 'back');
  await click(btnLabel(scr.detail, 'Chọn suất chiếu'), byName(scr.detail, 'Lịch chiếu').id, 'scroll', 'SCROLL_TO');
  for (const t of byName(scr.detail, 'Times').children) await click(t, S.login, 'fwd'); // chưa đăng nhập → Đăng nhập → quay lại chọn ghế
  // Đăng nhập
  await click(btnLabel(byName(scr.login, 'Form'), 'Đăng nhập'), S.seat, 'fwd');
  // Chọn ghế
  await click(textIs(scr.seat, '← Đổi suất chiếu'), S.detail, 'back');
  await click(btnLabel(scr.seat, 'Đặt vé & thanh toán'), S.result, 'up');
  // Kết quả
  await click(btnLabel(scr.result, 'Xem vé của tôi'), S.my, 'fwd');
  await click(btnLabel(scr.result, 'Về trang chủ'), S.home, 'back');

  // Component tương tác: bấm để đổi trạng thái (Smart Animate)
  const toggles = [['3:42', '3:44'], ['3:44', '3:42'], ['3:77', '3:80'], ['3:80', '3:77'], ['3:34', '3:36'], ['3:36', '3:34'], ['3:100', '3:107']];
  for (const p of toggles) await click(await N(p[0]), p[1], 'toggle', 'CHANGE_TO');

  page.flowStartingPoints = [{ nodeId: S.home, name: 'Client — Đặt vé' }];

  // Sửa chữ poster bị ngắt giữa từ ở màn Kết quả
  const rp = scr.result.findOne((n) => n.type === 'INSTANCE' && n.name === 'Poster' && Math.round(n.width) === 120);
  if (rp) { const t = rp.findOne((n) => n.type === 'TEXT' && n.name === 'Title'); if (t) t.fontSize = 14; }
}

// =====================================================================
// Lệnh 2 — Admin: 5 màn hình + prototype
// =====================================================================
async function admin() {
  const page = await N(PAGES.admin);
  await figma.setCurrentPageAsync(page);
  for (const n of page.children.slice()) if (/^A0\d/.test(n.name)) n.remove();

  const ID = { sidebar: '5:78', btnP: '5:160', btnS: '5:164', btnSs: '5:166', btnG: '5:168', bPAID: '5:179', bPENDING: '5:182', bCANCELLED: '5:185', bNeutral: '5:194',
    svcUp: '5:203', stat: '5:199', thumb: '7:71', seat: '7:73', search: '7:75', ffText: '7:80', bHead: '7:95', bRow: '7:110', mHead: '7:136', mRow: '7:151', iClose: '5:58' };
  const IC = { index: '5:24', movie: '5:28', showtime: '5:32', user: '5:36', booking: '5:40', payment: '5:44', notification: '5:48' };
  const C = {};
  await Promise.all(Object.keys(ID).map(async (k) => { C[k] = await N(ID[k]); if (!C[k]) throw new Error('Thiếu component ' + k + ' (' + ID[k] + ')'); }));
  const K = { btn: 'Label#5:12', sL: 'Label#5:21', sV: 'Value#5:22', sH: 'Hint#5:23', svc: 'Service#5:24', own: 'Owner#5:27', meta: 'Meta#5:30', svcIcon: 'Icon#5:33',
    init: 'Initial#7:0', seat: 'Seat#7:1', ph: 'Placeholder#7:2', ffL: 'Label#7:3', ffV: 'Value#7:6',
    bCode: 'Code#7:9', bUser: 'User#7:10', bMovie: 'Movie#7:11', bSt: 'Showtime#7:12', bTot: 'Total#7:13', bCr: 'Created#7:14',
    mId: 'ID#7:15', mTitle: 'Title#7:16', mDur: 'Duration#7:17', mPos: 'Poster#7:18', mCr: 'Created#7:19' };
  const ST = { PAID: 'Đã thanh toán', PENDING: 'Chờ thanh toán', CANCELLED: 'Đã hủy' };
  const BOOKINGS = [
    [4, 'user1', 'Avengers: Endgame', 1, ['D5', 'D6'], '180.000 đ', 'PAID', '2026-10-13 09:00:00'],
    [3, 'user1', 'Mai', 5, ['C3', 'C4'], '180.000 đ', 'PENDING', '2026-10-02 09:30:00'],
    [2, 'user2', 'Inception', 3, ['B5'], '85.000 đ', 'CANCELLED', '2026-10-01 11:00:00'],
    [1, 'user1', 'Avengers: Endgame', 1, ['A1', 'A2'], '180.000 đ', 'PAID', '2026-10-01 10:00:00']];
  const MOVIES = [[1, 'Avengers: Endgame', 'Hành động', 181], [2, 'Inception', 'Khoa học viễn tưởng', 148], [3, 'Parasite', 'Tâm lý', 132], [4, 'Mai', 'Tâm lý', 131], [5, 'Coco', 'Hoạt hình', 105]];

  const btn = (v, label) => { const b = v.createInstance(); b.setProperties({ [K.btn]: label }); return b; };
  const stat = (l, v, h) => { const s = C.stat.createInstance(); s.setProperties({ [K.sL]: l, [K.sV]: v, [K.sH]: h || ' ' }); return s; };
  const thumb = (title) => { const t = C.thumb.createInstance(); t.setProperties({ [K.init]: title.charAt(0).toUpperCase() }); t.fills = [grad(title)]; return t; };
  const seatTag = (s) => { const t = C.seat.createInstance(); t.setProperties({ [K.seat]: s }); return t; };
  const badge = (st, label) => { const b = C['b' + st].createInstance(); if (label) b.findOne((n) => n.type === 'TEXT').characters = label; return b; };
  async function card(name, title, right) {
    const c = A('VERTICAL', { name, itemSpacing: 14, cornerRadius: 12 }); pad(c, 18);
    c.fills = [P('Admin:card')]; stroke(c, 'Admin:line'); await c.setEffectStyleIdAsync(ES['Admin/Card'].id);
    if (title) {
      const h = A('HORIZONTAL', { name: 'Card head', primaryAxisAlignItems: 'SPACE_BETWEEN', counterAxisAlignItems: 'CENTER' });
      h.appendChild(await T(title, 'Admin/H3', 'Admin:text', 'Title')); if (right) h.appendChild(right);
      c.appendChild(h); fillW(h);
    }
    return c;
  }
  let col = 0;
  async function screen(name, active, crumb, title, sub) {
    const s = A('HORIZONTAL', { name }); s.fills = [P('Admin:bg')]; s.clipsContent = true;
    s.resize(1440, 900); s.primaryAxisSizingMode = 'FIXED'; s.counterAxisSizingMode = 'AUTO'; s.minHeight = 900;
    s.x = col * 1600; s.y = 0; col++;
    const sb = C.sidebar.createInstance(); s.appendChild(sb); sb.layoutSizingVertical = 'FILL';
    for (const n of sb.findAll((x) => x.type === 'INSTANCE' && x.name.indexOf('Nav / ') === 0)) n.setProperties({ State: n.name === 'Nav / ' + active ? 'Active' : 'Default' });
    const m = A('VERTICAL', { name: 'Main', itemSpacing: 18 }); m.paddingTop = 28; m.paddingBottom = 48; m.paddingLeft = 32; m.paddingRight = 32;
    s.appendChild(m); fillW(m);
    const tr = A('HORIZONTAL', { name: 'Page title', primaryAxisAlignItems: 'SPACE_BETWEEN', counterAxisAlignItems: 'MAX', paddingBottom: 4 });
    const tl = A('VERTICAL', { name: 'Heading', itemSpacing: 4 });
    tl.appendChild(await T(crumb, 'Admin/Overline', 'Admin:primary', 'Crumb'));
    tl.appendChild(await T(title, 'Admin/H1', 'Admin:text', 'Title'));
    tl.appendChild(await T(sub, 'Admin/Small', 'Admin:muted', 'Sub'));
    tr.appendChild(tl);
    const acts = A('HORIZONTAL', { name: 'Page actions', itemSpacing: 8 }); tr.appendChild(acts);
    m.appendChild(tr); fillW(tr);
    return { s, m, acts };
  }
  function row(parent, gapPx) { const r = A('HORIZONTAL', { name: 'Row', itemSpacing: gapPx == null ? 14 : gapPx }); parent.appendChild(r); fillW(r); return r; }
  function statsRow(m, items) { const r = row(m, 14); r.name = 'Stats'; for (const it of items) { const s = stat(it[0], it[1], it[2]); r.appendChild(s); s.layoutSizingHorizontal = 'FILL'; } return r; }
  async function dl(parent, pairs) {
    for (const p of pairs) {
      const r = A('HORIZONTAL', { name: 'DL / ' + p[0], itemSpacing: 14, counterAxisAlignItems: 'CENTER', paddingTop: 4, paddingBottom: 4 });
      parent.appendChild(r); fillW(r);
      const dt = await T(p[0], 'Admin/Body', 'Admin:muted', 'dt'); r.appendChild(dt); dt.resize(130, dt.height); dt.textAutoResize = 'HEIGHT';
      const dd = typeof p[1] === 'string' ? await T(p[1], p[2] || 'Admin/Body Strong', 'Admin:text', 'dd') : p[1];
      r.appendChild(dd); if (dd.type === 'TEXT') fillW(dd);
    }
  }
  async function overlayBase(s) {
    const scrim = figma.createRectangle(); scrim.name = 'Scrim'; s.appendChild(scrim); scrim.layoutPositioning = 'ABSOLUTE';
    scrim.x = 0; scrim.y = 0; scrim.resize(1440, s.height); scrim.fills = [{ type: 'SOLID', color: { r: 0.04, g: 0.05, b: 0.09 }, opacity: 0.45 }]; scrim.opacity = 0;
    scrim.constraints = { horizontal: 'STRETCH', vertical: 'STRETCH' };
    return scrim;
  }

  // ---------------- A01 · Tổng quan ----------------
  const d = await screen('A01 · Tổng quan', 'index', 'ADMIN', 'Tổng quan hệ thống', 'Sức khỏe các service và số liệu đặt vé, lấy trực tiếp qua API của từng service');
  d.acts.appendChild(btn(C.btnS, 'Làm mới'));
  statsRow(d.m, [['Phim', '5', 'Movie Service'], ['Suất chiếu', '6', 'Showtime Service'], ['Người dùng', '3', '1 quản trị viên'], ['Đơn đặt vé', '4', '2 đơn đã thanh toán'], ['Doanh thu', '360.000 đ', 'Tổng các đơn PAID']]);
  const healthNote = await T('6/6 service đang chạy · cập nhật 10:44:36', 'Admin/Small', 'Admin:muted', 'Updated');
  const hc = await card('Trạng thái 6 service', 'Trạng thái 6 service', healthNote); d.m.appendChild(hc); fillW(hc);
  const SVC = [['movie', 'Movie', 'TV1 · Python', 'Cổng 5001 · movie_db · MySQL · 9 ms'], ['showtime', 'Showtime', 'TV2 · PHP', 'Cổng 5002 · showtime_db · MySQL · 12 ms'], ['user', 'User', 'TV3 · Java', 'Cổng 5003 · user_db · MySQL · 8 ms'],
    ['booking', 'Booking', 'TV4 · C# .NET 8', 'Cổng 5004 · booking_db · MySQL · 11 ms'], ['payment', 'Payment', 'TV5 · Node.js', 'Cổng 5005 · payment_db · MongoDB · 7 ms'], ['notification', 'Notification', 'TV6 · Go', 'Cổng 5006 · notification_db · MySQL · 6 ms']];
  for (let i = 0; i < 2; i++) {
    const r = row(hc, 14); r.name = 'Services ' + (i + 1);
    for (const s of SVC.slice(i * 3, i * 3 + 3)) {
      const c = C.svcUp.createInstance(); c.setProperties({ [K.svc]: s[1], [K.own]: s[2], [K.meta]: s[3], [K.svcIcon]: IC[s[0]] }); c.name = 'Service / ' + s[1];
      r.appendChild(c); c.layoutSizingHorizontal = 'FILL';
    }
  }
  const cols = row(d.m, 18); cols.name = 'Columns'; cols.counterAxisAlignItems = 'MIN';
  const seeAll = await T('Xem tất cả →', 'Admin/Body Strong', 'Admin:primary', 'See all');
  const rc = await card('Đơn đặt vé gần đây', 'Đơn đặt vé gần đây', seeAll); cols.appendChild(rc); rc.layoutSizingHorizontal = 'FILL'; rc.itemSpacing = 0;
  for (const b of BOOKINGS) {
    const r = A('HORIZONTAL', { name: 'Recent #' + b[0], itemSpacing: 12, counterAxisAlignItems: 'CENTER', paddingTop: 10, paddingBottom: 10 }); sideStroke(r, 'Admin:line', 'bottom');
    rc.appendChild(r); fillW(r);
    r.appendChild(await T('#' + b[0], 'Admin/Mono', 'Admin:muted', 'Code'));
    const mv = A('HORIZONTAL', { name: 'Movie', itemSpacing: 10, counterAxisAlignItems: 'CENTER' }); mv.appendChild(thumb(b[2]));
    const mt = A('VERTICAL', { name: 'Text' }); mt.appendChild(await T(b[2], 'Admin/Body Strong', 'Admin:text', 'Title')); mt.appendChild(await T(b[1], 'Admin/Small', 'Admin:muted', 'User')); mv.appendChild(mt);
    r.appendChild(mv); mv.layoutSizingHorizontal = 'FILL';
    const sw = A('HORIZONTAL', { name: 'Seats', itemSpacing: 4 }); for (const s of b[4]) sw.appendChild(seatTag(s)); r.appendChild(sw);
    const tot = await T(b[5], 'Admin/Body', 'Admin:text', 'Total'); tot.textAlignHorizontal = 'RIGHT'; r.appendChild(tot); tot.resize(96, tot.height); tot.textAutoResize = 'HEIGHT';
    const bw = A('HORIZONTAL', { name: 'Status', primaryAxisAlignItems: 'MAX' }); bw.appendChild(badge(b[6])); r.appendChild(bw); width(bw, 130);
  }
  const right = A('VERTICAL', { name: 'Right', itemSpacing: 18 }); cols.appendChild(right); width(right, 420);
  const sc = await card('Tình trạng đơn đặt vé', 'Tình trạng đơn đặt vé'); right.appendChild(sc); fillW(sc);
  const meter = A('HORIZONTAL', { name: 'Meter', itemSpacing: 2, cornerRadius: 6, clipsContent: true }); meter.fills = [P('Admin:card-2')];
  for (const s of [['PAID', 190, 'Admin:status-paid'], ['PENDING', 94, 'Admin:status-pending'], ['CANCELLED', 94, 'Admin:status-cancelled']]) {
    const seg = figma.createRectangle(); seg.name = s[0]; seg.resize(s[1], 12); seg.fills = [P(s[2])]; meter.appendChild(seg);
  }
  sc.appendChild(meter);
  const lg = A('HORIZONTAL', { name: 'Legend', layoutWrap: 'WRAP', itemSpacing: 20, counterAxisSpacing: 8 }); sc.appendChild(lg); fillW(lg);
  for (const s of [['PAID', 'Admin:status-paid', 2, '50%'], ['PENDING', 'Admin:status-pending', 1, '25%'], ['CANCELLED', 'Admin:status-cancelled', 1, '25%']]) {
    const it = A('HORIZONTAL', { name: s[0], itemSpacing: 8, counterAxisAlignItems: 'CENTER' });
    const sw = figma.createRectangle(); sw.resize(10, 10); sw.cornerRadius = 3; sw.fills = [P(s[1])]; it.appendChild(sw);
    it.appendChild(await T(ST[s[0]], 'Admin/Body', 'Admin:text-2', 'Label')); it.appendChild(await T(String(s[2]), 'Admin/Body Strong', 'Admin:text', 'Count')); it.appendChild(await T(s[3], 'Admin/Small', 'Admin:muted', 'Pct'));
    lg.appendChild(it);
  }
  const fc = await card('Luồng đặt vé', 'Luồng đặt vé'); right.appendChild(fc); fillW(fc);
  const flow = A('HORIZONTAL', { name: 'Flow', layoutWrap: 'WRAP', itemSpacing: 8, counterAxisSpacing: 8, counterAxisAlignItems: 'CENTER' }); fc.appendChild(flow); fillW(flow);
  const nodes = ['Client', '→', 'Booking', '→', 'User', '→', 'Movie', '→', 'Showtime', '→', 'Lưu đơn PENDING', '→', 'Payment', '→', 'PAID / CANCELLED', '→', 'Notification'];
  for (const n of nodes) {
    if (n === '→') { flow.appendChild(await T('→', 'Admin/Body', 'Admin:muted', 'Arrow')); continue; }
    const main = n === 'Booking' || n === 'Payment';
    const b = A('HORIZONTAL', { name: n, cornerRadius: 8 }); pad(b, 6, 11);
    b.fills = [P(main ? 'Admin:primary' : 'Admin:card-2')]; stroke(b, main ? 'Admin:primary' : 'Admin:line-2');
    b.appendChild(await T(n, 'Admin/Body Strong', main ? 'Admin:primary-ink' : 'Admin:text', 'Label')); flow.appendChild(b);
  }
  const fnote = await T('Booking là điều phối duy nhất. Các trang Admin gọi trực tiếp từng service; không service nào đọc CSDL của service khác.', 'Admin/Small', 'Admin:muted', 'Note'); fc.appendChild(fnote); fillW(fnote);

  // ---------------- A02 · Đặt vé (+ A03 ngăn chi tiết) ----------------
  const b = await screen('A02 · Quản lý đặt vé', 'booking', 'BOOKING SERVICE · TV4', 'Quản lý đặt vé', 'Booking Service · cổng 5004 · booking_db (TV4) — điều phối User, Movie, Showtime, Payment, Notification');
  b.acts.appendChild(btn(C.btnS, 'Làm mới')); b.acts.appendChild(btn(C.btnP, '+ Đặt vé thử'));
  statsRow(b.m, [['Số đơn', '4', ' '], ['Đã thanh toán', '2', '360.000 đ'], ['Chờ thanh toán', '1', ' '], ['Đã hủy', '1', 'Thanh toán thất bại / service sập']]);
  const tb = A('HORIZONTAL', { name: 'Toolbar', itemSpacing: 8, counterAxisAlignItems: 'CENTER', cornerRadius: 12 }); pad(tb, 12); tb.fills = [P('Admin:card')]; stroke(tb, 'Admin:line');
  b.m.appendChild(tb); fillW(tb);
  for (const f of [['Tất cả trạng thái  ▾', 180], ['Username', 200]]) {
    const box = A('HORIZONTAL', { name: f[0], cornerRadius: 8, counterAxisAlignItems: 'CENTER' }); pad(box, 8, 11); box.fills = [P('Admin:card')]; stroke(box, 'Admin:line-2');
    box.appendChild(await T(f[0], 'Admin/Body', f[0] === 'Username' ? 'Admin:muted' : 'Admin:text', 'Value')); tb.appendChild(box); width(box, f[1]);
  }
  tb.appendChild(btn(C.btnS, 'Lọc')); tb.appendChild(btn(C.btnG, 'Xóa lọc'));
  const tc = await card('Danh sách đơn'); tc.itemSpacing = 0; b.m.appendChild(tc); fillW(tc);
  const tt = A('HORIZONTAL', { name: 'Table tools', primaryAxisAlignItems: 'SPACE_BETWEEN', counterAxisAlignItems: 'CENTER', paddingBottom: 12 });
  const srch = C.search.createInstance(); srch.setProperties({ [K.ph]: 'Tìm theo mã, người đặt, phim, ghế...' }); tt.appendChild(srch);
  tt.appendChild(await T('4 bản ghi', 'Admin/Small', 'Admin:muted', 'Count')); tc.appendChild(tt); fillW(tt);
  tc.appendChild(C.bHead.createInstance());
  const rows = [];
  for (const bk of BOOKINGS) {
    const r = C.bRow.createInstance(); r.name = 'Booking / #' + bk[0];
    r.setProperties({ [K.bCode]: '#' + bk[0], [K.bUser]: bk[1], [K.bMovie]: bk[2], [K.bSt]: 'Suất #' + bk[3], [K.bTot]: bk[5], [K.bCr]: bk[7] });
    const th = r.findOne((n) => n.type === 'INSTANCE' && n.name === 'Thumb'); if (th) { th.setProperties({ [K.init]: bk[2].charAt(0) }); th.fills = [grad(bk[2])]; }
    const seats = r.findAll((n) => n.type === 'INSTANCE' && n.name.indexOf('Seat ') === 0);
    seats.forEach((s, i) => { if (i < bk[4].length) s.setProperties({ [K.seat]: bk[4][i] }); else s.visible = false; });
    const stI = r.findOne((n) => n.type === 'INSTANCE' && n.name === 'Status'); if (stI) stI.setProperties({ Status: bk[6] });
    tc.appendChild(r); rows.push(r);
  }
  // Ngăn chi tiết (đóng: nằm ngoài khung bên phải; mở: x = 960) — Smart Animate trượt vào
  const scrimB = await overlayBase(b.s);
  const dr = A('VERTICAL', { name: 'Drawer' }); dr.fills = [P('Admin:card')]; sideStroke(dr, 'Admin:line', 'left'); await dr.setEffectStyleIdAsync(ES['Admin/Overlay'].id);
  b.s.appendChild(dr); dr.layoutPositioning = 'ABSOLUTE'; dr.resize(480, b.s.height); dr.primaryAxisSizingMode = 'FIXED'; dr.counterAxisSizingMode = 'FIXED'; dr.x = 1440; dr.y = 0;
  dr.constraints = { horizontal: 'MAX', vertical: 'STRETCH' };
  const dh = A('HORIZONTAL', { name: 'Drawer head', primaryAxisAlignItems: 'SPACE_BETWEEN', counterAxisAlignItems: 'CENTER' }); pad(dh, 18, 20); sideStroke(dh, 'Admin:line', 'bottom');
  const dht = await T('Đơn đặt vé #4', 'Admin/H3', 'Admin:text', 'Title'); dht.fontSize = 17; dh.appendChild(dht);
  const closeB = A('HORIZONTAL', { name: 'Close', cornerRadius: 8, primaryAxisAlignItems: 'CENTER', counterAxisAlignItems: 'CENTER' }); pad(closeB, 6); closeB.appendChild((await N('5:58')).createInstance());
  dh.appendChild(closeB); dr.appendChild(dh); fillW(dh);
  const body = A('VERTICAL', { name: 'Drawer body', itemSpacing: 6 }); pad(body, 20); dr.appendChild(body); fillW(body);
  const h4 = async (t, first) => { const w = A('HORIZONTAL', { name: 'Section', paddingTop: first ? 0 : 18, paddingBottom: 6 }); w.appendChild(await T(t, 'Admin/Overline', 'Admin:muted', 'Heading')); body.appendChild(w); };
  await h4('THÔNG TIN ĐƠN', true);
  const seatsDd = A('HORIZONTAL', { name: 'Seats', itemSpacing: 4 }); seatsDd.appendChild(seatTag('D5')); seatsDd.appendChild(seatTag('D6'));
  await dl(body, [['Trạng thái', badge('PAID')], ['Người đặt', 'user1'], ['Ghế', seatsDd], ['Tổng tiền', '180.000 đ'], ['Tạo lúc', '2026-10-13 09:00:00', 'Admin/Body']]);
  await h4('PHIM & SUẤT CHIẾU');
  await dl(body, [['Phim', 'Avengers: Endgame  #1'], ['Rạp', 'CGV Vincom Đồng Khởi · P1'], ['Giờ chiếu', '2026-10-10 18:00:00', 'Admin/Body'], ['Giá / ghế', '90.000 đ']]);
  await h4('GIAO DỊCH THANH TOÁN (PAYMENT SERVICE)');
  await dl(body, [['Mã giao dịch', '6acdb2a4dd0910faeeebe3f1', 'Admin/Mono'], ['Số tiền', '180.000 đ'], ['Phương thức', badge('Neutral', 'MOMO')], ['Kết quả', badge('PAID')], ['Thời điểm', '2026-10-13 02:00:01', 'Admin/Body']]);
  await h4('TIẾN TRÌNH');
  for (const t of [['status-paid', 'Tạo đơn (PENDING)', '2026-10-13 09:00:00'], ['status-paid', 'Thanh toán MOMO: PAID', '2026-10-13 02:00:01 · 180.000 đ'], ['status-paid', 'Trạng thái đơn: Đã thanh toán', ''], ['status-paid', 'Gửi thông báo EMAIL', '2026-10-13 02:00:02']]) {
    const li = A('HORIZONTAL', { name: 'Step', itemSpacing: 10, paddingBottom: 6 });
    const dot = figma.createEllipse(); dot.resize(10, 10); dot.fills = [P('Admin:' + t[0])];
    const dw = A('VERTICAL', { name: 'Dot', paddingTop: 5 }); dw.appendChild(dot); li.appendChild(dw);
    const tx = A('VERTICAL', { name: 'Text' }); tx.appendChild(await T(t[1], 'Admin/Body Strong', 'Admin:text', 'Title')); if (t[2]) tx.appendChild(await T(t[2], 'Admin/Small', 'Admin:muted', 'Time'));
    li.appendChild(tx); body.appendChild(li);
  }
  const bOpen = b.s.clone(); bOpen.name = 'A03 · Đặt vé — ngăn chi tiết đơn'; bOpen.x = b.s.x; bOpen.y = b.s.y + b.s.height + 160;
  byName(bOpen, 'Drawer').x = 960; byName(bOpen, 'Scrim').opacity = 1;

  // ---------------- A04 · Phim (+ A05 form thêm phim) ----------------
  const mv = await screen('A04 · Quản lý phim', 'movie', 'MOVIE SERVICE · TV1', 'Quản lý phim', 'Movie Service · cổng 5001 · movie_db (TV1)');
  mv.acts.appendChild(btn(C.btnS, 'Làm mới')); const addBtn = btn(C.btnP, '+ Thêm phim'); mv.acts.appendChild(addBtn);
  statsRow(mv.m, [['Tổng số phim', '5', ' '], ['Thể loại', '4', ' '], ['Thời lượng trung bình', '139 phút', ' ']]);
  const mc = await card('Danh sách phim'); mc.itemSpacing = 0; mv.m.appendChild(mc); fillW(mc);
  const mt2 = A('HORIZONTAL', { name: 'Table tools', primaryAxisAlignItems: 'SPACE_BETWEEN', counterAxisAlignItems: 'CENTER', paddingBottom: 12 });
  const s2 = C.search.createInstance(); s2.setProperties({ [K.ph]: 'Tìm theo tên, thể loại...' }); mt2.appendChild(s2);
  mt2.appendChild(await T('5 bản ghi', 'Admin/Small', 'Admin:muted', 'Count')); mc.appendChild(mt2); fillW(mt2);
  mc.appendChild(C.mHead.createInstance());
  for (const m of MOVIES) {
    const r = C.mRow.createInstance(); r.name = 'Movie / #' + m[0];
    r.setProperties({ [K.mId]: '#' + m[0], [K.mTitle]: m[1], [K.mDur]: m[3] + ' phút', [K.mPos]: 'poster' + m[0] + '.jpg', [K.mCr]: '2026-10-01 09:00:00' });
    const th = r.findOne((n) => n.type === 'INSTANCE' && n.name === 'Thumb'); if (th) { th.setProperties({ [K.init]: m[1].charAt(0) }); th.fills = [grad(m[1])]; }
    const g = r.findOne((n) => n.type === 'INSTANCE' && n.name === 'Genre'); if (g) g.findOne((n) => n.type === 'TEXT').characters = m[2];
    mc.appendChild(r);
  }
  const scrimM = await overlayBase(mv.s);
  const modal = A('VERTICAL', { name: 'Modal', itemSpacing: 0, cornerRadius: 14 }); pad(modal, 22); modal.fills = [P('Admin:card')]; stroke(modal, 'Admin:line');
  await modal.setEffectStyleIdAsync(ES['Admin/Overlay'].id);
  mv.s.appendChild(modal); modal.layoutPositioning = 'ABSOLUTE'; width(modal, 480);
  const mh = await T('Thêm phim', 'Admin/H3', 'Admin:text', 'Title'); mh.fontSize = 18; modal.appendChild(mh);
  const msub = await T('Dữ liệu được lưu trong movie_db qua Movie Service.', 'Admin/Small', 'Admin:muted', 'Sub'); modal.appendChild(msub); modal.appendChild(gap(18));
  for (const f of [['Tên phim *', 'Dune: Part Two'], ['Thể loại *', 'Khoa học viễn tưởng'], ['Thời lượng (phút) *', '166'], ['Poster', 'poster6.jpg']]) {
    const ff = C.ffText.createInstance(); ff.setProperties({ [K.ffL]: f[0], [K.ffV]: f[1] }); modal.appendChild(ff); ff.layoutSizingHorizontal = 'FILL'; modal.appendChild(gap(14));
  }
  const hint = await T('Client hiển thị ảnh nếu poster là URL; nếu là tên file thì dùng ảnh bìa tự sinh.', 'Admin/Small', 'Admin:muted', 'Hint'); modal.appendChild(hint); fillW(hint);
  const ma = A('HORIZONTAL', { name: 'Actions', itemSpacing: 8, primaryAxisAlignItems: 'MAX', paddingTop: 20 }); modal.appendChild(ma); fillW(ma);
  ma.appendChild(btn(C.btnS, 'Hủy')); ma.appendChild(btn(C.btnP, 'Thêm phim'));
  modal.x = (1440 - 480) / 2; modal.y = Math.round((900 - modal.height) / 2) + 16; modal.opacity = 0;
  const mOpen = mv.s.clone(); mOpen.name = 'A05 · Phim — form thêm phim'; mOpen.x = mv.s.x; mOpen.y = mv.s.y + mv.s.height + 160;
  const mm = byName(mOpen, 'Modal'); mm.opacity = 1; mm.y = mm.y - 16; byName(mOpen, 'Scrim').opacity = 1;

  // ---------------- Prototype Admin ----------------
  const SCR = { index: d.s, booking: b.s, movie: mv.s };
  for (const s of [d.s, b.s, bOpen, mv.s, mOpen]) {
    const sb = s.children[0];
    for (const k in SCR) if (SCR[k] !== s) await click(byName(sb, 'Nav / ' + k), SCR[k].id, 'fade');
  }
  await click(byName(d.s, 'See all'), b.s.id, 'fade');
  for (const r of rows) await click(r, bOpen.id, 'open');
  await click(byName(bOpen, 'Scrim'), b.s.id, 'close');
  await click(byName(bOpen, 'Close'), b.s.id, 'close');
  await click(addBtn, mOpen.id, 'open');
  await click(byName(mOpen, 'Scrim'), mv.s.id, 'close');
  const modalOpen = byName(mOpen, 'Modal');
  await click(btnLabel(modalOpen, 'Hủy'), mv.s.id, 'close');
  await click(btnLabel(modalOpen, 'Thêm phim'), mv.s.id, 'fade');
  page.flowStartingPoints = [{ nodeId: d.s.id, name: 'Admin — Tổng quan' }];
  figma.viewport.scrollAndZoomIntoView([d.s, b.s, bOpen, mv.s, mOpen]);
}

// ---------- Chạy ----------
(async () => {
  try {
    await setup();
    if (figma.command === 'admin') await admin(); else await client();
    const msg = '✅ Xong: ' + report.ok + ' tương tác' + (report.fail.length ? ' · ⚠ ' + report.fail.length + ' lỗi (xem Console)' : '');
    if (report.fail.length) console.warn('SOA Cinema Builder — lỗi:\n' + report.fail.join('\n'));
    figma.closePlugin(msg);
  } catch (e) {
    console.error(e);
    figma.closePlugin('❌ ' + (e && e.message ? e.message : String(e)));
  }
})();
