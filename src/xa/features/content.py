"""Contenu : `xa tweets/replies/media/likes/search/tweet/thread`."""

from __future__ import annotations

from ..core.output import ok, select_fields
from ..core.pagination import paginate_capped
from ..core.parsers import (
    parse_thread_entries,
    parse_tweet_entries,
    parse_user_entries,
    summarize_tweet,
)
from ..core.registry import register
from ..core.settings import DEFAULT_LIMIT
from ._common import (
    args_paginated_user,
    args_tweet_id_with_fields,
    get_client,
    run_user_paginated,
)


# ─────────── vars factory ───────────

def _user_timeline_vars(user_id: str) -> dict:
    """Variables GraphQL communes aux 4 timelines user (tweets/replies/media/likes)."""
    return {
        "userId": user_id,
        "includePromotedContent": False,
        "withClientEventToken": False,
        "withBirdwatchNotes": False,
        "withVoice": False,
        "withV2Timeline": True,
    }


# ─────────── args configurators spécifiques à content ───────────

def _args_search(sp):
    sp.add_argument("query")
    sp.add_argument(
        "--product",
        choices=["Latest", "Top", "Media", "People"],
        default="Latest",
    )
    sp.add_argument("--limit", type=int, default=DEFAULT_LIMIT)
    sp.add_argument("--cursor")
    sp.add_argument("--fields")


def _args_bookmarks(sp):
    sp.add_argument(
        "--query",
        help="filtre plein-texte côté X (sinon: tous les signets, du plus récent)",
    )
    sp.add_argument("--limit", type=int, default=DEFAULT_LIMIT)
    sp.add_argument("--cursor")
    sp.add_argument("--fields")


# ─────────── commandes par user (paginées) ───────────

@register("tweets", configure=args_paginated_user)
def cmd_tweets(args) -> dict:
    """Tweets publiés par un compte (sans réponses, avec pinned)."""
    def _vars(uid):
        v = _user_timeline_vars(uid)
        v["withQuickPromoteEligibilityTweetFields"] = False
        return v
    return run_user_paginated(args, "UserTweets", _vars, parse_tweet_entries)


@register("replies", configure=args_paginated_user)
def cmd_replies(args) -> dict:
    """Tweets + réponses d'un compte."""
    def _vars(uid):
        v = _user_timeline_vars(uid)
        v["withCommunity"] = True
        return v
    return run_user_paginated(args, "UserTweetsAndReplies", _vars,
                              parse_tweet_entries)


@register("media", configure=args_paginated_user)
def cmd_media(args) -> dict:
    """Tweets contenant un média (image, vidéo) d'un compte."""
    return run_user_paginated(args, "UserMedia", _user_timeline_vars,
                              parse_tweet_entries)


@register("likes", configure=args_paginated_user)
def cmd_likes(args) -> dict:
    """Tweets likés par un compte (si profil public)."""
    return run_user_paginated(args, "Likes", _user_timeline_vars,
                              parse_tweet_entries)


# ─────────── search ───────────

@register("search", configure=_args_search)
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


# ─────────── signets ───────────

@register("bookmarks", configure=_args_bookmarks)
def cmd_bookmarks(args) -> dict:
    """Tes signets (compte loggé). Avec --query: filtre plein-texte côté X."""
    client = get_client()
    if args.query:
        # NB: BookmarkSearchTimeline n'accepte QUE rawQuery + count (+ cursor).
        # Lui passer querySource (comme SearchTimeline) fait planter X en 422
        # "Internal server error" sur le path querySource.
        rows, next_c = paginate_capped(client, "BookmarkSearchTimeline", {
            "rawQuery": args.query,
        }, parse_tweet_entries, args.limit, args.cursor)
    else:
        rows, next_c = paginate_capped(client, "Bookmarks", {
            "includePromotedContent": False,
        }, parse_tweet_entries, args.limit, args.cursor)
    return ok(
        select_fields(rows, args.fields),
        next_cursor=next_c, count=len(rows), query=args.query,
    )


# ─────────── détail d'un tweet ───────────

@register("tweet", configure=args_tweet_id_with_fields)
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


@register("thread", configure=args_tweet_id_with_fields)
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
    tweets = parse_thread_entries(data)
    return ok(
        select_fields(tweets, args.fields),
        count=len(tweets), focal_tweet_id=args.tweet_id,
    )
