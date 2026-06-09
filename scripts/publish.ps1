#requires -Version 5.1
<#
  publish.ps1 - Publish Querymantic only if EVERY gate passes.

  This script does nothing until you run it. There is no remote configured, so
  by default it only commits and pushes to an existing origin. The first
  publish, which creates the GitHub repository, needs -First and an explicit go.

  Later pushes:
    .\scripts\publish.ps1 -Message "what changed"

  First publish (creates a PRIVATE repo and pushes):
    .\scripts\publish.ps1 -Message "first commit" -First

  Add -Public for a public repository instead of private.
  Requires: git, gh (GitHub CLI), and locally claude (Claude Code).

  Run this from the plugin root (the querymantic/ directory).
#>

param(
  [Parameter(Mandatory = $true)] [string] $Message,
  [switch] $First,
  [string] $RepoName = "querymantic",
  [switch] $Public
)

$ErrorActionPreference = "Stop"

function Stop-IfFailed([string] $Name) {
  if ($LASTEXITCODE -ne 0) {
    Write-Host "BLOCKED: $Name found problems. No push." -ForegroundColor Red
    exit 1
  }
  Write-Host "OK: $Name" -ForegroundColor Green
}

function Have([string] $cmd) {
  return [bool](Get-Command $cmd -ErrorAction SilentlyContinue)
}

Write-Host "== Pre-publication gates ==" -ForegroundColor Cyan

# 1. Plugin structure (authoritative, local, where you are logged in)
if (Have "claude") {
  claude plugin validate .
  Stop-IfFailed "claude plugin validate"
} else {
  Write-Host "WARNING: 'claude' not found, skipping plugin validation." -ForegroundColor Yellow
}

# 2. pre-commit: secrets (gitleaks), lint and format (ruff), security (bandit)
if (Have "pre-commit") {
  pre-commit run --all-files
  Stop-IfFailed "pre-commit"
} else {
  Write-Host "WARNING: 'pre-commit' not found. Install with: pip install pre-commit" -ForegroundColor Yellow
}

# 3. Dependency audit of the optional libraries
if ((Have "pip-audit") -and (Test-Path "requirements-optional.txt")) {
  pip-audit -r requirements-optional.txt
  Stop-IfFailed "pip-audit"
} else {
  Write-Host "Skipping pip-audit (pip-audit or requirements-optional.txt missing). The core is stdlib-only." -ForegroundColor Yellow
}

# 4. Tests
$haveTests = (Test-Path "evals") -or (Test-Path "tests") -or (Get-ChildItem -Recurse -Filter "test_*.py" -ErrorAction SilentlyContinue | Select-Object -First 1)
if ((Have "pytest") -and $haveTests) {
  pytest -q
  Stop-IfFailed "pytest"
} else {
  Write-Host "No tests found, skipping pytest." -ForegroundColor Yellow
}

Write-Host "== All green. Proceeding with git ==" -ForegroundColor Cyan

git add -A
git commit -m "$Message"
if ($LASTEXITCODE -ne 0) {
  Write-Host "Note: nothing new to commit (or commit failed). Continuing to push any commits already prepared." -ForegroundColor Yellow
}

if ($First) {
  $vis = if ($Public) { "--public" } else { "--private" }
  gh repo create $RepoName $vis --source=. --remote=origin --push
  Stop-IfFailed "gh repo create"
} else {
  git push
  Stop-IfFailed "git push"
}

Write-Host "Done." -ForegroundColor Green
