"""Recherche LOCALE dans les signets (le flag `xa bookmarks --grep`).

Pourquoi local plutôt que la recherche serveur (`--query`) ? La recherche
serveur de X (`BookmarkSearchTimeline`) fait du match de mots plein-texte :
elle est rapide mais rate les variantes et synonymes (chercher "design" ne
ramène pas un signet qui parle de "motion"/"animation"). Le grep local
travaille sur le corpus COMPLET déjà paginé : multi-termes OR/AND, regex,
insensible à la casse. Les deux méthodes sont complémentaires.

Ce module ne fait PAS de réseau : il reçoit les rows (récupérées par
`content.py` via le client) et gère le matching + le cache disque. Ça le
rend testable sans cookies ni WebSocket.
"""

from __future__ import annotations

import json
import re
import time
from typing import Callable

from .settings import BOOKMARKS_CACHE_FILE, BOOKMARKS_CACHE_TTL

# Champs d'un row de signet sur lesquels le grep cherche par défaut.
SEARCHED_FIELDS = ("text", "author", "author_name")


def build_matcher(
    pattern: str,
    *,
    regex: bool = False,
    require_all: bool = False,
) -> Callable[[dict], bool]:
    """Construit un prédicat row -> bool pour `--grep`.

    - `regex=True` : `pattern` est une regex (insensible casse) testée telle
      quelle sur le texte concaténé du row.
    - sinon : `pattern` est découpé en termes sur les espaces ; chaque terme
      est une sous-chaîne (insensible casse). `require_all=False` (défaut) =
      OR (au moins un terme), `require_all=True` = AND (tous les termes).
      Le OR par défaut maximise le rappel, ce qui est le but recherché.
    """
    if regex:
        rx = re.compile(pattern, re.IGNORECASE | re.DOTALL)

        def _match_regex(row: dict) -> bool:
            return bool(rx.search(_haystack(row)))

        return _match_regex

    terms = [t.lower() for t in pattern.split() if t.strip()]
    if not terms:
        # Pattern vide -> ne filtre rien (tout matche), évite un grep no-op
        # qui renverrait 0 résultat silencieusement.
        return lambda row: True

    combine = all if require_all else any

    def _match_terms(row: dict) -> bool:
        hay = _haystack(row).lower()
        return combine(t in hay for t in terms)

    return _match_terms


def _haystack(row: dict) -> str:
    """Concatène les champs cherchables d'un row en une seule chaîne."""
    return " ".join(str(row.get(f) or "") for f in SEARCHED_FIELDS)


def grep(rows: list[dict], matcher: Callable[[dict], bool]) -> list[dict]:
    """Filtre les rows par le prédicat (ordre préservé)."""
    return [r for r in rows if matcher(r)]


# ─────────── cache disque du corpus ───────────

def load_cache(ttl: int = BOOKMARKS_CACHE_TTL, path=None) -> dict | None:
    """Retourne le blob caché {rows, fetched_at, complete} si frais, sinon None.

    None si absent, illisible, ou périmé (> `ttl` secondes) — le caller repagine.
    `path` surchargeable pour les tests (défaut: BOOKMARKS_CACHE_FILE).
    """
    p = path or BOOKMARKS_CACHE_FILE
    if not p.exists():
        return None
    try:
        blob = json.loads(p.read_text())
        age = time.time() - float(blob["fetched_at"])
        if age > ttl:
            return None
        blob.setdefault("complete", False)
        return blob
    except (json.JSONDecodeError, KeyError, ValueError, OSError):
        return None


def save_cache(rows: list[dict], fetched_at: float,
               complete: bool = False, path=None) -> None:
    """Persiste le corpus + l'horodatage + le flag d'exhaustivité."""
    p = path or BOOKMARKS_CACHE_FILE
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(
        {"fetched_at": fetched_at, "count": len(rows),
         "complete": complete, "rows": rows},
        ensure_ascii=False,
    ))
