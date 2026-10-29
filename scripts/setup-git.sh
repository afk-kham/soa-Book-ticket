#!/usr/bin/env bash
# Nhóm trưởng chạy MỘT LẦN để tạo repository mới với đủ nhánh.
#   bash scripts/setup-git.sh https://github.com/<tài-khoản>/soa-datve.git
set -e
cd "$(dirname "$0")/.."
REMOTE="$1"; [ -z "$REMOTE" ] && { echo "Dùng: bash scripts/setup-git.sh <url-repo-rong>"; exit 1; }
git init -b main
git add -A && git commit -m "chore: Baseline V2 — chuẩn hóa hợp đồng, 6 service, admin, client, test tích hợp"
git remote add origin "$REMOTE"
git branch develop
for b in tv1-movie tv2-showtime tv3-user tv4-booking tv5-payment tv6-notification; do git branch "feature/$b"; done
git push -u origin main develop feature/tv1-movie feature/tv2-showtime feature/tv3-user feature/tv4-booking feature/tv5-payment feature/tv6-notification
echo "Xong. Vào GitHub → Settings → Branches: bật 'Require a pull request' cho main và develop."
