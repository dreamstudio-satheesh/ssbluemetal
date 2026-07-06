"""Database connection, schema, and backup."""

import sqlite3
import shutil
import os
from datetime import datetime

DB_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "db")
DB_PATH = os.path.join(DB_DIR, "billing.db")
BACKUP_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "backup")

_conn: sqlite3.Connection | None = None


def get_connection() -> sqlite3.Connection:
    global _conn
    if _conn is None:
        os.makedirs(DB_DIR, exist_ok=True)
        _conn = sqlite3.connect(DB_PATH)
        _conn.row_factory = sqlite3.Row
        _conn.execute("PRAGMA journal_mode=WAL")
        _conn.execute("PRAGMA foreign_keys=ON")
    return _conn


def close():
    global _conn
    if _conn:
        _conn.close()
        _conn = None


def init_db():
    conn = get_connection()
    cur = conn.cursor()

    cur.executescript("""
        CREATE TABLE IF NOT EXISTS company (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            name TEXT NOT NULL DEFAULT '',
            address TEXT DEFAULT '',
            gstin TEXT DEFAULT '',
            phone TEXT DEFAULT '',
            email TEXT DEFAULT '',
            website TEXT DEFAULT '',
            bank_name TEXT DEFAULT '',
            bank_account TEXT DEFAULT '',
            bank_ifsc TEXT DEFAULT '',
            pan TEXT DEFAULT '',
            invoice_prefix TEXT DEFAULT 'INV',
            footer_line1 TEXT DEFAULT '',
            footer_line2 TEXT DEFAULT '',
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS customer (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            mobile TEXT DEFAULT '',
            address TEXT DEFAULT '',
            gstin TEXT DEFAULT '',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS product (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            description TEXT DEFAULT '',
            unit TEXT NOT NULL DEFAULT 'Ton',
            hsn_code TEXT DEFAULT '',
            rate REAL NOT NULL DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS invoice (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            invoice_no TEXT NOT NULL UNIQUE,
            customer_id INTEGER REFERENCES customer(id),
            customer_name TEXT DEFAULT '',
            customer_mobile TEXT DEFAULT '',
            customer_gstin TEXT DEFAULT '',
            invoice_date TEXT NOT NULL,
            gst_type TEXT DEFAULT 'intra',
            subtotal REAL NOT NULL DEFAULT 0,
            gst_rate REAL NOT NULL DEFAULT 0,
            cgst_amount REAL NOT NULL DEFAULT 0,
            sgst_amount REAL NOT NULL DEFAULT 0,
            igst_amount REAL NOT NULL DEFAULT 0,
            round_off REAL NOT NULL DEFAULT 0,
            grand_total REAL NOT NULL DEFAULT 0,
            amount_in_words TEXT DEFAULT '',
            status TEXT DEFAULT 'active',
            notes TEXT DEFAULT '',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS invoice_item (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            invoice_id INTEGER REFERENCES invoice(id) ON DELETE CASCADE,
            product_id INTEGER REFERENCES product(id),
            product_name TEXT DEFAULT '',
            description TEXT DEFAULT '',
            quantity REAL NOT NULL DEFAULT 0,
            unit TEXT DEFAULT '',
            rate REAL NOT NULL DEFAULT 0,
            amount REAL NOT NULL DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT
        );

        CREATE TABLE IF NOT EXISTS vehicle (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            vehicle_no TEXT NOT NULL UNIQUE,
            owner_name TEXT DEFAULT '',
            mobile TEXT DEFAULT '',
            capacity TEXT DEFAULT '',
            vehicle_type TEXT DEFAULT 'Tipper',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS driver (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            mobile TEXT DEFAULT '',
            license_no TEXT DEFAULT '',
            address TEXT DEFAULT '',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS transporter (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            mobile TEXT DEFAULT '',
            address TEXT DEFAULT '',
            gstin TEXT DEFAULT '',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS delivery_challan (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            dc_no TEXT NOT NULL UNIQUE,
            invoice_no TEXT NOT NULL REFERENCES invoice(invoice_no),
            customer_id INTEGER REFERENCES customer(id),
            customer_name TEXT DEFAULT '',
            customer_mobile TEXT DEFAULT '',
            customer_gstin TEXT DEFAULT '',
            challan_date TEXT NOT NULL,
            vehicle_no TEXT DEFAULT '',
            vehicle_owner TEXT DEFAULT '',
            driver_name TEXT DEFAULT '',
            driver_mobile TEXT DEFAULT '',
            transporter_name TEXT DEFAULT '',
            transporter_gstin TEXT DEFAULT '',
            delivery_address TEXT DEFAULT '',
            notes TEXT DEFAULT '',
            status TEXT DEFAULT 'active',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS delivery_challan_item (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            challan_id INTEGER REFERENCES delivery_challan(id) ON DELETE CASCADE,
            product_id INTEGER REFERENCES product(id),
            product_name TEXT DEFAULT '',
            description TEXT DEFAULT '',
            quantity REAL NOT NULL DEFAULT 0,
            unit TEXT DEFAULT '',
            rate REAL NOT NULL DEFAULT 0,
            amount REAL NOT NULL DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS receipt (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            receipt_no TEXT NOT NULL UNIQUE,
            invoice_no TEXT REFERENCES invoice(invoice_no),
            customer_id INTEGER REFERENCES customer(id),
            customer_name TEXT DEFAULT '',
            customer_mobile TEXT DEFAULT '',
            receipt_date TEXT NOT NULL,
            amount REAL NOT NULL DEFAULT 0,
            amount_in_words TEXT DEFAULT '',
            mode TEXT DEFAULT 'Cash',
            reference_no TEXT DEFAULT '',
            notes TEXT DEFAULT '',
            status TEXT DEFAULT 'active',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            full_name TEXT DEFAULT '',
            role TEXT DEFAULT 'user',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        -- Default company row (complete placeholder data)
        INSERT OR IGNORE INTO company (id, name, address, gstin, phone, email, website,
            bank_name, bank_account, bank_ifsc, pan, invoice_prefix,
            footer_line1, footer_line2)
            VALUES (1, 'S.S. BLUE METAL',
            'Kurunthankadu 36/1,36/2, 45/2\nSukkampalayam, Kalivelampatti\nTamil Nadu - 641664',
            '33BVYPS0571C1ZC', '98765 43210', '', '',
            'Your Bank Name', '1234567890123456', 'IFSC0001234', '',
            'INV', '★  E. & O. E.  ★', 'Thank you for your business!');

        -- Default admin user (password: admin123)
        INSERT OR IGNORE INTO users (id, username, password_hash, full_name, role)
        VALUES (1, 'admin', '240be518fabd2724ddb6f04eeb1da5967448d7e831c08c8fa822809f74c720a9', 'Administrator', 'admin');
    """)

    conn.commit()


