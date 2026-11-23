import gzip
import json
import logging
import time
from datetime import UTC, datetime
from pathlib import Path

from .client import Client

log = logging.getLogger(__name__)


def run(source: str, endpoint: str, label: str, client: Client, path: str, params_list: list[dict],
        data_dir: Path, now: datetime | None = None) -> Path:
    """Пишет каждый ответ строкой в data/raw/<source>/<endpoint>/ГГГГ/ММ/ДД/<run_id>.jsonl.gz."""
    now = now or datetime.now(UTC)
    run_id = f"{now:%Y-%m-%dT%H%M%SZ}-{label}"
    out = data_dir / "raw" / source / endpoint / f"{now:%Y/%m/%d}" / f"{run_id}.jsonl.gz"
    out.parent.mkdir(parents=True, exist_ok=True)
    part = out.with_name(out.name + ".part")
    started, total, errors = time.monotonic(), 0, 0
    log.info("старт %s: %d запросов, файл %s", run_id, len(params_list), out)
    try:
        with gzip.open(part, "wt", encoding="utf-8") as f:
            for params in params_list:
                status, body = client.get(path, params)
                fetched_at = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
                f.write(json.dumps({"run_id": run_id, "endpoint": endpoint, "params": params,
                                    "fetched_at": fetched_at, "http_status": status, "body": body},
                                   ensure_ascii=False) + "\n")
                total += 1
                errors += status != 200
                if total % 50 == 0:
                    log.info("%s: %d/%d запросов, ошибок %d, %d с", run_id, total, len(params_list), errors, time.monotonic() - started)
    finally:
        part.rename(out)
        error_share = round(errors / total, 3) if total else 1.0  # 0 запросов — тоже провал
        log.info("итог %s", json.dumps({"run_id": run_id, "tier": label, "requests": total, "errors": errors,
                                         "error_share": error_share, "seconds": round(time.monotonic() - started),
                                         "file": str(out)}))
    if error_share <= 0.2:
        (data_dir / f"last_success_{label}").write_text(run_id + "\n")
    return out
