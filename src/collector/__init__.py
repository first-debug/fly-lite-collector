import logging
import os
import signal
import sys
from pathlib import Path

USAGE = "usage: collector routes | collector sweep near|far | collector weather | collector metar | collector cbr"


def main() -> None:
    from . import routes, sources, sweep

    from .client import Client

    # SIGTERM (выключение ПК) → обычный выход: finally дописывает gzip и снимает .part
    signal.signal(signal.SIGTERM, lambda *_: sys.exit(1))

    logging.basicConfig(level=os.environ.get("LOG_LEVEL", "INFO"), format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    logging.getLogger("httpx").setLevel(logging.WARNING)  # без строки на каждый запрос
    data_dir = Path(os.environ.get("DATA_DIR", "data"))
    match sys.argv[1:]:
        case ["routes"]:
            logging.info("routes: %d пар", routes.update(data_dir))
        case ["sweep", ("near" | "far") as tier]:
            token = os.environ.get("TRAVELPAYOUTS_TOKEN") or sys.exit("TRAVELPAYOUTS_TOKEN не задан (collector/.env)")
            client = Client(token, float(os.environ.get("RATE_PER_MIN", 50)))
            sweep.run(tier, client, routes.load(data_dir), data_dir)
        case ["weather"]:
            sources.weather(routes.load_airports(data_dir), data_dir)
        case ["metar"]:
            sources.metar_taf(routes.load_airports(data_dir), data_dir)
        case ["cbr"]:
            sources.cbr(data_dir)
        case _:
            sys.exit(USAGE)
