#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
=============================================================================
SOA Cinema — Seed Dữ liệu 10 Phim Mới & Suất Chiếu (Frontend / Data Layer)
Thực hiện qua API HTTP/JSON của Movie Service (:5001) và Showtime Service (:5002).
Tính chất: Idempotent (chạy nhiều lần an toàn, không trùng lặp phim hay suất).
=============================================================================
"""

import sys
import os
import json
import urllib.request
import urllib.parse
from datetime import datetime, timedelta

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

MOVIE_SERVICE_URL = os.environ.get("MOVIE_URL", "http://localhost:5001")
SHOWTIME_SERVICE_URL = os.environ.get("SHOWTIME_URL", "http://localhost:5002")

# Danh sách 10 phim mới cần thêm vào hệ thống (tổng 15 phim cùng 5 phim gốc)
NEW_MOVIES = [
    {
        "slug": "dune-part-two",
        "title": "Dune: Part Two",
        "genre": "Khoa học viễn tưởng",
        "duration": 166,
        "poster": "assets/posters/dune-part-two.jpg",
        "remotePoster": "https://image.tmdb.org/t/p/w500/6izwz7rsy95ARzTR3poZ8H6c5pp.jpg",
        "ageRating": "T16",
        "youtubeId": "Way9Dexny3w"
    },
    {
        "slug": "despicable-me-4",
        "title": "Despicable Me 4",
        "genre": "Hoạt hình",
        "duration": 94,
        "poster": "assets/posters/despicable-me-4.jpg",
        "remotePoster": "https://image.tmdb.org/t/p/w500/wWba3TaojhK7NdycRhoQpsG0FaH.jpg",
        "ageRating": "P",
        "youtubeId": "qQlr9-rF32A"
    },
    {
        "slug": "exhuma",
        "title": "Exhuma",
        "genre": "Kinh dị",
        "duration": 134,
        "poster": "assets/posters/exhuma.jpg",
        "remotePoster": "https://image.tmdb.org/t/p/w500/6dasJ58GGFcC62H9KuukAryltUp.jpg",
        "ageRating": "T18",
        "youtubeId": "5iRZLgrUuZM"
    },
    {
        "slug": "lat-mat-7",
        "title": "Lật Mặt 7: Một Điều Ước",
        "genre": "Gia đình",
        "duration": 138,
        "poster": "assets/posters/lat-mat-7.jpg",
        "remotePoster": "https://image.tmdb.org/t/p/w500/1K7pHhCZprfDXB7LkCquIK62yCb.jpg",
        "ageRating": "P",
        "youtubeId": "d1ZHdosjNX8"
    },
    {
        "slug": "kung-fu-panda-4",
        "title": "Kung Fu Panda 4",
        "genre": "Hoạt hình",
        "duration": 94,
        "poster": "assets/posters/kung-fu-panda-4.jpg",
        "remotePoster": "https://image.tmdb.org/t/p/w500/kDp1vUBnMpe8ak4rjgl3cLELqjU.jpg",
        "ageRating": "P",
        "youtubeId": "_inKs4eeHiI"
    },
    {
        "slug": "oppenheimer",
        "title": "Oppenheimer",
        "genre": "Tâm lý",
        "duration": 180,
        "poster": "assets/posters/oppenheimer.jpg",
        "remotePoster": "https://image.tmdb.org/t/p/w500/8Gxv8gSFCU0XGDykEGv7zR1n2ua.jpg",
        "ageRating": "T18",
        "youtubeId": "uYPbbksJxIg"
    },
    {
        "slug": "bong-dung-trung-so",
        "title": "Bỗng Dưng Trúng Số",
        "genre": "Hài",
        "duration": 113,
        "poster": "assets/posters/bong-dung-trung-so.jpg",
        "remotePoster": "https://image.tmdb.org/t/p/w500/AifHZptVzkzLLfk2tedIQixqrgV.jpg",
        "ageRating": "T13",
        "youtubeId": "D3KbO3QF-lg"
    },
    {
        "slug": "spider-man-across-the-spider-verse",
        "title": "Spider-Man: Across the Spider-Verse",
        "genre": "Hành động",
        "duration": 140,
        "poster": "assets/posters/spider-man-across-the-spider-verse.jpg",
        "remotePoster": "https://image.tmdb.org/t/p/w500/8Vt6mWEReuy4Of61Lnj5Xj704m8.jpg",
        "ageRating": "P",
        "youtubeId": "cqGjhVJWtEg"
    },
    {
        "slug": "nha-ba-nu",
        "title": "Nhà Bà Nữ",
        "genre": "Gia đình",
        "duration": 102,
        "poster": "assets/posters/nha-ba-nu.jpg",
        "remotePoster": "https://image.tmdb.org/t/p/w500/wqGZVSCUSXE92WH2zyol2REaqT4.jpg",
        "ageRating": "T16",
        "youtubeId": "rbOzCHazoaw"
    },
    {
        "slug": "godzilla-x-kong",
        "title": "Godzilla x Kong: The New Empire",
        "genre": "Hành động",
        "duration": 115,
        "poster": "assets/posters/godzilla-x-kong.jpg",
        "remotePoster": "https://image.tmdb.org/t/p/w500/z1p34vh7dEOnLDmyCrlUVLuoDzd.jpg",
        "ageRating": "T13",
        "youtubeId": "lV1OOlGwExM"
    }
]

def http_json(method, url, payload=None, timeout=10):
    """Gửi HTTP request JSON theo chuẩn REST API."""
    data_bytes = None
    headers = {"Accept": "application/json"}
    if payload is not None:
        data_bytes = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        headers["Content-Type"] = "application/json; charset=utf-8"

    req = urllib.request.Request(url, data=data_bytes, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8")
            return json.loads(raw), resp.getcode(), None
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8", errors="replace")
        try:
            return json.loads(raw), e.code, None
        except Exception:
            return None, e.code, raw
    except Exception as e:
        return None, 0, str(e)

def ensure_asset(url, dest_path):
    """Tải poster nếu chưa có trên ổ đĩa."""
    if os.path.exists(dest_path) and os.path.getsize(dest_path) > 1000:
        return True
    os.makedirs(os.path.dirname(dest_path), exist_ok=True)
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            content = resp.read()
            with open(dest_path, "wb") as f:
                f.write(content)
        return True
    except Exception as e:
        sys.stderr.write(f"  [Cảnh báo tải ảnh] {url} -> {e}\n")
        return False

def seed_movies():
    print("=" * 70)
    print("🎬 SOA CINEMA — SEED DỮ LIỆU PHIM MỚI & SUẤT CHIẾU")
    print("=" * 70)

    # 1. Kiểm tra Movie Service
    print(f"\n[1/3] Kết nối tới Movie Service: {MOVIE_SERVICE_URL}...")
    res, code, err = http_json("GET", f"{MOVIE_SERVICE_URL}/api/movies")
    if code != 200 or not res or res.get("status") != "success":
        print(f"❌ Không kết nối được Movie Service (Mã {code}, lỗi: {err})")
        print("👉 Vui lòng đảm bảo Movie Service đang chạy trên cổng 5001:")
        print("   cd services/movie && python movie_service.py")
        return False

    existing_movies = res.get("data", [])
    existing_titles = {m.get("title", "").strip().lower(): m for m in existing_movies}
    print(f"✓ Đã kết nối Movie Service. Hiện có {len(existing_movies)} phim trong hệ thống.")

    # 2. Thêm phim mới (Idempotent)
    print("\n[2/3] Kiểm tra & Thêm 10 phim mới...")
    all_movies = list(existing_movies)

    for item in NEW_MOVIES:
        title_key = item["title"].strip().lower()
        if title_key in existing_titles:
            m = existing_titles[title_key]
            print(f"  - [BỎ QUA] '{item['title']}' (ID #{m.get('id')}) đã tồn tại.")
        else:
            payload = {
                "title": item["title"],
                "genre": item["genre"],
                "duration": item["duration"],
                "poster": item["poster"]
            }
            create_res, ccode, cerr = http_json("POST", f"{MOVIE_SERVICE_URL}/api/movies", payload)
            if ccode == 201 and create_res and create_res.get("status") == "success":
                new_m = create_res.get("data", {})
                all_movies.append(new_m)
                existing_titles[title_key] = new_m
                print(f"  + [THÊM MỚI] '{item['title']}' -> ID #{new_m.get('id')}, {item['duration']}p, {item['genre']}")
            else:
                print(f"  ❌ [LỖI THÊM PHIM] '{item['title']}': mã {ccode}, {cerr or create_res}")

        # Đảm bảo poster đã tải về client/assets/posters/
        poster_file = os.path.join("client", "assets", "posters", f"{item['slug']}.jpg")
        ensure_asset(item["remotePoster"], poster_file)

    # 3. Kiểm tra & Tạo suất chiếu 7 ngày tới qua Showtime Service
    print(f"\n[3/3] Kết nối tới Showtime Service: {SHOWTIME_SERVICE_URL}...")
    st_res, st_code, st_err = http_json("GET", f"{SHOWTIME_SERVICE_URL}/api/showtimes")
    if st_code != 200 or not st_res or st_res.get("status") != "success":
        print(f"⚠️  Không kết nối được Showtime Service (Mã {st_code}). Bỏ qua tạo suất chiếu.")
        print("👉 Nếu muốn tạo suất chiếu, khởi động Showtime Service:")
        print("   cd services/showtime && php -S 0.0.0.0:5002 router.php")
    else:
        print("✓ Đã kết nối Showtime Service. Đang kiểm tra lịch chiếu cho từng phim...")
        cinemas = ["CGV Vincom Đồng Khởi", "Lotte Cinema Cantavil", "BHD Star Bitexco"]
        slots = ["10:00", "13:30", "16:45", "19:15", "21:30"]
        rooms = ["P1", "P2", "P3"]

        created_shows_count = 0
        today = datetime.now()

        for m in all_movies:
            mid = m.get("id")
            if not mid:
                continue

            # Kiểm tra phim đã có suất chiếu sắp tới chưa
            shows_res, scode, _ = http_json("GET", f"{SHOWTIME_SERVICE_URL}/api/showtimes?movieId={mid}&upcoming=1")
            existing_st = shows_res.get("data", []) if (scode == 200 and shows_res) else []

            if len(existing_st) >= 7:
                # Đã có đủ suất chiếu
                continue

            # Tạo suất chiếu 7 ngày tới cho phim (mỗi ngày 2-3 suất tại các rạp)
            for d in range(7):
                target_date = today + timedelta(days=d)
                date_str = target_date.strftime("%Y-%m-%d")
                is_weekend = target_date.weekday() in (5, 6)
                base_price = 85000 if not is_weekend else 95000

                # Tạo 2 suất/ngày cho mỗi phim mới
                for slot_idx, slot in enumerate([slots[mid % len(slots)], slots[(mid + 2) % len(slots)]]):
                    cinema = cinemas[(mid + slot_idx) % len(cinemas)]
                    room = rooms[(mid + d) % len(rooms)]
                    show_time = f"{date_str} {slot}:00"
                    price = base_price + (10000 if int(slot.split(":")[0]) >= 18 else 0)

                    show_payload = {
                        "movieId": mid,
                        "cinema": cinema,
                        "room": room,
                        "time": show_time,
                        "price": price
                    }
                    s_res, s_code, s_err = http_json("POST", f"{SHOWTIME_SERVICE_URL}/api/showtimes", show_payload)
                    if s_code == 201:
                        created_shows_count += 1

        print(f"✓ Đã bổ sung {created_shows_count} suất chiếu mới cho các phim vừa thêm.")

    print("\n" + "=" * 70)
    print("🎉 HOÀN TẤT SEED DỮ LIỆU! Danh mục phim hiện tại:")
    final_res, _, _ = http_json("GET", f"{MOVIE_SERVICE_URL}/api/movies")
    final_movies = final_res.get("data", []) if final_res else all_movies
    for m in final_movies:
        print(f"  #{m.get('id'):<2} | {m.get('title'):<36} | {m.get('genre'):<20} | {m.get('duration')} phút")
    print("=" * 70)
    return True

if __name__ == "__main__":
    seed_movies()

