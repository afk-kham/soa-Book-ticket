package userservice;

import com.google.gson.*;
import com.sun.net.httpserver.*;
import org.mindrot.jbcrypt.BCrypt;

import java.io.IOException;
import java.net.InetSocketAddress;
import java.nio.charset.StandardCharsets;
import java.sql.SQLException;
import java.util.*;
import java.util.concurrent.Executors;
import java.util.regex.Pattern;

/**
 * User/Auth Service (giua ky) - Java thuan: com.sun.net.httpserver + JDBC + jBCrypt.
 *   POST /api/login        : dang nhap, kiem tra BCrypt
 *   POST /api/register     : dang ky tai khoan moi (role luon la USER)
 *   GET  /api/users        : danh sach nguoi dung (khong co password_hash); ?username=x de tim 1 nguoi
 *   GET  /api/users/{id}   : chi tiet mot nguoi dung
 */
public class Main {
    private static final UserDao DAO = new UserDao();
    private static final Pattern USERNAME_RE = Pattern.compile("^[A-Za-z0-9_.]{3,50}$");
    private static final Pattern EMAIL_RE = Pattern.compile("^[^@\\s]+@[^@\\s]+\\.[^@\\s]+$");

    public static void main(String[] args) throws Exception {
        HttpServer server = HttpServer.create(new InetSocketAddress(Config.HOST, Config.PORT), 0);
        server.createContext("/", Main::route);
        server.setExecutor(Executors.newFixedThreadPool(8));
        server.start();
        System.out.println("User Service dang chay tai http://" + Config.HOST + ":" + Config.PORT);
    }

    /** Bo dinh tuyen: OPTIONS -> 204; sai duong dan -> 404; sai method -> 405. */
    private static void route(HttpExchange ex) throws IOException {
        try {
            if ("OPTIONS".equalsIgnoreCase(ex.getRequestMethod())) { Http.noContent(ex); return; }

            String path = ex.getRequestURI().getPath();
            if (path.length() > 1 && path.endsWith("/")) path = path.substring(0, path.length() - 1);
            String method = ex.getRequestMethod().toUpperCase();

            if (path.equals("/api/login")) {
                if (!method.equals("POST")) { methodNotAllowed(ex, "POST"); return; }
                login(ex);
            } else if (path.equals("/api/register")) {
                if (!method.equals("POST")) { methodNotAllowed(ex, "POST"); return; }
                register(ex);
            } else if (path.equals("/api/users")) {
                if (!method.equals("GET")) { methodNotAllowed(ex, "GET"); return; }
                String uq = queryParam(ex, "username");
                if (uq != null) {
                    Map<String, Object> one = DAO.findPublicByUsername(uq.trim());
                    Http.success(ex, 200, one == null ? List.of() : List.of(one));
                } else {
                    Http.success(ex, 200, DAO.findAllPublic());
                }
            } else if (path.startsWith("/api/users/")) {
                if (!method.equals("GET")) { methodNotAllowed(ex, "GET"); return; }
                userDetail(ex, path.substring("/api/users/".length()));
            } else {
                Http.error(ex, 404, "Không tìm thấy đường dẫn: " + path);
            }
        } catch (SQLException e) {
            System.err.println("[DB] " + e.getMessage());                 // khong in mat khau / hash
            Http.error(ex, 500, "Lỗi cơ sở dữ liệu");
        } catch (Exception e) {
            System.err.println("[ERR] " + e);
            Http.error(ex, 500, "Lỗi máy chủ");
        } finally {
            ex.close();
        }
    }

    private static void methodNotAllowed(HttpExchange ex, String allow) throws IOException {
        ex.getResponseHeaders().set("Allow", allow + ", OPTIONS");
        Http.error(ex, 405, "Phương thức không được hỗ trợ, chỉ chấp nhận " + allow);
    }

    /** Doc body thanh JsonObject; neu sai thi da gui loi 400 va tra ve null. */
    private static JsonObject readJson(HttpExchange ex) throws IOException {
        String raw = new String(ex.getRequestBody().readAllBytes(), StandardCharsets.UTF_8);
        try {
            JsonElement el = JsonParser.parseString(raw);
            if (!el.isJsonObject()) { Http.error(ex, 400, "Body phải là đối tượng JSON"); return null; }
            return el.getAsJsonObject();
        } catch (JsonParseException e) {
            Http.error(ex, 400, "JSON không hợp lệ");
            return null;
        }
    }

