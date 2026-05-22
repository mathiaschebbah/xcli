"""Pagination capée pour les commandes qui scrollent (timelines, follows...)."""

from __future__ import annotations

import time
from typing import Callable

from .client import XClient


def paginate_capped(
    client: XClient,
    op: str,
    base_vars: dict,
    parser: Callable[[dict], tuple[list[dict], str | None]],
    limit: int,
    cursor: str | None,
    page_size: int = 40,
    sleep: float = 1.5,
) -> tuple[list[dict], str | None]:
    """Pagine jusqu'à `limit` rows, retourne (rows, next_cursor).

    Si l'API renvoie un cursor identique au précédent, on s'arrête (boucle).
    """
    out: list[dict] = []
    cur = cursor
    while len(out) < limit:
        v = dict(base_vars)
        v["count"] = min(page_size, max(1, limit - len(out)))
        if cur:
            v["cursor"] = cur
        data = client.call(op, v)
        rows, next_cursor = parser(data)
        if not rows:
            break
        out.extend(rows)
        if not next_cursor or next_cursor == cur:
            return out[:limit], None
        cur = next_cursor
        if len(out) < limit:
            time.sleep(sleep)
    return out[:limit], cur
