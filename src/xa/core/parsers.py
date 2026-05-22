"""Parsers des réponses GraphQL de X (timelines, profiles, tweets).

Les réponses GraphQL de X ont une structure imbriquée par "instructions"
avec des "entries" typées (`tweet-XXX`, `user-XXX`, `cursor-bottom-XXX`).
Ce module les transforme en dicts plats utilisables par la CLI.
"""

from __future__ import annotations


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

    instructions = timeline.get("instructions", []) if timeline else []
    seen_ids: set[str] = set()

    def _add_tweet(item_content: dict) -> None:
        tw = (item_content.get("tweet_results") or {}).get("result") or {}
        summary = summarize_tweet(tw)
        tweet_id = summary["id"]
        # Tweets sans id (tombstones, withholdings) sont gardés pour
        # signaler leur présence ; dédup uniquement sur les ids non-null.
        if tweet_id is None:
            out.append(summary)
            return
        if tweet_id not in seen_ids:
            seen_ids.add(tweet_id)
            out.append(summary)

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
                core = u.get("core") or {}
                screen_name = core.get("screen_name") or legacy.get("screen_name")
                users.append({
                    "rest_id": u.get("rest_id"),
                    "screen_name": screen_name,
                    "name": core.get("name") or legacy.get("name"),
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
    user_legacy = user_results.get("legacy") or {}
    user_core = user_results.get("core") or {}
    screen_name = user_core.get("screen_name") or user_legacy.get("screen_name")
    tweet_id = tw.get("rest_id")
    return {
        "id": tweet_id,
        "created_at": legacy.get("created_at"),
        "author": screen_name,
        "author_name": user_core.get("name") or user_legacy.get("name"),
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
