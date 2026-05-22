"""Engagement : `xa post`, `xa reply`, `xa delete-tweet`, `xa like`/unlike,
`xa retweet`/unretweet, `xa bookmark`/unbookmark.

Toutes ces commandes modifient ton compte → verrouillées par `--yes`
(géré au niveau dispatcher dans `cli.py` via le flag `is_write`).
"""

from __future__ import annotations

from ..core.errors import XaError
from ..core.output import ok
from ..core.parsers import summarize_tweet
from ..core.registry import register
from ._common import (
    args_tweet_id,
    get_client,
    run_tweet_action,
)


# ─────────── Tableau des actions tweet "simples" ───────────
# Chaque entrée : nom_commande → (OpName GraphQL, past_participle pour la
# réponse, extra_vars éventuels)
TWEET_ACTIONS: dict[str, tuple[str, str, dict]] = {
    "like":        ("FavoriteTweet",   "liked",       {}),
    "unlike":      ("UnfavoriteTweet", "unliked",     {}),
    "retweet":     ("CreateRetweet",   "retweeted",   {"dark_request": False}),
    "unretweet":   ("DeleteRetweet",   "unretweeted", {"dark_request": False}),
    "bookmark":    ("CreateBookmark",  "bookmarked",  {}),
    "unbookmark":  ("DeleteBookmark",  "unbookmarked", {}),
}

# ─────────── Argparse configurators ───────────

def _args_post(sp):
    sp.add_argument("text")
    sp.add_argument("--reply-to", dest="reply_to",
                    help="ID du tweet auquel répondre (optionnel)")


def _args_reply(sp):
    sp.add_argument("tweet_id")
    sp.add_argument("text")


# ─────────── Commandes ───────────

@register("post", configure=_args_post, is_write=True)
def cmd_post(args) -> dict:
    """Publie un nouveau tweet (ou une réponse si --reply-to). Requiert --yes."""
    client = get_client()
    variables = {
        "tweet_text": args.text,
        "dark_request": False,
        "media": {"media_entities": [], "possibly_sensitive": False},
        "semantic_annotation_ids": [],
    }
    if getattr(args, "reply_to", None):
        variables["reply"] = {
            "in_reply_to_tweet_id": args.reply_to,
            "exclude_reply_user_ids": [],
        }
    data = client.call("CreateTweet", variables, method="POST")
    tw = (
        data.get("data", {}).get("create_tweet", {})
        .get("tweet_results", {}).get("result", {}) or {}
    )
    if not tw:
        raise XaError("post_failed", "réponse sans tweet", hint=str(data)[:200])
    return ok(summarize_tweet(tw))


@register("reply", configure=_args_reply, is_write=True)
def cmd_reply(args) -> dict:
    """Répond à un tweet. Requiert --yes."""
    args.reply_to = args.tweet_id
    return cmd_post(args)


@register("delete-tweet", configure=args_tweet_id, is_write=True)
def cmd_delete_tweet(args) -> dict:
    """Supprime un de tes tweets. Requiert --yes."""
    client = get_client()
    data = client.call(
        "DeleteTweet",
        {"tweet_id": args.tweet_id, "dark_request": False},
        method="POST",
    )
    return ok({"deleted": args.tweet_id, "raw": data.get("data")})


# ─────────── 6 actions tweet identiques, générées depuis TWEET_ACTIONS ───────────

def _make_tweet_action(op: str, past: str, extra_vars: dict):
    """Crée une fonction cmd_* à partir d'une entrée TWEET_ACTIONS."""

    def cmd(args) -> dict:
        return run_tweet_action(args, op, past, extra_vars)

    return cmd


for _name, (_op, _past, _extra) in TWEET_ACTIONS.items():
    _fn = _make_tweet_action(_op, _past, _extra)
    _fn.__doc__ = f"{_op} sur un tweet (requiert --yes)."
    register(_name, configure=args_tweet_id, is_write=True)(_fn)

# Cleanup loop variables
del _name, _op, _past, _extra, _fn
