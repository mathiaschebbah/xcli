"""Catalogue des opérations GraphQL de x.com.

Le catalogue (158 ops) est généré par `xa harvest-ops` (parsing des bundles
JS publics de x.com). Chargé depuis `data/x_ops.json`, embarqué dans le
package via `importlib.resources`.
"""

from __future__ import annotations

import json
from importlib.resources import files

from .errors import XaError


def load_ops() -> dict[str, dict]:
    """Retourne `{operationName: {queryId, operationType, sources}}`."""
    try:
        text = (files("xa") / "data" / "x_ops.json").read_text()
    except FileNotFoundError:
        raise XaError(
            "ops_catalog_missing",
            "Le catalogue x_ops.json est introuvable.",
            hint="lance `xa harvest-ops` pour le régénérer",
        )
    data = json.loads(text)
    return {op["operationName"]: op for op in data["operations"]}
