# Install the unified use manager; -Auto enables daily background upgrades.
param([switch]$Auto)
$ErrorActionPreference = 'Stop'
$Python = Get-Command python3,python -ErrorAction SilentlyContinue | Select-Object -First 1
if (-not $Python) { throw 'Python 3.9+ is required' }
$Local = if ($PSScriptRoot) { Join-Path $PSScriptRoot 'plugins/use-family/scripts/use.py' } else { $null }
$Temporary = $null
try {
  $ArgsList = @('install')
  if ($Local -and (Test-Path $Local)) { $ArgsList += '--local' }
  else {
    $Temporary = Join-Path ([IO.Path]::GetTempPath()) ([Guid]::NewGuid().ToString()+'.py')
    Invoke-WebRequest 'https://raw.githubusercontent.com/leeguooooo/plugins/main/plugins/use-family/scripts/use.py' -OutFile $Temporary
    $Local = $Temporary
  }
  if ($Auto) { $ArgsList += '--auto' }
  & $Python.Source $Local @ArgsList
  if ($LASTEXITCODE) { throw "use manager installation failed ($LASTEXITCODE)" }
} finally { if ($Temporary) { Remove-Item -LiteralPath $Temporary -ErrorAction SilentlyContinue } }
