"""Réseau social : `xa following`, `xa followers`, `xa follow`, `xa unfollow`."""

from __future__ import annotations

from ..core.parsers import parse_user_entries
from ..core.registry import register
from ._common import (
    args_paginated_user,
    args_screen,
    get_client,
    run_friendship,
    run_user_paginated,
)


def _follow_list_vars(user_id: str) -> dict:
    """Variables GraphQL communes à Following et Followers."""
    return {
        "userId": user_id,
        "includePromotedContent": False,
        "withGrokTranslatedBio": False,
    }


@register("following", configure=args_paginated_user)
def cmd_following(args) -> dict:
    """Comptes suivis par @screen_name."""
    return run_user_paginated(args, "Following", _follow_list_vars,
                              parse_user_entries)


@register("followers", configure=args_paginated_user)
def cmd_followers(args) -> dict:
    """Comptes qui suivent @screen_name."""
    return run_user_paginated(args, "Followers", _follow_list_vars,
                              parse_user_entries)


@register("follow", configure=args_screen, is_write=True)
def cmd_follow(args) -> dict:
    """Suivre un compte (action visible publiquement, requiert --yes)."""
    return run_friendship(get_client(), args.screen_name, "create")


@register("unfollow", configure=args_screen, is_write=True)
def cmd_unfollow(args) -> dict:
    """Ne plus suivre un compte (requiert --yes)."""
    return run_friendship(get_client(), args.screen_name, "destroy")
