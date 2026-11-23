# collector

Сборщик цен Aviasales Data API (внутренние рейсы РФ) в сырые файлы
`data/raw/aviasales/prices_for_dates/YYYY/MM/DD/<run_id>.jsonl.gz`, по строке на запрос.

```bash
uv sync
echo 'TRAVELPAYOUTS_TOKEN=...' > .env
uv run collector routes                          # data/routes.txt из справочников (токен не нужен)
uv run --env-file .env collector sweep near      # текущий месяц + 2 следующих
uv run --env-file .env collector sweep far       # месяцы с 4-го по 12-й
uv run pytest
```

Настройки: `TRAVELPAYOUTS_TOKEN`, `DATA_DIR` (по умолчанию `data`), `RATE_PER_MIN` (по умолчанию 50), `LOG_LEVEL` (по умолчанию INFO).
Итог прогона — строка JSON в `data/collector.log`; `data/last_success_<near|far>` — последний прогон с ошибками ≤ 20%.

Расписание: `sudo pacman -S cronie && sudo systemctl enable --now cronie && crontab crontab`.

Копия в S3: `./backup.sh` (нужен `rclone`) копирует `data/raw` в бакет за последние 7 дней, каждые 6 ч по crontab.
В `.env`: `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `S3_BUCKET` (необязательно `S3_ENDPOINT`, `S3_REGION`, по умолчанию Yandex Object Storage).
