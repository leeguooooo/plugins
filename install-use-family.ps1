# Install the *-use family as agent skills for Codex on Windows.
#   irm https://raw.githubusercontent.com/leeguooooo/plugins/main/install-use-family.ps1 | iex
# Re-run to update: every use is a git checkout under ~\.agents\use-family, linked into
# ~\.agents\skills with directory junctions (no admin rights needed).
# macOS-only uses (wechat-use, iphone-use, cookie-use, bitwarden-use, message-use) are skipped, and so are
# motion-use until it supports Windows and switch-use (macOS and Linux only).
$ErrorActionPreference = 'Stop'
$Base = if ($env:USE_FAMILY_DIR) { $env:USE_FAMILY_DIR } else { Join-Path $HOME '.agents\use-family' }
$Skills = if ($env:AGENTS_SKILLS_DIR) { $env:AGENTS_SKILLS_DIR } else { Join-Path $HOME '.agents\skills' }
if (-not (Get-Command git -ErrorAction SilentlyContinue)) { throw 'git is required' }
New-Item -ItemType Directory -Force -Path $Base, $Skills | Out-Null

# <repo> = <skill directory inside the repo>; '.' means SKILL.md sits at the repo root.
# Keep in step with .claude-plugin/marketplace.json.
$Uses = [ordered]@{
  'android-use' = 'skills/android-use'
  'chrome-use'  = 'skills/chrome-use'
  'mail-use'    = 'skills/mail-use'
  'discord-use' = '.'
  'profile-use' = '.'
  'chatgpt-use' = '.'
  'image-use'   = '.'
  'memory-use'  = '.'
  'ocs'         = 'skills/ocs'
  'paste-use'   = '.'
}
# Uses whose repo name differs from the use name.
$Repos = @{ 'ocs' = 'open-cross-session' }

$Failed = @()
# A failure is reported and recorded, never fixed by force.
function Get-Repo([string]$Repo, [string]$Dir) {
  if (-not (Test-Path (Join-Path $Dir '.git'))) {
    git clone -q --depth 1 "https://github.com/leeguooooo/$Repo.git" $Dir
    if ($LASTEXITCODE) { Write-Warning "${Repo}: clone failed"; $script:Failed += $Repo }
    return
  }
  git -C $Dir fetch -q
  if ($LASTEXITCODE) { Write-Warning "${Repo}: not updated, fetch failed (network?)"; $script:Failed += $Repo; return }
  git -C $Dir merge -q --ff-only '@{u}'
  if (-not $LASTEXITCODE) { return }
  $script:Failed += $Repo
  if (git -C $Dir status --porcelain) {
    Write-Warning "${Repo}: not updated, $Dir has local changes; commit or stash them and re-run"
  } else {
    Write-Warning "${Repo}: not updated, its history no longer fast-forwards to origin (upstream was rewritten). Your checkout is untouched; to recover, back it up and re-run:  Rename-Item `"$Dir`" `"$Dir.bak`""
  }
}

function Add-SkillLink([string]$Target, [string]$Name) {
  $dest = Join-Path $Skills $Name
  $item = Get-Item $dest -Force -ErrorAction SilentlyContinue
  if ($item -and -not $item.LinkType) { "skip   ${Name}: left alone (a real directory, possibly kept current by that use's own installer)"; return }
  if ($item -and -not ("$($item.Target)" -like "$Base\*")) { "keep   ${Name}: already linked to $($item.Target)"; return }
  if ($item) { $item.Delete() }
  New-Item -ItemType Junction -Path $dest -Target $Target | Out-Null
  "linked $Name"
}

Get-Repo 'plugins' (Join-Path $Base 'plugins')
if (Test-Path (Join-Path $Base 'plugins\.git')) { Add-SkillLink (Join-Path $Base 'plugins\plugins\use-family\skills\use-family') 'use-family' }

foreach ($name in $Uses.Keys) {
  $dir = Join-Path $Base $name
  Get-Repo $(if ($Repos[$name]) { $Repos[$name] } else { $name }) $dir
  if (-not (Test-Path (Join-Path $dir '.git'))) { continue }
  $target = if ($Uses[$name] -eq '.') { $dir } else { Join-Path $dir $Uses[$name] }
  if (Test-Path (Join-Path $target 'SKILL.md')) { Add-SkillLink $target $name } else { Write-Warning "$name has no SKILL.md at $($Uses[$name])" }
}

''
"Skills are in $Skills. Start a new Codex session to pick them up."
$missing = @('android-use', 'chrome-use', 'mail-use', 'discord-use', 'chatgpt-use', 'ocs', 'paste-use', 'image-use') | Where-Object { -not (Get-Command $_ -ErrorAction SilentlyContinue) }
if ($missing) {
  "CLIs not installed yet: $($missing -join ', '). See each repo's README for the Windows install."
  # image-use has no installer: the CLI is a single Python file at the root of its checkout.
  if ($missing -contains 'image-use') { "  image-use: run it as  py `"$(Join-Path $Base 'image-use\image-use')`"" }
}
# throw rather than exit: under `irm | iex`, exit would close the caller's PowerShell window.
if ($Failed) { throw "Not updated: $($Failed -join ', ') (each one's reason is above; their old skills stay linked)" }

# Install the manager from the trusted family checkout, without opting into scheduling.
$Manager = Join-Path $Base 'plugins/plugins/use-family/scripts/use.py'
$ManagerPython = Get-Command python3,python -ErrorAction SilentlyContinue | Select-Object -First 1
if ((Test-Path $Manager) -and $ManagerPython) {
  & $ManagerPython.Source $Manager install --local
  if ($LASTEXITCODE) { Write-Warning 'use manager installation did not finish' }
}
