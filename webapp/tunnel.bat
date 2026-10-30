@echo off
setlocal
cd /d "%~dp0\.."

where cloudflared >nul 2>&1
if errorlevel 1 (
  echo cloudflared not found. Install: winget install --id Cloudflare.cloudflared
  exit /b 1
)

set "PORT=8000"
if defined API_PORT set "PORT=%API_PORT%"

curl -s -m 3 http://127.0.0.1:%PORT%/api/health >nul 2>&1
if errorlevel 1 (
  echo API is not running on 127.0.0.1:%PORT% - start it first: webapi.bat
  exit /b 1
)

if defined TUNNEL_TOKEN (
  echo Token tunnel -^> http://127.0.0.1:%PORT%
  cloudflared tunnel --no-autoupdate run --token %TUNNEL_TOKEN%
  exit /b %errorlevel%
)

if defined TUNNEL_NAME (
  echo Named tunnel %TUNNEL_NAME% -^> http://127.0.0.1:%PORT%
  cloudflared tunnel --no-autoupdate run %TUNNEL_NAME%
  exit /b %errorlevel%
)

echo Quick tunnel -^> http://127.0.0.1:%PORT%  (URL changes on every restart)
cloudflared tunnel --no-autoupdate --url http://127.0.0.1:%PORT%