def backup_database() -> str:
    """Copy current DB to backup folder with timestamp. Returns backup path."""
    os.makedirs(BACKUP_DIR, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = os.path.join(BACKUP_DIR, f"billing_backup_{ts}.db")
    shutil.copy2(DB_PATH, backup_path)
    return backup_path


def _next_seq_no(table: str, column: str, prefix: str) -> str:
    """Generate {prefix}/{year}/{seq:06d} format number."""
    conn = get_connection()
    cur = conn.cursor()
    year = datetime.now().strftime("%Y")
    pattern = f"{prefix}/{year}/%"
    cur.execute(
        f"SELECT {column} FROM {table} WHERE {column} LIKE ? ORDER BY id DESC LIMIT 1",
        (pattern,),
    )
    row = cur.fetchone()
    if row:
        parts = row[column].split("/")
        seq = int(parts[-1]) + 1
    else:
        seq = 1
    return f"{prefix}/{year}/{seq:06d}"


def get_next_invoice_no(prefix: str = "INV") -> str:
    return _next_seq_no("invoice", "invoice_no", prefix)


def get_next_dc_no(prefix: str = "DC") -> str:
    return _next_seq_no("delivery_challan", "dc_no", prefix)


def get_next_receipt_no(prefix: str = "RC") -> str:
    return _next_seq_no("receipt", "receipt_no", prefix)
