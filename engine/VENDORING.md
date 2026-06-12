# Vendored engine: provenance and declared deltas

The `engine/keyword-intelligence/` directory is a vendored, read-only copy of
the MIT-licensed engine published at
<https://github.com/mario-montanari/keyword-intelligence>. Querymantic never
edits it in place: every change lands upstream first, then a re-vendor commit
copies the updated files here. Before any re-vendor, diff this snapshot
against the upstream main and reconcile it with the list below; anything not
on the list must stop the re-vendor and be reported.

## Reference

- Upstream repository: `mario-montanari/keyword-intelligence`
- Upstream commit this snapshot corresponds to: `798db1d2cc468bcd8347671b5ff2b9311c848cf7`
  (`fix(parser): detect difficulty scale at column level so decimals survive`)
- Re-vendored on: 2026-06-12

## Declared deltas between this snapshot and the upstream commit

These differences are intentional and known. They are the only acceptable
ones; a future comparison that finds anything else means the snapshot and the
upstream have drifted.

1. **`tests/` is not vendored.** The upstream regression tests (introduced
   with `798db1d`) stay upstream so the suite's pytest run does not collect
   engine-internal tests. The suite pins the same behavior through the
   adapter in `evals/test_engine_difficulty_scale.py`.
2. **`.gitignore` exists here, not upstream.** The public upstream currently
   tracks no `.gitignore`; this snapshot keeps the one from the original
   release. Restoring it upstream is recorded debt, out of scope for the
   difficulty fix round.
3. **Line endings in `expected_outputs/`.** The upstream blobs for the
   generated sample outputs are CRLF; this repository normalizes text to LF
   via `.gitattributes`, so the same files are LF here. Content is identical
   when compared with `git diff --ignore-cr-at-eol`.

## Known upstream debt (separate round, on explicit go)

Recorded for traceability, none of it blocks the suite: restore `.gitignore`,
add a `.gitattributes`, normalize line endings, remove the two pre-existing
unused imports in `scripts/analyze.py` (`asdict`, `Iterable`), and cut a
`v1.0.1` tag or a changelog line for the difficulty fix.
