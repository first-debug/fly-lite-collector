import gzip
import json
from datetime import UTC, date, datetime

import httpx
import pytest
import respx

from collector import routes, sweep
from collector.client import BASE_URL, AuthError, Client

URL = BASE_URL + sweep.PATH


def make_client(sleeps):
    return Client("t", rate_per_min=60, sleep=sleeps.append)


@respx.mock
def test_429_retries_with_backoff_and_slows_down():
    respx.get(URL).mock(side_effect=[httpx.Response(429), httpx.Response(429), httpx.Response(200, json={"data": []})])
    sleeps = []
    c = make_client(sleeps)
    assert c.get(sweep.PATH, {}) == (200, {"data": []})
    assert 2 in sleeps and 4 in sleeps
    assert c.interval == 4  # 1 с → удвоено дважды


@respx.mock
def test_gives_up_after_retries_and_returns_error():
    respx.get(URL).mock(return_value=httpx.Response(503, text="down"))
    sleeps = []
    assert make_client(sleeps).get(sweep.PATH, {}) == (503, "down")
    assert [s for s in sleeps if s >= 2] == [2, 4, 8, 16, 32]


@respx.mock
def test_401_stops():
    respx.get(URL).mock(return_value=httpx.Response(401, text="Unauthorized"))
    with pytest.raises(AuthError):
        make_client([]).get(sweep.PATH, {})


def test_months_wrap_year():
    assert sweep.months("near", date(2026, 11, 23)) == ["2026-11", "2026-12", "2027-01"]
    assert sweep.months("far", date(2026, 11, 23))[-1] == "2027-10"


def test_domestic_pairs():
    airports = [{"code": "SVO", "city_code": "MOW", "country_code": "RU", "flightable": True},
                {"code": "DME", "city_code": "MOW", "country_code": "RU", "flightable": True},
                {"code": "LED", "city_code": "LED", "country_code": "RU", "flightable": True},
                {"code": "IST", "city_code": "IST", "country_code": "TR", "flightable": True}]
    rs = [{"departure_airport_iata": a, "arrival_airport_iata": b}
          for a, b in [("SVO", "LED"), ("DME", "LED"), ("SVO", "DME"), ("SVO", "IST")]]
    assert routes.domestic_pairs(airports, rs) == [("MOW", "LED")]


@respx.mock
def test_sweep_writes_every_response(tmp_path):
    respx.get(URL).mock(side_effect=[httpx.Response(200, json={"data": [{"price": 1}]}), httpx.Response(400, json={})] * 3)
    out = sweep.run("near", make_client([]), [("MOW", "LED"), ("LED", "MOW")], tmp_path,
                    now=datetime(2026, 11, 23, 6, tzinfo=UTC))
    assert out == tmp_path / "raw/aviasales/prices_for_dates/2026/11/23/2026-11-23T060000Z-near.jsonl.gz"
    lines = [json.loads(l) for l in gzip.open(out, "rt")]
    assert len(lines) == 6 and lines[0]["body"] == {"data": [{"price": 1}]} and lines[1]["http_status"] == 400
    assert lines[0]["params"]["departure_at"] == "2026-11"
    assert not (tmp_path / "last_success_near").exists()  # половина ошибок


def test_load_routes_missing_or_broken(tmp_path):
    with pytest.raises(SystemExit, match="collector routes"):
        routes.load(tmp_path)
    (tmp_path / "routes.txt").write_text("MOW\n")
    with pytest.raises(SystemExit, match="испорчен"):
        routes.load(tmp_path)
    (tmp_path / "routes.txt").write_text("MOW LED\n\n")
    assert routes.load(tmp_path) == [("MOW", "LED")]


@respx.mock
def test_429_slowdown_is_capped():
    respx.get(URL).mock(return_value=httpx.Response(429))
    c = make_client([])
    c.get(sweep.PATH, {})
    assert c.interval == 6
    slow = Client("t", rate_per_min=5, sleep=lambda s: None)  # уже реже 10/мин — не ускоряемся
    slow.get(sweep.PATH, {})
    assert slow.interval == 12


@respx.mock
def test_sweep_keeps_data_when_run_aborts(tmp_path):
    respx.get(URL).mock(side_effect=[httpx.Response(200, json={"data": []}), httpx.Response(401)])
    with pytest.raises(AuthError):
        sweep.run("near", make_client([]), [("MOW", "LED")], tmp_path, now=datetime(2026, 11, 23, 6, tzinfo=UTC))
    [out] = tmp_path.rglob("*.jsonl.gz")
    assert [json.loads(l)["http_status"] for l in gzip.open(out, "rt")] == [200]
    assert not list(tmp_path.rglob("*.part"))
