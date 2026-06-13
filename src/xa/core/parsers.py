"""Parsers des réponses GraphQL de X (timelines, profiles, tweets).

Les réponses GraphQL de X ont une structure imbriquée par "instructions"
avec des "entries" typées (`tweet-XXX`, `user-XXX`, `cursor-bottom-XXX`).
Ce module les transforme en dicts plats utilisables par la CLI.
"""

from __future__ import annotations


def coalesce_user_field(user_node: dict, field: str):
    """Récupère un champ d'un noeud user GraphQL avec fallback core → legacy.

    X expose certains champs (screen_name, name, created_at) à la fois sous
    `user.core` (nouveau) et `user.legacy` (ancien). Cette fonction encode
    la règle de précédence : `core` d'abord, `legacy` en repli.
    """
    core = user_node.get("core") or {}
    legacy = user_node.get("legacy") or {}
    return core.get(field) or legacy.get(field)


def _append_tweet_from_itemcontent(
    out: list[dict],
    seen: set[str],
    item_content: dict,
    *,
    keep_tombstones: bool = False,
) -> None:
    """Extrait un tweet de `itemContent`, summarize, dedup, append.

    Helper interne partagé par parse_tweet_entries (timelines, keep_tombstones=True)
    et parse_thread_entries (TweetDetail, keep_tombstones=False).
    """
    tw = (item_content.get("tweet_results") or {}).get("result") or {}
    summary = summarize_tweet(tw)
    if summary["id"] is None:
        if keep_tombstones:
            out.append(summary)
        return
    if summary["id"] not in seen:
        seen.add(summary["id"])
        out.append(summary)


def parse_tweet_entries(payload: dict) -> tuple[list[dict], str | None]:
    """Parse une réponse type SearchTimeline / UserTweets / HomeTimeline.

    Retourne (tweets_list, next_cursor_or_None).
    """
    out: list[dict] = []
    cursor: str | None = None

    # SearchTimeline : data.search_by_raw_query.search_timeline.timeline
    timeline = (
        payload.get("data", {})
        .get("search_by_raw_query", {})
        .get("search_timeline", {})
        .get("timeline", {})
    )
    # UserTweets/Replies/Media/Likes : data.user.result.timeline.timeline
    if not timeline:
        timeline = (
            payload.get("data", {})
            .get("user", {})
            .get("result", {})
            .get("timeline", {})
            .get("timeline", {})
        )
    # Bookmarks : data.bookmark_timeline_v2.timeline
    if not timeline:
        timeline = (
            payload.get("data", {})
            .get("bookmark_timeline_v2", {})
            .get("timeline", {})
        )
    # BookmarkSearchTimeline : data.search_by_raw_query.bookmarks_search_timeline.timeline
    if not timeline:
        timeline = (
            payload.get("data", {})
            .get("search_by_raw_query", {})
            .get("bookmarks_search_timeline", {})
            .get("timeline", {})
        )

    instructions = timeline.get("instructions", []) if timeline else []
    seen_ids: set[str] = set()

    def _add_tweet(item_content: dict) -> None:
        # Timelines : on garde les tombstones (id=None) pour signaler les
        # tweets supprimés/withhelds, dédup uniquement sur ids non-null.
        _append_tweet_from_itemcontent(
            out, seen_ids, item_content, keep_tombstones=True,
        )

    def _add_module_items(items: list) -> None:
        for it in items or []:
            ic = ((it or {}).get("item") or {}).get("itemContent") or {}
            if ic:
                _add_tweet(ic)

    for inst in instructions:
        itype = inst.get("type")

        # TimelinePinEntry : un seul tweet pinned au top du profil
        if itype == "TimelinePinEntry":
            entry = inst.get("entry") or {}
            ic = (entry.get("content", {}) or {}).get("itemContent") or {}
            if ic:
                _add_tweet(ic)
            continue

        # TimelineAddToModule : module conversationnel (utilisé dans HomeTimeline)
        if itype == "TimelineAddToModule":
            _add_module_items(inst.get("moduleItems") or inst.get("items") or [])
            continue

        if itype != "TimelineAddEntries":
            continue

        for entry in inst.get("entries", []):
            eid = entry.get("entryId", "")
            content = entry.get("content", {})
            if (
                eid.startswith("tweet-")
                or eid.startswith("sq-I-t-")
                or eid.startswith("promoted-tweet-")
            ):
                _add_tweet(content.get("itemContent", {}))
            elif eid.startswith("profile-conversation-") or eid.startswith("conversationthread-"):
                # Module conversationnel imbriqué dans TimelineAddEntries
                _add_module_items(content.get("items") or [])
            elif eid.startswith("cursor-bottom-"):
                cursor = (
                    content.get("value")
                    or (content.get("itemContent") or {}).get("value")
                )
    return out, cursor


