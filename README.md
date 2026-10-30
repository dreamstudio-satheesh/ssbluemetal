# S.S. Blue Metal — Quarry Billing Software

A local-first desktop billing application for a stone quarry / blue-metal business.
It handles GST sales invoices, delivery challans, payment receipts, PDF printing,
and accounting reports — all stored in a single SQLite database on the machine.

- **App title:** S.S. Blue Metal (login screen says “Kal Quarry”)
- **Repository:** `ssbluemetal`
- **Type:** Offline desktop app (no server, no internet required)

---

## Tech stack

| Layer | Technology |
|---|---|
| UI | PySide6 (Qt 6) |
| Language | Python 3.13+ |
| Database | SQLite (WAL mode, foreign keys on) |
| PDF generation | ReportLab |
| Spreadsheet export | openpyxl |
| Packaging | PyInstaller (`--onefile --windowed`) |

Dependencies (`requirements.txt`):

```
PySide6>=6.6
reportlab>=4.0
openpyxl>=3.1
```

---

## Features

### Billing
- Multi-item GST invoice with product, HSN code, quantity, unit, rate and amount
- GST 5% split as CGST 2.5% + SGST 2.5% (intra-state)
- Automatic round-off
- Amount in words
- Vehicle number, driver name and customer “designation” on the invoice
- Invoice status handling: active / cancelled / deleted
- Edit invoice metadata (typo fixes) without deleting the invoice
- Auto invoice numbering: `INV/YYYY/NNNNNN`

### Masters
- **Customers** — name, mobile, address, GSTIN, plus customer-owned vehicles
- **Products** — name, description, unit, HSN code, rate
- **Vehicles, drivers, transporters** — used by delivery challans

### Documents
- **Sales invoice** PDF
- **Delivery challan** PDF (linked to an invoice), numbering `DC/YYYY/NNNNNN`
- **Payment receipt** PDF (part/full payment against an invoice), numbering `RC/YYYY/NNNNNN`
- **Blank invoice** PDF for manual use

### Reports
- Sales register (day / period grouping)
- HSN summary
- GSTR-1 export
- Export tables to CSV, XLSX and PDF

### Operations
- Dashboard: today’s sales, customer/product counts, active invoice count, recent invoices
- Company profile: name, address, GSTIN, phone, email, website, PAN, bank details, invoice prefix, footer lines
- Database backup to `backup/billing_backup_YYYYMMDD_HHMMSS.db`
- Optional login (SHA-256 password hash) or “Skip login (single user)”

---

## Getting started (Linux)

```bash
cd /home/satheesh/WORK/SSBlueMetal
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python3 main.py
```

Or use the launcher:

```bash
./run.sh
```

Install a desktop shortcut:

```bash
./install-desktop.sh
```

## Getting started (Windows)

See [WINDOWS_INSTALL.md](WINDOWS_INSTALL.md). Short version:

```cmd
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

Build a standalone executable:

```cmd
pip install pyinstaller
pyinstaller --onefile --windowed --name "KalQuarry" main.py
```

Output: `dist\KalQuarry.exe`

---

## Default login

| Username | Password |
|---|---|
| `admin` | `admin123` |

The login screen offers **“Skip login (single user)”**, which saves
`{"skip_login": true}` to `settings.json`. Delete that file (or uncheck the option
on a fresh install) to be prompted again.

> Change the default password before using the app for real business data.

---

## Data, PDFs and backups

| Path | Contents |
|---|---|
| `db/billing.db` | Main SQLite database |
| `backup/` | Timestamped database copies made from the app |
| `pdf_output/` | Generated invoice / challan / receipt PDFs |
| `settings.json` | Local UI settings (e.g. skip-login flag) |

These runtime files are git-ignored. Copy the whole folder to move the installation;
to migrate data, copy `db/billing.db` and `settings.json`.

---

## Database schema (main tables)

`company`, `customer`, `customer_vehicle`, `product`, `invoice`, `invoice_item`,
`vehicle`, `driver`, `transporter`, `delivery_challan`, `delivery_challan_item`,
`receipt`, `settings`, `users`.

A default company row seeds **S.S. BLUE METAL** with placeholder bank/GST details —
update them under **Settings** before printing real invoices.

---

## Project structure

```
SSBlueMetal/
├── main.py                  # Entry point + login dialog
├── database.py              # Connection, schema, migrations, backup, numbering
├── invoice.py               # Invoice CRUD + dashboard queries
├── delivery_challan.py      # Delivery challan CRUD
├── receipt.py               # Receipt CRUD
├── customer.py              # Customer + customer vehicle CRUD
├── product.py               # Product CRUD
├── vehicle.py               # Vehicle CRUD
├── driver.py                # Driver CRUD
├── transporter.py           # Transporter CRUD
├── reports.py               # Sales register, HSN summary, GSTR-1 queries
├── exporter.py              # CSV / XLSX / PDF table export
├── printer.py               # ReportLab PDF layouts (invoice, DC, receipt, blank)
├── settings.py              # JSON settings + company profile helpers
├── seed_data.py             # Demo/sample data loader
├── ui/                      # PySide6 windows
│   ├── main_window.py       # Sidebar, dashboard, settings, product management
│   ├── customer_window.py
│   ├── invoice_window.py
│   ├── delivery_challan_window.py
│   ├── receipt_window.py
│   ├── reports_window.py
│   ├── blank_invoice_window.py
│   ├── vehicle_window.py
│   ├── driver_window.py
│   └── transporter_window.py
├── run.sh / run.bat / run.vbs
├── install-desktop.sh / Billing.desktop
└── WINDOWS_INSTALL.md
```

---

## Notes and limitations

- Single-user, single-machine design. The SQLite file is meant to be used by one app
  instance at a time; it is not a multi-terminal/multi-branch system.
- GST is treated as intra-state only (CGST + SGST). There is no inter-state IGST flow
  in the invoice UI.
- Invoice numbers are generated from the highest existing sequence for the current year.
- PDFs use a bundled/system Unicode font; if rupee glyphs or Indian text render as boxes,
  install a font such as DejaVu Sans on the machine.
- Keep `backup/` and `pdf_output/` out of source control (already covered by `.gitignore`).

---

## Mobile API (web gateway)

`webapp/` is a JSON REST API that lets an Android app read and create invoices
against the **same** `db/billing.db` used by this desktop app — no second database,
no sync.

```bash
./webapi.sh      # Linux/macOS → http://127.0.0.1:8000
webapi.bat       # Windows
```

| Document | Contents |
|---|---|
| [`webapp/README.md`](webapp/README.md) | Setup, environment variables, endpoint reference, auth flow, backup, troubleshooting |
| [`webapp/CLOUDFLARE_TUNNEL.md`](webapp/CLOUDFLARE_TUNNEL.md) | Step-by-step HTTPS exposure: install, quick/named/token tunnel, Windows service, Access policies, diagnostics |

The desktop app keeps working unchanged while the API runs.
