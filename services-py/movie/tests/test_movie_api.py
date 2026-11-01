"""Bộ kiểm thử nghiệp vụ toàn diện cho Movie Service (Pytest)."""
import json


def test_health_endpoint(client):
    """GET /health phải trả về HTTP 200 và envelope chuẩn."""
    res = client.get("/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"
    assert data["data"] == {"service": "movie-service", "port": 5001}


def test_list_movies_empty(client):
    """GET /api/movies khi chưa có dữ liệu phải trả về danh sách rỗng [] (không phải 404)."""
    res = client.get("/api/movies")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"
    assert data["data"] == []


def test_list_movies_seeded(seeded_client):
    """GET /api/movies sau khi nạp seed phải trả về 5 bộ phim theo thứ tự id tăng dần."""
    res = seeded_client.get("/api/movies")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"
    movies = data["data"]
    assert len(movies) == 5
    assert movies[0]["id"] == 1
    assert movies[0]["title"] == "Avengers: Endgame"
    # Kiểm tra chuẩn camelCase (createdAt, không để lộ created_at)
    assert "createdAt" in movies[0]
    assert "created_at" not in json.dumps(data)


def test_get_movie_by_id_success(seeded_client):
    """GET /api/movies/{id} tìm thấy phim trả về HTTP 200 và dữ liệu chi tiết."""
    res = seeded_client.get("/api/movies/2")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"
    assert data["data"]["id"] == 2
    assert data["data"]["title"] == "Inception"
    assert data["data"]["duration"] == 148


def test_get_movie_by_id_not_found(client):
    """GET /api/movies/{id} khi phim không tồn tại phải trả về HTTP 404 với code NOT_FOUND."""
    res = client.get("/api/movies/99999")
    assert res.status_code == 404
    data = res.json()
    assert data["status"] == "error"
    assert data["code"] == "NOT_FOUND"
    assert "Không tìm thấy phim với ID = 99999" in data["message"]


def test_get_movie_by_invalid_id(client):
    """GET /api/movies/{id} với ID không hợp lệ (chuỗi hoặc số âm) phải trả về HTTP 400."""
    res = client.get("/api/movies/abc")
    assert res.status_code == 400
    assert res.json()["status"] == "error"
    assert res.json()["code"] == "VALIDATION_ERROR"

    res_neg = client.get("/api/movies/0")
    assert res_neg.status_code == 400
    assert res_neg.json()["code"] == "VALIDATION_ERROR"


def test_create_movie_success(client):
    """POST /api/movies thành công tạo phim mới và trả về HTTP 201."""
    payload = {
        "title": "Interstellar",
        "genre": "Khoa học viễn tưởng",
        "duration": 169,
        "poster": "interstellar.jpg",
    }
    res = client.post("/api/movies", json=payload)
    assert res.status_code == 201
    data = res.json()
    assert data["status"] == "success"
    movie = data["data"]
    assert movie["id"] > 0
    assert movie["title"] == "Interstellar"
    assert movie["genre"] == "Khoa học viễn tưởng"
    assert movie["duration"] == 169
    assert movie["poster"] == "interstellar.jpg"
    assert "createdAt" in movie


def test_create_movie_validation_empty_title(client):
    """POST /api/movies thiếu title hoặc title để rỗng phải trả về HTTP 400."""
    res1 = client.post("/api/movies", json={"genre": "Hành động", "duration": 120})
    assert res1.status_code == 400
    assert res1.json()["status"] == "error"
    assert res1.json()["code"] == "VALIDATION_ERROR"

    res2 = client.post("/api/movies", json={"title": "   ", "duration": 120})
    assert res2.status_code == 400
    assert res2.json()["code"] == "VALIDATION_ERROR"


def test_create_movie_validation_invalid_duration(client):
    """POST /api/movies với duration <= 0 hoặc sai kiểu phải trả về HTTP 400."""
    res1 = client.post("/api/movies", json={"title": "Phim mới", "duration": 0})
    assert res1.status_code == 400
    assert res1.json()["code"] == "VALIDATION_ERROR"

    res2 = client.post("/api/movies", json={"title": "Phim mới", "duration": -10})
    assert res2.status_code == 400
    assert res2.json()["code"] == "VALIDATION_ERROR"

    res3 = client.post("/api/movies", json={"title": "Phim mới", "duration": "khong-phai-so"})
    assert res3.status_code == 400
    assert res3.json()["code"] == "VALIDATION_ERROR"


def test_update_movie_success(seeded_client):
    """PUT /api/movies/{id} cập nhật thông tin thành công và trả về HTTP 200."""
    payload = {
        "title": "Inception (Bản đặc biệt)",
        "duration": 150,
    }
    res = seeded_client.put("/api/movies/2", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"
    movie = data["data"]
    assert movie["id"] == 2
    assert movie["title"] == "Inception (Bản đặc biệt)"
    assert movie["duration"] == 150
    # Các trường không cập nhật vẫn giữ nguyên
    assert movie["genre"] == "Khoa học viễn tưởng"


def test_update_movie_not_found(client):
    """PUT /api/movies/{id} với ID không tồn tại phải trả về HTTP 404."""
    res = client.put("/api/movies/99999", json={"title": "Không tồn tại"})
    assert res.status_code == 404
    data = res.json()
    assert data["status"] == "error"
    assert data["code"] == "NOT_FOUND"


def test_update_movie_invalid_data(seeded_client):
    """PUT /api/movies/{id} với title rỗng hoặc duration âm phải trả về HTTP 400."""
    res1 = seeded_client.put("/api/movies/1", json={"title": "  "})
    assert res1.status_code == 400
    assert res1.json()["code"] == "VALIDATION_ERROR"

    res2 = seeded_client.put("/api/movies/1", json={"duration": -5})
    assert res2.status_code == 400
    assert res2.json()["code"] == "VALIDATION_ERROR"


def test_delete_movie_success(seeded_client):
    """DELETE /api/movies/{id} xóa phim thành công và trả về HTTP 200."""
    res = seeded_client.delete("/api/movies/3")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"
    assert data["data"] == {"id": 3, "deleted": True}

    # Sau khi xóa, truy vấn lại phải ra 404
    check = seeded_client.get("/api/movies/3")
    assert check.status_code == 404


def test_delete_movie_not_found(client):
    """DELETE /api/movies/{id} với ID không tồn tại phải trả về HTTP 404."""
    res = client.delete("/api/movies/99999")
    assert res.status_code == 404
    data = res.json()
    assert data["status"] == "error"
    assert data["code"] == "NOT_FOUND"


def test_cors_preflight_options(client):
    """OPTIONS preflight request phải trả về HTTP 204 No Content và đủ CORS headers."""
    res = client.options("/api/movies")
    assert res.status_code == 204
    assert res.headers["Access-Control-Allow-Origin"] == "*"
    assert "GET" in res.headers["Access-Control-Allow-Methods"]

    res_item = client.options("/api/movies/1")
    assert res_item.status_code == 204
    assert res_item.headers["Access-Control-Allow-Origin"] == "*"


def test_swagger_ui_and_openapi_spec(client):
    """Kiểm tra giao diện Swagger UI (/docs) và đặc tả OpenAPI (/openapi.json)."""
    docs_res = client.get("/docs")
    assert docs_res.status_code == 200
    assert "swagger-ui" in docs_res.text.lower() or "html" in docs_res.headers.get("content-type", "")

    spec_res = client.get("/openapi.json")
    assert spec_res.status_code == 200
    spec = spec_res.json()
    assert spec["info"]["title"] == "Movie Service API (TV1)"
    assert spec["info"]["version"] == "1.0.0"
    assert "SOA" in spec["info"]["description"]
    # Kiểm tra phân nhóm tags
    tag_names = [t["name"] for t in spec.get("tags", [])]
    assert "Health" in tag_names
    assert "Movies" in tag_names
    # Kiểm tra schemas có example
    schemas = spec["components"]["schemas"]
    assert "MovieCreate" in schemas
    assert "example" in schemas["MovieCreate"]
    assert schemas["MovieCreate"]["example"]["title"] == "Avengers: Secret Wars"


