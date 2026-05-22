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
from ._common import attach_yes_flag, get_client


def _args_raw(sp):
    sp.add_argument("op", help="nom d'op GraphQL (ex: TweetResultByRestId)")
    sp.add_argument("--vars",
                    help='JSON des variables (ex: \'{"tweetId":"123"}\')')
    sp.add_argument("--method", default="GET", choices=["GET", "POST"])
    attach_yes_flag(sp)


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
    try:
        variables = json.loads(args.vars) if args.vars else {}
    except json.JSONDecodeError as e:
        raise XaError(
            "invalid_json",
            f"--vars n'est pas du JSON valide: {e}",
            hint='quote correctement: --vars \'{"k":"v"}\'',
        )
    data = client.call(args.op, variables, method=args.method)
    return ok(data)
