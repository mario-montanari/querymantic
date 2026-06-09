# Publishing Spektr

This is the checklist to run before Spektr goes public. Nothing here reaches a
remote until every gate below is green. The repository ships with the gates
already wired: `.pre-commit-config.yaml` for the local hooks, the CI workflow at
`.github/workflows/publish-check.yml` for the same checks on every push, and
`.github/dependabot.yml` for dependency alerts. This document is the order to
run them in and what each one guards against.

There is no GitHub remote configured. Connecting one, pushing, or creating a
release is a separate, explicit step (see the last section).

## One-time setup

The audit tools are not part of the suite, so install them once into your
environment:

```
pip install pre-commit pip-audit pytest ruff bandit
pre-commit install
```

The core suite itself needs nothing installed: it runs on the Python standard
library. The optional libraries in `requirements-optional.txt` are only for the
Output Forge document formats and the optional STL seasonal path.

## The gates, in order

Run these from the plugin root (the `spektr/` directory). Each one must pass
before the next.

1. **Plugin structure.** `claude plugin validate .`
   The authoritative check for `plugin.json`, skills, agents, and commands. Run
   it locally, where you are logged in. CI runs an unofficial schema check only,
   so this local pass is the real one.

2. **Secrets, lint, and Python security.** `pre-commit run --all-files`
   This runs gitleaks (no key or token committed), ruff and ruff-format (lint
   and formatting), bandit (Python security), and the base hooks. If ruff
   auto-fixes a file, the run stops; re-run the same command and it passes the
   second time because the fix is already applied.

3. **Dependency audit.** `pip-audit -r requirements-optional.txt`
   Flags any optional library with a known vulnerability. The core has no
   third-party dependencies to audit.

4. **Tests.** `pytest -q`
   The full suite must be green. As of this writing that is 73 tests across all
   sprints, with a deterministic sample run included.

## Content checks (by hand)

These are project rules that no tool enforces, so check them yourself:

- **No em-dash anywhere.** Search every shipped file for the character and
  confirm zero hits.
- **No AI writing patterns** in the README or any public prose. Run the README
  through the humanizer rules before publishing.
- **NOTICE is current.** Every optional library the code imports is listed in
  `NOTICE` with its license. If a new library was added, or one was removed, the
  NOTICE must match the imports.
- **No internal references leak.** Public files cite primary sources only. They
  never name the internal framework, the research notes, or the verification
  ledger.
- **Least-privilege agents.** Each file under `agents/` declares only the tools
  it needs, nothing wider.
- **Sample data only.** The repository ships sample exports under
  `assets/samples/`, never a real client dataset. `runs/` and `*.run.json` are
  gitignored; confirm none are staged.

## Connecting to GitHub

Only after every gate above is green, and only with an explicit go:

- Create the repository (private first is the safe default; the analysis logic
  is the value).
- Protect `main`: require the publish check to pass before a merge.
- Push, then tag the release.

The vendored engine stays read-only. Refresh it only with `engine/sync_engine.py`,
never by editing the copy under `engine/` by hand.
