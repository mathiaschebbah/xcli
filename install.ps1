# install.ps1 — installe xa en local sur Windows.
#
# Équivalent PowerShell de install.sh. Ce que ça fait :
#   1. Synchronise l'environnement Python (uv sync --native-tls)
#   2. Crée un wrapper exécutable `xa.cmd` dans %LOCALAPPDATA%\xa\bin (dans le PATH user)
#   3. (Optionnel) Installe le skill Claude Code dans %USERPROFILE%\.claude\skills\x-twitter\
#
# Usage :
#   .\install.ps1               # installe wrapper + skill
#   .\install.ps1 -NoSkill      # installe seulement le wrapper
#   .\install.ps1 -Uninstall    # désinstalle tout

[CmdletBinding()]
param(
    [switch]$NoSkill,
    [switch]$Uninstall
)

$ErrorActionPreference = "Stop"

$RepoDir     = $PSScriptRoot
$BinDir      = Join-Path $env:LOCALAPPDATA "xa\bin"
$WrapperPath = Join-Path $BinDir "xa.cmd"
$SkillDir    = Join-Path $env:USERPROFILE ".claude\skills\x-twitter"

function Write-Ok   ($m) { Write-Host "OK  $m" -ForegroundColor Green }
function Write-Info ($m) { Write-Host "--> $m" -ForegroundColor Cyan }
function Write-Warn2($m) { Write-Host "!   $m" -ForegroundColor Yellow }
function Write-Err  ($m) { Write-Host "X   $m" -ForegroundColor Red; exit 1 }

if ($Uninstall) {
    Write-Info "Désinstallation..."
    if (Test-Path $WrapperPath) { Remove-Item $WrapperPath -Force; Write-Ok "wrapper retiré" }
    if (Test-Path $SkillDir)    { Remove-Item $SkillDir -Recurse -Force; Write-Ok "skill retiré" }
    Write-Ok "xa désinstallé. (Le venv local du repo reste, supprime-le manuellement si besoin.)"
    exit 0
}

# 1. Vérifie uv
$uv = Get-Command uv -ErrorAction SilentlyContinue
if (-not $uv) {
    Write-Err "uv introuvable. Installe-le : https://docs.astral.sh/uv/getting-started/installation/"
}
Write-Ok ("uv: " + (uv --version))

# 2. Sync env Python
# `--native-tls` permet d'utiliser le store certificats Windows (utile derrière
# un proxy d'entreprise qui injecte un cert root custom).
Write-Info "uv sync --native-tls (installe Python 3.13 + dépendances)"
Push-Location $RepoDir
try {
    uv sync --native-tls --quiet
    if ($LASTEXITCODE -ne 0) { Write-Err "uv sync a échoué" }
} finally {
    Pop-Location
}
Write-Ok "environnement prêt : $RepoDir\.venv"

# 3. Crée le wrapper
New-Item -ItemType Directory -Force -Path $BinDir | Out-Null
$wrapperContent = @"
@echo off
REM xa.cmd — wrapper installé par xcli\install.ps1
REM Source du projet : $RepoDir
if not exist "$RepoDir" (
    echo xa: repo introuvable a "$RepoDir" -- re-clone et relance install.ps1 1>&2
    exit /b 1
)
uv run --project "$RepoDir" --quiet xa %*
"@
Set-Content -Path $WrapperPath -Value $wrapperContent -Encoding ASCII
Write-Ok "wrapper installé : $WrapperPath"

# 4. Vérifie PATH user
$userPath = [Environment]::GetEnvironmentVariable("Path", "User")
if (-not $userPath) { $userPath = "" }
$paths = $userPath -split ";" | Where-Object { $_ -ne "" }
if ($paths -notcontains $BinDir) {
    Write-Warn2 "$BinDir n'est pas dans ton PATH user."
    Write-Host  "  Ajoute-le maintenant ? (utilise setx, persistant après reboot)"
    Write-Host  "    setx PATH `"%PATH%;$BinDir`""
    Write-Host  "  Puis ouvre un NOUVEAU terminal."
}

# 5. Skill Claude Code
if (-not $NoSkill) {
    $skillSrc = Join-Path $RepoDir ".claude\skills\x-twitter\SKILL.md"
    if (Test-Path $skillSrc) {
        New-Item -ItemType Directory -Force -Path $SkillDir | Out-Null
        Copy-Item $skillSrc (Join-Path $SkillDir "SKILL.md") -Force
        Write-Ok "skill Claude Code installé : $SkillDir\SKILL.md"
    } else {
        Write-Warn2 "fichier skill introuvable, skipped."
    }
} else {
    Write-Info "skill Claude Code non installé (-NoSkill)"
}

# 6. Auth initiale
Write-Host ""
Write-Info "Étape suivante : connecte-toi à X dans Chrome (https://x.com), puis lance :"
Write-Host "    xa auth-init"
Write-Host "    xa auth-status"
Write-Host ""
Write-Warn2 "Note Chromium v127+ : si auth-init renvoie RequiresAdminError, relance"
Write-Warn2 "dans un PowerShell ouvert 'En tant qu'administrateur', OU ferme"
Write-Warn2 "entièrement le navigateur avant de réessayer."
Write-Host ""
Write-Ok "Installation terminée."
