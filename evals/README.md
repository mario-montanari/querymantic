# Evals

Scenarios and tests that prove each sprint's deliverable.

- `scenarios/` holds declarative YAML scenarios: an input, the command, and the
  behaviour to expect. They document what a run should do in plain terms.
- `test_*.py` files are pytest checks on the calculations and contracts. They run
  the real pipeline on the sample corpus and assert concrete results.

Run the tests from the plugin root:

```bash
pytest -q
```

Each sprint adds a scenario and at least one test, and every test must stay green
before the sprint closes.
