from datetime import UTC, datetime
from pathlib import Path

from . import snapshot
from .client import Client

ENDPOINT = "prices_for_dates"
PATH = "/aviasales/v3/prices_for_dates"
TIERS = {"near": range(0, 3), "far": range(3, 12)}  # смещения месяца вылета от текущего


def months(tier: str, today: datetime) -> list[str]:
    return [f"{today.year + (today.month - 1 + k) // 12}-{(today.month - 1 + k) % 12 + 1:02d}" for k in TIERS[tier]]


def run(tier: str, client: Client, pairs, data_dir: Path, now: datetime | None = None) -> Path:
    now = now or datetime.now(UTC)
    # shortcut: одна страница до 1000 билетов на маршрут×месяц; если упрёмся — добавить page
    params_list = [{"origin": o, "destination": d, "departure_at": month,
                    "one_way": "true", "direct": "false", "sorting": "price",
                    "currency": "rub", "limit": 1000, "page": 1}
                   for o, d in pairs for month in months(tier, now)]
    return snapshot.run("aviasales", ENDPOINT, tier, client, PATH, params_list, data_dir, now)
