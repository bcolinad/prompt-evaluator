Run linting and type checking on the entire project.

```bash
uv run ruff check src/ tests/ --fix
uv run ruff format src/ tests/
uv run mypy src/
```

Fix any linting errors found. For mypy errors, add proper type annotations rather than suppressing with `# type: ignore`.
