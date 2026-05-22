"""Contrat de sortie agent-native : `ok()`, `err()`, `emit()`, `select_fields()`.

xa garantit qu'à chaque invocation :
- stdout contient UN SEUL document JSON
- stderr contient les logs (TID init, retries, etc.)
- l'exit code reflète ok/err (0 / 1)

Avec `--human`, la sortie est lisible humain au lieu de JSON.
"""

from __future__ import annotations

import json
import sys
from typing import Any


def ok(data: Any = None, **extras) -> dict:
    """Construit une réponse de succès."""
    out: dict = {"ok": True}
    if data is not None:
        out["data"] = data
    out.update(extras)
    return out


def err(code: str, message: str, hint: str | None = None, **extras) -> dict:
    """Construit une réponse d'erreur typée."""
    out: dict = {"ok": False, "error": code, "message": message}
    if hint:
        out["hint"] = hint
    out.update(extras)
    return out


def emit(payload: dict, human: bool = False) -> int:
    """Écrit la réponse sur stdout et retourne le code de sortie."""
    if human:
        sys.stdout.write(_render_human(payload))
    else:
        sys.stdout.write(json.dumps(payload, ensure_ascii=False, indent=2))
        sys.stdout.write("\n")
    sys.stdout.flush()
    return 0 if payload.get("ok") else 1


def select_fields(rows, fields: str | None):
    """Filtre les champs des rows (list[dict] ou dict) selon `--fields a,b,c`."""
    if not fields:
        return rows
    keys = [k.strip() for k in fields.split(",") if k.strip()]
    if isinstance(rows, dict):
        return {k: rows.get(k) for k in keys}
    return [{k: r.get(k) for k in keys} for r in rows]


def _render_human(payload: dict) -> str:
    if not payload.get("ok"):
        out = f"ERROR [{payload.get('error')}]: {payload.get('message')}\n"
        if payload.get("hint"):
            out += f"hint: {payload['hint']}\n"
        return out
    data = payload.get("data")
    if isinstance(data, list):
        return "\n".join(_short_row(r) for r in data) + "\n"
    if isinstance(data, dict):
        return json.dumps(data, indent=2, ensure_ascii=False) + "\n"
    return f"{data}\n"


def _short_row(r: dict) -> str:
    if "text" in r and "author" in r:
        return f"@{r['author']:<20} {r.get('text', '')[:140]}"
    if "screen_name" in r:
        return (
            f"@{r['screen_name']:<20} "
            f"{(r.get('name') or '')[:30]:<32} "
            f"{(r.get('description') or '')[:80]}"
        )
    return json.dumps(r, ensure_ascii=False)
