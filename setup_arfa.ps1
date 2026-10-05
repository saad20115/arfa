# Arfa - one-click local setup: Odoo 19 + PostgreSQL 16 on Docker Desktop
# Restores arfa2026_db.dump and arfa2026_filestore.tar.gz, then opens http://localhost:8071
param([switch]$Force)
$ErrorActionPreference = 'Continue'
Set-Location -Path $PSScriptRoot
Start-Transcript -Path (Join-Path $PSScriptRoot 'setup_log.txt') -Force | Out-Null

function Step($m) { Write-Host ""; Write-Host "==== $m ====" -ForegroundColor Cyan }
function Fail($m) { Write-Host "FAILED: $m" -ForegroundColor Red; Stop-Transcript | Out-Null; Read-Host "Press Enter to close"; exit 1 }

Step "1/6 Checking Docker"
docker info *> $null
if ($LASTEXITCODE -ne 0) {
    $dd = "C:\Program Files\Docker\Docker\Docker Desktop.exe"
    if (Test-Path $dd) { Write-Host "Starting Docker Desktop..."; Start-Process $dd } else { Fail "Docker Desktop not found" }
    $ok = $false
    for ($i = 0; $i -lt 60; $i++) { Start-Sleep 5; docker info *> $null; if ($LASTEXITCODE -eq 0) { $ok = $true; break }; Write-Host "  waiting for Docker... ($($i*5)s)" }
    if (-not $ok) { Fail "Docker did not start within 5 minutes. Open Docker Desktop, finish its setup, then run this again." }
}
docker version --format "Docker {{.Server.Version}}"

Step "2/6 Downloading images (odoo:19, postgres:16) - first time can take several minutes"
docker compose pull
if ($LASTEXITCODE -ne 0) { Fail "docker compose pull" }

Step "3/6 Starting PostgreSQL"
docker compose up -d --wait db
if ($LASTEXITCODE -ne 0) { Fail "starting db" }

$exists = "$(docker compose exec -T db psql -U odoo -d postgres -tAc "select 1 from pg_database where datname='arfa2026'")".Trim()
if ($exists -eq '1' -and -not $Force) {
    Write-Host "Database arfa2026 already exists - skipping restore (run with -Force to re-restore)."
    $restored = $false
} else {
    Step "4/6 Restoring database arfa2026"
    docker compose stop odoo 2>$null
    if ($exists -eq '1') { docker compose exec -T db dropdb -U odoo arfa2026 }
    docker compose cp arfa2026_db.dump db:/tmp/arfa.dump
    docker compose exec -T db createdb -U odoo -O odoo arfa2026
    docker compose exec -T db pg_restore -U odoo -d arfa2026 --no-owner --no-privileges -j 4 /tmp/arfa.dump
    Write-Host "pg_restore exit code: $LASTEXITCODE (1 = warnings only)"
    $n = "$(docker compose exec -T db psql -U odoo -d arfa2026 -tAc "select count(*) from ir_module_module where state='installed'")".Trim()
    Write-Host "Installed modules in restored DB: $n"
    if (-not $n -or [int]$n -lt 1) { Fail "restore produced an empty database" }
    docker compose exec -T db rm -f /tmp/arfa.dump

    Step "5/6 Restoring filestore"
    docker compose run --rm --no-deps -u root --entrypoint bash odoo -c "mkdir -p /var/lib/odoo/filestore && rm -rf /var/lib/odoo/filestore/arfa2026 && tar xzf /mnt/arfa-src/arfa2026_filestore.tar.gz -C /var/lib/odoo/filestore && chown -R odoo:odoo /var/lib/odoo && echo files: && find /var/lib/odoo/filestore/arfa2026 -type f | wc -l"
    if ($LASTEXITCODE -ne 0) { Fail "filestore extraction" }
    $restored = $true
}

Step "6/6 Updating custom modules and starting Odoo"
docker compose run --rm odoo odoo -d arfa2026 -u wasm_debrand,wasm_website --stop-after-init --no-http
Write-Host "module update exit code: $LASTEXITCODE"
docker compose up -d odoo
$up = $false
for ($i = 0; $i -lt 60; $i++) {
    Start-Sleep 3
    try { $r = Invoke-WebRequest -UseBasicParsing -TimeoutSec 5 http://localhost:8071/web/login; if ($r.StatusCode -eq 200) { $up = $true; break } } catch {}
}
if (-not $up) { docker compose logs --tail 60 odoo; Fail "Odoo did not answer on http://localhost:8071" }

Write-Host ""
Write-Host "DONE - Odoo is running at http://localhost:8071" -ForegroundColor Green
Write-Host "Website: http://localhost:8071/   Backend: http://localhost:8071/web"
Start-Process "http://localhost:8071/web/login"
Stop-Transcript | Out-Null
Start-Sleep 8
