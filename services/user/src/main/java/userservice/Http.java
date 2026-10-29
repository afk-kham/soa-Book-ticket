package userservice;

import com.google.gson.Gson;
import com.google.gson.GsonBuilder;
import com.sun.net.httpserver.HttpExchange;

import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.util.LinkedHashMap;
import java.util.Map;

/**
 * Helper dung chung cho HTTP response cua User/Auth Service.
 *
 * Chuc nang:
 * - Tra JSON response
 * - CORS cho Client/Admin
 * - Tra 204 No Content
 * - Tra 200/201/... voi data
 * - Tra loi JSON voi message
 */
public final class Http {

    private Http() {
        // Khong cho tao object
    }

    private static final Gson GSON = new GsonBuilder()
            .serializeNulls()
            .create();

    /**
     * Cau hinh CORS chung.
     *
     * Hien tai cho phep Client/Admin chay localhost:
     * - http://localhost:8080
     * - http://127.0.0.1:8080
     * - http://localhost:8081
     * - http://127.0.0.1:8081
     *
     * Neu sau nay deploy domain that thi sua lai danh sach nay.
     */
    private static void setCorsHeaders(HttpExchange ex) {
        // Hop dong chung (API_CONTRACT.md): moi service tra Access-Control-Allow-Origin: *
        ex.getResponseHeaders().set("Access-Control-Allow-Origin", "*");
        ex.getResponseHeaders().set("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS");
        ex.getResponseHeaders().set("Access-Control-Allow-Headers", "Content-Type, Authorization");
        ex.getResponseHeaders().set("Access-Control-Max-Age", "3600");
    }

    /**
     * Tra HTTP 204 No Content.
     *
     * Duoc Main.java su dung cho OPTIONS/preflight.
     */
    public static void noContent(HttpExchange ex) throws IOException {
        setCorsHeaders(ex);

        ex.sendResponseHeaders(204, -1);
    }

    /**
     * Tra response thanh JSON.
     *
     * Vi du:
     * Http.success(ex, 200, data);
     * Http.success(ex, 201, data);
     */
    public static void success(
            HttpExchange ex,
            int status,
            Object data
    ) throws IOException {

        setCorsHeaders(ex);

        ex.getResponseHeaders().set(
                "Content-Type",
                "application/json; charset=UTF-8"
        );

        // Envelope chung: {"status":"success","data":...}
        Map<String, Object> envelope = new LinkedHashMap<>();
        envelope.put("status", "success");
        envelope.put("data", data);
        String json = GSON.toJson(envelope);
        byte[] body = json.getBytes(StandardCharsets.UTF_8);

        ex.sendResponseHeaders(status, body.length);

        try {
            ex.getResponseBody().write(body);
        } finally {
            ex.getResponseBody().close();
        }
    }

    private static String codeFor(int status) {
        switch (status) {
            case 400: return "VALIDATION_ERROR";
            case 401: return "UNAUTHORIZED";
            case 403: return "FORBIDDEN";
            case 404: return "NOT_FOUND";
            case 405: return "METHOD_NOT_ALLOWED";
            case 409: return "CONFLICT";
            default:  return status >= 500 ? "INTERNAL_ERROR" : "ERROR";
        }
    }

    /**
     * Tra response loi JSON.
     *
     * Dang response chuan cua ca he thong:
     * {
     *   "status": "error",
     *   "code": "VALIDATION_ERROR",
     *   "message": "Noi dung loi"
     * }
     */
    public static void error(
            HttpExchange ex,
            int status,
            String message
    ) throws IOException {

        setCorsHeaders(ex);

        ex.getResponseHeaders().set(
                "Content-Type",
                "application/json; charset=UTF-8"
        );

        Map<String, String> bodyData = new LinkedHashMap<>();
        bodyData.put("status", "error");
        bodyData.put("code", codeFor(status));
        bodyData.put("message", message);

        String json = GSON.toJson(bodyData);
        byte[] body = json.getBytes(StandardCharsets.UTF_8);

        ex.sendResponseHeaders(status, body.length);

        try {
            ex.getResponseBody().write(body);
        } finally {
            ex.getResponseBody().close();
        }
    }
}