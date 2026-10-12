<?php
/**
 * Showtime Service (TV2 – PHP core + PDO) — cổng 5002, CSDL showtime_db
 * Chạy:  php -S 0.0.0.0:5002 router.php
 *
 *   GET    /api/showtimes[?movieId=1]   danh sách (lọc theo phim, tùy chọn)
 *   GET    /api/showtimes/{id}          chi tiết
 *   POST   /api/showtimes               thêm
 *   PUT    /api/showtimes/{id}          sửa
 *   DELETE /api/showtimes/{id}          xóa
 *   GET    /health                      kiểm tra sống
 */
require __DIR__ . '/src/config.php';
require __DIR__ . '/src/response.php';
require __DIR__ . '/src/db.php';
require __DIR__ . '/src/validate.php';

$method = $_SERVER['REQUEST_METHOD'];
$path   = rtrim(parse_url($_SERVER['REQUEST_URI'], PHP_URL_PATH) ?: '/', '/') ?: '/';

if ($method === 'OPTIONS') {            // preflight CORS: bắt buộc trả 204
    http_response_code(204);
    send_cors_headers();
    exit;
}

if ($path === '/health' && $method === 'GET') {
    send_success(['service' => 'showtime-service', 'port' => 5002]);
}

$isCollection = ($path === '/api/showtimes');
$isItem       = (bool) preg_match('#^/api/showtimes/(\d+)$#', $path, $m);
$id           = $isItem ? (int) $m[1] : null;

if (!$isCollection && !$isItem) {
    send_error('Endpoint không tồn tại', 404);
}

try {
    if ($isCollection && $method === 'GET') {
        $mid = $_GET['movieId'] ?? $_GET['movie_id'] ?? null;     // movie_id: tên cũ, còn nhận để tương thích
        if ($mid !== null && (!is_int_like($mid) || (int) $mid <= 0)) {
            send_error('movieId phải là số nguyên dương', 400);
        }
        send_success(find_showtimes($mid !== null ? (int) $mid : null));
    }

    if ($isItem && $method === 'GET') {
        $row = find_showtime($id);
        $row ? send_success($row) : send_error("Không tìm thấy suất chiếu với ID = $id", 404);
    }

    if ($isCollection && $method === 'POST') {
        $v = validate_showtime(read_json_body(), false);
        assert_movie_exists($v['movie_id']);
        $st = db()->prepare('INSERT INTO showtimes (movie_id, cinema, room, `time`, price) VALUES (?, ?, ?, ?, ?)');
        $st->execute([$v['movie_id'], $v['cinema'], $v['room'], $v['time'], $v['price']]);
        send_success(find_showtime((int) db()->lastInsertId()), 201);
    }

    if ($isItem && $method === 'PUT') {
        if (find_showtime($id) === null) send_error("Không tìm thấy suất chiếu với ID = $id", 404);
        $v = validate_showtime(read_json_body(), true);
        if (isset($v['movie_id'])) assert_movie_exists($v['movie_id']);
        $sets = implode(', ', array_map(fn($k) => ($k === 'time' ? '`time`' : $k) . ' = ?', array_keys($v)));
        $st = db()->prepare("UPDATE showtimes SET $sets WHERE id = ?");
        $st->execute([...array_values($v), $id]);
        send_success(find_showtime($id));
    }

    if ($isItem && $method === 'DELETE') {
        $st = db()->prepare('DELETE FROM showtimes WHERE id = ?');
        $st->execute([$id]);
        $st->rowCount() > 0
            ? send_success(['id' => $id, 'deleted' => true])
            : send_error("Không tìm thấy suất chiếu với ID = $id", 404);
    }

    header('Allow: ' . ($isCollection ? 'GET, POST' : 'GET, PUT, DELETE') . ', OPTIONS');
    send_error('Phương thức không được hỗ trợ trên endpoint này', 405);
} catch (PDOException $e) {
    error_log('[showtime-service] DB error: ' . $e->getMessage());   // chi tiết chỉ ghi log, không trả cho client
    send_error('Lỗi cơ sở dữ liệu', 500);
} catch (Throwable $e) {
    error_log('[showtime-service] ' . $e);
    send_error('Lỗi máy chủ nội bộ', 500);
}
