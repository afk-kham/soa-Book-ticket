# User/Auth Service (TV3) — Java · cổng 5003 · `user_db`

Tài khoản và đăng nhập. Java 17+, `com.sun.net.httpserver`, JDBC (MySQL Connector/J), jBCrypt, Gson.

```bash
cd services/user
cp .env.example .env              # sửa DB_USER / DB_PASSWORD  (Config.java tự đọc .env)
mvn -q compile exec:java          # http://localhost:5003
```
Tài khoản mẫu: `admin / Admin@123`, `user1 / User@123`, `user2 / User@123`.

| Endpoint | Ghi chú |
|---|---|
| `POST /api/register` | Trùng username → **409** |
| `POST /api/login` | Trả `{id, username, role, token}` (token demo; cuối kỳ là JWT) |
| `GET /api/users`, `GET /api/users?username=x`, `GET /api/users/{id}` | Không bao giờ trả mật khẩu |

Biến môi trường: `PORT`, `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD` (tùy chọn `DB_URL` để ghi đè chuỗi JDBC).
Mã nguồn: `src/main/java/userservice/` (`Main`, `Http`, `UserDao`, `Config`).
