<?php
/**
 * Lịch chiếu cuốn chiếu: đảm bảo AUTO_SCHEDULE_DAYS ngày tới (tính từ hôm nay) luôn có suất chiếu.
 * Chỉ sinh cho NGÀY CHƯA CÓ suất nào → không đụng tới suất đã có / đã có người đặt; xóa lẻ một suất cũng không bị sinh lại.
 * Danh sách phim lấy qua API của Movie Service (không đọc movie_db); Movie sập thì dùng các phim đã có trong showtime_db.
 * Tắt: AUTO_SCHEDULE_DAYS=0.
 */

const SCHEDULE_CINEMAS = ['CGV Vincom Đồng Khởi', 'Lotte Cinema Cantavil', 'BHD Star Bitexco'];
const SCHEDULE_SLOTS   = ['09:30', '12:15', '15:00', '17:45', '20:30', '22:45'];

function ensure_schedule(): void
{
    $days = (int) env('AUTO_SCHEDULE_DAYS', '7');
    if ($days <= 0) {
        return;
    }
    $today = new DateTimeImmutable('today');
    $end   = $today->modify("+$days day");
    $missing = schedule_missing_days($today, $end, $days);
    if (!$missing) {
        return;                                    // trường hợp thường gặp: 1 truy vấn nhẹ rồi thoát
    }

    $pdo = db();
    // Khóa theo tên để hai request đồng thời không cùng sinh lịch (MySQL 8 và MariaDB đều hỗ trợ)
    $got = (int) $pdo->query("SELECT GET_LOCK('showtime_schedule', 5)")->fetchColumn();
    if ($got !== 1) {
        return;
    }
    try {
        $missing = schedule_missing_days($today, $end, $days);   // kiểm tra lại sau khi giữ khóa
        $movieIds = schedule_movie_ids();
        if (!$missing || !$movieIds) {
            return;
        }
        $ins = $pdo->prepare('INSERT INTO showtimes (movie_id, cinema, room, `time`, price) VALUES (?, ?, ?, ?, ?)');
        $pdo->beginTransaction();
        foreach ($missing as $day) {
            foreach (schedule_for_day($day, $movieIds) as $row) {
                $ins->execute($row);
            }
        }
        $pdo->commit();
    } catch (Throwable $e) {
        if ($pdo->inTransaction()) {
            $pdo->rollBack();
        }
        error_log('[showtime-service] không sinh được lịch chiếu: ' . $e->getMessage());
    } finally {
        $pdo->query("SELECT RELEASE_LOCK('showtime_schedule')");
    }
}

/** Các ngày trong [today, end) chưa có suất chiếu nào. */
function schedule_missing_days(DateTimeImmutable $today, DateTimeImmutable $end, int $days): array
{
    $st = db()->prepare('SELECT DISTINCT DATE(`time`) AS d FROM showtimes WHERE `time` >= ? AND `time` < ?');
    $st->execute([$today->format('Y-m-d H:i:s'), $end->format('Y-m-d H:i:s')]);
    $have = array_flip(array_map('strval', array_column($st->fetchAll(), 'd')));
    $out = [];
    for ($i = 0; $i < $days; $i++) {
        $d = $today->modify("+$i day");
        if (!isset($have[$d->format('Y-m-d')])) {
            $out[] = $d;
        }
    }
    return $out;
}

/** id các phim đang có: hỏi Movie Service, lỗi thì lấy từ các suất chiếu đã có. */
function schedule_movie_ids(): array
{
    $c = config();
    $ctx = stream_context_create(['http' => ['timeout' => 3, 'ignore_errors' => true]]);
    $body = @file_get_contents("{$c['movie_url']}/api/movies", false, $ctx);
    $json = $body !== false ? json_decode($body, true) : null;
    if (is_array($json) && ($json['status'] ?? '') === 'success' && is_array($json['data'] ?? null)) {
        $ids = array_values(array_filter(array_map(fn($m) => (int) ($m['id'] ?? 0), $json['data'])));
        if ($ids) {
            sort($ids);
            return $ids;
        }
    }
    return array_map('intval', db()->query('SELECT DISTINCT movie_id FROM showtimes ORDER BY movie_id')->fetchAll(PDO::FETCH_COLUMN));
}

/**
 * Lịch một ngày: mỗi phim chiếu ở cả 3 rạp, mỗi rạp 2 suất lệch nhau; mỗi phim một phòng riêng nên không trùng phòng.
 * Giá: 75.000đ; suất trước 12h -10.000đ; suất từ 17h +10.000đ; thứ 7, CN +15.000đ.
 */
function schedule_for_day(DateTimeImmutable $day, array $movieIds): array
{
    $rows = [];
    $n = count(SCHEDULE_SLOTS);
    $weekend = in_array((int) $day->format('N'), [6, 7], true);
    foreach ($movieIds as $i => $movieId) {
        foreach (SCHEDULE_CINEMAS as $c => $cinema) {
            foreach ([($i + $c) % $n, ($i + $c + 3) % $n] as $slot) {
                $hm = SCHEDULE_SLOTS[$slot];
                $hour = (int) substr($hm, 0, 2);
                $price = 75000 + ($hour < 12 ? -10000 : 0) + ($hour >= 17 ? 10000 : 0) + ($weekend ? 15000 : 0);
                $rows[] = [$movieId, $cinema, 'P' . ($i % 8 + 1), $day->format('Y-m-d') . " $hm:00", $price];
            }
        }
    }
    return $rows;
}
