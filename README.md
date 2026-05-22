# xa

CLI Python qui parle à l'API privée GraphQL de X.com (Twitter) en réutilisant
une session Chrome connectée. Sortie JSON. Conçue pour être pilotée par un
agent.

---

## Agent install instructions

You are an AI agent installing this project on the user's machine. Execute
the steps below in order. Stop at the first non-zero exit and report it to
the user.

### Prerequisites (check, install if missing)

```bash
# 1. macOS (currently only supported OS for cookie extraction)
[ "$(uname)" = "Darwin" ] || { echo "ERROR: macOS required"; exit 1; }

# 2. uv (Python package manager) — install via this command if absent:
command -v uv >/dev/null || curl -LsSf https://astral.sh/uv/install.sh | sh

# 3. Chrome (or Brave/Edge/Chromium) installed and logged in on https://x.com
#    Cannot be auto-checked. Ask the user to confirm before proceeding.
```

### Install

```bash
# Replace <REPO_URL> with the repo URL the user gave you.
git clone <REPO_URL> ~/Desktop/Projets/xcli
cd ~/Desktop/Projets/xcli
./install.sh
```

`install.sh` performs:
1. `uv sync` (installs Python 3.13 + deps in `.venv/`)
2. Writes a wrapper to `~/.local/bin/xa` (single command in PATH)
3. Copies the Claude Code skill to `~/.claude/skills/x-twitter/SKILL.md`

If `~/.local/bin` is not in `PATH`, the script prints the line to add to
the user's shell rc. You must show that line to the user.

### Verify install (run these and check `ok: true` in the JSON output)

```bash
xa --help                 # should print 30+ subcommands
xa cookies x.com          # should list 5+ cookies if Chrome is logged in
```

### Initialize auth (one-time, requires Chrome logged in on x.com)

```bash
xa auth-init              # extracts cookies from Chrome → ~/.config/xa/cookies.json
xa auth-status            # validates the session
xa whoami                 # returns the logged-in user
```

If any of these returns `{"ok": false, "error": "auth_required"}` or
`session_invalid`, the user is not logged in on x.com in Chrome. Tell them
to open Chrome, log in to https://x.com, then re-run `xa auth-init`.

### Uninstall

```bash
~/Desktop/Projets/xcli/install.sh --uninstall
```

---

## Usage reference

All commands output a single JSON document on stdout:

```json
{ "ok": true, "data": <value>, "next_cursor": "...", "count": N }
```

Errors:

```json
{ "ok": false, "error": "<code>", "message": "...", "hint": "..." }
```

Full command reference: see [`.claude/skills/x-twitter/SKILL.md`](.claude/skills/x-twitter/SKILL.md)
(parseable Markdown documenting all 30+ commands with options, error codes,
recipes).

Quick discovery:

```bash
xa --help                 # human-readable subcommand list
xa help                   # JSON schema of all commands
xa ops --filter <term>    # search the 158-op GraphQL catalog
```

---

## License

MIT — see [LICENSE](LICENSE).
