# Arfa - apply the new version of the website module (wasm_website) to the local Odoo
# 1) backs up DB + filestore to C:\arfa\backups  2) upgrades wasm_website  3) restarts Odoo
$ErrorActionPreference = 'Continue'
Set-Location -Path $PSScriptRoot
Start-Transcript -Path (Join-Path $PSScriptRoot 'update_log.txt') -Force | Out-Null
function Step($m) { Write-Host ""; Write-Host "==== $m ====" -ForegroundColor Cyan }
function Fail($m) { Write-Host "FAILED: $m" -ForegroundColor Red; Stop-Transcript | Out-Null; Read-Host "Press Enter to close"; exit 1 }
$stamp = Get-Date -Format 'yyyyMMdd_HHmm'
New-Item -ItemType Directory -Force -Path backups | Out-Null

Step "1/4 Backup database"
docker compose up -d --wait db
docker compose exec -T db pg_dump -U odoo -Fc -f /tmp/backup.dump arfa2026
if ($LASTEXITCODE -ne 0) { Fail "pg_dump" }
docker compose cp db:/tmp/backup.dump "backups/arfa2026_before_update_$stamp.dump"
if ($LASTEXITCODE -ne 0) { Fail "copy backup" }
docker compose exec -T db rm -f /tmp/backup.dump

Step "2/4 Backup filestore"
docker compose up -d odoo
docker compose cp odoo:/var/lib/odoo/filestore/arfa2026 "backups/filestore_before_update_$stamp"
if ($LASTEXITCODE -ne 0) { Fail "filestore backup" }

Step "3/4 Updating the website module (1-3 minutes)"
docker compose stop odoo
docker compose run --rm -T odoo odoo -d arfa2026 -u wasm_website --stop-after-init --no-http --log-level=warn
if ($LASTEXITCODE -ne 0) { Fail "module update - restore the backup from C:\arfa\backups if needed" }
$v = "$(docker compose exec -T db psql -U odoo -d arfa2026 -tAc "select latest_version from ir_module_module where name='wasm_website'")".Trim()
Write-Host "wasm_website version: $v"

Step "4/4 Starting Odoo"
docker compose up -d odoo
$up = $false
for ($i = 0; $i -lt 60; $i++) { Start-Sleep 3; try { $r = Invoke-WebRequest -UseBasicParsing -TimeoutSec 5 http://localhost:8071/web/login; if ($r.StatusCode -eq 200) { $up = $true; break } } catch {} }
if (-not $up) { docker compose logs --tail 60 odoo; Fail "Odoo did not answer on http://localhost:8071" }
Write-Host ""
Write-Host "DONE - website module updated to $v. Backups are in C:\arfa\backups" -ForegroundColor Green
Start-Process "http://localhost:8071/"
Stop-Transcript | Out-Null
Read-Host "Press Enter to close"
