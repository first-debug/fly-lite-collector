"""Отправка сырых файлов в Ingest API утилитой push из ../ingest.

Файл сначала пишется локально (он же уходит в S3), потом отправляется. Отправленные пути
копятся в data/pushed.txt; что не ушло (Ingest недоступен), дошлёт `collector push`.
"""

import logging
import os
import subprocess
from pathlib import Path

log = logging.getLogger(__name__)


def push(data_dir: Path, files: list[Path]) -> int:
    """Отправляет ещё не отправленные файлы, возвращает число отправленных. Без INGEST_PUSH ничего не делает."""
    binary = os.environ.get("INGEST_PUSH")
    if not binary:
        return 0
    raw, done_file = data_dir / "raw", data_dir / "pushed.txt"
    done = set(done_file.read_text().split()) if done_file.exists() else set()
    sent = 0
    for f in files:
        rel = f.relative_to(raw).as_posix()
        if rel in done:
            continue
        try:  # сбой отправки не должен ронять сбор: файл остался на диске и уйдёт позже
            r = subprocess.run([binary, str(raw), str(f)], capture_output=True, text=True, timeout=600)
        except (OSError, subprocess.TimeoutExpired) as e:
            log.warning("push %s: %s", rel, e)
            continue
        if r.returncode:
            log.warning("push %s: %s", rel, r.stderr.strip())
            continue
        log.info("push %s: %s", rel, r.stderr.strip())
        with done_file.open("a") as fh:
            fh.write(rel + "\n")
        sent += 1
    return sent


def pending(data_dir: Path) -> list[Path]:
    """Все готовые сырые файлы, старые первыми (*.part ещё пишется и сюда не попадает)."""
    return sorted((data_dir / "raw").rglob("*.jsonl.gz"))
