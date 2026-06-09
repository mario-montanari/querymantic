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

# Every gate is fail-closed: a missing tool BLOCKS the publish rather than skipping
# the check, so the script can never push with a gate silently bypassed.

# 1. Plugin structure (authoritative, local, where you are logged in)
if (Have "claude") {
  claude plugin validate .
  Stop-IfFailed "claude plugin validate"
} else {
  Write-Host "BLOCKED: 'claude' (Claude Code) not found; plugin validation is required. No push." -ForegroundColor Red
  exit 1
}

# 2. pre-commit: secrets (gitleaks), lint and format (ruff), security (bandit)
if (Have "pre-commit") {
  pre-commit run --all-files
  Stop-IfFailed "pre-commit"
} else {
  Write-Host "BLOCKED: 'pre-commit' not found; secret/lint/security gates are required. Install with: pip install pre-commit. No push." -ForegroundColor Red
  exit 1
}

# 3. Dependency audit of the optional libraries
if (-not (Have "pip-audit")) {
  Write-Host "BLOCKED: 'pip-audit' not found; the dependency audit is required. Install with: pip install pip-audit. No push." -ForegroundColor Red
  exit 1
}
if (Test-Path "requirements-optional.txt") {
  pip-audit -r requirements-optional.txt
  Stop-IfFailed "pip-audit"
} else {
  Write-Host "OK: no requirements-optional.txt to audit (core is stdlib-only)" -ForegroundColor Green
}

# 4. Tests
$haveTests = (Test-Path "evals") -or (Test-Path "tests")
if ($haveTests) {
  if (Have "pytest") {
    pytest -q
    Stop-IfFailed "pytest"
  } else {
    Write-Host "BLOCKED: tests are present but 'pytest' is not installed; the suite must run before a publish. Install with: pip install pytest. No push." -ForegroundColor Red
    exit 1
  }
} else {
  Write-Host "OK: no test directory present to run" -ForegroundColor Green
}

Write-Host "== All green. Proceeding with git ==" -ForegroundColor Cyan

git add -A
# Distinguish a clean tree (legitimately nothing to commit, push prepared commits)
# from a real commit failure (a failing hook, for example), which must block.
$pending = git status --porcelain
if (-not $pending) {
  Write-Host "OK: working tree clean, nothing new to commit. Pushing prepared commits." -ForegroundColor Green
} else {
  git commit -m "$Message"
  Stop-IfFailed "git commit"
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
