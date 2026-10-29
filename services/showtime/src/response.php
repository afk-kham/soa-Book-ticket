<?php
// Helper trả JSON theo hợp đồng chung: {"status":"success","data":...} | {"status":"error","code":"...","message":"..."}

const ERROR_CODES = [
    400 => 'VALIDATION_ERROR', 404 => 'NOT_FOUND', 405 => 'METHOD_NOT_ALLOWED',
    409 => 'CONFLICT', 500 => 'INTERNAL_ERROR', 503 => 'SERVICE_UNAVAILABLE',
];

function send_cors_headers(): void
{
    header('Access-Control-Allow-Origin: *');
    header('Access-Control-Allow-Methods: GET, POST, PUT, DELETE, OPTIONS');
    header('Access-Control-Allow-Headers: Content-Type, Authorization');
    header('Access-Control-Max-Age: 3600');
}

function send_json(int $status, array $payload): void
{
    http_response_code($status);
    send_cors_headers();
    header('Content-Type: application/json; charset=utf-8');
    echo json_encode($payload, JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES);
    exit;
}

function send_success($data, int $status = 200): void
{
    send_json($status, ['status' => 'success', 'data' => $data]);
}

function send_error(string $message, int $status = 400, ?string $code = null): void
{
    send_json($status, [
        'status'  => 'error',
        'code'    => $code ?? (ERROR_CODES[$status] ?? 'ERROR'),
        'message' => $message,
    ]);
}
