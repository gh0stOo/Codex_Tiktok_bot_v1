# Docker Setup Anleitung

## Voraussetzungen
- Docker Desktop muss laufen und vollständig gestartet sein
- Prüfe ob Docker bereit ist: `docker ps` (sollte ohne Fehler laufen)

## Development Mode (Port 5173)

### Container starten:
```bash
cd C:\OpenCode-Infrastructure\Projects\Codex_Tiktok_bot_v1
make up-dev
# oder
docker compose -f infra/docker-compose.dev.yml up --build -d
```

### Frontend erreichbar:
- **Frontend**: http://localhost:5173
- **Backend**: http://localhost:8000
- **Backend Health**: http://localhost:8000/health/healthz

### Logs ansehen:
```bash
make logs-dev
# oder
docker compose -f infra/docker-compose.dev.yml logs -f frontend
```

### Container stoppen:
```bash
make down-dev
# oder
docker compose -f infra/docker-compose.dev.yml down
```

## Production Mode (Port 80)

### Container starten:
```bash
make up
# oder
docker compose -f infra/docker-compose.yml up --build -d
```

### Frontend erreichbar:
- **Frontend**: http://localhost (Port 80)
- **Backend**: http://localhost:8000

## Troubleshooting

### Port 5173 nicht erreichbar?

1. **Prüfe ob Container laufen:**
   ```bash
   docker ps
   ```
   Sollte `frontend` Container zeigen

2. **Prüfe Frontend Logs:**
   ```bash
   docker compose -f infra/docker-compose.dev.yml logs frontend
   ```

3. **Prüfe ob Port belegt ist:**
   ```bash
   netstat -ano | findstr :5173
   ```

4. **Container neu starten:**
   ```bash
   docker compose -f infra/docker-compose.dev.yml restart frontend
   ```

5. **Container komplett neu bauen:**
   ```bash
   docker compose -f infra/docker-compose.dev.yml down
   docker compose -f infra/docker-compose.dev.yml up --build -d
   ```

### Docker Desktop nicht erreichbar?

- Docker Desktop neu starten
- Warte bis Docker vollständig gestartet ist (Icon in der Taskleiste)
- Prüfe: `docker ps` sollte funktionieren

### Datenbank Migrationen:

Nach dem ersten Start:
```bash
docker compose -f infra/docker-compose.dev.yml exec backend sh -c "cd /app/migrations && PYTHONPATH=/app alembic upgrade head"
```


