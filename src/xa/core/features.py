"""Feature flags GraphQL X — bootstrap + auto-discovery + persistance.

Les endpoints GraphQL de X demandent un paramètre `features` (gros JSON
avec ~40 flags booléens). On capture une fois ces flags depuis Network,
on les stocke ici en bootstrap, et on s'auto-répare quand X râle avec
"FeatureNotEnabled: <X>" en ajoutant le flag manquant et persistant dans
`~/.config/xa/features.json`.
"""

from __future__ import annotations

import json

from .settings import CFG_DIR, FEATURES_FILE


# Set initial : 39 features capturées depuis SearchTimeline du client web.
# Si X ajoute un flag, on le récupère via _find_missing_feature() dans
# `client.py` et on le persiste.
FEATURES_BOOTSTRAP: dict[str, bool] = {
    "rweb_video_screen_enabled": False,
    "rweb_cashtags_enabled": True,
    "profile_label_improvements_pcf_label_in_post_enabled": True,
    "responsive_web_profile_redirect_enabled": False,
    "rweb_tipjar_consumption_enabled": False,
    "verified_phone_label_enabled": False,
    "creator_subscriptions_tweet_preview_api_enabled": True,
    "responsive_web_graphql_timeline_navigation_enabled": True,
    "responsive_web_graphql_skip_user_profile_image_extensions_enabled": False,
    "premium_content_api_read_enabled": False,
    "communities_web_enable_tweet_community_results_fetch": True,
    "c9s_tweet_anatomy_moderator_badge_enabled": True,
    "responsive_web_grok_analyze_button_fetch_trends_enabled": False,
    "responsive_web_grok_analyze_post_followups_enabled": True,
    "rweb_cashtags_composer_attachment_enabled": True,
    "responsive_web_jetfuel_frame": True,
    "responsive_web_grok_share_attachment_enabled": True,
    "responsive_web_grok_annotations_enabled": True,
    "articles_preview_enabled": True,
    "responsive_web_edit_tweet_api_enabled": True,
    "rweb_conversational_replies_downvote_enabled": False,
    "graphql_is_translatable_rweb_tweet_is_translatable_enabled": True,
    "view_counts_everywhere_api_enabled": True,
    "longform_notetweets_consumption_enabled": True,
    "responsive_web_twitter_article_tweet_consumption_enabled": True,
    "tweet_awards_web_tipping_enabled": False,
    "responsive_web_grok_show_grok_translated_post": False,
    "responsive_web_grok_analysis_button_from_backend": True,
    "creator_subscriptions_quote_tweet_preview_enabled": False,
    "freedom_of_speech_not_reach_fetch_enabled": True,
    "standardized_nudges_misinfo": True,
    "tweet_with_visibility_results_prefer_gql_limited_actions_policy_enabled": True,
    "longform_notetweets_rich_text_read_enabled": True,
    "longform_notetweets_inline_media_enabled": True,
    "responsive_web_grok_image_annotation_enabled": True,
    "responsive_web_grok_imagine_annotation_enabled": True,
    "responsive_web_grok_community_note_auto_translation_is_enabled": True,
    "responsive_web_enhance_cards_enabled": False,
    "payments_enabled": False,
}


def load_features() -> dict[str, bool]:
    """Charge les flags persistés, sinon retourne le bootstrap."""
    if FEATURES_FILE.exists():
        try:
            return json.loads(FEATURES_FILE.read_text())
        except json.JSONDecodeError:
            pass
    return dict(FEATURES_BOOTSTRAP)


def save_features(features: dict[str, bool]) -> None:
    """Persiste les flags (utilisé après auto-discovery d'un nouveau flag)."""
    CFG_DIR.mkdir(parents=True, exist_ok=True)
    FEATURES_FILE.write_text(json.dumps(features, indent=2, sort_keys=True))
