# Mobile API — S.S. Blue Metal

JSON REST API for the Android app. It reads and writes the **same** `db/billing.db`
file as the desktop application, so invoices created on a phone appear instantly on
the billing PC and vice versa. There is no second database and no sync step.

```
Android APK ──HTTPS──> Cloudflare Tunnel ──> FastAPI (127.0.0.1:8000) ──> db/billing.db
                                                    ▲
                                          PySide6 desktop app ──┘
```

| Item | Value |
|---|---|
| Framework | FastAPI + Uvicorn |
| Auth | JWT (HS256), bearer token, 12 h default |
| Database | SQLite `db/billing.db` (WAL, thread-local connections, `busy_timeout=5000`) |
| PDF | ReportLab (same generator as the desktop app) |
| Python | 3.11+ (3.12 in Docker) |
| Entry point | `webapp.main:app` |

---

## 1. Install

### Linux / macOS

```bash
uv venv .venv
uv pip install --python .venv/bin/python -r webapp/requirements-web.txt

cp webapp/.env.example webapp/.env
python3 -c "import secrets;print(secrets.token_hex(32))"   # paste into WEBAPP_SECRET

./webapi.sh                      # http://127.0.0.1:8000
```

### Windows (recommended for production)

```cmd
py -3 -m venv .venv
.venv\Scripts\python -m pip install -r webapp\requirements-web.txt

copy webapp\.env.example webapp\.env
py -c "import secrets;print(secrets.token_hex(32))"

webapi.bat
```

### Docker

```bash
cd webapp
cp .env.example .env
docker compose up -d --build
docker compose logs -f api
```

| | |
|---|---|
| Image | `ssbluemetal-api:latest` (non-root uid 1000, healthcheck on `/api/health`) |
| Published port | `127.0.0.1:8000` only |
| Volumes | `../db`, `../pdf_output`, `../backup` |

> **Windows + Docker:** the database is bind-mounted across WSL2, where SQLite file
> locking is unreliable while the desktop app is writing. On a Windows production
> machine run `webapi.bat` natively instead of Docker.

---

## 2. Configuration (`webapp/.env`)

| Variable | Default | Meaning |
|---|---|---|
| `WEBAPP_SECRET` | random per process | JWT signing key. **Must be set** — otherwise every restart logs all APKs out. |
| `TOKEN_TTL_HOURS` | `12` | Token lifetime |
| `ALLOWED_ORIGINS` | empty | Comma-separated CORS origins. Only needed for a WebView/browser client; a native APK needs none. |
| `API_DOCS` | `1` | `0` disables `/docs` and `/openapi.json` (use on public URLs) |
| `LOGIN_MAX_FAILS` | `5` | Failed logins per IP before `429` |
| `LOGIN_WINDOW_SECONDS` | `600` | Throttle window |
| `BILLING_DB_DIR` | `./db` | Directory holding `billing.db` (set to `/app/db` in Docker) |
| `PDF_OUTPUT_DIR` | `./pdf_output` | Where invoice PDFs are written |
| `API_HOST` / `API_PORT` | `127.0.0.1` / `8000` | Used by `webapi.sh` / `webapi.bat` only |

`webapp/.env` is gitignored. Never commit it.

---

## 3. Authentication

```http
POST /api/auth/login
Content-Type: application/json

{ "username": "admin", "password": "admin123" }
```

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer",
  "expires_in": 43200,
  "user": { "id": 1, "username": "admin", "full_name": "Administrator", "role": "admin" }
}
```

Send it on every protected request:

```http
Authorization: Bearer <access_token>
```

- Users live in the existing `users` table (`sha256` hashes) — the same accounts the
  desktop login uses.
- `POST /api/auth/change-password` — `{ "current_password": "...", "new_password": "..." }`
  (min 8 chars). Changes the shared account, desktop included.
- Roles: `admin` required for `DELETE` endpoints and invoice cancellation.
- 5 failed logins per IP / 10 min → `429`. Uses `CF-Connecting-IP` behind Cloudflare.

| Status | Meaning |
|---|---|
| `401` | Missing/expired/invalid token, or bad credentials |
| `403` | Authenticated but not `admin` |
| `404` | Record not found |
| `422` | Request body failed validation |
| `429` | Login throttled |

---

## 4. Endpoints

Base URL: `http://127.0.0.1:8000` (public: your `https://…trycloudflare.com`)

