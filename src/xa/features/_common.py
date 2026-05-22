"""Helpers partagés par les features (DRY).

Convention de nommage :
- `args_*`   : configurateurs argparse partagés (publics, dans `_common.py`)
- `_args_*`  : configurateurs argparse locaux à une feature (module-private)
- `run_*`    : runners business-logic (prennent args, retournent dict)
- `get_*`    : factories (client, etc.)

Pour les écritures, marquer la commande avec `is_write=True` dans
`@register(...)`. Le dispatcher (`cli.py:_dispatch`) injecte `--yes` et
valide sa présence — il n'y a PAS de helper `require_yes()` à appeler
manuellement (sauf cas dynamique comme `xa raw <op>` où l'op n'est
connue qu'à l'exécution).
"""

from __future__ import annotations

from typing import Callable, Literal

from ..core.auth import read_cookies
from ..core.client import XClient
from ..core.errors import XaError
from ..core.ops import load_ops
from ..core.output import ok, select_fields
from ..core.pagination import paginate_capped
from ..core.settings import DEFAULT_LIMIT


# ─────────── client / user resolution ───────────

def get_client() -> XClient:
    """Construit un XClient depuis les cookies sauvegardés."""
    return XClient(read_cookies(), load_ops())


def resolve_user(client: XClient, screen_name: str) -> dict:
    """Résout @screen_name → noeud `user.result` GraphQL (rest_id, legacy, core)."""
    data = client.call("UserByScreenName", {
        "screen_name": screen_name.lstrip("@"),
        "withSafetyModeUserFields": True,
    })
    u = (data.get("data", {}).get("user", {}) or {}).get("result", {}) or {}
    if not u or not u.get("rest_id"):
        raise XaError(
            "user_not_found",
            f"@{screen_name} introuvable",
            hint="vérifie le screen_name (sans @)",
        )
    return u


# ─────────── argparse configurators réutilisables ───────────

def args_paginated_user(sp) -> None:
    """`<screen_name> [--limit N] [--cursor C] [--fields ...]`."""
    sp.add_argument("screen_name")
    sp.add_argument("--limit", type=int, default=DEFAULT_LIMIT)
    sp.add_argument("--cursor")
    sp.add_argument("--fields")


def args_screen(sp) -> None:
    """`<screen_name>` seul (pour follow/unfollow)."""
    sp.add_argument("screen_name")


def args_tweet_id(sp) -> None:
    """`<tweet_id>` seul."""
    sp.add_argument("tweet_id")


def args_tweet_id_with_fields(sp) -> None:
    """`<tweet_id> [--fields ...]` (pour tweet / thread)."""
    sp.add_argument("tweet_id")
    sp.add_argument("--fields")


# ─────────── runners réutilisables ───────────

def run_user_paginated(
    args,
    op: str,
    vars_factory: Callable[[str], dict],
    parser: Callable[[dict], tuple[list[dict], str | None]],
) -> dict:
    """Pattern commun: resolve @user → paginate `op` → return ok JSON.

    Args:
        args: namespace argparse (doit avoir screen_name, limit, cursor, fields)
        op: nom d'op GraphQL (ex: "UserTweets", "Following")
        vars_factory: callable user_id → dict de variables GraphQL
        parser: parse_tweet_entries ou parse_user_entries
    """
    client = get_client()
    u = resolve_user(client, args.screen_name)
    rows, next_c = paginate_capped(
        client, op, vars_factory(u["rest_id"]),
        parser, args.limit, args.cursor,
    )
    return ok(
        select_fields(rows, args.fields),
        next_cursor=next_c, count=len(rows),
    )


def run_friendship(
    client: XClient,
    screen_name: str,
    action: Literal["create", "destroy"],
) -> dict:
    """Endpoint REST `/1.1/friendships/{create,destroy}.json` (follow/unfollow).

    GraphQL n'a pas de mutation Follow, on passe par l'API REST historique.
    """
    u = resolve_user(client, screen_name)
    r = client._raw(
        "POST",
        f"https://x.com/i/api/1.1/friendships/{action}.json",
        headers={"content-type": "application/x-www-form-urlencoded"},
        data={"user_id": u["rest_id"]},
    )
    if r.status_code != 200:
        raise XaError(
            f"{action}_failed",
            f"HTTP {r.status_code}: {r.text[:200]}",
        )
    past = "followed" if action == "create" else "unfollowed"
    return ok({past: screen_name, "user_id": u["rest_id"]})


def run_tweet_action(
    args,
    op: str,
    past_participle: str,
    extra_vars: dict | None = None,
) -> dict:
    """Pattern commun pour les actions sur un tweet (like, RT, bookmark...).

    Args:
        args: namespace argparse (doit avoir tweet_id)
        op: nom de la mutation GraphQL
        past_participle: clé de la réponse (ex: "liked", "retweeted")
        extra_vars: variables supplémentaires fusionnées avec tweet_id

    Note: ne fait PAS le require_yes (géré au niveau dispatcher via is_write).
    """
    client = get_client()
    variables = {"tweet_id": args.tweet_id}
    if extra_vars:
        variables.update(extra_vars)
    data = client.call(op, variables, method="POST")
    return ok({past_participle: args.tweet_id, "raw": data.get("data")})
