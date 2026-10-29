/* Sinh mã QR (ISO/IEC 18004) ngay trên trình duyệt — không cần thư viện ngoài, không cần mạng.
   Chế độ byte (UTF-8), mức sửa lỗi M, tự chọn phiên bản 1–40 và mặt nạ tốt nhất.
   Thuật toán theo bản tham khảo "QR Code generator" của Project Nayuki (MIT).
   Dùng: QR.svg("nội dung", { margin: 2 }) -> chuỗi <svg>;  QR.vietQR({...}) -> nội dung chuẩn VietQR (NAPAS 247). */
(function () {
  var ECC_PER_BLOCK = {   // [phiên bản] -> số codeword sửa lỗi mỗi khối
    L: [-1, 7, 10, 15, 20, 26, 18, 20, 24, 30, 18, 20, 24, 26, 30, 22, 24, 28, 30, 28, 28, 28, 28, 30, 30, 26, 28, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30],
    M: [-1, 10, 16, 26, 18, 24, 16, 18, 22, 22, 26, 30, 22, 22, 24, 24, 28, 28, 26, 26, 26, 26, 28, 28, 28, 28, 28, 28, 28, 28, 28, 28, 28, 28, 28, 28, 28, 28, 28, 28, 28]
  };
  var NUM_BLOCKS = {
    L: [-1, 1, 1, 1, 1, 1, 2, 2, 2, 2, 4, 4, 4, 4, 4, 6, 6, 6, 6, 7, 8, 8, 9, 9, 10, 12, 12, 12, 13, 14, 15, 16, 17, 18, 19, 19, 20, 21, 22, 24, 25],
    M: [-1, 1, 1, 1, 2, 2, 4, 4, 4, 5, 5, 5, 8, 9, 9, 10, 10, 11, 13, 14, 16, 17, 17, 18, 20, 21, 23, 25, 26, 28, 29, 31, 33, 35, 37, 38, 40, 43, 45, 47, 49]
  };
  var FORMAT_BITS = { L: 1, M: 0 };

  function rawDataModules(ver) {
    var r = (16 * ver + 128) * ver + 64;
    if (ver >= 2) { var na = Math.floor(ver / 7) + 2; r -= (25 * na - 10) * na - 55; if (ver >= 7) r -= 36; }
    return r;
  }
  function dataCodewords(ver, ecl) { return Math.floor(rawDataModules(ver) / 8) - ECC_PER_BLOCK[ecl][ver] * NUM_BLOCKS[ecl][ver]; }

  // ---- Reed–Solomon trên GF(2^8), đa thức 0x11D
  function gfMul(x, y) { var z = 0; for (var i = 7; i >= 0; i--) { z = (z << 1) ^ ((z >>> 7) * 0x11D); z ^= ((y >>> i) & 1) * x; } return z; }
  function rsDivisor(degree) {
    var r = []; for (var i = 0; i < degree - 1; i++) r.push(0); r.push(1);
    var root = 1;
    for (i = 0; i < degree; i++) {
      for (var j = 0; j < r.length; j++) { r[j] = gfMul(r[j], root); if (j + 1 < r.length) r[j] ^= r[j + 1]; }
      root = gfMul(root, 0x02);
    }
    return r;
  }
  function rsRemainder(data, div) {
    var r = div.map(function () { return 0; });
    data.forEach(function (b) {
      var f = b ^ r.shift(); r.push(0);
      div.forEach(function (c, i) { r[i] ^= gfMul(c, f); });
    });
    return r;
  }

  function utf8(s) {
    var out = [], b = unescape(encodeURIComponent(s));
    for (var i = 0; i < b.length; i++) out.push(b.charCodeAt(i));
    return out;
  }

  function encode(text, ecl) {
    ecl = ecl || "M";
    var bytes = utf8(text), ver, cap;
    for (ver = 1; ver <= 40; ver++) {
      cap = dataCodewords(ver, ecl) * 8;
      if (4 + (ver < 10 ? 8 : 16) + bytes.length * 8 <= cap) break;
    }
    if (ver > 40) throw new Error("Nội dung quá dài để tạo mã QR");

    // ---- Chuỗi bit dữ liệu: mode byte (0100) + độ dài + dữ liệu + terminator + đệm
    var bits = [];
    function put(val, len) { for (var i = len - 1; i >= 0; i--) bits.push((val >>> i) & 1); }
    put(4, 4); put(bytes.length, ver < 10 ? 8 : 16); bytes.forEach(function (b) { put(b, 8); });
    put(0, Math.min(4, cap - bits.length));
    put(0, (8 - bits.length % 8) % 8);
    for (var pad = 0xEC; bits.length < cap; pad ^= 0xEC ^ 0x11) put(pad, 8);
    var data = [];
    for (var i = 0; i < bits.length; i += 8) { var v = 0; for (var k = 0; k < 8; k++) v = (v << 1) | bits[i + k]; data.push(v); }

    // ---- Chia khối, thêm mã sửa lỗi, xen kẽ
    var nb = NUM_BLOCKS[ecl][ver], eccLen = ECC_PER_BLOCK[ecl][ver], raw = Math.floor(rawDataModules(ver) / 8);
    var nShort = nb - raw % nb, shortLen = Math.floor(raw / nb), div = rsDivisor(eccLen), blocks = [];
    for (i = 0, k = 0; i < nb; i++) {
      var dat = data.slice(k, k + shortLen - eccLen + (i < nShort ? 0 : 1)); k += dat.length;
      var ecc = rsRemainder(dat, div);
      if (i < nShort) dat.push(0);
      blocks.push(dat.concat(ecc));
    }
    var cw = [];
    for (i = 0; i < blocks[0].length; i++) blocks.forEach(function (b, j) { if (i !== shortLen - eccLen || j >= nShort) cw.push(b[i]); });

    // ---- Ma trận + vùng chức năng
    var size = ver * 4 + 17, mod = [], fn = [];
    for (i = 0; i < size; i++) { mod.push(new Array(size).fill(false)); fn.push(new Array(size).fill(false)); }
    function setF(x, y, dark) { mod[y][x] = dark; fn[y][x] = true; }
    for (i = 0; i < size; i++) { setF(6, i, i % 2 === 0); setF(i, 6, i % 2 === 0); }
    function finder(cx, cy) {
      for (var dy = -4; dy <= 4; dy++) for (var dx = -4; dx <= 4; dx++) {
        var d = Math.max(Math.abs(dx), Math.abs(dy)), x = cx + dx, y = cy + dy;
        if (x >= 0 && x < size && y >= 0 && y < size) setF(x, y, d !== 2 && d !== 4);
      }
    }
    finder(3, 3); finder(size - 4, 3); finder(3, size - 4);
    var align = [];
    if (ver > 1) {
      var na = Math.floor(ver / 7) + 2, step = Math.floor((ver * 8 + na * 3 + 5) / (na * 4 - 4)) * 2;
      align = [6]; for (var pos = size - 7; align.length < na; pos -= step) align.splice(1, 0, pos);
    }
    align.forEach(function (ay, ii) {
      align.forEach(function (ax, jj) {
        var last = align.length - 1;
        if ((ii === 0 && jj === 0) || (ii === 0 && jj === last) || (ii === last && jj === 0)) return;
        for (var dy = -2; dy <= 2; dy++) for (var dx = -2; dx <= 2; dx++) setF(ax + dx, ay + dy, Math.max(Math.abs(dx), Math.abs(dy)) !== 1);
      });
    });
    function drawFormat(mask) {
      var d = FORMAT_BITS[ecl] << 3 | mask, rem = d;
      for (var i = 0; i < 10; i++) rem = (rem << 1) ^ ((rem >>> 9) * 0x537);
      var b = (d << 10 | rem) ^ 0x5412, bit = function (i) { return ((b >>> i) & 1) !== 0; };
      for (i = 0; i <= 5; i++) setF(8, i, bit(i));
      setF(8, 7, bit(6)); setF(8, 8, bit(7)); setF(7, 8, bit(8));
      for (i = 9; i < 15; i++) setF(14 - i, 8, bit(i));
      for (i = 0; i < 8; i++) setF(size - 1 - i, 8, bit(i));
      for (i = 8; i < 15; i++) setF(8, size - 15 + i, bit(i));
      setF(8, size - 8, true);
    }
    drawFormat(0);
    if (ver >= 7) {
      var rem = ver; for (i = 0; i < 12; i++) rem = (rem << 1) ^ ((rem >>> 11) * 0x1F25);
      var vb = ver << 12 | rem;
      for (i = 0; i < 18; i++) { var c = ((vb >>> i) & 1) !== 0, a = size - 11 + i % 3, bb = Math.floor(i / 3); setF(a, bb, c); setF(bb, a, c); }
    }

    // ---- Đặt dữ liệu theo đường zigzag
    var n = 0;
    for (var right = size - 1; right >= 1; right -= 2) {
      if (right === 6) right = 5;
      for (var vert = 0; vert < size; vert++) for (var j = 0; j < 2; j++) {
        var x = right - j, up = ((right + 1) & 2) === 0, y = up ? size - 1 - vert : vert;
        if (!fn[y][x] && n < cw.length * 8) { mod[y][x] = ((cw[n >>> 3] >>> (7 - (n & 7))) & 1) !== 0; n++; }
      }
    }

    // ---- Chọn mặt nạ có điểm phạt thấp nhất
    function maskBit(m, x, y) {
      switch (m) {
        case 0: return (x + y) % 2 === 0;
        case 1: return y % 2 === 0;
        case 2: return x % 3 === 0;
        case 3: return (x + y) % 3 === 0;
        case 4: return (Math.floor(x / 3) + Math.floor(y / 2)) % 2 === 0;
        case 5: return x * y % 2 + x * y % 3 === 0;
        case 6: return (x * y % 2 + x * y % 3) % 2 === 0;
        default: return ((x + y) % 2 + x * y % 3) % 2 === 0;
      }
    }
    function applyMask(m) { for (var y = 0; y < size; y++) for (var x = 0; x < size; x++) if (!fn[y][x] && maskBit(m, x, y)) mod[y][x] = !mod[y][x]; }
    function penalty() {
      var p = 0, dark = 0, x, y;
      function line(get) {
        var run = 1, prev = get(0), s = "";
        for (var i = 0; i < size; i++) s += get(i) ? "1" : "0";
        for (i = 1; i < size; i++) {
          var c = get(i);
          if (c === prev) { run++; if (run === 5) p += 3; else if (run > 5) p++; } else { run = 1; prev = c; }
        }
        var re = /(?=(00001011101|10111010000))/g, m;
        s = "0000" + s + "0000";
        while ((m = re.exec(s))) { p += 40; re.lastIndex++; }
      }
      for (y = 0; y < size; y++) line(function (i) { return mod[y][i]; });
      for (x = 0; x < size; x++) line(function (i) { return mod[i][x]; });
      for (y = 0; y < size - 1; y++) for (x = 0; x < size - 1; x++) {
        var c = mod[y][x];
        if (c === mod[y][x + 1] && c === mod[y + 1][x] && c === mod[y + 1][x + 1]) p += 3;
      }
      for (y = 0; y < size; y++) for (x = 0; x < size; x++) if (mod[y][x]) dark++;
      var total = size * size;
      p += (Math.ceil(Math.abs(dark * 20 - total * 10) / total) - 1) * 10;
      return p;
    }
    var best = 0, bestP = Infinity;
    for (var m = 0; m < 8; m++) {
      applyMask(m); drawFormat(m);
      var pp = penalty(); if (pp < bestP) { bestP = pp; best = m; }
      applyMask(m);
    }
    applyMask(best); drawFormat(best);
    return { size: size, version: ver, mask: best, modules: mod };
  }

  /** Mã QR dạng SVG (nền trắng, chấm tối) — sắc nét ở mọi kích thước. */
  function svg(text, opts) {
    opts = opts || {};
    var q = encode(text, opts.ecl), m = opts.margin == null ? 2 : opts.margin, s = q.size + m * 2, d = "";
    for (var y = 0; y < q.size; y++) for (var x = 0; x < q.size; x++) if (q.modules[y][x]) d += "M" + (x + m) + " " + (y + m) + "h1v1h-1z";
    return '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ' + s + " " + s + '" shape-rendering="crispEdges" role="img" aria-label="' + (opts.label || "Mã QR") + '">' +
      '<rect width="' + s + '" height="' + s + '" fill="#fff"/><path d="' + d + '" fill="' + (opts.color || "#000") + '"/></svg>';
  }

  // ---- VietQR (chuẩn EMVCo / NAPAS 247): ứng dụng ngân hàng quét là điền sẵn người nhận, số tiền, nội dung
  function tlv(id, v) { v = String(v); return id + (v.length < 10 ? "0" : "") + v.length + v; }
  function crc16(s) {
    var crc = 0xFFFF;
    for (var i = 0; i < s.length; i++) {
      crc ^= s.charCodeAt(i) << 8;
      for (var k = 0; k < 8; k++) crc = crc & 0x8000 ? ((crc << 1) ^ 0x1021) & 0xFFFF : (crc << 1) & 0xFFFF;
    }
    return ("000" + crc.toString(16).toUpperCase()).slice(-4);
  }
  /** o = { bin: "970436", account: "0123456789", amount: 180000, content: "SOA123" } (content chỉ nên dùng A–Z, 0–9). */
  function vietQR(o) {
    var s = tlv("00", "01") + tlv("01", "12") +
      tlv("38", tlv("00", "A000000727") + tlv("01", tlv("00", o.bin) + tlv("01", o.account)) + tlv("02", "QRIBFTTA")) +
      tlv("53", "704") + (o.amount ? tlv("54", Math.round(o.amount)) : "") + tlv("58", "VN") +
      (o.content ? tlv("62", tlv("08", o.content)) : "") + "6304";
    return s + crc16(s);
  }

  window.QR = { encode: encode, svg: svg, vietQR: vietQR, _rs: { divisor: rsDivisor, remainder: rsRemainder }, _crc16: crc16 };
})();
