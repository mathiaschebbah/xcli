"""Contenu : `xa tweets`, `xa replies`, `xa media`, `xa likes`, `xa search`,
`xa tweet`, `xa thread`."""

from __future__ import annotations

from ..core.output import ok, select_fields
from ..core.pagination import paginate_capped
from ..core.parsers import parse_tweet_entries, parse_user_entries, summarize_tweet
from ..core.registry import register
from ..core.settings import DEFAULT_LIMIT
from ._common import get_client, resolve_user


# ─────────── helpers de configuration ───────────

def _configure_paginated_user(sp):
    sp.add_argument("screen_name")
    sp.add_argument("--limit", type=int, default=DEFAULT_LIMIT)
    sp.add_argument("--cursor")
    sp.add_argument("--fields")


def _configure_search(sp):
    sp.add_argument("query")
    sp.add_argument(
        "--product",
        choices=["Latest", "Top", "Media", "People"],
        default="Latest",
    )
    sp.add_argument("--limit", type=int, default=DEFAULT_LIMIT)
    sp.add_argument("--cursor")
    sp.add_argument("--fields")


def _configure_tweet(sp):
    sp.add_argument("tweet_id")
    sp.add_argument("--fields")


# ─────────── helper privé pour les ops user-paginées ───────────

def _user_paginated(args, op: str, vars_factory) -> dict:
    client = get_client()
    u = resolve_user(client, args.screen_name)
    rows, next_c = paginate_capped(
        client, op, vars_factory(u["rest_id"]),
        parse_tweet_entries, args.limit, args.cursor,
    )
    return ok(select_fields(rows, args.fields),
              next_cursor=next_c, count=len(rows))


# ─────────── commandes ───────────

@register("tweets", configure=_configure_paginated_user)
def cmd_tweets(args) -> dict:
    """Tweets publiés par un compte (sans réponses)."""
    return _user_paginated(args, "UserTweets", lambda uid: {
        "userId": uid,
        "includePromotedContent": False,
        "withQuickPromoteEligibilityTweetFields": False,
        "withVoice": False,
        "withV2Timeline": True,
    })


@register("replies", configure=_configure_paginated_user)
def cmd_replies(args) -> dict:
    """Tweets + réponses d'un compte."""
    return _user_paginated(args, "UserTweetsAndReplies", lambda uid: {
        "userId": uid,
        "includePromotedContent": False,
        "withCommunity": True,
        "withVoice": False,
        "withV2Timeline": True,
    })


@register("media", configure=_configure_paginated_user)
def cmd_media(args) -> dict:
    """Tweets contenant un média (image, vidéo) d'un compte."""
    return _user_paginated(args, "UserMedia", lambda uid: {
        "userId": uid,
        "includePromotedContent": False,
        "withClientEventToken": False,
        "withBirdwatchNotes": False,
        "withVoice": False,
        "withV2Timeline": True,
    })


@register("likes", configure=_configure_paginated_user)
def cmd_likes(args) -> dict:
    """Tweets likés par un compte (si profil public)."""
    return _user_paginated(args, "Likes", lambda uid: {
        "userId": uid,
        "includePromotedContent": False,
        "withClientEventToken": False,
        "withBirdwatchNotes": False,
        "withVoice": False,
        "withV2Timeline": True,
    })


@register("search", configure=_configure_search)
def cmd_search(args) -> dict:
    """Recherche : tweets (Latest/Top/Media) ou comptes (People)."""
    client = get_client()
    parser = parse_user_entries if args.product == "People" else parse_tweet_entries
    rows, next_c = paginate_capped(client, "SearchTimeline", {
        "rawQuery": args.query,
        "querySource": "typed_query",
        "product": args.product,
        "withGrokTranslatedBio": False,
        "withQuickPromoteEligibilityTweetFields": False,
    }, parser, args.limit, args.cursor)
    return ok(
        select_fields(rows, args.fields),
        next_cursor=next_c, count=len(rows),
        product=args.product, query=args.query,
    )


@register("tweet", configure=_configure_tweet)
def cmd_tweet(args) -> dict:
    """Détail d'un tweet par son ID."""
    client = get_client()
    data = client.call("TweetResultByRestId", {
        "tweetId": args.tweet_id,
        "withCommunity": False,
        "includePromotedContent": False,
        "withVoice": False,
    })
    tw = (data.get("data", {}).get("tweetResult", {}) or {}).get("result") or {}
    return ok(select_fields(summarize_tweet(tw), args.fields))


@register("thread", configure=_configure_tweet)
def cmd_thread(args) -> dict:
    """Fil de conversation autour d'un tweet (TweetDetail)."""
    client = get_client()
    data = client.call("TweetDetail", {
        "focalTweetId": args.tweet_id,
        "with_rux_injections": False,
        "includePromotedContent": False,
        "withCommunity": True,
        "withQuickPromoteEligibilityTweetFields": False,
        "withBirdwatchNotes": False,
        "withVoice": False,
    })
    # TweetDetail = structure différente : data.threaded_conversation_with_injections_v2
    instructions = (
        data.get("data", {})
        .get("threaded_conversation_with_injections_v2", {})
        .get("instructions", [])
    )
    out: list[dict] = []
    seen: set[str] = set()
    for inst in instructions:
        if inst.get("type") != "TimelineAddEntries":
            continue
        for entry in inst.get("entries", []):
            content = entry.get("content", {}) or {}
            items = content.get("items", []) or []
            if not items and (content.get("itemContent") or {}).get("tweet_results"):
                items = [{"item": {"itemContent": content["itemContent"]}}]
            for it in items:
                ic = ((it or {}).get("item") or {}).get("itemContent") or {}
                tw = (ic.get("tweet_results") or {}).get("result") or {}
                if not tw:
                    continue
                summary = summarize_tweet(tw)
                if summary["id"] and summary["id"] not in seen:
                    seen.add(summary["id"])
                    out.append(summary)
    return ok(
        select_fields(out, args.fields),
        count=len(out), focal_tweet_id=args.tweet_id,
    )