    // ---------- POST /api/login ----------
    private static void login(HttpExchange ex) throws IOException, SQLException {
        JsonObject json = readJson(ex);
        if (json == null) return;
        String username = str(json, "username");
        String password = str(json, "password");
        if (username == null || username.isBlank() || password == null || password.isEmpty()) {
            Http.error(ex, 400, "Thiếu username hoặc password");
            return;
        }

        UserDao.User u = DAO.findByUsername(username.trim());
        // Cung mot thong bao cho "khong ton tai" va "sai mat khau" de khong lo thong tin tai khoan.
        if (u == null || !checkPassword(password, u.passwordHash())) {
            Http.error(ex, 401, "Sai tên đăng nhập hoặc mật khẩu");
            return;
        }
        Map<String, Object> data = new LinkedHashMap<>();
        data.put("id", u.id());
        data.put("username", u.username());
        data.put("role", u.role());
        data.put("token", "demo-token-" + u.username());   // giua ky: token tam; cuoi ky thay bang JWT
        Http.success(ex, 200, data);
    }

    // ---------- POST /api/register ----------
    private static void register(HttpExchange ex) throws IOException, SQLException {
        JsonObject json = readJson(ex);
        if (json == null) return;
        String username = str(json, "username");
        String password = str(json, "password");
        String email = str(json, "email");
        // KHONG doc truong "role" tu client: tai khoan dang ky luon la USER (tranh tu cap quyen ADMIN).

        if (username == null || !USERNAME_RE.matcher(username.trim()).matches()) {
            Http.error(ex, 400, "username phải dài 3–50 ký tự, chỉ gồm chữ, số, dấu _ hoặc .");
            return;
        }
        if (password == null || password.length() < 6 || password.length() > 72) {
            Http.error(ex, 400, "password phải dài từ 6 đến 72 ký tự");
            return;
        }
        if (email != null && email.isBlank()) email = null;
        if (email != null && (email.length() > 100 || !EMAIL_RE.matcher(email).matches())) {
            Http.error(ex, 400, "email không hợp lệ");
            return;
        }
        username = username.trim();
        if (DAO.findByUsername(username) != null) {
            Http.error(ex, 409, "Tên đăng nhập đã tồn tại");
            return;
        }

        String hash = BCrypt.hashpw(password, BCrypt.gensalt(10));   // tien to $2a$
        int id;
        try {
            id = DAO.insert(username, hash, email);
        } catch (SQLException e) {
            if ("23000".equals(e.getSQLState())) {            // hai yeu cau cung luc trung username (UNIQUE)
                Http.error(ex, 409, "Tên đăng nhập đã tồn tại");
                return;
            }
            throw e;
        }
        Map<String, Object> data = new LinkedHashMap<>();
        data.put("id", id);
        data.put("username", username);
        data.put("email", email);
        data.put("role", "USER");
        Http.success(ex, 201, data);
    }

    // ---------- GET /api/users/{id} ----------
    private static void userDetail(HttpExchange ex, String idText) throws IOException, SQLException {
        int id;
        try { id = Integer.parseInt(idText); }
        catch (NumberFormatException e) { Http.error(ex, 400, "id phải là số nguyên"); return; }
        Map<String, Object> u = DAO.findPublicById(id);
        if (u == null) { Http.error(ex, 404, "Không tìm thấy người dùng có id " + id); return; }
        Http.success(ex, 200, u);
    }

    /** Lay 1 tham so query (da giai ma URL); null neu khong co. */
    private static String queryParam(HttpExchange ex, String name) {
        String q = ex.getRequestURI().getQuery();
        if (q == null) return null;
        for (String pair : q.split("&")) {
            int eq = pair.indexOf('=');
            String k = eq < 0 ? pair : pair.substring(0, eq);
            if (k.equals(name)) {
                String v = eq < 0 ? "" : pair.substring(eq + 1);
                return java.net.URLDecoder.decode(v, StandardCharsets.UTF_8);
            }
        }
        return null;
    }

    private static boolean checkPassword(String plain, String hash) {
        try { return BCrypt.checkpw(plain, hash); }
        catch (IllegalArgumentException e) { return false; }   // hash hong -> coi nhu khong khop
    }

    private static String str(JsonObject o, String key) {
        JsonElement e = o.get(key);
        return (e == null || !e.isJsonPrimitive()) ? null : e.getAsString();
    }
}
