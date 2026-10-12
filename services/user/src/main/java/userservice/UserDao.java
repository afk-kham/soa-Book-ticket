package userservice;

import java.sql.*;
import java.util.*;

/** Truy cap bang users bang JDBC + PreparedStatement (chong SQL injection). */
public class UserDao {

    /** Mot dong trong bang users (co password_hash - chi dung noi bo, KHONG tra ra API). */
    public record User(int id, String username, String passwordHash, String email, String role) {}

    private Connection open() throws SQLException {
        return DriverManager.getConnection(Config.DB_URL, Config.DB_USER, Config.DB_PASSWORD);
    }

    public User findByUsername(String username) throws SQLException {
        String sql = "SELECT id, username, password_hash, email, role FROM users WHERE username = ?";
        try (Connection c = open(); PreparedStatement ps = c.prepareStatement(sql)) {
            ps.setString(1, username);
            try (ResultSet rs = ps.executeQuery()) {
                if (!rs.next()) return null;
                return new User(rs.getInt("id"), rs.getString("username"),
                        rs.getString("password_hash"), rs.getString("email"), rs.getString("role"));
            }
        }
    }

    /** Danh sach cong khai: KHONG chon cot password_hash. */
    public List<Map<String, Object>> findAllPublic() throws SQLException {
        String sql = "SELECT id, username, email, role FROM users ORDER BY id";
        List<Map<String, Object>> list = new ArrayList<>();
        try (Connection c = open(); PreparedStatement ps = c.prepareStatement(sql);
             ResultSet rs = ps.executeQuery()) {
            while (rs.next()) list.add(toPublic(rs));
        }
        return list;
    }

    /** Chi tiet mot nguoi dung (khong co password_hash); null neu khong ton tai. */
    public Map<String, Object> findPublicById(int id) throws SQLException {
        String sql = "SELECT id, username, email, role FROM users WHERE id = ?";
        try (Connection c = open(); PreparedStatement ps = c.prepareStatement(sql)) {
            ps.setInt(1, id);
            try (ResultSet rs = ps.executeQuery()) {
                return rs.next() ? toPublic(rs) : null;
            }
        }
    }

    /** Tim cong khai theo username (cho Booking Service xac thuc nguoi dung qua HTTP); null neu khong co. */
    public Map<String, Object> findPublicByUsername(String username) throws SQLException {
        String sql = "SELECT id, username, email, role FROM users WHERE username = ?";
        try (Connection c = open(); PreparedStatement ps = c.prepareStatement(sql)) {
            ps.setString(1, username);
            try (ResultSet rs = ps.executeQuery()) {
                return rs.next() ? toPublic(rs) : null;
            }
        }
    }

    /** Them nguoi dung moi voi role USER; tra ve id vua sinh. Nem SQLException (SQLState 23000) neu trung username. */
    public int insert(String username, String passwordHash, String email) throws SQLException {
        String sql = "INSERT INTO users (username, password_hash, email, role) VALUES (?, ?, ?, 'USER')";
        try (Connection c = open(); PreparedStatement ps = c.prepareStatement(sql, Statement.RETURN_GENERATED_KEYS)) {
            ps.setString(1, username);
            ps.setString(2, passwordHash);
            if (email == null) ps.setNull(3, Types.VARCHAR); else ps.setString(3, email);
            ps.executeUpdate();
            try (ResultSet k = ps.getGeneratedKeys()) { k.next(); return k.getInt(1); }
        }
    }

    private static Map<String, Object> toPublic(ResultSet rs) throws SQLException {
        Map<String, Object> m = new LinkedHashMap<>();
        m.put("id", rs.getInt("id"));
        m.put("username", rs.getString("username"));
        m.put("email", rs.getString("email"));
        m.put("role", rs.getString("role"));
        return m;
    }
}
