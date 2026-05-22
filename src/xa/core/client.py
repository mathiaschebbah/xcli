"""Client HTTP/GraphQL pour X.

Encapsule :
- Headers (Bearer + CSRF dérivé du cookie ct0 + transaction-id)
- Retry exponentiel sur 429/5xx
- Auto-discovery des feature flags : si X répond "FeatureNotEnabled: X",
  on ajoute X=True dans les features, on persiste et on retente.
"""

from __future__ import annotations

import json
import random
import re
import sys
import time
import urllib.parse

import requests

from .errors import XaError
from .features import load_features, save_features
from .settings import BEARER, USER_AGENT
from .transaction import TidGenerator


class XClient:
    """Client GraphQL X. Construit à partir des cookies sauvegardés."""

    def __init__(self, cookies: dict[str, str], ops: dict[str, dict]):
        if "ct0" not in cookies or "auth_token" not in cookies:
            raise XaError(
                "auth_required",
                "Cookies invalides (ct0/auth_token manquants).",
                hint="relance `xa auth-init`",
            )
        self.cookies = cookies
        self.ops = ops
        self.features = load_features()
        self._tid = TidGenerator(cookies)
        self.s = requests.Session()
        self.s.cookies.update(cookies)
        self.s.headers.update({
            "User-Agent": USER_AGENT,
            "Accept": "*/*",
            "Accept-Language": "fr-FR,fr;q=0.9,en;q=0.8",
            "authorization": BEARER,
            "x-csrf-token": cookies["ct0"],
            "x-twitter-auth-type": "OAuth2Session",
            "x-twitter-active-user": "yes",
            "x-twitter-client-language": "fr",
            "content-type": "application/json",
            "Referer": "https://x.com/",
            "Origin": "https://x.com",
        })

    # ───────────── identity ─────────────

    def whoami(self) -> dict | None:
        """Extrait le user_id du cookie twid (`u=<id>`)."""
        twid = urllib.parse.unquote(self.cookies.get("twid", ""))
        m = re.search(r"u=(\d+)", twid)
        return {"user_id": m.group(1)} if m else None

    # ───────────── GraphQL call ─────────────

    def call(
        self,
        op_name: str,
        variables: dict,
        method: str = "GET",
        extra_features: dict | None = None,
        max_feature_retries: int = 15,
    ) -> dict:
        """Appel d'une op GraphQL connue du catalogue.

        Retentera jusqu'à `max_feature_retries` fois si X demande un nouveau
        flag (`FeatureNotEnabled: X`). Les flags ajoutés sont persistés.
        """
        op = self.ops.get(op_name)
        if not op:
            raise XaError(
                "unknown_op",
                f"Op inconnue '{op_name}'.",
                hint="lance `xa ops` pour lister, ou `xa harvest-ops` pour rafraîchir",
            )
        url = f"https://x.com/i/api/graphql/{op['queryId']}/{op_name}"
        path = f"/i/api/graphql/{op['queryId']}/{op_name}"
        # Les mutations sont toujours POST
        if op["operationType"] == "mutation":
            method = "POST"

        features = dict(self.features)
        if extra_features:
            features.update(extra_features)

        for attempt in range(max_feature_retries):
            params = {
                "variables": json.dumps(variables, separators=(",", ":")),
                "features": json.dumps(features, separators=(",", ":")),
            }
            extra_headers = {}
            tid = self._tid.transaction_id(method, path)
            if tid:
                extra_headers["x-client-transaction-id"] = tid

            r = self._raw(method, url, params=params, headers=extra_headers)

            if r.status_code == 200:
                try:
                    data = r.json()
                except ValueError:
                    raise XaError(
                        "invalid_response",
                        f"Réponse non-JSON: {r.text[:200]}",
                    )
                missing = _find_missing_feature(data)
                if missing:
                    sys.stderr.write(f"  [feature] +{missing}=True\n")
                    features[missing] = True
                    continue
                # Persiste les nouveaux flags si on en a découvert
                if features != self.features:
                    self.features = features
                    save_features(features)
                return data

            if r.status_code in (401, 403):
                # Auth cassée — pas de retry, l'utilisateur doit relogger.
                raise XaError(
                    "session_invalid",
                    f"HTTP {r.status_code} sur {op_name}: cookies expirés ou invalides.",
                    hint="reconnecte-toi sur https://x.com puis relance `xa auth-init`",
                )

            if r.status_code in (429, 500, 502, 503, 504):
                wait = 2 ** attempt + random.uniform(0, 2)
                sys.stderr.write(
                    f"  retry {op_name} status={r.status_code} sleep={wait:.1f}s\n"
                )
                time.sleep(wait)
                continue

            raise XaError(
                "http_error",
                f"HTTP {r.status_code} sur {op_name}: {r.text[:300]}",
            )

        raise XaError(
            "too_many_retries",
            f"Trop de retries sur {op_name} (probable problème de feature flag).",
        )

    def _raw(
        self,
        method: str,
        url: str,
        headers: dict | None = None,
        **kw,
    ) -> requests.Response:
        """Appel HTTP brut (utilisé par les endpoints REST `/1.1/...` aussi)."""
        h = dict(self.s.headers)
        if headers:
            h.update(headers)
        return self.s.request(method, url, timeout=30, headers=h, **kw)


def _find_missing_feature(data: dict) -> str | None:
    """Parse les `errors` d'une réponse GraphQL pour détecter un flag manquant."""
    errs = data.get("errors") or []
    for e in errs:
        msg = e.get("message", "")
        for pat in (
            r'feature[^\']*"\s*:\s*"([^"]+)"',
            r"FeatureNotEnabled[: ]+([A-Za-z_][A-Za-z0-9_]+)",
            r"feature ([a-z_][a-z0-9_]+) is not enabled",
        ):
            m = re.search(pat, msg)
            if m:
                return m.group(1)
    return None
