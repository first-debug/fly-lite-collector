"""Бесплатные источники без ключа: погода, авиапогода, курсы ЦБ. Пишут сырьё так же, как sweep."""
from pathlib import Path

from . import snapshot
from .client import Client

OPEN_METEO = "https://api.open-meteo.com"
AVIATIONWEATHER = "https://aviationweather.gov"
CBR = "https://www.cbr.ru"
DAILY = ("weather_code,temperature_2m_max,temperature_2m_min,precipitation_sum,snowfall_sum,"
         "wind_speed_10m_max,wind_gusts_10m_max")


def weather(airports, data_dir: Path) -> Path:
    # Все аэропорты одним запросом: Open-Meteo принимает списки координат и отвечает списком
    params = {"latitude": ",".join(str(a[2]) for a in airports), "longitude": ",".join(str(a[3]) for a in airports),
              "daily": DAILY, "forecast_days": 16, "timezone": "auto", "wind_speed_unit": "ms"}
    return snapshot.run("openmeteo", "forecast", "weather", Client(None, base_url=OPEN_METEO), "/v1/forecast", [params], data_dir)


def metar_taf(airports, data_dir: Path) -> list[Path]:
    ids = ",".join(a[1] for a in airports if a[1] != "-")
    client = Client(None, base_url=AVIATIONWEATHER)
    return [snapshot.run("aviationweather", kind, kind, client, f"/api/data/{kind}", [{"ids": ids, "format": "json"}], data_dir)
            for kind in ("metar", "taf")]


def cbr(data_dir: Path) -> Path:
    return snapshot.run("cbr", "XML_daily", "cbr", Client(None, base_url=CBR), "/scripts/XML_daily.asp", [{}], data_dir)
