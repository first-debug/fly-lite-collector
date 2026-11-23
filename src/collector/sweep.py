import gzip
import json
import logging
import time
from datetime import UTC, datetime
from pathlib import Path

from .client import Client

ENDPOINT = "prices_for_dates"
PATH = "/aviasales/v3/prices_for_dates"
log = logging.getLogger(__name__)
TIERS = {"near": range(0, 3), "far": range(3, 12)}  # смещения месяца вылета от текущего


def months(tier: str, today: datetime) -> list[str]:
    return [f"{today.year + (today.month - 1 + k) // 12}-{(today.month - 1 + k) % 12 + 1:02d}" for k in TIERS[tier]]


def run(tier: str, client: Client, pairs, data_dir: Path, now: datetime | None = None) -> Path:
    now = now or datetime.now(UTC)
    run_id = f"{now:%Y-%m-%dT%H%M%SZ}-{tier}"
    out = data_dir / "raw/aviasales" / ENDPOINT / f"{now:%Y/%m/%d}" / f"{run_id}.jsonl.gz"
    out.parent.mkdir(parents=True, exist_ok=True)
    part = out.with_name(out.name + ".part")
    started, total, errors = time.monotonic(), 0, 0
    planned = len(pairs) * len(TIERS[tier])
    log.info("старт %s: %d маршрутов × %d мес. = %d запросов, файл %s", run_id, len(pairs), len(TIERS[tier]), planned, out)
    try:
        with gzip.open(part, "wt", encoding="utf-8") as f:
            for origin, destination in pairs:
                for month in months(tier, now):
                    # shortcut: одна страница до 1000 билетов на маршрут×месяц; если упрёмся — добавить page
                    params = {"origin": origin, "destination": destination, "departure_at": month,
                              "one_way": "true", "direct": "false", "sorting": "price",
                              "currency": "rub", "limit": 1000, "page": 1}
                    status, body = client.get(PATH, params)
                    fetched_at = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
                    f.write(json.dumps({"run_id": run_id, "endpoint": ENDPOINT, "params": params,
                                        "fetched_at": fetched_at, "http_status": status, "body": body},
                                       ensure_ascii=False) + "\n")
                    total += 1
                    errors += status != 200
                    if total % 50 == 0:
                        log.info("%s: %d/%d запросов, ошибок %d, %d с", run_id, total, planned, errors, time.monotonic() - started)
    finally:
        part.rename(out)
        error_share = round(errors / total, 3) if total else 1.0  # 0 запросов — тоже провал
        log.info("итог %s", json.dumps({"run_id": run_id, "tier": tier, "requests": total, "errors": errors,
                                         "error_share": error_share, "seconds": round(time.monotonic() - started),
                                         "file": str(out)}))
    if error_share <= 0.2:
        (data_dir / f"last_success_{tier}").write_text(run_id + "\n")
    return out
