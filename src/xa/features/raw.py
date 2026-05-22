"""Échappatoire générique : `xa raw <OpName> --vars '{}'`.

Appelle n'importe quelle op GraphQL du catalogue (158 ops). Utile pour
les ops avancées non couvertes par les sous-commandes spécifiques
(BookmarkSearchTimeline, ListMembers, etc.).

Note : on ne peut pas savoir au moment de `@register` si une op donnée
est une mutation. On enregistre la commande comme `is_write=False`
(dispatcher n'exige donc PAS de --yes), MAIS on re-vérifie dans cmd_raw
si l'op résolue est une mutation, auquel cas on raise sans --yes.
"""

from __future__ import annotations

import json

from ..core.errors import XaError
from ..core.ops import load_ops
from ..core.output import ok
from ..core.registry import register
from ._common import get_client


def _args_raw(sp):
    sp.add_argument("op", help="nom d'op GraphQL (ex: TweetResultByRestId)")
    sp.add_argument("--vars",
                    help='JSON des variables (ex: \'{"tweetId":"123"}\')')
    sp.add_argument("--method", default="GET", choices=["GET", "POST"])
    sp.add_argument("--yes", action="store_true",
                    help="obligatoire si l'op résolue est une mutation")


@register("raw", configure=_args_raw)
def cmd_raw(args) -> dict:
    """Appel GraphQL générique (n'importe quelle op du catalogue)."""
    client = get_client()
    ops = load_ops()
    op = ops.get(args.op)
    if not op:
        raise XaError(
            "unknown_op",
            f"op '{args.op}' pas dans le catalogue",
            hint="`xa ops --filter X` pour chercher",
        )
    if op["operationType"] == "mutation" and not args.yes:
        raise XaError(
            "confirmation_required",
            f"raw mutation '{args.op}' modifie ton compte X et requiert --yes",
            hint="ajoute --yes pour confirmer explicitement",
        )
    variables = json.loads(args.vars) if args.vars else {}
    data = client.call(args.op, variables, method=args.method)
    return ok(data)
