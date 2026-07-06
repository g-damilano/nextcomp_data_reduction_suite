from __future__ import annotations

import json
from functools import lru_cache

from jinja2 import Environment, PackageLoader, StrictUndefined, select_autoescape


@lru_cache(maxsize=1)
def jinja_environment() -> Environment:
    env = Environment(
        loader=PackageLoader("html_renderer", "templates"),
        autoescape=select_autoescape(enabled_extensions=("html", "j2", "xml"), default_for_string=True),
        undefined=StrictUndefined,
        trim_blocks=False,
        lstrip_blocks=False,
        keep_trailing_newline=False,
    )
    env.filters["tojson_stable"] = _tojson_stable
    return env


def _tojson_stable(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
