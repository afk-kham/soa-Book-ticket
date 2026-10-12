import pymysql
from pymysql.cursors import DictCursor
import config

def get_connection():
    """Tạo kết nối đến MySQL movie_db với chuẩn utf8mb4."""
    return pymysql.connect(
        host=config.DB_HOST,
        port=config.DB_PORT,
        user=config.DB_USER,
        password=config.DB_PASSWORD,
        database=config.DB_NAME,
        charset=config.DB_CHARSET,
        cursorclass=DictCursor,
        autocommit=True
    )

def get_all_movies():
    """Lấy danh sách tất cả các bộ phim."""
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            sql = "SELECT id, title, genre, duration, poster, created_at AS createdAt FROM movies ORDER BY id ASC"
            cursor.execute(sql)
            results = cursor.fetchall()
            # Chuyển đổi createdAt datetime sang string ISO để serialize JSON mượt mà
            for row in results:
                if row.get("createdAt"):
                    row["createdAt"] = str(row["createdAt"])
            return results
    finally:
        conn.close()

def get_movie_by_id(movie_id):
    """Lấy thông tin chi tiết một bộ phim theo ID."""
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            sql = "SELECT id, title, genre, duration, poster, created_at AS createdAt FROM movies WHERE id = %s"
            cursor.execute(sql, (movie_id,))
            result = cursor.fetchone()
            if result and result.get("createdAt"):
                result["createdAt"] = str(result["createdAt"])
            return result
    finally:
        conn.close()

def create_movie(title, genre=None, duration=None, poster=None):
    """
    Thêm một bộ phim mới vào CSDL.
    Sử dụng Prepared Statement (%s) chống SQL Injection.
    """
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            sql = "INSERT INTO movies (title, genre, duration, poster) VALUES (%s, %s, %s, %s)"
            cursor.execute(sql, (title, genre, duration, poster))
            new_id = cursor.lastrowid
            return get_movie_by_id(new_id)
    finally:
        conn.close()

def update_movie(movie_id, title=None, genre=None, duration=None, poster=None):
    """
    Cập nhật thông tin phim theo ID.
    """
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            # Kiểm tra xem phim có tồn tại không
            check_sql = "SELECT id FROM movies WHERE id = %s"
            cursor.execute(check_sql, (movie_id,))
            if not cursor.fetchone():
                return None

            # Cập nhật các trường
            sql = """
                UPDATE movies 
                SET title = COALESCE(%s, title),
                    genre = COALESCE(%s, genre),
                    duration = COALESCE(%s, duration),
                    poster = COALESCE(%s, poster)
                WHERE id = %s
            """
            cursor.execute(sql, (title, genre, duration, poster, movie_id))
            return get_movie_by_id(movie_id)
    finally:
        conn.close()

def delete_movie(movie_id):
    """
    Xóa một bộ phim theo ID.
    Trả về True nếu xóa thành công, False nếu phim không tồn tại.
    """
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            check_sql = "SELECT id FROM movies WHERE id = %s"
            cursor.execute(check_sql, (movie_id,))
            if not cursor.fetchone():
                return False

            sql = "DELETE FROM movies WHERE id = %s"
            cursor.execute(sql, (movie_id,))
            return True
    finally:
        conn.close()
