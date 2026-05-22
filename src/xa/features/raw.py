"""Échappatoire générique : `xa raw <OpName> --vars '{}'` pour appeler
n'importe quelle op GraphQL du catalogue.

Utile pour les ops avancées non couvertes par les sous-commandes
spécifiques (ex: BookmarkSearchTimeline, ListMembers, etc.).
"""

from __future__ import annotations

import json

from ..core.ops import load_ops
from ..core.output import ok
from ..core.registry import register
from ._common import get_client, require_yes


def _configure_raw(sp):
    sp.add_argument("op", help="nom d'op GraphQL (ex: TweetResultByRestId)")
    sp.add_argument("--vars",
                    help='JSON des variables (ex: \'{"tweetId":"123"}\')')
    sp.add_argument("--method", default="GET", choices=["GET", "POST"])
    sp.add_argument("--yes", action="store_true",
                    help="obligatoire pour les mutations")


@register("raw", configure=_configure_raw, is_write=False)
def cmd_raw(args) -> dict:
    """Appel GraphQL générique (n'importe quelle op du catalogue)."""
    client = get_client()
    ops = load_ops()
    op = ops.get(args.op)
    if not op:
        from ..core.errors import XaError
        raise XaError(
            "unknown_op",
            f"op '{args.op}' pas dans le catalogue",
            hint="`xa ops --filter X` pour chercher",
        )
    if op["operationType"] == "mutation":
        require_yes(args, f"raw mutation {args.op}")
    variables = json.loads(args.vars) if args.vars else {}
    data = client.call(args.op, variables, method=args.method)
    return ok(data)
