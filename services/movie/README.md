# Movie Service (TV1) — Python · cổng 5001 · `movie_db`

Danh mục phim. Python 3.10+, `http.server` (ThreadingHTTPServer) + PyMySQL, không dùng framework.

```bash
cd services/movie
pip install -r requirements.txt
cp .env.example .env          # sửa DB_USER / DB_PASSWORD
python movie_service.py       # http://localhost:5001
```
CSDL: `bash scripts/init-db.sh` (từ thư mục gốc). API: xem `API_CONTRACT.md` mục 2.

| Tệp | Vai trò |
|---|---|
| `movie_service.py` | Server HTTP, định tuyến regex, kiểm tra dữ liệu, envelope |
| `database.py` | Truy vấn MySQL bằng câu lệnh có tham số |
| `config.py` | Đọc `.env` / biến môi trường |
