# Run the API as a true Windows service

Starts **before anyone logs in**, survives reboot, restarts automatically after a crash.
Requires an Administrator prompt for installation only — not for daily use.

Use this when the Windows PC is the production server for the mobile app. For a quick
manual run, use `webapi.bat` instead (see [README.md](README.md#windows-recommended-for-production)).

---

## 1. What you get

| | |
|---|---|
| Service name | `SSBlueMetalAPI` |
| Start type | Automatic (boot) |
| Logon | Dedicated account or Local System — no interactive login |
| Listener | `127.0.0.1:8000` by default (never exposed directly) |
| Restart | On crash, with throttle |
| Logs | `C:\KalQuarry\billing\logs\api.log`, `api-error.log` (rotated) |

The service runs `webapi.bat`, so `webapp\.env` stays the single source of truth for
`WEBAPP_SECRET` and the other settings. The Python code does **not** read `.env` by
itself — the batch file loads it into the process environment. Do not skip that step.

---

## 2. Why `sc.exe create` alone does not work

A Windows service must speak the Service Control Protocol (start / stop / pause
callbacks) and report status to the Service Control Manager. A Python process or a
`.bat` file does neither, so `sc.exe create ... binPath= uvicorn` installs something
that fails with **error 1053: the service did not respond in a timely fashion**.

You need a small shim that hosts the process as a service. This guide uses **NSSM**
(Non-Sucking Service Manager), the standard choice for Python services. A WinSW
alternative is in [§10](#10-alternative-winsw).

---

## 3. Prerequisites

1. **Python 3.12+** with *Add Python to PATH* enabled.
2. Project copied to a **local** folder outside OneDrive, e.g. `C:\KalQuarry\billing`
   (SQLite in a synced folder causes `database is locked`).
3. Writable folders exist: `db`, `pdf_output`, `backup`, `logs`.
4. Venv and dependencies:

```cmd
cd /d C:\KalQuarry\billing
py -3 -m venv .venv
.venv\Scripts\python -m pip install -r webapp\requirements-web.txt
```

5. `webapp\.env` created and `WEBAPP_SECRET` set to a long random value:

```cmd
copy webapp\.env.example webapp\.env
py -c "import secrets;print(secrets.token_hex(32))"
```

Paste the output into `webapp\.env` as `WEBAPP_SECRET=<value>`. If it is missing, the
API generates a random secret per process and **every APK is logged out on each restart**.

6. Sanity check before installing the service:

```cmd
webapi.bat
curl http://127.0.0.1:8000/api/health
```

Expect `{"status":"ok"}`. Stop it with `Ctrl+C` before continuing — two processes cannot
bind port 8000.

---

## 4. Install NSSM

Download the 64-bit build from <https://nssm.cc/download> and extract `win64\nssm.exe`
to `C:\Tools\nssm\nssm.exe` (or install with `choco install nssm`).

Open an **elevated** Command Prompt:

```cmd
set NSSM=C:\Tools\nssm\nssm.exe
%NSSM% version
```

---

## 5. Install the service

Point NSSM at `cmd.exe` running `webapi.bat` so the `.env` loader is used:

```cmd
set NSSM=C:\Tools\nssm\nssm.exe

%NSSM% install SSBlueMetalAPI "C:\Windows\System32\cmd.exe"
%NSSM% set SSBlueMetalAPI AppParameters "/c C:\KalQuarry\billing\webapi.bat"
%NSSM% set SSBlueMetalAPI AppDirectory "C:\KalQuarry\billing"
%NSSM% set SSBlueMetalAPI DisplayName "S.S. Blue Metal API"
%NSSM% set SSBlueMetalAPI Description "JSON API for the S.S. Blue Metal mobile app (uvicorn, 127.0.0.1:8000)"
%NSSM% set SSBlueMetalAPI Start SERVICE_AUTO_START
```

`AppParameters` must be a single line: `/c C:\KalQuarry\billing\webapi.bat`. If the project
lives in a path with spaces, quote it:

```cmd
%NSSM% set SSBlueMetalAPI AppParameters "/c \"C:\My Folder\KalQuarry\billing\webapi.bat\""
```

If the quoting is mangled, use `%NSSM% edit SSBlueMetalAPI` → **Application** tab and set
it in the GUI.

### Direct-python variant (no `.env` loader)

Only if you prefer to start Python directly:

```cmd
%NSSM% install SSBlueMetalAPI "C:\KalQuarry\billing\.venv\Scripts\python.exe"
%NSSM% set SSBlueMetalAPI AppParameters "-m uvicorn webapp.main:app --host 127.0.0.1 --port 8000"
%NSSM% set SSBlueMetalAPI AppDirectory "C:\KalQuarry\billing"
```

Then you **must** add every value from `webapp\.env` to the process environment:
`%NSSM% edit SSBlueMetalAPI` → **Environment** tab, one `KEY=VALUE` per line. At minimum
`WEBAPP_SECRET`. Without it, tokens break on every restart.

---

## 6. Restart policy, throttling and logs

```cmd
%NSSM% set SSBlueMetalAPI AppExit Default Restart
%NSSM% set SSBlueMetalAPI AppRestartDelay 5000
%NSSM% set SSBlueMetalAPI AppThrottle 10000

mkdir C:\KalQuarry\billing\logs
%NSSM% set SSBlueMetalAPI AppStdout "C:\KalQuarry\billing\logs\api.log"
%NSSM% set SSBlueMetalAPI AppStderr "C:\KalQuarry\billing\logs\api-error.log"
%NSSM% set SSBlueMetalAPI AppRotateFiles 1
%NSSM% set SSBlueMetalAPI AppRotateOnline 1
%NSSM% set SSBlueMetalAPI AppRotateBytes 10485760
```

`AppThrottle` stops NSSM from hammering a service that dies on startup (for example a
missing venv or a port already in use) — it waits increasingly long between attempts.

Stop behaviour defaults to Ctrl+C first, then terminate. Uvicorn handles Ctrl+C cleanly,
which lets SQLite finish its write-ahead-log checkpoint.

---

## 7. Run as a dedicated account

By default the service runs as **Local System**. That works if the project is under
`C:\KalQuarry\billing` (not under a user profile). For least privilege, create a local user
`svc-ssblue` with no interactive logon rights and grant it:

- *Log on as a service* — `secpol.msc` → Local Policies → User Rights Assignment.
- Full control on `db`, `pdf_output`, `backup`, `logs`; read+execute on the code.

Set it via the GUI so the password does not land in command history or the Event Log:

```cmd
%NSSM% edit SSBlueMetalAPI
```

→ **Log on** tab → *This account* → `.\\svc-ssblue` + password.

---

## 8. Start and verify

```cmd
%NSSM% start SSBlueMetalAPI
sc query SSBlueMetalAPI
sc qc SSBlueMetalAPI
curl http://127.0.0.1:8000/api/health
```

Expected:

- `sc query` → `STATE : 4 RUNNING`
- `sc qc` → `START_TYPE : 2 AUTO_START`
- `curl` → `{"status":"ok"}`
- `logs\api.log` contains `Uvicorn running on http://127.0.0.1:8000`

Crash recovery check (do this off-hours):

```cmd
taskkill /F /PID <pid-from: netstat -ano | findstr :8000>
timeout /t 15
curl http://127.0.0.1:8000/api/health
```

The service must come back on its own.

### Reboot test — the part people forget

1. `shutdown /r /t 0`
2. At the lock screen, **do not log in**.
3. From a phone with the tunnel URL: `https://<your-host>/api/health` → `{"status":"ok"}`.
4. Or log in later and run `sc query SSBlueMetalAPI`.

A service that only works after login was configured with *Automatic (Delayed Start)*
plus a logon trigger, or is actually a Task Scheduler entry. Check with `sc qc`.

---

## 9. Coexistence with the Cloudflare tunnel service

The API service and `cloudflared` are independent. Install the tunnel service as
described in [CLOUDFLARE_TUNNEL.md](CLOUDFLARE_TUNNEL.md#37-install-as-a-windows-service-auto-start-on-boot):

```cmd
cloudflared service install <TUNNEL_TOKEN>
sc config cloudflared depend= SSBlueMetalAPI
```

The dependency only orders startup; `cloudflared` retries on its own, so a slow API
start does not matter. Keep the API on `127.0.0.1` — only `cloudflared` is exposed.

Do **not** open `8000` in Windows Firewall. If someone sets `API_HOST=0.0.0.0` in
`.env`, add a firewall rule restricted to the LAN, and accept that the API is then
reachable without the tunnel.

---

## 10. Alternative: WinSW

Same result, single `.exe` plus an XML file, no install step. Keep the `cmd.exe` wrapper
so `webapp\.env` is still loaded.

`C:\KalQuarry\billing\ssblue-api.xml`:

```xml
<service>
  <id>SSBlueMetalAPI</id>
  <name>S.S. Blue Metal API</name>
  <description>JSON API for the mobile app</description>
  <executable>C:\Windows\System32\cmd.exe</executable>
  <arguments>/c C:\KalQuarry\billing\webapi.bat</arguments>
  <workingdirectory>C:\KalQuarry\billing</workingdirectory>
  <startmode>Automatic</startmode>
  <logpath>C:\KalQuarry\billing\logs</logpath>
  <log mode="roll-by-size">
    <sizeThreshold>10240</sizeThreshold>
    <keepFiles>8</keepFiles>
  </log>
  <onfailure action="restart" delay="5 sec"/>
  <onfailure action="restart" delay="10 sec"/>
</service>
```

Copy `WinSW-x64.exe` next to it as `ssblue-api.exe`, then from an elevated prompt:

```cmd
C:\KalQuarry\billing\ssblue-api.exe install
C:\KalQuarry\billing\ssblue-api.exe start
C:\KalQuarry\billing\ssblue-api.exe status
```

Uninstall with `ssblue-api.exe uninstall`.

---

## 11. Day-to-day management

| Task | Command |
|---|---|
| Status | `sc query SSBlueMetalAPI` |
| Start | `%NSSM% start SSBlueMetalAPI` |
| Stop | `%NSSM% stop SSBlueMetalAPI` |
| Restart after `.env` change | `%NSSM% restart SSBlueMetalAPI` |
| Edit config | `%NSSM% edit SSBlueMetalAPI` |
| Tail log | `powershell Get-Content C:\KalQuarry\billing\logs\api.log -Wait -Tail 50` |
| Event log | `eventvwr.msc` → Windows Logs → Application |

`webapp\.env` changes need a restart: the batch file reads it only at process start.

### Uninstall

```cmd
%NSSM% stop SSBlueMetalAPI
%NSSM% remove SSBlueMetalAPI confirm
```

Data in `db`, `pdf_output` and `backup` is untouched.

---

## 12. Troubleshooting

| Symptom | Cause / fix |
|---|---|
| Error 1053 on start | `binPath` points at Python/`.bat` directly — install through NSSM/WinSW |
| Service starts then stops | Run `webapi.bat` in a console as the same account; error is in `logs\api-error.log` |
| `Missing .venv` in log | Venv not created, or service account cannot see `C:\KalQuarry\billing\.venv` |
| `WEBAPP_SECRET not set — tokens break on restart` | `.env` not loaded (direct-python variant) or `.env` has no `WEBAPP_SECRET` |
| `[Errno 10048]` address in use | Old console `webapi.bat` still running; `netstat -ano \| findstr :8000` |
| `database is locked` | DB on OneDrive/network share, antivirus lock, or desktop app writing during backup |
| Service RUNNING, tunnel 502 | API bound elsewhere: check `API_HOST` in `.env`; `curl` locally |
| Works after login only | Not a service — a Task Scheduler ONLOGON entry; `sc qc SSBlueMetalAPI` |
| PDF font boxes | Arial missing; `printer.py` falls back to Liberation/Noto on non-Windows paths |

---

## 13. Security checklist

- [ ] Service account is not an interactive Administrator
- [ ] `WEBAPP_SECRET` set, long, random, only in `webapp\.env`
- [ ] `API_DOCS=0` before sharing the public URL
- [ ] API bound to `127.0.0.1`; no firewall rule for port 8000
- [ ] `webapp\.env` not readable by other local users
- [ ] DB folder is local NTFS, not OneDrive/network
- [ ] Nightly `VACUUM INTO` backup to `backup\` (Task Scheduler, off-hours)
- [ ] Windows Update reboot policy accounts for the service (it self-starts)
