import logging
import os
import sys
from pathlib import Path

USAGE = "usage: collector routes | collector sweep near|far"


def main() -> None:
    from . import routes, sweep
    from .client import Client

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
        case _:
            sys.exit(USAGE)
