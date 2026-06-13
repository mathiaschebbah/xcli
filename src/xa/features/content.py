"""Contenu : `xa tweets/replies/media/likes/search/bookmarks/tweet/thread`."""

from __future__ import annotations

import time

from ..core import bookmarks_local as bm
from ..core.output import ok, select_fields
from ..core.pagination import paginate_capped
from ..core.parsers import (
    parse_thread_entries,
    parse_tweet_entries,
    parse_user_entries,
    summarize_tweet,
)
from ..core.registry import register
from ..core.settings import DEFAULT_LIMIT, MAX_LIMIT
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
        help="recherche plein-texte CÔTÉ X (rapide, mais match de mots exacts ; "
             "rate les synonymes)",
    )
    sp.add_argument(
        "--grep",
        help="recherche LOCALE sur le corpus complet (pagine tout puis filtre) : "
             "termes séparés par espace = OR par défaut, insensible casse. "
             "Plus exhaustif que --query. Combinable avec --query.",
    )
    sp.add_argument(
        "--grep-all",
        action="store_true",
        help="avec --grep : exige TOUS les termes (AND) au lieu de OR",
    )
    sp.add_argument(
        "--regex",
        action="store_true",
        help="avec --grep : traite le motif comme une regex (insensible casse)",
    )
    sp.add_argument(
        "--refresh",
        action="store_true",
        help="avec --grep : ignore le cache local et repagine le corpus",
    )
    sp.add_argument(
        "--max-pages",
        type=int,
        default=20,
        help="avec --grep : plafond de pages de 100 à paginer (défaut 20 = 2000 signets)",
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

def _fetch_bookmarks_corpus(client, max_pages: int) -> tuple[list[dict], bool]:
    """Pagine TOUT le timeline des signets (jusqu'à max_pages * 100).

    Utilisé par la recherche locale --grep. S'arrête quand X ne renvoie plus
    de cursor ou plus de rows (fin réelle), ou au plafond max_pages.
    Retourne (rows, complete) où `complete` indique qu'on a atteint la fin
    réelle (et non le plafond) — pour ne pas faire passer un corpus tronqué
    pour exhaustif.
    """
    rows: list[dict] = []
    seen: set[str] = set()
    cursor = None
    complete = False
    for _ in range(max(1, max_pages)):
        page, next_c = paginate_capped(
            client, "Bookmarks", {"includePromotedContent": False},
            parse_tweet_entries, 100, cursor,
        )
        for r in page:
            rid = r.get("id")
            if rid and rid not in seen:
                seen.add(rid)
                rows.append(r)
        if not next_c or not page:
            complete = True
            break
        cursor = next_c
    return rows, complete


def _bookmarks_grep(args) -> dict:
    """Recherche locale sur le corpus complet (avec cache disque)."""
    cached = None if args.refresh else bm.load_cache()
    from_cache = cached is not None
    if cached is not None:
        rows = cached["rows"]
        complete = cached.get("complete", False)
    else:
        client = get_client()
        fetched_at = time.time()
        rows, complete = _fetch_bookmarks_corpus(client, args.max_pages)
        # Ne pas remplacer un cache COMPLET et frais par un fetch tronqué
        # (ex: --refresh --max-pages 2). On garde le plus exhaustif.
        prev = bm.load_cache()
        if (prev and prev.get("complete") and not complete
                and len(prev["rows"]) > len(rows)):
            rows, complete, from_cache = prev["rows"], True, True
        else:
            bm.save_cache(rows, fetched_at, complete)

    # Affine éventuellement avec la recherche serveur d'abord (--query + --grep).
    if args.query:
        client = get_client()
        srv, _ = paginate_capped(
            client, "BookmarkSearchTimeline", {"rawQuery": args.query},
            parse_tweet_entries, MAX_LIMIT, None,
        )
        srv_ids = {r.get("id") for r in srv}
        rows = [r for r in rows if r.get("id") in srv_ids] or srv

    matcher = bm.build_matcher(
        args.grep, regex=args.regex, require_all=args.grep_all,
    )
    hits = bm.grep(rows, matcher)
    capped = hits[: args.limit] if args.limit else hits
    return ok(
        select_fields(capped, args.fields),
        count=len(capped), total_matches=len(hits),
        corpus_size=len(rows), corpus_complete=complete,
        from_cache=from_cache, grep=args.grep, query=args.query,
    )


@register("bookmarks", configure=_args_bookmarks)
def cmd_bookmarks(args) -> dict:
    """Tes signets (compte loggé).

    Trois modes (combinables) :
    - défaut : timeline complète, du plus récent (op Bookmarks).
    - --query X : recherche plein-texte CÔTÉ X (rapide, mots exacts).
    - --grep X : recherche LOCALE exhaustive (pagine tout + filtre, regex/OR/AND).
    """
    if args.grep is not None:
        return _bookmarks_grep(args)
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
