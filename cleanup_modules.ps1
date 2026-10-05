# Arfa - uninstall unused Odoo modules (keeps website, contacts, mail, wasm_* and their dependencies)
# 1) backs up DB + filestore to C:\arfa\backups  2) uninstalls 158 unused modules  3) restarts Odoo
$ErrorActionPreference = 'Continue'
Set-Location -Path $PSScriptRoot
Start-Transcript -Path (Join-Path $PSScriptRoot 'cleanup_log.txt') -Force | Out-Null
function Step($m) { Write-Host ""; Write-Host "==== $m ====" -ForegroundColor Cyan }
function Fail($m) { Write-Host "FAILED: $m" -ForegroundColor Red; Stop-Transcript | Out-Null; Read-Host "Press Enter to close"; exit 1 }

$stamp = Get-Date -Format 'yyyyMMdd_HHmm'
New-Item -ItemType Directory -Force -Path backups | Out-Null

Step "1/4 Backup database"
docker compose up -d --wait db
docker compose exec -T db pg_dump -U odoo -Fc -f /tmp/backup.dump arfa2026
if ($LASTEXITCODE -ne 0) { Fail "pg_dump" }
docker compose cp db:/tmp/backup.dump "backups/arfa2026_before_cleanup_$stamp.dump"
if ($LASTEXITCODE -ne 0) { Fail "copy backup" }
docker compose exec -T db rm -f /tmp/backup.dump
Write-Host ("DB backup: backups\arfa2026_before_cleanup_$stamp.dump  (" + [math]::Round((Get-Item "backups/arfa2026_before_cleanup_$stamp.dump").Length/1MB,1) + " MB)")

Step "2/4 Backup filestore"
docker compose up -d odoo
docker compose cp odoo:/var/lib/odoo/filestore/arfa2026 "backups/filestore_before_cleanup_$stamp"
if ($LASTEXITCODE -ne 0) { Fail "filestore backup" }
Write-Host "Filestore backup: backups\filestore_before_cleanup_$stamp"

Step "3/4 Uninstalling unused modules (about 3-5 minutes)"
docker compose stop odoo
docker compose run --rm -T --entrypoint bash odoo -c "odoo shell -c /etc/odoo/odoo.conf -d arfa2026 --no-http --log-level=warn < /mnt/arfa-src/docker/uninstall_unused.py 2>&1 | grep -E 'round|ok |cleaned|ALL DONE|Traceback|Error' | grep -v 'bad query'"
$left = "$(docker compose exec -T db psql -U odoo -d arfa2026 -tAc "select count(*) from ir_module_module where state='installed'")".Trim()
Write-Host "Installed modules now: $left"

Step "4/4 Starting Odoo"
docker compose up -d odoo
$up = $false
for ($i = 0; $i -lt 60; $i++) { Start-Sleep 3; try { $r = Invoke-WebRequest -UseBasicParsing -TimeoutSec 5 http://localhost:8071/web/login; if ($r.StatusCode -eq 200) { $up = $true; break } } catch {} }
if (-not $up) { docker compose logs --tail 60 odoo; Fail "Odoo did not answer on http://localhost:8071" }
Write-Host ""
Write-Host "DONE - installed modules: $left (was 202). Backups are in C:\arfa\backups" -ForegroundColor Green
Start-Process "http://localhost:8071/"
Stop-Transcript | Out-Null
Read-Host "Press Enter to close"
