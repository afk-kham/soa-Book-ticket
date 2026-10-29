<?php
// Kiểm tra dữ liệu đầu vào. Trả về [giá trị đã chuẩn hóa, null] hoặc [null, thông điệp lỗi].

function read_json_body(): array
{
    $raw = file_get_contents('php://input');
    if ($raw === false || trim($raw) === '') {
        send_error('Body yêu cầu rỗng', 400);
    }
    $data = json_decode($raw, true);
    if (!is_array($data) || array_is_list($data)) {
        send_error('Body phải là một đối tượng JSON hợp lệ', 400);
    }
    return $data;
}

/** Đếm ký tự Unicode, không phụ thuộc extension mbstring. */
function char_len(string $s): int
{
    return function_exists('mb_strlen') ? mb_strlen($s, 'UTF-8') : (int) preg_match_all('/./us', $s);
}

function is_int_like($v): bool
{
    return is_int($v) || (is_string($v) && preg_match('/^-?\d+$/', $v) === 1);
}

function normalize_time($v): ?string
{
    if (!is_string($v) || trim($v) === '') {
        return null;
    }
    $v = str_replace('T', ' ', trim($v));
    foreach (['Y-m-d H:i:s', 'Y-m-d H:i'] as $fmt) {
        $d = DateTime::createFromFormat($fmt, $v);
        if ($d !== false && $d->format($fmt) === $v) {
            return $d->format('Y-m-d H:i:s');
        }
    }
    return null;
}

/**
 * $partial = true cho PUT (chỉ kiểm tra các trường được gửi lên).
 * Chấp nhận thêm movie_id (tên cũ) như bí danh của movieId để tương thích ngược.
 */
function validate_showtime(array $in, bool $partial): array
{
    if (isset($in['movie_id']) && !isset($in['movieId'])) {
        $in['movieId'] = $in['movie_id'];
    }
    $out = [];
    $fail = fn(string $m) => send_error($m, 400);

    if (array_key_exists('movieId', $in)) {
        if (!is_int_like($in['movieId']) || (int) $in['movieId'] <= 0) $fail('movieId phải là số nguyên dương');
        $out['movie_id'] = (int) $in['movieId'];
    } elseif (!$partial) $fail('movieId là bắt buộc');

    foreach (['cinema' => 150, 'room' => 50] as $f => $max) {
        if (array_key_exists($f, $in)) {
            if (!is_string($in[$f]) || trim($in[$f]) === '' || char_len(trim($in[$f])) > $max) $fail("$f là bắt buộc, tối đa $max ký tự");
            $out[$f] = trim($in[$f]);
        } elseif (!$partial) $fail("$f là bắt buộc");
    }

    if (array_key_exists('time', $in)) {
        $t = normalize_time($in['time']);
        if ($t === null) $fail("time phải có dạng 'YYYY-MM-DD HH:MM:SS'");
        $out['time'] = $t;
    } elseif (!$partial) $fail('time là bắt buộc');

    if (array_key_exists('price', $in)) {
        if (!is_int_like($in['price']) || (int) $in['price'] < 0) $fail('price phải là số nguyên không âm (VND)');
        $out['price'] = (int) $in['price'];
    } elseif (!$partial) $fail('price là bắt buộc');

    if ($partial && !$out) {
        $fail('Không có trường nào để cập nhật');
    }
    return $out;
}

/** Gọi API Movie Service để biết phim có tồn tại không (Showtime KHÔNG đọc movie_db). */
function assert_movie_exists(int $movieId): void
{
    $c = config();
    if (!$c['validate_movie']) {
        return;
    }
    $ctx = stream_context_create(['http' => ['timeout' => 3, 'ignore_errors' => true]]);
    $body = @file_get_contents("{$c['movie_url']}/api/movies/{$movieId}", false, $ctx);
    if ($body === false || !isset($http_response_header[0])) {
        send_error('Không gọi được Movie Service để kiểm tra movieId', 503, 'MOVIE_SERVICE_UNAVAILABLE');
    }
    preg_match('#\s(\d{3})\s#', $http_response_header[0] . ' ', $m);
    $code = (int) ($m[1] ?? 0);
    if ($code === 404) {
        send_error("Không tồn tại phim có movieId = $movieId", 400, 'MOVIE_NOT_FOUND');
    }
    if ($code !== 200) {
        send_error('Movie Service trả lỗi khi kiểm tra movieId', 503, 'MOVIE_SERVICE_UNAVAILABLE');
    }
}
