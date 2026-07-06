from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Literal


LogLevel = Literal["info", "ok", "warn", "err", "now"]


@dataclass(slots=True)
class LogEntry:
    ts: str
    msg: str
    level: LogLevel


def now_entry(msg: str, level: LogLevel = "info") -> LogEntry:
    return LogEntry(ts=datetime.now().strftime("%H:%M:%S"), msg=msg, level=level)
