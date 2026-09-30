# Install the *-use family as agent skills for Codex on Windows.
#   irm https://raw.githubusercontent.com/leeguooooo/plugins/main/install-use-family.ps1 | iex
# Re-run to update: every use is a git checkout under ~\.agents\use-family, linked into
# ~\.agents\skills with directory junctions (no admin rights needed).
# macOS-only uses (wechat-use, iphone-use, cookie-use, bitwarden-use, message-use) are skipped.
$ErrorActionPreference = 'Stop'
$Base = if ($env:USE_FAMILY_DIR) { $env:USE_FAMILY_DIR } else { Join-Path $HOME '.agents\use-family' }
$Skills = if ($env:AGENTS_SKILLS_DIR) { $env:AGENTS_SKILLS_DIR } else { Join-Path $HOME '.agents\skills' }
if (-not (Get-Command git -ErrorAction SilentlyContinue)) { throw 'git is required' }
New-Item -ItemType Directory -Force -Path $Base, $Skills | Out-Null

# <repo> = <skill directory inside the repo>; '.' means SKILL.md sits at the repo root.
# Keep in step with .claude-plugin/marketplace.json.
$Uses = [ordered]@{
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

function Get-Repo([string]$Repo, [string]$Dir) {
  if (Test-Path (Join-Path $Dir '.git')) {
    git -C $Dir pull -q --ff-only
    if ($LASTEXITCODE) { Write-Warning "$Repo not updated (local changes?)" }
  } else {
    git clone -q --depth 1 "https://github.com/leeguooooo/$Repo.git" $Dir
    if ($LASTEXITCODE) { throw "clone failed: $Repo" }
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
Add-SkillLink (Join-Path $Base 'plugins\plugins\use-family\skills\use-family') 'use-family'

foreach ($name in $Uses.Keys) {
  $dir = Join-Path $Base $name
  Get-Repo $(if ($Repos[$name]) { $Repos[$name] } else { $name }) $dir
  $target = if ($Uses[$name] -eq '.') { $dir } else { Join-Path $dir $Uses[$name] }
  if (Test-Path (Join-Path $target 'SKILL.md')) { Add-SkillLink $target $name } else { Write-Warning "$name has no SKILL.md at $($Uses[$name])" }
}

''
"Skills are in $Skills. Start a new Codex session to pick them up."
$missing = @('chrome-use', 'mail-use', 'discord-use', 'chatgpt-use', 'ocs', 'paste-use') | Where-Object { -not (Get-Command $_ -ErrorAction SilentlyContinue) }
if ($missing) { "CLIs not installed yet: $($missing -join ', '). See each repo's README for the Windows install." }
