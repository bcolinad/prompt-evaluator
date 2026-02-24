Run the full test suite with coverage enforcement.

```bash
uv run pytest tests/ -v --cov=src --cov-report=term-missing --cov-fail-under=80
```

If any tests fail, analyze the failure and fix it. If coverage is below 80%, identify uncovered code paths and write tests for them.
