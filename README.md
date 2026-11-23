# collector

Сборщик цен Aviasales Data API (внутренние рейсы РФ) в сырые файлы
`data/raw/aviasales/prices_for_dates/YYYY/MM/DD/<run_id>.jsonl.gz`, по строке на запрос.

```bash
uv sync
echo 'TRAVELPAYOUTS_TOKEN=...' > .env
uv run collector routes                          # data/routes.txt из справочников (токен не нужен)
uv run --env-file .env collector sweep near      # текущий месяц + 2 следующих
uv run --env-file .env collector sweep far       # месяцы с 4-го по 12-й
uv run collector weather                         # Open-Meteo: прогноз на 16 дней по аэропортам (без ключа)
uv run collector metar                           # aviationweather.gov: METAR и TAF по аэропортам (без ключа)
uv run collector cbr                             # ЦБ РФ: курсы валют на сегодня, XML как есть (без ключа)
uv run pytest
```

`collector routes` заодно пишет `data/airports.txt` (IATA, ICAO, широта, долгота) для weather и metar; у аэропортов без станции METAR вместо ICAO стоит `-`.
Сырьё лежит так же: `data/raw/<openmeteo|aviationweather|cbr>/<эндпоинт>/YYYY/MM/DD/<run_id>.jsonl.gz`, итог прогона с `tier` = `weather|metar|taf|cbr`.

Настройки: `TRAVELPAYOUTS_TOKEN`, `DATA_DIR` (по умолчанию `data`), `RATE_PER_MIN` (по умолчанию 50), `LOG_LEVEL` (по умолчанию INFO).
Итог прогона — строка JSON в `data/collector.log`; `data/last_success_<tier>` — последний прогон с ошибками ≤ 20%.

Расписание:
`sudo pacman -S cronie
sudo systemctl enable --now cronie`

 Из папки `collector`:
`sed "s|^COLLECTOR_DIR=.*|COLLECTOR_DIR=$PWD|" crontab | crontab -`

Копия в S3: `./backup.sh` (нужен `rclone`) копирует `data/raw` в бакет за последние 30 дней, каждые 6 ч по crontab.
В `.env`: `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `S3_BUCKET` (необязательно `S3_ENDPOINT`, `S3_REGION`, по умолчанию Yandex Object Storage).

## Логи в Grafana Cloud

Alloy читает `data/collector.log` и отправляет строки в Loki (метки `job="collector"`, `host`, `level`).

Установка на Arch:
```bash
sudo pacman -S grafana-alloy
```

Конфигурация Alloy:
```bash
mkdir -p ~/.local/share/flylite-alloy ~/.config/systemd/user
ln -sf "$PWD/.env" ~/.local/share/flylite-alloy/.env
ln -sf "$PWD/alloy/config.alloy" ~/.local/share/flylite-alloy/config.alloy
cp alloy/flylite-alloy.service ~/.config/systemd/user/
```

Запуск:
```bash
systemctl --user daemon-reload && systemctl --user enable --now flylite-alloy
loginctl enable-linger "$USER"   # служба работает и без входа в систему
```

Команды выполняются из папки `collector`. В `.env`: `LOKI_LOG_FILE` (абсолютный путь к `data/collector.log`), `LOKI_URL` (…/loki/api/v1/push), `LOKI_USER` (числовой User ID), `LOKI_TOKEN` (токен с правом `logs:write`).

Алерты в Grafana (Alerting → New alert rule, источник — Loki):

| Алерт | Запрос | Условие |
|---|---|---|
| Сбор встал | `sum(count_over_time({job="collector"} \|= "итог" \| regexp "итог (?P<s>\\{.*\\})" \| line_format "{{.s}}" \| json \| tier="near" [12h]))` | < 1, «No data» → Alerting |
| Много ошибок | `max(max_over_time({job="collector"} \|= "итог" \| regexp "итог (?P<s>\\{.*\\})" \| line_format "{{.s}}" \| json \| unwrap error_share [6h]))` | > 0.2 |
| Падение | `sum(count_over_time({job="collector"} \|~ "ERROR\|CRITICAL\|Traceback" [15m]))` | > 0 |
