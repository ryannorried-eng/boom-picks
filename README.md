# Boom Picks (Paper Trading)

FastAPI + Postgres foundation for an autonomous sports betting analytics pipeline focused on measuring edge via Market CLV.

## Run locally
```bash
docker compose up --build
```

## Migrations
```bash
alembic -c backend/alembic.ini upgrade head
```

## Tests
```bash
pytest -q
```
