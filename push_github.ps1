# Arfa - push the prepared commit to GitHub (branches main and master)
$ErrorActionPreference = 'Continue'
Set-Location -Path $PSScriptRoot
git --version *> $null
if ($LASTEXITCODE -ne 0) {
    Write-Host "Git is not installed on this computer." -ForegroundColor Red
    Write-Host "Install it from https://git-scm.com/download/win (default options), then run this again."
    Read-Host "Press Enter to close"; exit 1
}
git config --global --add safe.directory C:/arfa 2>$null
git log --oneline -1
Write-Host "Pushing to GitHub (a browser window may open to sign in)..." -ForegroundColor Cyan
git push origin main
$r1 = $LASTEXITCODE
git push origin main:master
$r2 = $LASTEXITCODE
if ($r1 -eq 0 -and $r2 -eq 0) { Write-Host "DONE - GitHub updated (main + master)." -ForegroundColor Green }
else { Write-Host "FAILED - see the message above (sign-in or permissions)." -ForegroundColor Red }
Read-Host "Press Enter to close"
