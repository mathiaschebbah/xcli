"""Utilitaire générique d'inspection des cookies navigateur : `xa cookies <domain>`.

Sortie en plusieurs formats (json/pretty/netscape/header). Utile pour
debug auth (vérifier que les bons cookies sont là, qu'ils ne sont pas
expirés) ou pour bootstrap d'autres scrapers (ex: export Netscape pour
curl --cookie-jar).
"""

from __future__ import annotations

import re
import time

from ..core.auth import discover_browser_profiles
from ..core.errors import XaError
from ..core.output import ok
from ..core.registry import register
from ..core.settings import BROWSERS

SENSITIVE_NAME_RE = re.compile(
    r"(session|token|auth|secret|csrf|bearer|sid|access|refresh|claim)",
    re.IGNORECASE,
)


def _args_cookies(sp):
    sp.add_argument("domain", help="domaine cible (ex: x.com, github.com)")
    sp.add_argument("--format",
                    choices=["json", "pretty", "netscape", "header"],
                    default="json",
                    help="format de sortie (json par défaut)")
    sp.add_argument("--reveal", action="store_true",
                    help="affiche les valeurs sensibles en clair (sinon masquées)")
    sp.add_argument("--source",
                    help="filtre un profil ex: 'chrome/Profile 1'")


@register("cookies", configure=_args_cookies)
def cmd_cookies(args) -> dict:
    """Extrait les cookies d'un domaine depuis tous les profils Chrome/Brave/etc.

    Utilitaire de debug : sert à vérifier l'état d'auth ou à exporter les
    cookies pour un autre outil (curl, wget, yt-dlp...).
    """
    sources = discover_browser_profiles()
    if args.source:
        sources = [s for s in sources if f"{s[0]}/{s[1]}" == args.source]
    if not sources:
        raise XaError("no_browser_profile", "Aucun profil navigateur trouvé.")

    all_rows: list[dict] = []
    errors: list[str] = []
    for br, prof, ck_path in sources:
        fn = BROWSERS[br][1]
        try:
            jar = fn(cookie_file=str(ck_path), domain_name=args.domain)
        except Exception as e:
            errors.append(f"{br}/{prof}: {type(e).__name__}: {e}")
            continue
        for c in jar:
            all_rows.append({
                "source": f"{br}/{prof}",
                "name": c.name,
                "value": c.value if args.reveal else _mask(c.name, c.value),
                "domain": c.domain,
                "path": c.path,
                "secure": bool(c.secure),
                "expires": c.expires,
                "expires_human": _fmt_expiry(c.expires),
            })

    if not all_rows:
        return ok([], errors=errors, count=0,
                  message=f"Aucun cookie pour {args.domain}")

    # Formats qui exposent forcément les valeurs : exige --reveal
    if args.format in ("header", "netscape") and not args.reveal:
        raise XaError(
            "reveal_required",
            f"--format {args.format} expose les valeurs en clair, --reveal est obligatoire.",
            hint="ajoute --reveal si tu veux vraiment exporter les cookies",
        )

    # Formats spéciaux (les valeurs sont toujours révélées ici, vu qu'on a
    # vérifié --reveal plus haut)
    if args.format == "header":
        seen: dict[str, str] = {}
        for r in all_rows:
            seen.setdefault(r["name"], r["value"])
        return ok({
            "header": "; ".join(f"{k}={v}" for k, v in seen.items()),
            "count": len(seen),
        })
    if args.format == "netscape":
        lines = ["# Netscape HTTP Cookie File"]
        for r in all_rows:
            lines.append("\t".join([
                r["domain"],
                "TRUE" if r["domain"].startswith(".") else "FALSE",
                r["path"] or "/",
                "TRUE" if r["secure"] else "FALSE",
                str(int(r["expires"] or 0)),
                r["name"],
                r["value"],
            ]))
        return ok({"netscape": "\n".join(lines), "count": len(all_rows)})

    return ok(all_rows, count=len(all_rows), errors=errors or None)


def _mask(name: str, value: str) -> str:
    if SENSITIVE_NAME_RE.search(name):
        if len(value) <= 8:
            return "***"
        return f"{value[:4]}…{value[-4:]} ({len(value)} chars)"
    if len(value) > 40:
        return value[:37] + "..."
    return value


def _fmt_expiry(expires: float | None) -> str:
    if not expires:
        return "session"
    now = time.time()
    if expires < now:
        return f"EXPIRED ({int((now - expires) / 86400)}d ago)"
    return f"in {(expires - now) / 86400:.1f}d"
