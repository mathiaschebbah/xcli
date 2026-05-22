"""Engagement : `xa post`, `xa reply`, `xa delete-tweet`, `xa like`/unlike,
`xa retweet`/unretweet, `xa bookmark`/unbookmark.

Toutes ces commandes modifient ton compte → verrouillées par `--yes`."""

from __future__ import annotations

from ..core.output import ok
from ..core.parsers import summarize_tweet
from ..core.registry import register
from ._common import get_client, require_yes
from ..core.errors import XaError


# ─────────── argparse configurators ───────────

def _configure_post(sp):
    sp.add_argument("text")
    sp.add_argument("--reply-to", dest="reply_to",
                    help="ID du tweet auquel répondre (optionnel)")
    sp.add_argument("--yes", action="store_true")


def _configure_reply(sp):
    sp.add_argument("tweet_id")
    sp.add_argument("text")
    sp.add_argument("--yes", action="store_true")


def _configure_tw_yes(sp):
    sp.add_argument("tweet_id")
    sp.add_argument("--yes", action="store_true")


# ─────────── commandes ───────────

@register("post", configure=_configure_post, is_write=True)
def cmd_post(args) -> dict:
    """Publie un nouveau tweet (ou une réponse si --reply-to). Requiert --yes."""
    require_yes(args, "post")
    client = get_client()
    variables = {
        "tweet_text": args.text,
        "dark_request": False,
        "media": {"media_entities": [], "possibly_sensitive": False},
        "semantic_annotation_ids": [],
    }
    if args.reply_to:
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


@register("reply", configure=_configure_reply, is_write=True)
def cmd_reply(args) -> dict:
    """Répond à un tweet. Requiert --yes."""
    args.reply_to = args.tweet_id
    return cmd_post(args)


@register("delete-tweet", configure=_configure_tw_yes, is_write=True)
def cmd_delete_tweet(args) -> dict:
    """Supprime un de tes tweets. Requiert --yes."""
    require_yes(args, "delete-tweet")
    client = get_client()
    data = client.call("DeleteTweet", {
        "tweet_id": args.tweet_id, "dark_request": False,
    }, method="POST")
    return ok({"deleted": args.tweet_id, "raw": data.get("data")})


@register("like", configure=_configure_tw_yes, is_write=True)
def cmd_like(args) -> dict:
    """Like un tweet. Requiert --yes."""
    require_yes(args, "like")
    client = get_client()
    data = client.call("FavoriteTweet", {"tweet_id": args.tweet_id}, method="POST")
    return ok({"liked": args.tweet_id, "raw": data.get("data")})


@register("unlike", configure=_configure_tw_yes, is_write=True)
def cmd_unlike(args) -> dict:
    """Retire ton like sur un tweet. Requiert --yes."""
    require_yes(args, "unlike")
    client = get_client()
    data = client.call("UnfavoriteTweet", {"tweet_id": args.tweet_id}, method="POST")
    return ok({"unliked": args.tweet_id, "raw": data.get("data")})


@register("retweet", configure=_configure_tw_yes, is_write=True)
def cmd_retweet(args) -> dict:
    """Retweet (RT) un tweet. Requiert --yes."""
    require_yes(args, "retweet")
    client = get_client()
    data = client.call("CreateRetweet", {
        "tweet_id": args.tweet_id, "dark_request": False,
    }, method="POST")
    return ok({"retweeted": args.tweet_id, "raw": data.get("data")})


@register("unretweet", configure=_configure_tw_yes, is_write=True)
def cmd_unretweet(args) -> dict:
    """Annule un RT. Requiert --yes."""
    require_yes(args, "unretweet")
    client = get_client()
    data = client.call("DeleteRetweet", {
        "source_tweet_id": args.tweet_id, "dark_request": False,
    }, method="POST")
    return ok({"unretweeted": args.tweet_id, "raw": data.get("data")})


@register("bookmark", configure=_configure_tw_yes, is_write=True)
def cmd_bookmark(args) -> dict:
    """Ajoute un tweet à tes signets. Requiert --yes."""
    require_yes(args, "bookmark")
    client = get_client()
    data = client.call("CreateBookmark", {"tweet_id": args.tweet_id}, method="POST")
    return ok({"bookmarked": args.tweet_id, "raw": data.get("data")})


@register("unbookmark", configure=_configure_tw_yes, is_write=True)
def cmd_unbookmark(args) -> dict:
    """Retire un tweet de tes signets. Requiert --yes."""
    require_yes(args, "unbookmark")
    client = get_client()
    data = client.call("DeleteBookmark", {"tweet_id": args.tweet_id}, method="POST")
    return ok({"unbookmarked": args.tweet_id, "raw": data.get("data")})
