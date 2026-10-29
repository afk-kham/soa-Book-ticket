<?php
// Kết nối showtime_db bằng PDO (prepared statement thật, chống SQL injection)

function db(): PDO
{
    static $pdo = null;
    if ($pdo === null) {
        $c = config();
        $dsn = "mysql:host={$c['db_host']};port={$c['db_port']};dbname={$c['db_name']};charset=utf8mb4";
        $pdo = new PDO($dsn, $c['db_user'], $c['db_password'], [
            PDO::ATTR_ERRMODE            => PDO::ERRMODE_EXCEPTION,
            PDO::ATTR_DEFAULT_FETCH_MODE => PDO::FETCH_ASSOC,
            PDO::ATTR_EMULATE_PREPARES   => false,
        ]);
    }
    return $pdo;
}

/** Chuyển dòng DB (snake_case) sang JSON API (camelCase). */
function to_api(array $row): array
{
    return [
        'id'      => (int) $row['id'],
        'movieId' => (int) $row['movie_id'],
        'cinema'  => $row['cinema'],
        'room'    => $row['room'],
        'time'    => $row['time'],
        'price'   => (int) $row['price'],
    ];
}

/** $upcoming = true: chỉ các suất chưa bắt đầu (so với giờ hiện tại của máy chủ). */
function find_showtimes(?int $movieId, bool $upcoming = false): array
{
    $where = [];
    $args = [];
    if ($movieId !== null) {
        $where[] = 'movie_id = ?';
        $args[] = $movieId;
    }
    if ($upcoming) {
        $where[] = '`time` > ?';
        $args[] = date('Y-m-d H:i:s');
    }
    $st = db()->prepare('SELECT id, movie_id, cinema, room, `time`, price FROM showtimes'
        . ($where ? ' WHERE ' . implode(' AND ', $where) : '') . ' ORDER BY `time`, id');
    $st->execute($args);
    return array_map('to_api', $st->fetchAll());
}

function find_showtime(int $id): ?array
{
    $st = db()->prepare('SELECT id, movie_id, cinema, room, `time`, price FROM showtimes WHERE id = ?');
    $st->execute([$id]);
    $row = $st->fetch();
    return $row ? to_api($row) : null;
}
