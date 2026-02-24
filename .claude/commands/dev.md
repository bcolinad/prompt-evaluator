Start the development environment.

```bash
# Ensure Docker services are running
docker compose -f docker/docker-compose.yml up -d

# Run migrations
uv run alembic upgrade head

# Start Chainlit dev server with hot reload
uv run chainlit run src/app.py -w
```
