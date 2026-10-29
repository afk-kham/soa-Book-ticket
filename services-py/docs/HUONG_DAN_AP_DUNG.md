# HUONG_DAN_AP_DUNG — Áp dụng bộ khung vào repo, kiểm tra diff, tự push

Gói zip `soa-python-scaffold.zip` chỉ chứa **file mới** dưới `services-py/`. Không có file nào trùng đường dẫn với file đang có trong repo, nên giải nén **không ghi đè** gì. Khung **không tự commit/push**; các bước Git bên dưới do bạn tự chạy.

## 1. Áp dụng

```bash
cd soa-Book-ticket
git fetch origin && git status                  # đang ở main, working tree sạch?
git switch -c scaffold/python-fastapi           # KHUYẾN NGHỊ: làm trên nhánh riêng rồi mở PR (xem §4)

unzip -n ../soa-python-scaffold.zip -d .        # -n = KHÔNG BAO GIỜ ghi đè file đã có
```

## 2. Kiểm tra: chỉ có file mới, không file cũ nào bị đụng

```bash
git status --porcelain | grep -v '^??' ; echo "exit=$?"     # mong đợi: không in dòng nào (exit=1)
git diff --stat                                              # mong đợi: rỗng
git ls-files --others --exclude-standard | grep -v '^services-py/' ; echo "exit=$?"   # mong đợi: rỗng (exit=1)
git ls-files --others --exclude-standard | wc -l             # số file mới
git ls-files --others --exclude-standard | grep -Ei '\.(png|jpe?g|svg|docx?|pdf|pptx|drawio|db|sqlite3?)$|(^|/)\.env$' ; echo "exit=$?"   # mong đợi: rỗng (exit=1)
```

Diễn giải: không có dòng `M`/`D`/`R` (sửa/xóa/đổi tên); mọi file mới nằm dưới `services-py/`; không có file nhị phân, không có `.env`/`.db`. Frontend (`admin/`, `client/`), `docs/`, `services/`, `database/`, `scripts/`, `tests/`, `design/` không bị thay đổi.

## 3. Kiểm tra khung chạy được

```bash
cd services-py/movie                       # lặp lại cho showtime user booking payment notification
python3.12 -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
python -m pytest -q                        # mong đợi: 2 passed
uvicorn app.main:app --port 5001 &         # đúng cổng của service
curl -s localhost:5001/health              # {"status":"success","data":{"service":"movie-service","port":5001}}
kill %1
```

Docker (**chưa được kiểm chứng trong lúc dựng khung vì môi trường không có Docker** — hãy chạy và báo lại nếu lỗi):

```bash
cd services-py
docker compose config -q && echo "compose hợp lệ"
docker compose build                       # kiểm tra tag python:3.12.12-slim-bookworm kéo được
docker compose up -d
for p in 5001 5002 5003 5004 5005 5006; do curl -s localhost:$p/health; echo; done
docker compose ps                          # cột STATUS có "(healthy)" sau ~15–25 giây
docker compose down                        # KHÔNG dùng -v nếu muốn giữ dữ liệu sau này
```

Nếu cổng 500x bị chiếm (ví dụ còn chạy service cũ): tạo `services-py/.env` từ `.env.example` và đổi `MOVIE_HOST_PORT=…` (chỉ đổi cổng host; Admin/Client trỏ cổng cố định nên chỉ nên làm tạm khi test).

## 4. Commit và push (bạn tự thực hiện)

Khuyến nghị **nhánh + Pull Request** thay vì push thẳng `main` (`TEAM_RULES.md` quy định `main` chỉ nhận từ `develop` sau checklist). Gói khung chỉ thêm file nên rủi ro thấp, nhưng PR cho phép cả nhóm xem diff.

```bash
git add services-py
git status                                  # xác nhận chỉ có services-py/**
git commit -m "chore(scaffold): thêm khung Python/FastAPI/SQLite cho 6 service (chưa có nghiệp vụ)"
git push -u origin scaffold/python-fastapi  # rồi mở PR vào main (hoặc develop)
```

Nếu bạn quyết định đưa thẳng lên `main`: `git switch main && git merge --ff-only scaffold/python-fastapi && git push origin main` (không `--force`). Sau đó đồng bộ `develop` và các `feature/*` với `main` bằng **merge** (không rebase/force-push) — xem D-15: hiện các nhánh này đang **sau `main` 5–6 commit**.

Trước khi push, kiểm tra không lộ bí mật: `git diff --cached --name-only | grep -Ei '(^|/)\.env$|\.db$' ; echo "exit=$?"` → mong đợi rỗng.

## 5. Hoàn tác an toàn

Chưa commit: `git clean -n services-py` (xem trước) rồi `git clean -fd services-py` — chỉ xóa thư mục khung vừa thêm. Đã commit trên nhánh riêng: bỏ nhánh, hoặc `git revert <commit>`. Không dùng `reset --hard`/`push --force`.

## 6. Việc bạn cần tự bổ sung sau khi áp dụng

| Việc | Ở đâu | Ghi chú |
|---|---|---|
| Quyết định các mục `D-01 … D-19` | `docs/OPEN_QUESTIONS.md` | Tối thiểu D-19 (hỏi giảng viên), D-01, D-04, D-07, D-15 trước khi các TV bắt đầu |
| Cập nhật `ARCHITECTURE.md` gốc (6 ngôn ngữ → 6× FastAPI) | thư mục gốc | D-12 |
| Sửa `API_CONTRACT.md` gốc khi nhóm duyệt (DB_PATH, `/health`, mã Notification…) | thư mục gốc | PR ≥ 2 người duyệt |
| Sơ đồ ERD/DFD mới (nếu cần) | `docs/tv<N>-…/` | Tự vẽ; khung không tạo file nặng (xem `ASSETS_GUIDE.md`) |
| Build thử Docker | máy có Docker | §3 |
