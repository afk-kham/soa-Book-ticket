/**
 * barcode.js — Bộ sinh mã vạch 1D Code 128 (Code Set B) thuần JavaScript.
 * Render SVG sắc nét, chạy hoàn toàn offline, không phụ thuộc thư viện ngoài.
 */
(function (root, factory) {
  if (typeof exports === "object" && typeof module !== "undefined") {
    module.exports = factory();
  } else {
    root.Barcode = factory();
  }
})(typeof self !== "undefined" ? self : this, function () {
  "use strict";

  // Mẫu vạch 0-106 của Code 128 (mỗi ký tự gồm 3 thanh và 3 khoảng trắng, trừ Stop có 7 phần tử)
  var PATTERNS = [
    "212222", "222122", "222221", "121223", "121322", "131222", "122213", "122312", "132212", "221213",
    "221312", "231212", "112232", "122132", "122231", "113222", "123122", "123221", "223211", "221132",
    "221231", "213212", "223112", "312131", "311222", "321122", "321221", "312212", "322112", "322211",
    "212123", "212321", "232121", "111323", "131123", "131321", "112313", "132113", "132311", "211313",
    "231113", "231311", "112133", "112331", "132131", "113123", "113321", "133121", "313121", "211331",
    "231131", "213113", "213311", "213131", "311123", "311321", "331121", "312113", "312311", "332111",
    "314111", "221411", "431111", "111224", "111422", "121124", "121421", "141122", "141221", "112214",
    "112412", "122114", "122411", "142112", "142211", "241211", "221114", "413111", "241112", "134111",
    "111242", "121142", "121241", "114212", "124112", "124211", "411212", "421112", "421211", "212141",
    "214121", "412121", "111143", "111341", "131141", "114113", "114311", "411113", "411311", "113141",
    "114131", "311141", "411131", "211412", "211214", "211232", "2331112"
  ];

  var START_B = 104;
  var STOP = 106;

  /**
   * Mã hóa chuỗi ký tự theo chuẩn Code 128 Set B.
   */
  function encode(text) {
    text = String(text || "").trim();
    if (!text) text = "SOA000000";

    var codes = [START_B];
    var checksum = START_B;

    for (var i = 0; i < text.length; i++) {
      var charCode = text.charCodeAt(i);
      var val = (charCode >= 32 && charCode <= 126) ? (charCode - 32) : 0;
      codes.push(val);
      checksum += val * (i + 1);
    }

    var checkVal = checksum % 103;
    codes.push(checkVal);
    codes.push(STOP);

    var patternStr = "";
    for (var j = 0; j < codes.length; j++) {
      patternStr += PATTERNS[codes[j]];
    }

    // Chuyển chuỗi độ rộng thành chuỗi module bit '1' và '0'
    var modules = "";
    var isBar = true;
    for (var k = 0; k < patternStr.length; k++) {
      var w = parseInt(patternStr.charAt(k), 10);
      for (var b = 0; b < w; b++) {
        modules += isBar ? "1" : "0";
      }
      isBar = !isBar;
    }

    return {
      text: text,
      codes: codes,
      checkVal: checkVal,
      modules: modules
    };
  }

  /**
   * Sinh mã SVG cho mã vạch Code 128.
   * @param {string} text Nội dung cần tạo mã (ví dụ "SOA000017")
   * @param {Object} opts Tùy chọn hiển thị
   */
  function svg(text, opts) {
    opts = opts || {};
    var res = encode(text);
    var modules = res.modules;

    var barWidth = Number(opts.barWidth) || 2;
    var barHeight = Number(opts.height) || 55;
    var quietZone = Number(opts.quietZone) || 12;
    var showText = opts.showText !== false;
    var fontSize = Number(opts.fontSize) || 13;
    var textGap = 5;

    var totalModules = modules.length;
    var barcodeWidth = totalModules * barWidth;
    var fullWidth = barcodeWidth + quietZone * 2 * barWidth;
    var fullHeight = barHeight + (showText ? fontSize + textGap + 8 : 8);

    var rects = [];
    var curX = quietZone * barWidth;

    for (var i = 0; i < totalModules; i++) {
      if (modules.charAt(i) === "1") {
        // Gom các module liền nhau thành một thanh rect duy nhất để tối ưu dung lượng SVG
        var run = 1;
        while (i + 1 < totalModules && modules.charAt(i + 1) === "1") {
          run++;
          i++;
        }
        rects.push('<rect x="' + curX + '" y="4" width="' + (run * barWidth) + '" height="' + barHeight + '" fill="#000000"/>');
        curX += run * barWidth;
      } else {
        curX += barWidth;
      }
    }

    var textElement = "";
    if (showText) {
      var textY = 4 + barHeight + textGap + fontSize;
      textElement = '<text x="' + (fullWidth / 2) + '" y="' + textY +
        '" fill="#111827" font-family="ui-monospace,SFMono-Regular,Consolas,\'Liberation Mono\',Menlo,monospace"' +
        ' font-size="' + fontSize + 'px" font-weight="700" letter-spacing="3px" text-anchor="middle">' +
        escapeHtml(res.text) + '</text>';
    }

    return '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ' + fullWidth + ' ' + fullHeight + '"' +
      ' width="100%" height="' + fullHeight + '" class="' + (opts.className || "barcode-svg") + '"' +
      ' style="max-width:' + fullWidth + 'px;background:#ffffff;border-radius:6px;padding:2px;display:block;margin:0 auto"' +
      ' shape-rendering="crispEdges" role="img" aria-label="Mã vạch soát vé: ' + escapeHtml(res.text) + '">' +
      '<rect width="100%" height="100%" fill="#ffffff"/>' +
      rects.join("") +
      textElement +
      '</svg>';
  }

  function escapeHtml(s) {
    return String(s || "").replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
  }

  return {
    encode: encode,
    svg: svg
  };
});

