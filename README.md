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
# 1. Supported OS: macOS, Linux, or Windows.
#    (On Windows, use the install.ps1 PowerShell script — see below.)

# 2. uv (Python package manager) — install via this command if absent:
#    macOS / Linux :
command -v uv >/dev/null || curl -LsSf https://astral.sh/uv/install.sh | sh
#    Windows (PowerShell) :
#    irm https://astral.sh/uv/install.ps1 | iex

# 3. Chrome (or Brave/Edge/Chromium) installed and logged in on https://x.com
#    Cannot be auto-checked. Ask the user to confirm before proceeding.
```

### Install (macOS / Linux)

```bash
# Replace <REPO_URL> with the repo URL the user gave you.
# Clone wherever you want — install.sh records the absolute path of the
# repo in the wrapper and uses it on every invocation.
git clone <REPO_URL> xcli
cd xcli
./install.sh
```

`install.sh` performs:
1. `uv sync` (installs Python 3.13 + deps in `.venv/`)
2. Writes a wrapper to `~/.local/bin/xa` (single command in PATH)
3. Copies the Claude Code skill to `~/.claude/skills/x-twitter/SKILL.md`

If `~/.local/bin` is not in `PATH`, the script prints the line to add to
the user's shell rc. You must show that line to the user.

### Install (Windows, PowerShell)

```powershell
git clone <REPO_URL> xcli
cd xcli
.\install.ps1
```

`install.ps1` performs:
1. `uv sync --native-tls` (the `--native-tls` flag uses the Windows
   certificate store — necessary behind corporate proxies that inject
   a custom root cert)
2. Writes `xa.cmd` to `%LOCALAPPDATA%\xa\bin` (add to `Path` if missing —
   the script tells you the exact `setx` command)
3. Copies the Claude Code skill to `%USERPROFILE%\.claude\skills\x-twitter\SKILL.md`

Cookies live in `%APPDATA%\xa\cookies.json` (vs `~/.config/xa/cookies.json`
on macOS / Linux).

**Note about Chromium v127+ on Windows.** Chrome/Edge/Brave encrypt the
cookie DB with App-Bound Encryption since v127. `browser_cookie3` requires
either (a) an elevated PowerShell ("Run as administrator"), or (b) the
browser to be fully closed before `xa auth-init` is called. If you see
`RequiresAdminError`, take one of those two paths.

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
# macOS / Linux, depuis la racine du repo cloné :
./install.sh --uninstall
```

```powershell
# Windows, depuis la racine du repo cloné :
.\install.ps1 -Uninstall
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
