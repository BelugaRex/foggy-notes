[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"

$repoRoot = (& git rev-parse --show-toplevel).Trim()
if ($LASTEXITCODE -ne 0 -or -not $repoRoot) {
    throw "Run this script from inside the Foggy Notes repository."
}

$hook = Join-Path $repoRoot ".githooks/pre-push"
$checker = Join-Path $repoRoot "scripts/check_drafts.py"
if (-not (Test-Path -LiteralPath $hook)) {
    throw "Missing hook: $hook"
}
if (-not (Test-Path -LiteralPath $checker)) {
    throw "Missing draft checker: $checker"
}

& python --version
if ($LASTEXITCODE -ne 0) {
    throw "Python is required to check local drafts."
}

& git -C $repoRoot config core.hooksPath .githooks
if ($LASTEXITCODE -ne 0) {
    throw "Could not configure core.hooksPath."
}

$configuredPath = (& git -C $repoRoot config --get core.hooksPath).Trim()
if ($configuredPath -ne ".githooks") {
    throw "Unexpected core.hooksPath: $configuredPath"
}

& python $checker --json | Out-Null
if ($LASTEXITCODE -ne 0) {
    throw "The draft checker could not inspect this workspace."
}

Write-Host "Installed Foggy Notes pre-push hook from .githooks."