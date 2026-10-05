# Arfa - upload the latest "for_server" backup (made by backup_now.ps1) to the VPS: /root/arfa_upload/
param([string]$Server = "72.61.98.195", [string]$User = "root")
$ErrorActionPreference = 'Continue'
Set-Location -Path $PSScriptRoot
$dump = Get-ChildItem backups -Filter "arfa2026_for_server_*.dump" | Sort-Object LastWriteTime -Descending | Select-Object -First 1
if (-not $dump) { Write-Host "No backup found. Run backup_now.ps1 first." -ForegroundColor Red; Read-Host "Press Enter"; exit 1 }
$stamp = $dump.BaseName -replace 'arfa2026_for_server_', ''
$fs = "backups\filestore_for_server_$stamp"
if (-not (Test-Path $fs)) { Write-Host "Filestore folder $fs not found." -ForegroundColor Red; Read-Host "Press Enter"; exit 1 }
Write-Host "Uploading $($dump.Name) + filestore to ${User}@${Server}:/root/arfa_upload/" -ForegroundColor Cyan
Write-Host "(you will be asked for the server password - typing is invisible, that's normal)"
ssh "${User}@${Server}" "mkdir -p /root/arfa_upload"
scp "$($dump.FullName)" "${User}@${Server}:/root/arfa_upload/arfa2026.dump"
scp -r "$fs" "${User}@${Server}:/root/arfa_upload/filestore"
if ($LASTEXITCODE -eq 0) { Write-Host "DONE - uploaded to /root/arfa_upload/" -ForegroundColor Green } else { Write-Host "FAILED - check the password / connection" -ForegroundColor Red }
Read-Host "Press Enter to close"