| Method | Path | Auth | Purpose |
|---|---|---|---|
| GET | `/api/health` | — | Liveness probe |
| POST | `/api/auth/login` | — | Get JWT |
| POST | `/api/auth/change-password` | user | Change own password |
| GET | `/api/auth/me` | user | Current user |
| GET | `/api/dashboard` | user | Today's sales, counts, 5 recent invoices |
| GET | `/api/company` | user | Company header, GST rate, default unit |
| GET | `/api/customers?q=&limit=` | user | Search / list customers |
| GET | `/api/customers/{id}` | user | One customer |
| POST | `/api/customers` | user | Create |
| PUT | `/api/customers/{id}` | user | Update |
| DELETE | `/api/customers/{id}` | admin | Delete |
| GET | `/api/products?q=&limit=` | user | Search / list products |
| GET | `/api/products/{id}` | user | One product |
| POST | `/api/products` | user | Create |
| PUT | `/api/products/{id}` | user | Update |
| DELETE | `/api/products/{id}` | admin | Delete |
| GET | `/api/invoices?q=&date_from=&date_to=&status=&page=&page_size=` | user | Paged list |
| POST | `/api/invoices` | user | Create invoice |
| GET | `/api/invoices/{id}` | user | Invoice + items |
| GET | `/api/invoices/{id}/pdf` | user | `application/pdf` |
| POST | `/api/invoices/{id}/cancel` | admin | Mark cancelled |
| DELETE | `/api/invoices/{id}` | admin | Delete |
| GET | `/api/reports/daily?date=` | user | Invoices for a day |
| GET | `/api/reports/range?from_date=&to_date=` | user | Sales per day |
| GET | `/api/reports/top-products?limit=` | user | Best sellers |
| GET | `/api/reports/gstr1?from_date=&to_date=` | user | GSTR-1 rows |
| GET | `/api/reports/hsn?from_date=&to_date=` | user | HSN summary |

Interactive schema: `GET /docs`, `GET /openapi.json` (unless `API_DOCS=0`).

---

## 5. Creating an invoice

GST, CGST/SGST split, round-off, invoice number and amount-in-words are all computed
**server side** — the app only sends quantities and optional rates.

```http
POST /api/invoices
Authorization: Bearer <token>
Content-Type: application/json

{
  "customer_id": 6,
  "invoice_date": "2026-10-30",
  "vehicle_no": "TN 33 AB 1234",
  "driver_name": "Optional",
  "notes": "",
  "round_off": true,
  "items": [
    { "product_id": 5, "quantity": 2 },
    { "product_id": 3, "quantity": 1, "rate": 3900 }
  ]
}
```

```json
{
  "id": 62,
  "invoice_no": "INV/2026/000057",
  "subtotal": 11500.0,
  "cgst_amount": 287.5,
  "sgst_amount": 287.5,
  "round_off": 0.0,
  "grand_total": 12075.0,
  "amount_in_words": "Twelve Thousand Seventy Five Rupees Only"
}
```

| Field | Rule |
|---|---|
| `items[].quantity` | `> 0`, decimal allowed (e.g. `2.5`) |
| `items[].rate` | optional; omitted → the product's stored rate is used |
| `invoice_date` | `YYYY-MM-DD`, defaults to today |
| `round_off` | `true` → grand total rounded to the nearest rupee |
| GST | 5 % intra-state: CGST `round(gst/2,2)`, SGST the remainder |

- Numbers follow `{prefix}/{year}/{seq:06d}` from `company.invoice_prefix`.
- Concurrent creation from two devices retries on the unique constraint (5 attempts).
- `422` when `items` is empty; `400` for an unknown customer/product.

List response:

```json
{ "items": [ { "id": 62, "invoice_no": "INV/2026/000057", "grand_total": 12075.0, "…": "…" } ],
  "total": 56, "page": 1, "page_size": 25 }
```

---

## 6. Android app notes

- Store the base URL and token in `EncryptedSharedPreferences` / Keystore-backed storage.
- Base URL is `https://api.abc.com` in the examples — a **placeholder** until the domain
  is decided (§11 of the tunnel guide). Keep it in a single `const` so it is one edit later.
- On `401` → discard token, show login again. On `429` → back off the login form.
- Dates are plain `YYYY-MM-DD` strings; money is a JSON number (rupees, 2 dp).
- Amount-in-words is returned by the server — don't reimplement currency wording.
- Download PDFs with `Accept: application/pdf`; the filename comes from `Content-Disposition`.
- If the phone cannot reach the API, the URL is still bound to `127.0.0.1` on the PC —
  use the tunnel (below) or set `API_HOST=0.0.0.0` (exposes the LAN).

