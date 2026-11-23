import json
import logging
from pathlib import Path

import httpx

AIRPORTS_URL = "https://api.travelpayouts.com/data/ru/airports.json"
ROUTES_URL = "https://api.travelpayouts.com/data/routes.json"
log = logging.getLogger(__name__)


def domestic_pairs(airports: list[dict], routes: list[dict]) -> list[tuple[str, str]]:
    city = {a["code"]: a["city_code"] for a in airports if a["country_code"] == "RU" and a.get("flightable")}
    pairs = {
        (city[r["departure_airport_iata"]], city[r["arrival_airport_iata"]])
        for r in routes
        if r["departure_airport_iata"] in city and r["arrival_airport_iata"] in city
    }
    return sorted(p for p in pairs if p[0] != p[1])


def update(data_dir: Path) -> int:
    refs = data_dir / "refs"
    refs.mkdir(parents=True, exist_ok=True)
    docs = {}
    for name, url in (("airports", AIRPORTS_URL), ("routes", ROUTES_URL)):
        log.info("скачиваю %s", url)
        r = httpx.get(url, timeout=60, follow_redirects=True)
        r.raise_for_status()
        (refs / f"{name}.json").write_bytes(r.content)
        docs[name] = r.json()
    pairs = domestic_pairs(docs["airports"], docs["routes"])
    if not pairs:
        raise RuntimeError("справочник дал 0 маршрутов, старый routes.txt остаётся без изменений")
    tmp = data_dir / "routes.txt.tmp"
    tmp.write_text("".join(f"{o} {d}\n" for o, d in pairs))
    tmp.replace(data_dir / "routes.txt")
    return len(pairs)


def load(data_dir: Path) -> list[tuple[str, str]]:
    path = data_dir / "routes.txt"
    if not path.is_file():
        raise SystemExit(f"{path} не найден: сначала запустите `collector routes`")
    pairs = [tuple(line.split()) for line in path.read_text().splitlines() if line.strip()]
    if not pairs or any(len(p) != 2 for p in pairs):
        raise SystemExit(f"{path} пуст или испорчен: перезапустите `collector routes`")
    return pairs
