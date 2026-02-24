Run Alembic database migrations.

```bash
# Check current migration status
uv run alembic current

# Run all pending migrations
uv run alembic upgrade head

# If you need to create a new migration after model changes:
# uv run alembic revision --autogenerate -m "description"
```