---

## 7. Cloudflare Tunnel

Publishes `http://127.0.0.1:8000` over HTTPS with no port forwarding and no inbound
firewall rule. Full walkthrough — install, quick tunnel, named tunnel, dashboard
token tunnel, Windows service, Access policies and troubleshooting:
**[CLOUDFLARE_TUNNEL.md](CLOUDFLARE_TUNNEL.md)**

Quick tunnel (random URL, dies with the process — testing only):

```bash
cloudflared tunnel --no-autoupdate --url http://127.0.0.1:8000

./webapp/tunnel.sh          # Linux/macOS wrapper, checks the API first
webapp\tunnel.bat           # Windows wrapper
```

Named tunnel with your own domain (stable URL — `api.abc.com` is a placeholder until the
real domain is chosen, see [§11 of the tunnel guide](CLOUDFLARE_TUNNEL.md#11-domain-decided-later)):

```bash
cloudflared tunnel login
cloudflared tunnel create ssm-api
cloudflared tunnel route dns ssm-api api.abc.com
cloudflared tunnel run ssm-api          # reads ~/.cloudflared/config.yml
```

Windows service (token method, no local files):

```cmd
cloudflared service install <TUNNEL_TOKEN>
```

Docker: put `TUNNEL_TOKEN` in `webapp/.env` and
`docker compose --profile tunnel up -d`.

Keep the app bound to `127.0.0.1`; only `cloudflared` is exposed.

---

## 8. Backup and restore

The API and the desktop app share one file. Safe options:

```bash
# consistent snapshot without stopping anything
sqlite3 db/billing.db "VACUUM INTO 'backup/billing-$(date +%F).db'"
```

```bash
# or a plain copy while nothing is writing
cp db/billing.db db/billing.db-wal backup/
```

Restore: stop the API and the desktop app, replace `db/billing.db`, delete any stale
`billing.db-wal` / `billing.db-shm`, restart. The desktop app's own
`database.backup_database()` still works unchanged.

---

## 9. Troubleshooting

| Symptom | Cause / fix |
|---|---|
| `database is locked` | Long-running write or an antivirus/OneDrive lock. Keep the DB on local NTFS, not a synced folder. `busy_timeout` is 5 s. |
| `401` right after login | `WEBAPP_SECRET` changed (missing from `.env` → random per process). Set it and restart. |
| Phone gets `connection refused` | Server is on `127.0.0.1`. Use the tunnel or `API_HOST=0.0.0.0`. |
| Tunnel URL stopped working | Quick-tunnel URL changes on every restart. Use a named tunnel. |
| PDF font boxes/tofu | `printer.py` looks for Arial in `%WINDIR%\Fonts` on Windows, Liberation/Noto on Linux. Install one of them. |
| `/docs` returns 404 | `API_DOCS=0` is set. |
| Invoice number collision | Two devices submitted at once; the API retries, and returns `503`/`400` if all attempts fail. |

---

## 10. Security checklist

- [ ] `WEBAPP_SECRET` set to a long random value; `.env` never committed
- [ ] `admin123` changed before the public URL is shared
- [ ] `API_DOCS=0` on the public deployment
- [ ] API bound to `127.0.0.1`, exposure only through the tunnel
- [ ] Cloudflare Access / WAF rules on the hostname if the APK is distributed widely
- [ ] Nightly `VACUUM INTO` backup on local disk
- [ ] Windows: run as a non-admin user task, DB folder not in OneDrive

---

## 11. Project layout

```
webapp/
  main.py           app wiring, CORS, /api/health
  auth.py           sha256 verification, JWT, throttling, roles
  schemas.py        Pydantic models
  services.py       invoice math (GST, round-off, numbering, retry)
  routes/
    meta.py         auth, dashboard, company
    customers.py    customer CRUD
    products.py     product CRUD
    invoices.py     invoice CRUD, PDF, cancel
    reports.py      daily / range / top products / GSTR-1 / HSN
  Dockerfile        non-root image, healthcheck
  docker-compose.yml api + optional `tunnel` profile
  .env.example
  tunnel.sh / tunnel.bat
webapi.sh / webapi.bat   run the API locally
```

The desktop app (`main.py`, `ui/`, `printer.py`, `reports.py`, …) is unchanged and can
keep running at the same time.
