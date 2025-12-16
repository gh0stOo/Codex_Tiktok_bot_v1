# PowerShell Script zum Starten der Development Container

Write-Host "Prüfe Docker..." -ForegroundColor Yellow

# Prüfe ob Docker läuft
try {
    docker ps | Out-Null
    Write-Host "Docker ist bereit!" -ForegroundColor Green
} catch {
    Write-Host "FEHLER: Docker ist nicht erreichbar!" -ForegroundColor Red
    Write-Host "Bitte starte Docker Desktop und warte bis es vollständig geladen ist." -ForegroundColor Yellow
    exit 1
}

Write-Host "`nStarte Development Container..." -ForegroundColor Yellow
Write-Host "Frontend wird auf http://localhost:5173 verfügbar sein" -ForegroundColor Cyan
Write-Host "Backend wird auf http://localhost:8000 verfügbar sein`n" -ForegroundColor Cyan

# Wechsle ins Projektverzeichnis
$scriptPath = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $scriptPath

# Starte Container
docker compose -f infra/docker-compose.dev.yml up --build -d

if ($LASTEXITCODE -eq 0) {
    Write-Host "`nContainer werden gestartet..." -ForegroundColor Green
    Write-Host "Warte 10 Sekunden..." -ForegroundColor Yellow
    Start-Sleep -Seconds 10
    
    Write-Host "`nContainer Status:" -ForegroundColor Cyan
    docker compose -f infra/docker-compose.dev.yml ps
    
    Write-Host "`nFrontend Logs (letzte 20 Zeilen):" -ForegroundColor Cyan
    docker compose -f infra/docker-compose.dev.yml logs frontend --tail=20
    
    Write-Host "`n✅ Container gestartet!" -ForegroundColor Green
    Write-Host "Frontend: http://localhost:5173" -ForegroundColor Yellow
    Write-Host "Backend: http://localhost:8000" -ForegroundColor Yellow
    Write-Host "`nLogs ansehen: docker compose -f infra/docker-compose.dev.yml logs -f" -ForegroundColor Gray
} else {
    Write-Host "`n❌ Fehler beim Starten der Container!" -ForegroundColor Red
    Write-Host "Prüfe die Logs: docker compose -f infra/docker-compose.dev.yml logs" -ForegroundColor Yellow
}

