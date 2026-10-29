#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
=============================================================================
TV1 - MOVIE SERVICE (PYTHON CODE THUẦN - GIỮA KỲ)
Môn học: Kiến trúc Hướng Dịch vụ (SOA)
Cổng: 5001 | Lắng nghe: 0.0.0.0
Công nghệ: http.server (BaseHTTPRequestHandler, ThreadingHTTPServer) + PyMySQL
Định dạng dữ liệu: JSON chuẩn { "status": "success", "data": ... } | { "status": "error", "code": "...", "message": "..." }
=============================================================================
"""

import json
import re
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

# Đảm bảo console Windows hỗ trợ UTF-8 không bị crash vì emoji/tiếng Việt
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

import config
import database

class MovieRequestHandler(BaseHTTPRequestHandler):
    """
    Handler xử lý các HTTP requests cho Movie Service.
    Sử dụng Regex để định tuyến (Routing) theo đúng yêu cầu bài tập.
    """

    # Các mẫu regex định tuyến
    ROUTE_COLLECTION = re.compile(r"^/api/movies/?$")
    ROUTE_ITEM = re.compile(r"^/api/movies/(\d+)/?$")

    # -------------------------------------------------------------------------
    # HÀM BỔ TRỢ GỬI RESPONSE & CORS
    # -------------------------------------------------------------------------
    def _send_cors_headers(self):
        """Gửi các header CORS cho phép Client và Admin từ cổng khác gọi tới."""
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")

    def _send_json(self, status_code, payload):
        """Gửi phản hồi JSON chuẩn UTF-8."""
        body = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self._send_cors_headers()
        self.end_headers()
        self.wfile.write(body)

    def _send_success(self, data, status_code=200):
        """Gửi phản hồi thành công chuẩn: {"status": "success", "data": ...}"""
        self._send_json(status_code, {
            "status": "success",
            "data": data
        })

    ERROR_CODES = {400: "VALIDATION_ERROR", 404: "NOT_FOUND", 405: "METHOD_NOT_ALLOWED",
                   413: "PAYLOAD_TOO_LARGE", 500: "INTERNAL_ERROR"}

    def _send_error(self, message, status_code=400):
        """Gửi phản hồi lỗi chuẩn: {"status": "error", "code": "...", "message": "..."}"""
        self._send_json(status_code, {
            "status": "error",
            "code": self.ERROR_CODES.get(status_code, "ERROR"),
            "message": message
        })

    def _server_error(self, context, exc):
        """Lỗi 500: ghi chi tiết ra log của server, KHÔNG trả chi tiết CSDL cho client."""
        sys.stderr.write(f"[movie-service] {context}: {exc}\n")
        self._send_error("Lỗi máy chủ nội bộ", 500)

    def _read_json_body(self):
        """Đọc và giải mã dữ liệu JSON từ body request."""
        try:
            content_length = int(self.headers.get("Content-Length", 0))
            if content_length == 0:
                return None, "Body yêu cầu rỗng"
            raw_data = self.rfile.read(content_length).decode("utf-8")
            parsed = json.loads(raw_data)
            if not isinstance(parsed, dict):
                return None, "Body phải là một đối tượng JSON"
            return parsed, None
        except json.JSONDecodeError:
            return None, "Định dạng JSON không hợp lệ"
        except Exception as e:
            return None, f"Lỗi đọc dữ liệu body: {str(e)}"

    # -------------------------------------------------------------------------
    # XỬ LÝ PREFLIGHT REQUEST (OPTIONS)
    # -------------------------------------------------------------------------
    def do_OPTIONS(self):
        """
        Xử lý request OPTIONS preflight từ trình duyệt.
        Bắt buộc trả về HTTP 204 No Content theo yêu cầu Hợp đồng API chung.
        """
        self.send_response(204)
        self._send_cors_headers()
        self.end_headers()

    # -------------------------------------------------------------------------
    # XỬ LÝ GET REQUESTS
    # GET /api/movies           -> Danh sách phim (200)
    # GET /api/movies/{id}      -> Chi tiết một phim (200 hoặc 404)
    # -------------------------------------------------------------------------
    def do_GET(self):
        path = urlparse(self.path).path

        # 1. GET /api/movies
        if self.ROUTE_COLLECTION.match(path):
            try:
                movies = database.get_all_movies()
                self._send_success(movies, 200)
            except Exception as e:
                self._server_error("db", e)
            return

        # 2. GET /api/movies/{id}
        match = self.ROUTE_ITEM.match(path)
        if match:
            movie_id = int(match.group(1))
            try:
                movie = database.get_movie_by_id(movie_id)
                if movie:
                    self._send_success(movie, 200)
                else:
                    self._send_error(f"Không tìm thấy phim với ID = {movie_id}", 404)
            except Exception as e:
                self._server_error("db", e)
            return

        # Đường dẫn không hợp lệ
        self._send_error("Endpoint không tồn tại", 404)

    # -------------------------------------------------------------------------
    # XỬ LÝ POST REQUESTS
    # POST /api/movies          -> Thêm phim mới (201)
    # -------------------------------------------------------------------------
    def do_POST(self):
        path = urlparse(self.path).path

        if self.ROUTE_COLLECTION.match(path):
            data, err = self._read_json_body()
            if err:
                self._send_error(err, 400)
                return

            # Kiểm tra dữ liệu bắt buộc (Validation)
            # Theo phiếu giao việc: title bắt buộc, duration > 0
            title = data.get("title")
            if not title or not str(title).strip():
                self._send_error("Trường 'title' là bắt buộc và không được để trống", 400)
                return

            duration = data.get("duration")
            if duration is not None:
                try:
                    duration = int(duration)
                    if duration <= 0:
                        self._send_error("Thời lượng phim ('duration') phải lớn hơn 0", 400)
                        return
                except (ValueError, TypeError):
                    self._send_error("Thời lượng phim ('duration') phải là số nguyên hợp lệ", 400)
                    return

            genre = data.get("genre", "")
            poster = data.get("poster", "")

            try:
                new_movie = database.create_movie(
                    title=str(title).strip(),
                    genre=str(genre).strip() if genre else None,
                    duration=duration,
                    poster=str(poster).strip() if poster else None
                )
                self._send_success(new_movie, 201)
            except Exception as e:
                self._server_error("db", e)
            return

        self._send_error("Phương thức POST không được hỗ trợ trên endpoint này", 405)

    # -------------------------------------------------------------------------
    # XỬ LÝ PUT REQUESTS
    # PUT /api/movies/{id}      -> Cập nhật phim (200 hoặc 404)
    # -------------------------------------------------------------------------
    def do_PUT(self):
        path = urlparse(self.path).path
        match = self.ROUTE_ITEM.match(path)

        if match:
            movie_id = int(match.group(1))
            data, err = self._read_json_body()
            if err:
                self._send_error(err, 400)
                return

            title = data.get("title")
            if title is not None and not str(title).strip():
                self._send_error("Tên phim ('title') không được để rỗng", 400)
                return

            duration = data.get("duration")
            if duration is not None:
                try:
                    duration = int(duration)
                    if duration <= 0:
                        self._send_error("Thời lượng phim ('duration') phải lớn hơn 0", 400)
                        return
                except (ValueError, TypeError):
                    self._send_error("Thời lượng phim ('duration') phải là số nguyên hợp lệ", 400)
                    return

            genre = data.get("genre")
            poster = data.get("poster")

            try:
                updated_movie = database.update_movie(
                    movie_id=movie_id,
                    title=str(title).strip() if title is not None else None,
                    genre=str(genre).strip() if genre is not None else None,
                    duration=duration,
                    poster=str(poster).strip() if poster is not None else None
                )
                if updated_movie:
                    self._send_success(updated_movie, 200)
                else:
                    self._send_error(f"Không tìm thấy phim với ID = {movie_id}", 404)
            except Exception as e:
                self._server_error("db", e)
            return

        self._send_error("Phương thức PUT không được hỗ trợ trên endpoint này", 405)

    # -------------------------------------------------------------------------
    # XỬ LÝ DELETE REQUESTS
    # DELETE /api/movies/{id}   -> Xóa phim (200 hoặc 404)
    # -------------------------------------------------------------------------
    def do_DELETE(self):
        path = urlparse(self.path).path
        match = self.ROUTE_ITEM.match(path)

        if match:
            movie_id = int(match.group(1))
            try:
                deleted = database.delete_movie(movie_id)
                if deleted:
                    self._send_success({"id": movie_id, "deleted": True}, 200)
                else:
                    self._send_error(f"Không tìm thấy phim với ID = {movie_id} để xóa", 404)
            except Exception as e:
                self._server_error("db", e)
            return

        self._send_error("Phương thức DELETE không được hỗ trợ trên endpoint này", 405)

    # Tùy chỉnh log hiển thị trực quan
    def log_message(self, format, *args):
        sys.stdout.write(f"[{self.log_date_time_string()}] {self.address_string()} - {format % args}\n")


def run():
    """Khởi động máy chủ ThreadingHTTPServer phục vụ đa luồng."""
    host = config.SERVER_HOST
    port = config.SERVER_PORT
    server_address = (host, port)

    # ThreadingHTTPServer giúp phục vụ nhiều request đồng thời, không bị block
    httpd = ThreadingHTTPServer(server_address, MovieRequestHandler)
    print("=" * 65)
    print(f"🎬 TV1 - MOVIE SERVICE (Python Core HTTP Server)")
    print(f"🚀 Server đang lắng nghe tại: http://{host}:{port}/api/movies")
    print(f"💡 CSDL MySQL: {config.DB_USER}@{config.DB_HOST}:{config.DB_PORT}/{config.DB_NAME}")
    print(f"📌 Nhấn Ctrl+C để dừng server.")
    print("=" * 65)

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n🛑 Đang dừng Movie Service...")
        httpd.server_close()
        print("✅ Đã dừng Movie Service an toàn.")


if __name__ == "__main__":
    run()
