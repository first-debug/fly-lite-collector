#!/bin/sh
# Копия сырых файлов в S3 (Yandex Object Storage). Ключи и бакет берутся из .env.
set -eu
cd "$(dirname "$0")"
die() { echo "backup: $*" >&2; exit 1; }
[ -f .env ] || die "нет $PWD/.env"
command -v rclone >/dev/null || die "rclone не установлен (sudo pacman -S rclone)"
[ -d data/raw ] || die "нет $PWD/data/raw: ещё не было ни одного прогона sweep"
set -a; . ./.env; set +a
for v in AWS_ACCESS_KEY_ID AWS_SECRET_ACCESS_KEY S3_BUCKET; do
  eval "[ -n \"\${$v:-}\" ]" || die "$v не задан в .env"
done
export RCLONE_CONFIG_S3_TYPE=s3 RCLONE_CONFIG_S3_PROVIDER=Other RCLONE_CONFIG_S3_ENV_AUTH=true \
  RCLONE_CONFIG_S3_ENDPOINT="${S3_ENDPOINT:-https://storage.yandexcloud.net}" \
  RCLONE_CONFIG_S3_REGION="${S3_REGION:-ru-central1}"
# copy, а не sync: удалённое локально в бакете остаётся. 7d — догоняем, если ПК был выключен.
# --size-only: не перезаписываем объекты ради даты изменения (ключу хватает прав только на загрузку).
exec rclone copy data/raw "s3:$S3_BUCKET/raw" --max-age 7d --no-traverse --size-only \
  --exclude '*.part' --s3-no-check-bucket -v
