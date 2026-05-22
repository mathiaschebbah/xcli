"""Régénération du catalogue d'ops GraphQL : `xa harvest-ops`.

Télécharge les bundles JS publics de x.com, extrait via regex toutes les
ops `{queryId, operationName, operationType}`, et écrit le résultat dans
`src/xa/data/x_ops.json` (le fichier embarqué dans le package).

À relancer quand X push une mise à jour et qu'on voit beaucoup de 404 ou
`unknown_op`. Le fichier généré écrase l'ancien.

Note: ne touche PAS à `~/.config/xa/features.json` (qui est un dict
`{flag: bool}` géré par auto-discovery dans `core/client.py`). Le
`x_features_inventory.json` écrit ici est un inventaire informatif des
flags vus dans les bundles, distinct des flags effectivement utilisés.
"""

from __future__ import annotations

import json
import re
from importlib.resources import files
from pathlib import Path

import requests

from ..core.output import ok
from ..core.registry import register
from ..core.settings import USER_AGENT

BASE = "https://x.com"

RE_OP = re.compile(
    r'queryId:"(?P<qid>[A-Za-z0-9_\-]+)",'
    r'operationName:"(?P<op>[A-Za-z0-9_]+)",'
    r'operationType:"(?P<typ>query|mutation|subscription)"'
)
RE_FEATURE = re.compile(r'"([a-z][a-zA-Z0-9_]+_enabled)"')
RE_BUNDLE_URL = re.compile(
    r'https://abs\.twimg\.com/responsive-web/client-web/[A-Za-z0-9./_\-]+\.js'
)


def _fetch(url: str) -> bytes:
    r = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=30)
    r.raise_for_status()
    return r.content


def _args_harvest(sp):
    sp.add_argument(
        "--out-dir",
        help="dossier où écrire x_ops.json (défaut: le data/ du package, "
             "écrase celui embarqué)",
    )


@register("harvest-ops", configure=_args_harvest)
def cmd_harvest_ops(args) -> dict:
    """Régénère x_ops.json + x_features.json depuis les bundles JS de x.com.

    À utiliser quand X met à jour son client et que les anciens queryId
    ne fonctionnent plus (beaucoup de 404 ou erreurs `unknown_op`).
    """
    html = _fetch(f"{BASE}/").decode("utf-8", "ignore")
    bundles = sorted(set(RE_BUNDLE_URL.findall(html)))

    blobs: dict[str, bytes] = {}
    for u in bundles:
        try:
            blobs[u] = _fetch(u)
        except Exception:
            continue

    # ops
    found: dict[str, dict] = {}
    for url, content in blobs.items():
        text = content.decode("utf-8", "ignore")
        for m in RE_OP.finditer(text):
            qid, op, typ = m.group("qid"), m.group("op"), m.group("typ")
            cur = found.get(qid)
            if cur:
                cur["sources"].add(Path(url).name)
            else:
                found[qid] = {
                    "queryId": qid,
                    "operationName": op,
                    "operationType": typ,
                    "sources": {Path(url).name},
                }
    ops_list = []
    for op in sorted(found.values(), key=lambda x: x["operationName"].lower()):
        op["sources"] = sorted(op["sources"])
        ops_list.append(op)

    by_type = {"query": 0, "mutation": 0, "subscription": 0}
    for op in ops_list:
        by_type[op["operationType"]] += 1

    # features
    feats: dict[str, set[str]] = {}
    for url, content in blobs.items():
        text = content.decode("utf-8", "ignore")
        for m in RE_FEATURE.finditer(text):
            feats.setdefault(m.group(1), set()).add(Path(url).name)
    feats_dict = {k: sorted(v) for k, v in sorted(feats.items())}

    # Cible : par défaut, le data/ embarqué du package (pour persister)
    if args.out_dir:
        out_dir = Path(args.out_dir)
    else:
        out_dir = Path(str(files("xa") / "data"))
    out_dir.mkdir(parents=True, exist_ok=True)

    ops_path = out_dir / "x_ops.json"
    feats_path = out_dir / "x_features_inventory.json"
    ops_path.write_text(json.dumps({
        "total": len(ops_list),
        "by_type_count": by_type,
        "operations": ops_list,
    }, indent=2))
    feats_path.write_text(json.dumps({
        "total": len(feats_dict),
        "features": feats_dict,
    }, indent=2))

    return ok({
        "bundles_scanned": list(blobs.keys()),
        "ops_total": len(ops_list),
        "ops_by_type": by_type,
        "features_total": len(feats_dict),
        "ops_written_to": str(ops_path),
        "features_written_to": str(feats_path),
    })
