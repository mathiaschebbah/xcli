"""Générateur de `x-client-transaction-id`, header anti-bot exigé par X.

Sans ce header, plusieurs endpoints "sensibles" (SearchTimeline,
HomeTimeline, …) renvoient 404 vide depuis 2024.

L'algo (obfusqué dans le JS de X) est implémenté par la lib pypi
`x-client-transaction-id`. On l'initialise paresseusement (1 fetch
home + 1 fetch du fichier `ondemand.s.<hash>.js`) puis on le réutilise
pour toute la session.
"""

from __future__ import annotations

import sys

import requests

try:
    from x_client_transaction import ClientTransaction
    from x_client_transaction.utils import (
        get_ondemand_file_url,
        handle_x_migration,
    )
    from x_client_transaction.utils import (
        generate_headers as _tid_headers,
    )

    AVAILABLE = True
except ImportError:
    AVAILABLE = False


class TidGenerator:
    """Wrapper paresseux autour de `x_client_transaction.ClientTransaction`.

    Construit avec les cookies courants pour pouvoir fetch la home page
    authentifiée (qui contient l'index nécessaire à l'algo).
    """

    def __init__(self, cookies: dict[str, str]):
        self.cookies = cookies
        self._ct: ClientTransaction | None = None
        self._init_failed = False

    def transaction_id(self, method: str, path: str) -> str | None:
        """Retourne un TID pour (method, path), ou None si l'init a échoué."""
        if not AVAILABLE or self._init_failed:
            return None
        if self._ct is None:
            try:
                self._init()
            except Exception as e:
                self._init_failed = True
                sys.stderr.write(f"[tid] init failed: {e}\n")
                return None
        try:
            return self._ct.generate_transaction_id(method=method, path=path)
        except Exception as e:
            sys.stderr.write(f"[tid] generate failed: {e}\n")
            return None

    def _init(self) -> None:
        sys.stderr.write("[tid] init x-client-transaction (1 home + 1 ondemand fetch)\n")
        sess = requests.Session()
        sess.headers = _tid_headers()
        sess.cookies.update(self.cookies)
        home = handle_x_migration(sess)
        ondemand_url = get_ondemand_file_url(home)
        ondemand = sess.get(ondemand_url, timeout=30).text
        self._ct = ClientTransaction(home, ondemand)
