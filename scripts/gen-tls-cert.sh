#!/usr/bin/env bash
# Sinh chứng chỉ TLS cục bộ cho API Gateway (services-py/gateway/certs/).
# Ưu tiên dùng mkcert (tin cậy sẵn trên trình duyệt), fallback sang openssl tự ký.
set -euo pipefail

cd "$(dirname "$0")/.."
CERT_DIR="services-py/gateway/certs"
mkdir -p "$CERT_DIR"

CERT_FILE="$CERT_DIR/localhost.crt"
KEY_FILE="$CERT_DIR/localhost.key"

if command -v mkcert >/dev/null 2>&1; then
  mkcert -cert-file "$CERT_FILE" -key-file "$KEY_FILE" localhost 127.0.0.1 ::1
  echo "Da tao chung chi bang mkcert: $CERT_FILE"
elif command -v openssl >/dev/null 2>&1; then
  openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
    -keyout "$KEY_FILE" -out "$CERT_FILE" \
    -subj "/CN=localhost" \
    -addext "subjectAltName=DNS:localhost,IP:127.0.0.1"
  echo "Da tao chung chi tu ky bang openssl: $CERT_FILE"
else
  echo "[LOI] Chua co mkcert hoac openssl trong PATH. Hay cai mkcert hoac openssl roi chay lai." >&2
  exit 1
fi
