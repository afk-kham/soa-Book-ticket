package userservice;

import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.HashMap;
import java.util.Map;

/**
 * Cau hinh tap trung, dung CHUNG ten bien voi .env.example cua kho nhom:
 *   PORT, DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD, JWT_SECRET (cuoi ky).
 * Thu tu uu tien: bien moi truong he dieu hanh > file .env (thu muc hien tai) > gia tri mac dinh.
 * Java KHONG tu doc .env nen lop nay tu doc file .env don gian (dong KEY=VALUE, bo qua dong # va dong trong).
 * File .env chua mat khau that -> da nam trong .gitignore, KHONG commit.
 */
public final class Config {
    private Config() {}

    private static final Map<String, String> DOTENV = loadDotEnv(Path.of(".env"));

    public static final String HOST = "0.0.0.0";                       // lang nghe moi giao dien mang
    public static final int    PORT = Integer.parseInt(get("PORT", "5003"));

    private static final String DB_HOST = get("DB_HOST", "localhost");
    private static final String DB_PORT = get("DB_PORT", "3306");
    private static final String DB_NAME = get("DB_NAME", "user_db");

    /** Co the ghi de tron chuoi ket noi bang DB_URL (vi du khi dung driver khac). */
    public static final String DB_URL = get("DB_URL",
            "jdbc:mysql://" + DB_HOST + ":" + DB_PORT + "/" + DB_NAME
          + "?useUnicode=true&characterEncoding=UTF-8&useSSL=false&allowPublicKeyRetrieval=true&serverTimezone=UTC");
    public static final String DB_USER     = get("DB_USER", "root");
    public static final String DB_PASSWORD = get("DB_PASSWORD", "");
    public static final String JWT_SECRET  = get("JWT_SECRET", "");    // giua ky chua dung; cuoi ky ky JWT HS256

    private static String get(String key, String def) {
        String v = System.getenv(key);
        if (v == null || v.isBlank()) v = DOTENV.get(key);
        return (v == null || v.isBlank()) ? def : v;
    }

    private static Map<String, String> loadDotEnv(Path file) {
        Map<String, String> map = new HashMap<>();
        if (!Files.isRegularFile(file)) return map;
        try {
            for (String line : Files.readAllLines(file, StandardCharsets.UTF_8)) {
                String s = line.strip();
                if (s.isEmpty() || s.startsWith("#")) continue;
                int eq = s.indexOf('=');
                if (eq <= 0) continue;
                String k = s.substring(0, eq).strip();
                String v = s.substring(eq + 1).strip();
                if (v.length() >= 2 && ((v.startsWith("\"") && v.endsWith("\"")) || (v.startsWith("'") && v.endsWith("'"))))
                    v = v.substring(1, v.length() - 1);
                map.put(k, v);
            }
        } catch (IOException e) {
            System.err.println("[Config] Khong doc duoc .env: " + e.getMessage());
        }
        return map;
    }
}
