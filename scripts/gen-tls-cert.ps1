# Sinh chứng chỉ TLS cục bộ cho API Gateway (services-py/gateway/certs/).
# Ưu tiên dùng mkcert (tin cậy sẵn trên trình duyệt), fallback sang openssl tự ký.
$ErrorActionPreference = 'Stop'
$repoRoot = Split-Path -Parent $PSScriptRoot
$certDir = Join-Path $repoRoot 'services-py\gateway\certs'
New-Item -ItemType Directory -Force -Path $certDir | Out-Null

$certFile = Join-Path $certDir 'localhost.crt'
$keyFile = Join-Path $certDir 'localhost.key'

if (Get-Command mkcert -ErrorAction SilentlyContinue) {
  & mkcert -cert-file $certFile -key-file $keyFile localhost 127.0.0.1 ::1
  Write-Host "Da tao chung chi bang mkcert: $certFile"
} elseif (Get-Command openssl -ErrorAction SilentlyContinue) {
  & openssl req -x509 -nodes -days 365 -newkey rsa:2048 `
    -keyout $keyFile -out $certFile `
    -subj "/CN=localhost" `
    -addext "subjectAltName=DNS:localhost,IP:127.0.0.1"
  Write-Host "Da tao chung chi tu ky bang openssl: $certFile"
} else {
  Write-Error "Chua co mkcert hoac openssl trong PATH. Hay cai mkcert (khuyen dung: winget install FiloSottile.mkcert) hoac openssl roi chay lai."
  exit 1
}
