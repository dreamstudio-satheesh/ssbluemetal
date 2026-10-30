@echo off
setlocal
cd /d "%~dp0"

if exist webapp\.env (
  for /f "usebackq tokens=1,* delims==" %%A in ("webapp\.env") do (
    if not "%%A"=="" if not "%%A:~0,1"=="#" set "%%A=%%B"
  )
)

if not exist ".venv\Scripts\python.exe" (
  echo Missing .venv
  echo   py -3 -m venv .venv
  echo   .venv\Scripts\python -m pip install -r webapp\requirements-web.txt
  exit /b 1
)

set "HOST=127.0.0.1"
if defined API_HOST set "HOST=%API_HOST%"
set "PORT=8000"
if defined API_PORT set "PORT=%API_PORT%"

echo API on http://%HOST%:%PORT%  (docs: /docs)
".venv\Scripts\python.exe" -m uvicorn webapp.main:app --host %HOST% --port %PORT%
