<?php
// Cấu hình Showtime Service — đọc từ biến môi trường hoặc file .env (KHÔNG hard-code, KHÔNG commit .env)
// Tên biến dùng CHUNG cho cả 6 service: PORT, DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD

function load_dotenv(string $path): void
{
    if (!is_file($path)) {
        return;
    }
    foreach (file($path, FILE_IGNORE_NEW_LINES | FILE_SKIP_EMPTY_LINES) as $line) {
        $line = trim($line);
        if ($line === '' || $line[0] === '#' || strpos($line, '=') === false) {
            continue;
        }
        [$k, $v] = explode('=', $line, 2);
        $k = trim($k);
        $v = trim(trim($v), "\"'");
        if (getenv($k) === false) {
            putenv("$k=$v");
        }
    }
}

load_dotenv(__DIR__ . '/../.env');

function env(string $key, string $default = ''): string
{
    $v = getenv($key);
    return ($v === false || $v === '') ? $default : $v;
}

function config(): array
{
    static $cfg = null;
    if ($cfg === null) {
        $cfg = [
            'db_host'        => env('DB_HOST', '127.0.0.1'),
            'db_port'        => env('DB_PORT', '3306'),
            'db_name'        => env('DB_NAME', 'showtime_db'),   // tên chuẩn duy nhất: showtime_db (KHÔNG dùng cinema_db)
            'db_user'        => env('DB_USER', 'root'),
            'db_password'    => env('DB_PASSWORD', ''),
            // Kiểm tra movieId tồn tại bằng cách gọi API của Movie Service (không đọc movie_db)
            'validate_movie' => strtolower(env('VALIDATE_MOVIE', 'true')) !== 'false',
            'movie_url'      => rtrim(env('MOVIE_SERVICE_URL', 'http://localhost:5001'), '/'),
        ];
    }
    return $cfg;
}
