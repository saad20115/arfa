# Arfa - take a backup of the current site (DB + filestore) into C:\arfa\backups, e.g. before uploading to the server
$ErrorActionPreference = 'Continue'
Set-Location -Path $PSScriptRoot
$stamp = Get-Date -Format 'yyyyMMdd_HHmm'
New-Item -ItemType Directory -Force -Path backups | Out-Null
docker compose up -d --wait db
docker compose exec -T db pg_dump -U odoo -Fc -f /tmp/backup.dump arfa2026
docker compose cp db:/tmp/backup.dump "backups/arfa2026_for_server_$stamp.dump"
docker compose exec -T db rm -f /tmp/backup.dump
docker compose up -d odoo
docker compose cp odoo:/var/lib/odoo/filestore/arfa2026 "backups/filestore_for_server_$stamp"
Write-Host ""
Write-Host "DONE - backup for the server:" -ForegroundColor Green
Write-Host "  C:\arfa\backups\arfa2026_for_server_$stamp.dump"
Write-Host "  C:\arfa\backups\filestore_for_server_$stamp"
Read-Host "Press Enter to close"
