@echo off
cd /d "%~dp0"
docker compose up -d
start "" http://localhost:8071/web/login