def parse_thread_entries(payload: dict) -> list[dict]:
    """Parse une réponse TweetDetail (fil de conversation).

    La structure est `data.threaded_conversation_with_injections_v2.instructions`,
    différente des timelines normales : les entries contiennent souvent un
    array `items` (réponses imbriquées) au lieu d'un `itemContent` direct.

    Retourne la liste dédupliquée des tweets du fil (sans cursor, le fil
    n'est pas paginé comme une timeline).
    """
    out: list[dict] = []
    seen: set[str] = set()

    instructions = (
        payload.get("data", {})
        .get("threaded_conversation_with_injections_v2", {})
        .get("instructions", [])
    )
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
                if ic:
                    # TweetDetail : on skip les tombstones (ils n'apportent
                    # rien dans le contexte d'un fil de conversation focal).
                    _append_tweet_from_itemcontent(
                        out, seen, ic, keep_tombstones=False,
                    )
    return out


def parse_user_entries(payload: dict) -> tuple[list[dict], str | None]:
    """Parse une réponse type Following / Followers.

    Retourne (users_list, next_cursor_or_None).
    """
    instructions = (
        payload.get("data", {})
        .get("user", {})
        .get("result", {})
        .get("timeline", {})
        .get("timeline", {})
        .get("instructions", [])
    )
    users: list[dict] = []
    cursor = None
    for inst in instructions:
        if inst.get("type") != "TimelineAddEntries":
            continue
        for entry in inst.get("entries", []):
            eid = entry.get("entryId", "")
            content = entry.get("content", {})
            if eid.startswith("user-"):
                item = content.get("itemContent", {})
                u = (item.get("user_results") or {}).get("result") or {}
                legacy = u.get("legacy") or {}
                screen_name = coalesce_user_field(u, "screen_name")
                users.append({
                    "rest_id": u.get("rest_id"),
                    "screen_name": screen_name,
                    "name": coalesce_user_field(u, "name"),
                    "description": legacy.get("description") or "",
                    "followers_count": legacy.get("followers_count"),
                    "friends_count": legacy.get("friends_count"),
                    "verified": u.get("is_blue_verified") or legacy.get("verified"),
                    "url": f"https://x.com/{screen_name}" if screen_name else None,
                })
            elif eid.startswith("cursor-bottom-"):
                cursor = content.get("value")
    return users, cursor


def summarize_tweet(tw: dict) -> dict:
    """Aplatit un noeud Tweet GraphQL en dict plat avec les champs utiles."""
    if tw.get("__typename") == "TweetWithVisibilityResults":
        tw = tw.get("tweet", {}) or tw
    legacy = tw.get("legacy") or {}
    user_results = (
        ((tw.get("core") or {}).get("user_results") or {}).get("result", {})
    )
    screen_name = coalesce_user_field(user_results, "screen_name")
    tweet_id = tw.get("rest_id")
    return {
        "id": tweet_id,
        "created_at": legacy.get("created_at"),
        "author": screen_name,
        "author_name": coalesce_user_field(user_results, "name"),
        "text": legacy.get("full_text"),
        "lang": legacy.get("lang"),
        "favorite_count": legacy.get("favorite_count"),
        "retweet_count": legacy.get("retweet_count"),
        "reply_count": legacy.get("reply_count"),
        "quote_count": legacy.get("quote_count"),
        "view_count": (tw.get("views") or {}).get("count"),
        "is_reply": bool(legacy.get("in_reply_to_status_id")),
        "in_reply_to_status_id": legacy.get("in_reply_to_status_id_str"),
        "url": (
            f"https://x.com/{screen_name}/status/{tweet_id}"
            if screen_name and tweet_id
            else None
        ),
    }
