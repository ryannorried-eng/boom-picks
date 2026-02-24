# Boom Picks (Paper Trading)

FastAPI + Postgres foundation for an autonomous sports betting analytics pipeline focused on measuring edge via Market CLV.

## Run locally
```bash
docker compose up -d --build
```

## Rebuild clean (after migration changes)
```bash
docker compose down -v && docker compose up -d --build
```

## Migrations (inside container)
```bash
docker compose exec backend bash -lc "cd backend && alembic upgrade head"
```

## Tests
```bash
docker compose exec backend pytest -q
```
