from __future__ import annotations

import json
from typing import Any


def json_bytes(payload: Any) -> bytes:
    return json.dumps(payload, indent=2, sort_keys=True).encode("utf-8")


def json_text(payload: Any) -> str:
    return json.dumps(payload, indent=2, sort_keys=True)


def read_json_bytes(data: bytes) -> Any:
    return json.loads(data.decode("utf-8"))

