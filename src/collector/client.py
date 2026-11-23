import logging
import time

import httpx

log = logging.getLogger(__name__)

BASE_URL = "https://api.travelpayouts.com"
RETRIES = 5  # паузы 2, 4, 8, 16, 32 с


class AuthError(Exception):
    """401/403: скорее всего, проблема с токеном — дальше прогон не имеет смысла."""


class Client:
    def __init__(self, token: str, rate_per_min: float = 50, sleep=time.sleep):
        self.http = httpx.Client(base_url=BASE_URL, headers={"X-Access-Token": token}, timeout=30)
        self.interval = 60 / rate_per_min
        self.sleep = sleep
        self._next_at = 0.0

    def get(self, path: str, params: dict) -> tuple[int | None, object]:
        """(http_status, body). Неудачный ответ после всех повторов тоже возвращается — его сохраняем."""
        for attempt in range(RETRIES + 1):
            wait = self._next_at - time.monotonic()
            if wait > 0:
                self.sleep(wait)
            self._next_at = time.monotonic() + self.interval
            try:
                r = self.http.get(path, params=params)
            except httpx.TransportError as e:
                status, body = None, f"{type(e).__name__}: {e}"
            else:
                status, body = r.status_code, _body(r)
                if status in (401, 403):
                    raise AuthError(f"{status}: {body}")
                if status != 429 and status < 500:
                    return status, body
                if status == 429:
                    self.interval = min(self.interval * 2, max(self.interval, 6))  # сбавляем темп до конца прогона, но не реже 10/мин
            if attempt < RETRIES:
                log.warning("%s %s: статус %s, повтор %d/%d через %d с", path, params, status, attempt + 1, RETRIES, 2 ** (attempt + 1))
                self.sleep(2 ** (attempt + 1))
        log.error("%s %s: сдаюсь после %d повторов, статус %s", path, params, RETRIES, status)
        return status, body


def _body(r: httpx.Response):
    try:
        return r.json()
    except ValueError:
        return r.text
