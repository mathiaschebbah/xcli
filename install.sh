#!/usr/bin/env bash
# install.sh — installe xa en local sur ta machine.
#
# Ce que ça fait :
#   1. Synchronise l'environnement Python (uv sync)
#   2. Crée un wrapper exécutable `xa` dans ~/.local/bin/ (dans ton PATH)
#   3. (Optionnel) Installe le skill Claude Code dans ~/.claude/skills/x-twitter/
#
# Usage :
#   ./install.sh             # installe wrapper + skill
#   ./install.sh --no-skill  # installe seulement le wrapper
#   ./install.sh --uninstall # désinstalle tout

set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BIN_DIR="${HOME}/.local/bin"
WRAPPER_PATH="${BIN_DIR}/xa"
SKILL_DIR="${HOME}/.claude/skills/x-twitter"

color() { printf "\033[%sm%s\033[0m\n" "$1" "$2"; }
ok()    { color "32" "✓ $1"; }
info()  { color "36" "→ $1"; }
warn()  { color "33" "! $1"; }
errx()  { color "31" "✗ $1" >&2; exit 1; }

uninstall() {
    info "Désinstallation..."
    [ -f "$WRAPPER_PATH" ] && rm -v "$WRAPPER_PATH" || true
    [ -d "$SKILL_DIR" ] && rm -rv "$SKILL_DIR" || true
    ok "xa désinstallé. (Le venv local du repo reste, supprime-le manuellement si besoin.)"
    exit 0
}

if [[ "${1:-}" == "--uninstall" ]]; then
    uninstall
fi

INSTALL_SKILL=true
if [[ "${1:-}" == "--no-skill" ]]; then
    INSTALL_SKILL=false
fi

# ── 1. Vérifie uv ──
if ! command -v uv >/dev/null 2>&1; then
    errx "uv introuvable. Installe-le : https://docs.astral.sh/uv/getting-started/installation/"
fi
ok "uv: $(uv --version)"

# ── 2. Sync env Python ──
info "uv sync (installe Python 3.13 + dépendances)"
cd "$REPO_DIR"
uv sync --quiet
ok "environnement prêt : $REPO_DIR/.venv"

# ── 3. Crée le wrapper ──
mkdir -p "$BIN_DIR"
cat > "$WRAPPER_PATH" <<EOF
#!/usr/bin/env bash
# xa — wrapper installé par xcli/install.sh
# Source du projet : $REPO_DIR
[ -d "$REPO_DIR" ] || {
    echo "xa: repo introuvable à $REPO_DIR — re-clone et relance install.sh" >&2
    exit 1
}
exec uv run --project "$REPO_DIR" --quiet xa "\$@"
EOF
chmod +x "$WRAPPER_PATH"
ok "wrapper installé : $WRAPPER_PATH"

# ── 4. Vérifie PATH ──
if [[ ":$PATH:" != *":$BIN_DIR:"* ]]; then
    warn "$BIN_DIR n'est pas dans ton PATH."
    echo "  Ajoute cette ligne à ton ~/.zshrc ou ~/.bashrc :"
    echo "    export PATH=\"\$HOME/.local/bin:\$PATH\""
fi

# ── 5. Skill Claude Code ──
if $INSTALL_SKILL; then
    if [ -f "$REPO_DIR/.claude/skills/x-twitter/SKILL.md" ]; then
        mkdir -p "$SKILL_DIR"
        cp "$REPO_DIR/.claude/skills/x-twitter/SKILL.md" "$SKILL_DIR/SKILL.md"
        ok "skill Claude Code installé : $SKILL_DIR/SKILL.md"
    else
        warn "fichier skill introuvable, skipped."
    fi
else
    info "skill Claude Code non installé (--no-skill)"
fi

# ── 6. Auth initiale ──
echo
info "Étape suivante : connecte-toi à X dans Chrome (https://x.com), puis lance :"
echo "    xa auth-init"
echo "    xa auth-status"
echo
ok "Installation terminée."
