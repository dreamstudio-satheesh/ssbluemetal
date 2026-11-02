# Windows Installation & Build Guide

## Option A: Run directly (Python required)

### 1. Install Python
- Download **Python 3.13+** from https://www.python.org/downloads/
- ✅ Check **"Add Python to PATH"** during installation

### 2. Copy the project
Copy the `billing/` folder to your Windows PC — e.g.:
```
C:\KalQuarry\billing\
```

### 3. Open Command Prompt
```cmd
cd C:\KalQuarry\billing
```

### 4. Setup virtual environment & install
```cmd
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

### 5. Run the app
```cmd
python main.py
```
Default login: `admin` / `admin123`

---

## Option B: Build standalone .exe (no Python needed)

### 1. Follow steps 1–4 from Option A

### 2. Install PyInstaller & build
```cmd
pip install pyinstaller
pyinstaller --onefile --windowed --name "KalQuarry" main.py
```

### 3. The .exe is at:
```
C:\KalQuarry\billing\dist\KalQuarry.exe
```
You can copy this single file to any Windows PC and run it directly.

---

## Option C: One-click launcher (`.bat` file)

Save this as `run.bat` inside `C:\KalQuarry\`:

```batch
@echo off
cd /d "C:\KalQuarry\billing"
call venv\Scripts\activate
python main.py
pause
```

Double-click `run.bat` to launch.

---

## Option D: Mobile API as a true Windows service

Runs the mobile API (`webapp.main:app`) in the background: starts **before anyone logs
in**, survives reboot, restarts after a crash. Needs an Administrator prompt once, at
install time only. The desktop app and the API share `C:\KalQuarry\billing\db\billing.db`.

Full walkthrough, service accounts, logging and troubleshooting:
**[webapp/WINDOWS_SERVICE.md](webapp/WINDOWS_SERVICE.md)**.

### 1. Prepare the API

```cmd
cd /d C:\KalQuarry\billing
py -3 -m venv .venv
.venv\Scripts\python -m pip install -r webapp\requirements-web.txt
copy webapp\.env.example webapp\.env
py -c "import secrets;print(secrets.token_hex(32))"
```

Paste the generated value into `webapp\.env` as `WEBAPP_SECRET=...`. Without it, every
phone is logged out on each API restart.

Test it in a console, then stop with `Ctrl+C`:

```cmd
webapi.bat
curl http://127.0.0.1:8000/api/health
```

### 2. Install NSSM and register the service

Download <https://nssm.cc/download> and extract `win64\nssm.exe` to
`C:\Tools\nssm\nssm.exe`. From an **elevated** Command Prompt:

```cmd
set NSSM=C:\Tools\nssm\nssm.exe
%NSSM% install SSBlueMetalAPI "C:\Windows\System32\cmd.exe"
%NSSM% set SSBlueMetalAPI AppParameters "/c C:\KalQuarry\billing\webapi.bat"
%NSSM% set SSBlueMetalAPI AppDirectory "C:\KalQuarry\billing"
%NSSM% set SSBlueMetalAPI DisplayName "S.S. Blue Metal API"
%NSSM% set SSBlueMetalAPI Start SERVICE_AUTO_START
%NSSM% set SSBlueMetalAPI AppExit Default Restart
%NSSM% set SSBlueMetalAPI AppRestartDelay 5000
mkdir C:\KalQuarry\billing\logs
%NSSM% set SSBlueMetalAPI AppStdout "C:\KalQuarry\billing\logs\api.log"
%NSSM% set SSBlueMetalAPI AppStderr "C:\KalQuarry\billing\logs\api-error.log"
%NSSM% start SSBlueMetalAPI
```

`webapi.bat` is the entry point on purpose: it loads `webapp\.env`, which the Python code
does not read by itself. Do not point NSSM at `uvicorn` directly unless you also add
`WEBAPP_SECRET` in NSSM's Environment tab.

### 3. Verify

```cmd
sc query SSBlueMetalAPI
sc qc SSBlueMetalAPI
curl http://127.0.0.1:8000/api/health
```

`STATE : 4 RUNNING`, `START_TYPE : 2 AUTO_START`, and `{"status":"ok"}`.
Then reboot, do **not** log in, and check the tunnel URL from a phone.

### 4. Cloudflare tunnel as a service

The API and the tunnel are separate services; both are set to Automatic:

```cmd
cloudflared service install <TUNNEL_TOKEN>
sc config cloudflared depend= SSBlueMetalAPI
```

The API stays bound to `127.0.0.1` — only `cloudflared` is exposed. Details:
[webapp/CLOUDFLARE_TUNNEL.md](webapp/CLOUDFLARE_TUNNEL.md).

### Manage

| Task | Command |
|------|---------|
| Status | `sc query SSBlueMetalAPI` |
| Start / stop / restart | `%NSSM% start SSBlueMetalAPI` / `stop` / `restart` |
| Edit config | `%NSSM% edit SSBlueMetalAPI` |
| Logs | `C:\KalQuarry\billing\logs\api.log`, `api-error.log` |
| Uninstall | `%NSSM% stop SSBlueMetalAPI` then `%NSSM% remove SSBlueMetalAPI confirm` |

---

## Quick reference

| Command | Purpose |
|---------|---------|
| `python main.py` | Run the app |
| `pyinstaller --onefile --windowed --name "KalQuarry" main.py` | Build .exe |
| `python -m venv venv` | Create virtual env |
| `venv\Scripts\activate` | Activate virtual env |
| `pip install -r requirements.txt` | Install dependencies |
| `webapi.bat` | Run the mobile API in a console |
| `sc query SSBlueMetalAPI` | Check the mobile API service |
| `cloudflared service install <TOKEN>` | Publish the API over HTTPS at boot |

---

## Troubleshooting

### "No module named PySide6" error

**Cause:** You skipped the virtual environment or didn't install dependencies.

**Fix — run these 3 commands in order:**

```cmd
cd C:\KalQuarry\billing
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

Make sure you see `(venv)` at the start of the command prompt line after step 3. If you don't see `(venv)`, the virtual environment is not activated — run `venv\Scripts\activate` again.

### "pip is not recognized"

**Cause:** Python was not added to PATH during installation.

**Fix:** Re-run the Python installer and ✅ check **"Add Python to PATH"**, then restart Command Prompt.
