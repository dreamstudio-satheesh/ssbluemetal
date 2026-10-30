# Cloudflare Tunnel — step-by-step guide

How to publish the billing API (`http://127.0.0.1:8000`) over HTTPS so the Android
app can reach it — no port forwarding, no router changes, no inbound firewall rule.

```
Android APK ──HTTPS──> Cloudflare edge ──tunnel (outbound)──> cloudflared ──> 127.0.0.1:8000
```

`cloudflared` on the Windows PC opens an **outbound** connection to Cloudflare and
serves requests back through it. The PC never accepts an inbound connection.

> **Placeholder domain.** Every example in this guide uses `api.abc.com`. The real
> domain is not decided yet — keep the steps as they are and replace the hostname
> later. See [§11 Domain decided later](#11-domain-decided-later) for the exact list
> of places to change. Until then, the quick tunnel (Option A) is enough for APK
> development.

---

## 0. Before you start

1. API is running and healthy on the PC:

   ```cmd
   curl http://127.0.0.1:8000/api/health
   ```
   Expect `{"status":"ok"}`. If not, start it: `webapi.bat`.

2. `webapp\.env` has a real `WEBAPP_SECRET` (not `change-me`).
3. The default `admin123` password is changed:

   ```cmd
   curl -X POST http://127.0.0.1:8000/api/auth/login -H "Content-Type: application/json" -d "{\"username\":\"admin\",\"password\":\"admin123\"}"
   ```
   Take `access_token` from the response, then:

   ```cmd
   curl -X POST http://127.0.0.1:8000/api/auth/change-password ^
     -H "Authorization: Bearer <TOKEN>" -H "Content-Type: application/json" ^
     -d "{\"current_password\":\"admin123\",\"new_password\":\"<new-password>\"}"
   ```

4. Once the URL is public, set `API_DOCS=0` in `webapp\.env` and restart the API.

---

## 1. Install cloudflared (Windows)

```cmd
winget install --id Cloudflare.cloudflared
```

Alternatives:

```cmd
choco install cloudflared
```

or download `cloudflared-windows-amd64.exe` from the Cloudflare releases page, rename
it to `cloudflared.exe`, and put it in a folder on `PATH` (e.g. `C:\Tools`).

Verify:

```cmd
cloudflared --version
```

Linux: `curl -L https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64 -o /usr/local/bin/cloudflared && chmod +x /usr/local/bin/cloudflared`

---

## 2. Option A — Quick tunnel (testing only)

No domain, no account. Random `https://<words>.trycloudflare.com` URL.

```cmd
webapp\tunnel.bat
```

The wrapper picks the mode from environment variables:

| Variables | Mode | URL |
|---|---|---|
| *(none)* | Quick tunnel | random `*.trycloudflare.com` |
| `TUNNEL_NAME=ssm-api` | Named tunnel (Option B) | your domain |
| `TUNNEL_TOKEN=eyJ...` | Dashboard token tunnel (Option C) | your domain |

```cmd
set TUNNEL_NAME=ssm-api
webapp\tunnel.bat
```

```bash
TUNNEL_NAME=ssm-api ./webapp/tunnel.sh
TUNNEL_TOKEN=eyJ... ./webapp/tunnel.sh
```

Raw command if you prefer:

```cmd
cloudflared tunnel --no-autoupdate --url http://127.0.0.1:8000
```

The console prints:

```
+--------------------------------------------------------------------------------------------+
|  Your quick Tunnel has been created! Visit it at:                                          |
|  https://advised-manufacturing-september-percentage.trycloudflare.com                      |
+--------------------------------------------------------------------------------------------+
```

Put that URL in the APK's base URL and test:

```bash
curl https://advised-manufacturing-september-percentage.trycloudflare.com/api/health
# {"status":"ok"}

curl -i https://advised-manufacturing-september-percentage.trycloudflare.com/api/invoices
# HTTP/2 401  {"detail":"Not authenticated"}
```

**Limits:** the hostname changes every restart, no SLA, no Cloudflare Access support,
not for production. Use Option B or C for the real deployment.

Stop with `Ctrl+C`. On Linux run it detached:

```bash
setsid cloudflared tunnel --no-autoupdate --url http://127.0.0.1:8000 \
  </dev/null >/tmp/cf.log 2>&1 &
grep -oE "https://[a-z0-9-]+\.trycloudflare\.com" /tmp/cf.log | head -1
```

---

## 3. Option B — Named tunnel with your own domain

Stable URL such as `https://api.abc.com`, survives restarts and reboots.

### 3.1 Requirements

- A domain whose **nameservers point to Cloudflare** (free plan is fine).
  Add the site in the Cloudflare dashboard → Cloudflare gives you two nameservers →
  set them at your registrar → wait until the zone status is *Active*.

### 3.2 Authorize the machine

```cmd
cloudflared tunnel login
```

A browser opens; pick the zone. This writes
`C:\Users\<you>\.cloudflared\cert.pem`.

### 3.3 Create the tunnel

```cmd
cloudflared tunnel create ssm-api
```

Output gives the tunnel UUID and writes
`C:\Users\<you>\.cloudflared\<UUID>.json`. Keep that file private.

```cmd
cloudflared tunnel list
```

### 3.4 Point a hostname at it

```cmd
cloudflared tunnel route dns ssm-api api.abc.com
```

This creates the proxied `CNAME api.abc.com -> <UUID>.cfargotunnel.com`.
Do **not** create an A record — Cloudflare handles it.

### 3.5 Config file

Create `C:\Users\<you>\.cloudflared\config.yml` — a ready template is in
[`cloudflared.config.example.yml`](cloudflared.config.example.yml):

```yaml
tunnel: <TUNNEL_UUID>
credentials-file: C:\Users\<you>\.cloudflared\<TUNNEL_UUID>.json

ingress:
  - hostname: api.abc.com
    service: http://127.0.0.1:8000
  - service: http_status:404
```

`ingress` is ordered — the last rule must be a catch-all.

### 3.6 Run it

Foreground (test):

```cmd
cloudflared tunnel run ssm-api
```

Verify from any network:

```bash
curl https://api.abc.com/api/health      # {"status":"ok"}
curl -i https://api.abc.com/api/invoices # 401 without a token
```

### 3.7 Install as a Windows service (auto-start on boot)

Elevated Command Prompt:

```cmd
cloudflared service install
```

The service reads `config.yml` from `C:\Windows\System32\config\systemprofile\.cloudflared\`
when running as Local System. If the service cannot find the credentials, either copy
`config.yml` and the `<UUID>.json` there, or use **Option C** (token), which needs no
local files.

```cmd
sc query cloudflared
net start cloudflared
```

Logs: Event Viewer → Windows Logs → Application (source `cloudflared`), or run
`cloudflared tunnel run ssm-api` in a console to see errors live.

---

## 4. Option C — Token tunnel from the dashboard (recommended for production)

No config file, no credentials file, ideal for Windows services and Docker.

1. Cloudflare dashboard → **Zero Trust** → **Networks** → **Tunnels** →
   **Create a tunnel** → *Cloudflared* → name it `ssm-api`.
2. Choose **Windows** and copy the install command, e.g.:

   ```cmd
   cloudflared.exe service install eyJhIjoi...
   ```

3. In the tunnel's **Public Hostname** tab add:

   | Field | Value |
   |---|---|
   | Subdomain | `api` |
   | Domain | `abc.com` |
   | Type | `HTTP` |
   | URL | `localhost:8000` |

4. Verify:

   ```bash
   curl https://api.abc.com/api/health
   ```

To move it to another PC later, install with the same token — no files to copy.

---

## 5. Docker variant

Put the token in `webapp/.env`:

```env
TUNNEL_TOKEN=eyJhIjoi...
```

```bash
cd webapp
docker compose --profile tunnel up -d --build
docker compose logs -f tunnel
```

The `tunnel` service uses `network_mode: service:api`, so the dashboard hostname
should point at `localhost:8000` (same network namespace as the API container).

---

## 6. Optional: Cloudflare Access (edge auth)

Extra password/OTP layer in front of the API. Useful if the URL leaks.

1. Zero Trust → **Access** → **Applications** → **Add an application** → *Self-hosted*.
2. Application domain: `api.abc.com`.
3. Policy: allow your email(s), or `Service Auth` for the APK.
4. For the APK use a **service token** (Access → Service Auth → Create service token)
   and send these headers from the app:

   ```
   CF-Access-Client-Id: <id>.access
   CF-Access-Client-Secret: <secret>
   ```

**Important:** with a browser-based Access policy, unauthenticated API calls get an
HTML login redirect instead of `401` — the APK would break. Either use a service token,
or add a `Bypass` policy for `/api/*` and rely on the API's JWT auth.

---

## 7. Verify from the phone's network

```bash
# on mobile data / another Wi-Fi, not the billing PC
curl https://api.abc.com/api/health
curl -X POST https://api.abc.com/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"<password>"}'
```

Both must succeed with the PC's API **and** `cloudflared` running. If `health` works
but login fails, the API is fine and the credentials are wrong — not a tunnel problem.

---

## 8. Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `502 Bad Gateway` | Nothing listening on `127.0.0.1:8000` | `curl http://127.0.0.1:8000/api/health`, start `webapi.bat` |
| Cloudflare error `1033` | `cloudflared` not connected / crashed | `cloudflared tunnel run <name>`, check the service status |
| Cloudflare error `530` | Hostname not routed to the tunnel | `cloudflared tunnel route dns`, check the DNS `CNAME` is proxied (orange cloud) |
| `404` from Cloudflare, `cloudflared` fine | Public hostname missing in the token tunnel | Add it under Public Hostname (or `ingress` rule) |
| Works on PC, not on phone | Bound to `127.0.0.1` and no tunnel running | Start `webapp\tunnel.bat` |
| URL changed after restart | Quick tunnel | Use a named/token tunnel |
| HTML login page instead of JSON | Cloudflare Access policy intercepts the API | Service token headers, or bypass `/api/*` |
| Windows service starts then stops | Credentials file not readable by Local System | Use Option C (token) or copy files to the systemprofile folder |
| `429 Too Many Requests` on login | Login throttle (5 fails / 10 min) | Wait, or raise `LOGIN_MAX_FAILS` |
| Slow responses | Bind-mounted SQLite in Docker on Windows | Run the API natively (`webapi.bat`) |

Logs:

```cmd
cloudflared tunnel --loglevel debug run ssm-api
```

```bash
journalctl -u cloudflared -f        # Linux service
docker compose logs -f tunnel       # Docker
```

---

## 9. Security checklist

- [ ] API stays on `127.0.0.1` — only `cloudflared` is exposed
- [ ] `WEBAPP_SECRET` set (tokens survive restarts)
- [ ] `admin123` changed, no other default accounts
- [ ] `API_DOCS=0` on the public hostname
- [ ] Access policy or service token if the APK is shared widely
- [ ] `config.yml` and `<UUID>.json` never committed (`.gitignore` covers `.env`)
- [ ] Rotate the tunnel: dashboard delete + `cloudflared service install` with a new token
- [ ] Nightly DB backup (`VACUUM INTO`) on local NTFS

---

## 10. Uninstall / rotate

```cmd
cloudflared service uninstall
cloudflared tunnel delete ssm-api          # only after DNS no longer points at it
```

Then remove the `CNAME api.abc.com` record in the Cloudflare DNS tab if it remains.

---

## 11. Domain decided later

`api.abc.com` is a placeholder in every example. Nothing breaks while it stays a
placeholder — the quick tunnel works with no domain at all.

When the real hostname is chosen, change it in these places (all of them, or the
tunnel and the app will disagree):

| # | Where | What to change |
|---|---|---|
| 1 | `%USERPROFILE%\.cloudflared\config.yml` | `ingress[0].hostname` |
| 2 | Cloudflare dashboard → Zero Trust → Tunnels → *Public Hostname* | Subdomain + Domain (token tunnel only) |
| 3 | Cloudflare DNS tab | the proxied `CNAME` created by `cloudflared tunnel route dns` |
| 4 | `webapp/cloudflared.config.example.yml` | `hostname:` comment + value |
| 5 | `webapp/README.md` §7 and this guide | `route dns` / `curl` examples |
| 6 | Android app | base URL constant, e.g. `https://api.<real-domain>` (keep it in one `BuildConfig`/`const`) |
| 7 | Cloudflare Access application (if used) | application domain |

Procedure:

```cmd
cloudflared tunnel route dns ssm-api api.<real-domain>
:: edit %USERPROFILE%\.cloudflared\config.yml -> hostname: api.<real-domain>
cloudflared tunnel run ssm-api
```

Old DNS records for `api.abc.com` can be deleted in the Cloudflare DNS tab; nothing on
the server needs to change, because `cloudflared` always forwards to
`http://127.0.0.1:8000` regardless of the public hostname.

Keep `api.abc.com` out of the APK — shipping an app with a placeholder host is the one
mistake here that cannot be fixed by a DNS change.
