"""Exception unique du domaine xa : encapsule un code, un message, un hint."""

from __future__ import annotations


class XaError(Exception):
    """Erreur métier de xa. Toujours sérialisée en JSON `{ok:false, ...}`."""

    def __init__(
        self,
        code: str,
        message: str,
        hint: str | None = None,
        **extras,
    ):
        super().__init__(message)
        self.code = code
        self.message = message
        self.hint = hint
        self.extras = extras
