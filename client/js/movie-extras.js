/**
 * movie-extras.js — Metadata mở rộng cho danh mục phim SOA Cinema.
 * Bổ sung các trường giao diện (poster thật, backdrop, trailer YouTube đa nguồn, nhãn tuổi, mô tả)
 * mà không cần sửa đổi schema CSDL của Movie Service backend.
 */
(function (root, factory) {
  if (typeof exports === "object" && typeof module !== "undefined") {
    module.exports = factory();
  } else {
    var exp = factory();
    root.MOVIE_EXTRAS = exp.MOVIE_EXTRAS;
    root.mergeMovieExtras = exp.mergeMovieExtras;
    root.normalizeMovieKey = exp.normalizeMovieKey;
  }
})(typeof self !== "undefined" ? self : this, function () {
  "use strict";

  function normalizeKey(str) {
    return String(str || "")
      .trim()
      .toLowerCase()
      .normalize("NFD")
      .replace(/[\u0300-\u036f]/g, "")
      .replace(/[^a-z0-9]/g, "");
  }

  var MOVIE_EXTRAS = {
    "avengers-endgame": {
      slug: "avengers-endgame",
      title: "Avengers: Endgame",
      titleVi: "Biệt Đội Siêu Anh Hùng: Hồi Kết",
      posterUrl: "assets/posters/avengers-endgame.jpg",
      remotePosterUrl: "https://image.tmdb.org/t/p/w500/or06FN3Dka5tukK1e9sl16pB3iy.jpg",
      backdropUrl: "assets/backdrops/avengers-endgame.jpg",
      remoteBackdropUrl: "https://image.tmdb.org/t/p/w1280/7RyHsO4yDXtBv1zUU3mTpHeQ0d5.jpg",
      youtubeId: "TcMBFSGVi1c",
      youtubeIds: ["TcMBFSGVi1c", "0jNvJU52LvU", "eOrNdBpGMv8"],
      ageRating: "T13",
      genres: ["Hành động", "Phiêu lưu", "Khoa học viễn tưởng"],
      featured: true,
      description: "Sau thảm họa diệt vong do Thanos gây ra, các Avengers còn sống sót phải tập hợp lại một lần cuối cùng. Họ thực hiện chuyến du hành thời gian mạo hiểm nhằm đảo ngược cú búng tay và khôi phục sự sống cho toàn vũ trụ."
    },
    "inception": {
      slug: "inception",
      title: "Inception",
      titleVi: "Kẻ Đánh Cắp Giấc Mơ",
      posterUrl: "assets/posters/inception.jpg",
      remotePosterUrl: "https://image.tmdb.org/t/p/w500/oYuLEt3zVCKq57qu2F8dT7NIa6f.jpg",
      backdropUrl: "assets/backdrops/inception.jpg",
      remoteBackdropUrl: "https://image.tmdb.org/t/p/w1280/8ZTVqvKDQ8emSGUEMjsS4yHAwrp.jpg",
      youtubeId: "YoHD9XEInc0",
      youtubeIds: ["YoHD9XEInc0", "8hP9D6FlL6o", "CPTIgS670zY"],
      ageRating: "T16",
      genres: ["Khoa học viễn tưởng", "Hành động", "Giật gân"],
      featured: true,
      description: "Dom Cobb là một đạo chích bậc thầy chuyên đánh cắp các bí mật sâu kín nhất trong tiềm thức khi đối tượng đang ngủ say. Để chuộc lại cuộc đời tự do, anh nhận nhiệm vụ bất khả thi: cấy một ý niệm mới vào tâm trí người thừa kế tập đoàn đối thủ."
    },
    "parasite": {
      slug: "parasite",
      title: "Parasite",
      titleVi: "Ký Sinh Trùng",
      posterUrl: "assets/posters/parasite.jpg",
      remotePosterUrl: "https://image.tmdb.org/t/p/w500/7IiTTgloJzvGI1TAYymCfbfl3vT.jpg",
      backdropUrl: null,
      remoteBackdropUrl: null,
      youtubeId: "Wg_Ql89fWy4",
      youtubeIds: ["Wg_Ql89fWy4", "isOGD_7hNIY", "8VzB1V40VYA"],
      backupYoutubeId: "isOGD_7hNIY",
      ageRating: "T18",
      genres: ["Tâm lý", "Giật gân", "Hài đen"],
      featured: false,
      description: "Gia đình Kim nghèo khó sống chen chúc trong căn hộ bán hầm bẩn thỉu. Bằng sự mưu mẹo, từng thành viên lần lượt thâm nhập làm việc cho gia đình Park giàu có, khởi đầu cho chuỗi bi kịch phân hóa giai cấp đầy ám ảnh."
    },
    "mai": {
      slug: "mai",
      title: "Mai",
      titleVi: "Mai",
      posterUrl: "assets/posters/mai.jpg",
      remotePosterUrl: "https://upload.wikimedia.org/wikipedia/vi/3/36/Mai_2024_poster.jpg",
      backdropUrl: null,
      remoteBackdropUrl: null,
      youtubeId: "Yz96EBNwMGw",
      youtubeIds: ["Yz96EBNwMGw", "AUnLlwZ6q5Y", "N6YlC8_rX08"],
      ageRating: "T18",
      genres: ["Tâm lý", "Tình cảm"],
      featured: false,
      description: "Mai là một phụ nữ ngoài ba mươi làm nghề massage trị liệu, mang trên mình những vết sẹo quá khứ và định kiến xã hội. Cuộc đời cô rẽ hướng khi gặp gỡ Dương - chàng trai trẻ đào hoa quyết tâm theo đuổi tình yêu chân thành."
    },
    "coco": {
      slug: "coco",
      title: "Coco",
      titleVi: "Vùng Đất Linh Hồn",
      posterUrl: "assets/posters/coco.jpg",
      remotePosterUrl: "https://image.tmdb.org/t/p/w500/gEU2QniE6E77NI6lCU6MxlNBvIx.jpg",
      backdropUrl: null,
      remoteBackdropUrl: null,
      youtubeId: "xlnPHQ3TLX8",
      youtubeIds: ["xlnPHQ3TLX8", "Rvr68u6k5sI", "bvomHFNBCnQ"],
      ageRating: "P",
      genres: ["Hoạt hình", "Gia đình", "Âm nhạc", "Phiêu lưu"],
      featured: false,
      description: "Cậu bé Miguel nuôi ước mơ trở thành nghệ sĩ guitar bất chấp lệnh cấm âm nhạc nhiều thế hệ của gia đình. Vào đêm hội Dia de Muertos, Miguel vô tình bước vào Vùng Đất Linh Hồn rực rỡ và khám phá bí ẩn bất ngờ về tổ tiên."
    },
    "dune-part-two": {
      slug: "dune-part-two",
      title: "Dune: Part Two",
      titleVi: "Hành Tinh Cát: Phần Hai",
      posterUrl: "assets/posters/dune-part-two.jpg",
      remotePosterUrl: "https://image.tmdb.org/t/p/w500/6izwz7rsy95ARzTR3poZ8H6c5pp.jpg",
      backdropUrl: "assets/backdrops/dune-part-two.jpg",
      remoteBackdropUrl: "https://image.tmdb.org/t/p/w1280/uhUO7vQQKvCTfQWubOt5MAKokbL.jpg",
      youtubeId: "Way9Dexny3w",
      youtubeIds: ["Way9Dexny3w", "U2Qp5pL3ovA", "qEVUtrk8_B4"],
      ageRating: "T16",
      genres: ["Khoa học viễn tưởng", "Phiêu lưu", "Hành động"],
      featured: true,
      description: "Paul Atreides liên minh cùng Chani và tộc Fremen trên hành tinh sa mạc Arrakis để báo thù những kẻ đã tàn sát gia tộc mình. Đứng trước định mệnh cứu rỗi thiên hà, anh phải lựa chọn giữa tình yêu và sự cứu vớt số phận loài người."
    },
    "despicable-me-4": {
      slug: "despicable-me-4",
      title: "Despicable Me 4",
      titleVi: "Kẻ Trộm Mặt Trăng 4",
      posterUrl: "assets/posters/despicable-me-4.jpg",
      remotePosterUrl: "https://image.tmdb.org/t/p/w500/wWba3TaojhK7NdycRhoQpsG0FaH.jpg",
      backdropUrl: null,
      remoteBackdropUrl: null,
      youtubeId: "qQlr9-rF32A",
      youtubeIds: ["qQlr9-rF32A", "LtNYaH61dXY", "sR3o3Wp8z8o"],
      ageRating: "P",
      genres: ["Hoạt hình", "Hài", "Gia đình", "Phiêu lưu"],
      featured: false,
      description: "Gru và đại gia đình chào đón thành viên mới Gru Jr. - cậu bé nghịch ngợm khiến bố luôn đau đầu. Bình yên chưa lâu, kẻ thù không đội trời chung Maxime Le Mal vượt ngục khiến cả nhà cùng dàn Minions bước vào cuộc trốn chạy dở khóc dở cười."
    },
    "exhuma": {
      slug: "exhuma",
      title: "Exhuma",
      titleVi: "Quật Mộ Trùng Tang",
      posterUrl: "assets/posters/exhuma.jpg",
      remotePosterUrl: "https://image.tmdb.org/t/p/w500/6dasJ58GGFcC62H9KuukAryltUp.jpg",
      backdropUrl: null,
      remoteBackdropUrl: null,
      youtubeId: "5iRZLgrUuZM",
      youtubeIds: ["5iRZLgrUuZM", "9XWfu3QATks", "q6KfdU5Eis4"],
      ageRating: "T18",
      genres: ["Kinh dị", "Bí ẩn", "Giật gân"],
      featured: false,
      description: "Một gia đình giàu có gốc Hàn tại Mỹ thuê hai pháp sư trừ tà, một chuyên gia phong thủy và một nhân viên tang lễ khai quật ngôi mộ cổ bí ẩn. Việc di dời quan tài vô tình giải phóng một thế lực tà ác khủng khiếp chôn giấu hàng trăm năm."
    },
    "lat-mat-7": {
      slug: "lat-mat-7",
      title: "Lật Mặt 7: Một Điều Ước",
      titleVi: "Lật Mặt 7: Một Điều Ước",
      posterUrl: "assets/posters/lat-mat-7.jpg",
      remotePosterUrl: "https://image.tmdb.org/t/p/w500/1K7pHhCZprfDXB7LkCquIK62yCb.jpg",
      backdropUrl: null,
      remoteBackdropUrl: null,
      youtubeId: "d1ZHdosjNX8",
      youtubeIds: ["d1ZHdosjNX8", "8sU0xV2G1qQ", "J_c7J3qV0uI"],
      ageRating: "P",
      genres: ["Gia đình", "Tâm lý", "Hài"],
      featured: false,
      description: "Bà Hai 73 tuổi sống cô quạnh tại vùng quê hẻo lánh nuôi nấng 5 người con khôn lớn. Khi bà không may gặp nạn, cuộc họp gia đình giữa các người con ở khắp phương trời phơi bày những trăn trở, mâu thuẫn và cả sự hiếu nghĩa gia đình thiêng liêng."
    },
    "kung-fu-panda-4": {
      slug: "kung-fu-panda-4",
      title: "Kung Fu Panda 4",
      titleVi: "Kung Fu Panda 4",
      posterUrl: "assets/posters/kung-fu-panda-4.jpg",
      remotePosterUrl: "https://image.tmdb.org/t/p/w500/kDp1vUBnMpe8ak4rjgl3cLELqjU.jpg",
      backdropUrl: null,
      remoteBackdropUrl: null,
      youtubeId: "_inKs4eeHiI",
      youtubeIds: ["_inKs4eeHiI", "km3s534066E", "fQ9R056X5vQ"],
      ageRating: "P",
      genres: ["Hoạt hình", "Võ thuật", "Hài", "Phiêu lưu"],
      featured: false,
      description: "Po được chọn trở thành Thủ lĩnh Tinh thần của Thung lũng Bình Yên và cần tìm một Thần Long Đại Hiệp kế vị. Cùng sự giúp đỡ của nàng cáo trộm Zhen, Po phải đương đầu với Tắc Kè Bông - phù thủy nham hiểm có khả năng biến hình thành mọi kẻ thù trong quá khứ."
    },
    "oppenheimer": {
      slug: "oppenheimer",
      title: "Oppenheimer",
      titleVi: "Oppenheimer",
      posterUrl: "assets/posters/oppenheimer.jpg",
      remotePosterUrl: "https://image.tmdb.org/t/p/w500/8Gxv8gSFCU0XGDykEGv7zR1n2ua.jpg",
      backdropUrl: "assets/backdrops/oppenheimer.jpg",
      remoteBackdropUrl: "https://image.tmdb.org/t/p/w1280/nb3xI8XI3w4pMVZ38VijbsyBqP4.jpg",
      youtubeId: "uYPbbksJxIg",
      youtubeIds: ["uYPbbksJxIg", "bK6ldnjE3Y0", "9x_QJ2FwHw8"],
      ageRating: "T18",
      genres: ["Tâm lý", "Lịch sử", "Tiểu sử"],
      featured: true,
      description: "Câu chuyện lịch sử về nhà vật lý lý thuyết J. Robert Oppenheimer - người đứng đầu Dự án Manhattan khai sinh ra bom nguyên tử đầu tiên trên thế giới. Tác phẩm đào sâu vào những dằn vặt lương tâm và cuộc đấu tố chính trị khốc liệt thời hậu chiến."
    },
    "bong-dung-trung-so": {
      slug: "bong-dung-trung-so",
      title: "Bỗng Dưng Trúng Số",
      titleVi: "Bỗng Dưng Trúng Số (6/45)",
      posterUrl: "assets/posters/bong-dung-trung-so.jpg",
      remotePosterUrl: "https://image.tmdb.org/t/p/w500/AifHZptVzkzLLfk2tedIQixqrgV.jpg",
      backdropUrl: null,
      remoteBackdropUrl: null,
      youtubeId: "D3KbO3QF-lg",
      youtubeIds: ["D3KbO3QF-lg", "x6v_49_Fz3g", "f9k7_e0z764"],
      ageRating: "T13",
      genres: ["Hài", "Quân đội"],
      featured: false,
      description: "Một anh lính Hàn Quốc tình cờ nhặt được tờ vé số trúng độc đắc 5,7 tỷ won, nhưng không may cơn gió đã thổi bay tấm vé sang bên kia chiến tuyến Triều Tiên. Cuộc đàm phán bí mật và hoán đổi thân phận đầy hài hước giữa binh lính hai bên chính thức bắt đầu."
    },
    "spider-man-across-the-spider-verse": {
      slug: "spider-man-across-the-spider-verse",
      title: "Spider-Man: Across the Spider-Verse",
      titleVi: "Người Nhện: Du Hành Vũ Trụ Nhện",
      posterUrl: "assets/posters/spider-man-across-the-spider-verse.jpg",
      remotePosterUrl: "https://image.tmdb.org/t/p/w500/8Vt6mWEReuy4Of61Lnj5Xj704m8.jpg",
      backdropUrl: "assets/backdrops/spider-man-across-the-spider-verse.jpg",
      remoteBackdropUrl: "https://image.tmdb.org/t/p/w1280/4HodYYKEIsGOdinkGi2Ucz6X9i0.jpg",
      youtubeId: "cqGjhVJWtEg",
      youtubeIds: ["cqGjhVJWtEg", "shW9i6k8cB0", "u31qwQUeGuM"],
      ageRating: "P",
      genres: ["Hành động", "Hoạt hình", "Khoa học viễn tưởng"],
      featured: true,
      description: "Miles Morales tái ngộ Gwen Stacy và dấn thân vào đa vũ trụ, nơi có Quân đoàn Người Nhện chịu trách nhiệm bảo vệ dòng thời gian. Khi phát hiện ra cái giá phải trả để bảo vệ trật tự vũ trụ, Miles phải chiến đấu chống lại chính các Người Nhện khác để cứu người mình yêu thương."
    },
    "nha-ba-nu": {
      slug: "nha-ba-nu",
      title: "Nhà Bà Nữ",
      titleVi: "Nhà Bà Nữ",
      posterUrl: "assets/posters/nha-ba-nu.jpg",
      remotePosterUrl: "https://image.tmdb.org/t/p/w500/wqGZVSCUSXE92WH2zyol2REaqT4.jpg",
      backdropUrl: null,
      remoteBackdropUrl: null,
      youtubeId: "rbOzCHazoaw",
      youtubeIds: ["rbOzCHazoaw", "IkaP0KJWTsQ", "9zJg4hZ2-eU"],
      ageRating: "T16",
      genres: ["Gia đình", "Hài", "Tâm lý"],
      featured: false,
      description: "Gia đình ba thế hệ của bà Nữ làm nghề bán bánh canh cua nức tiếng nhưng luôn ngột ngạt vì sự kiểm soát khắt khe của người mẹ. Khát khao tự do của cô con gái út Nhi dẫn đến những rạn nứt gia đình sâu sắc trước khi mọi người học cách thấu hiểu."
    },
    "godzilla-x-kong": {
      slug: "godzilla-x-kong",
      title: "Godzilla x Kong: The New Empire",
      titleVi: "Godzilla x Kong: Đế Chế Mới",
      posterUrl: "assets/posters/godzilla-x-kong.jpg",
      remotePosterUrl: "https://image.tmdb.org/t/p/w500/z1p34vh7dEOnLDmyCrlUVLuoDzd.jpg",
      backdropUrl: "assets/backdrops/godzilla-x-kong.jpg",
      remoteBackdropUrl: "https://image.tmdb.org/t/p/w1280/veIyxxi5Gs8gvztLEW1Ysb8rrzs.jpg",
      youtubeId: "lV1OOlGwExM",
      youtubeIds: ["lV1OOlGwExM", "qqrpMRDuPfc", "V75dMMIW2B4"],
      ageRating: "T13",
      genres: ["Hành động", "Khoa học viễn tưởng", "Phiêu lưu"],
      featured: true,
      description: "Hai quái thú huyền thoại Godzilla và Kong buộc phải gạt bỏ hiềm khích để cùng hợp lực chống lại Skar King - bạo chúa tàn độc đang thống trị thế giới ngầm Trái Đất Rỗng. Cuộc đại chiến khốc liệt định đoạt tương lai tồn vong của cả nhân loại và muôn loài quái thú."
    }
  };

  // Tạo chỉ mục tra cứu theo nhiều biến thể tên, id và poster
  var LOOKUP_MAP = {};
  Object.keys(MOVIE_EXTRAS).forEach(function (slug) {
    var item = MOVIE_EXTRAS[slug];
    LOOKUP_MAP[slug] = item;
    LOOKUP_MAP[normalizeKey(item.title)] = item;
    if (item.titleVi) LOOKUP_MAP[normalizeKey(item.titleVi)] = item;
  });

  // Hỗ trợ ánh xạ theo ID và tên tệp poster của 15 phim gốc
  var ID_MAP = [
    [1, "avengers-endgame", "poster1"],
    [2, "inception", "poster2"],
    [3, "parasite", "poster3"],
    [4, "mai", "poster4"],
    [5, "coco", "poster5"],
    [6, "dune-part-two", "dune-part-two"],
    [7, "despicable-me-4", "despicable-me-4"],
    [8, "exhuma", "exhuma"],
    [9, "lat-mat-7", "lat-mat-7"],
    [10, "kung-fu-panda-4", "kung-fu-panda-4"],
    [11, "oppenheimer", "oppenheimer"],
    [12, "bong-dung-trung-so", "bong-dung-trung-so"],
    [13, "spider-man-across-the-spider-verse", "spider-man-across-the-spider-verse"],
    [14, "nha-ba-nu", "nha-ba-nu"],
    [15, "godzilla-x-kong", "godzilla-x-kong"]
  ];

  ID_MAP.forEach(function (pair) {
    var item = MOVIE_EXTRAS[pair[1]];
    if (item) {
      LOOKUP_MAP[String(pair[0])] = item;
      LOOKUP_MAP[pair[2]] = item;
      LOOKUP_MAP[pair[2] + ".jpg"] = item;
      LOOKUP_MAP["assets/posters/" + pair[2] + ".jpg"] = item;
    }
  });

  /**
   * Hợp nhất đối tượng phim từ backend API với metadata mở rộng ở frontend.
   * Cung cấp fallback an toàn khi thiếu thông tin.
   *
   * @param {Object} apiMovie Đối tượng phim trả về từ GET /api/movies ({id, title, genre, duration, poster, createdAt})
   * @returns {Object} Đối tượng phim hoàn chỉnh đã gộp extras
   */
  function mergeMovieExtras(apiMovie) {
    if (!apiMovie) return null;
    var title = apiMovie.title || "";
    var key = normalizeKey(title);
    var extra = LOOKUP_MAP[key] || null;

    // Khớp theo ID nếu không khớp tên
    if (!extra && apiMovie.id) {
      extra = LOOKUP_MAP[String(apiMovie.id)] || null;
    }

    // Nếu không khớp tên, thử khớp theo trường poster
    if (!extra && apiMovie.poster) {
      var posterStr = String(apiMovie.poster).trim().toLowerCase();
      var posterSlug = posterStr.replace(/\.[a-z0-9]+$/i, "");
      var baseName = posterSlug.split("/").pop();
      extra = LOOKUP_MAP[posterStr] || LOOKUP_MAP[posterSlug] || LOOKUP_MAP[baseName] || null;
    }

    // Giá trị fallback an toàn khi không tìm thấy extra
    var slug = extra ? extra.slug : (key || "movie-" + (apiMovie.id || "0"));
    var ageRating = extra ? extra.ageRating : "P";
    var youtubeId = extra ? extra.youtubeId : null;
    var youtubeIds = extra && extra.youtubeIds ? extra.youtubeIds.slice() : (youtubeId ? [youtubeId] : []);
    var featured = extra ? !!extra.featured : false;
    var genres = extra ? extra.genres : (apiMovie.genre ? [apiMovie.genre] : ["Phim"]);
    var description = extra
      ? extra.description
      : (title ? "Bộ phim " + title + " đang chiếu tại cụm rạp SOA Cinema." : "Thông tin phim đang được cập nhật.");

    // Ưu tiên poster cục bộ theo slug, tiếp theo là poster của API, rồi remote fallback
    var posterUrl = extra
      ? extra.posterUrl
      : (apiMovie.poster ? (apiMovie.poster.indexOf("/") >= 0 ? apiMovie.poster : "img/posters/" + apiMovie.poster) : null);

    var backdropUrl = extra ? extra.backdropUrl : null;

    return {
      id: apiMovie.id,
      title: apiMovie.title,
      titleVi: extra ? extra.titleVi : apiMovie.title,
      genre: apiMovie.genre || (genres[0] || ""),
      genres: genres,
      duration: apiMovie.duration || 0,
      poster: apiMovie.poster,
      posterUrl: posterUrl,
      remotePosterUrl: extra ? extra.remotePosterUrl : null,
      backdropUrl: backdropUrl,
      remoteBackdropUrl: extra ? extra.remoteBackdropUrl : null,
      youtubeId: youtubeId,
      youtubeIds: youtubeIds,
      trailerUrl: youtubeId ? "https://www.youtube.com/watch?v=X".replace("X", youtubeId) : null,
      embedUrl: youtubeId ? "https://www.youtube-nocookie.com/embed/X".replace("X", youtubeId) : null,
      ageRating: ageRating,
      featured: featured,
      description: description,
      slug: slug,
      createdAt: apiMovie.createdAt || null
    };
  }

  return {
    MOVIE_EXTRAS: MOVIE_EXTRAS,
    mergeMovieExtras: mergeMovieExtras,
    normalizeMovieKey: normalizeKey
  };
});
