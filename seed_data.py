"""Seed the database with dummy data for testing.

Usage:  python seed_data.py
"""

import hashlib
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database import get_connection, init_db


def seed():
    init_db()  # ensure tables exist
    conn = get_connection()

    # Clear existing data (order matters for FK)
    conn.executescript("""
        DELETE FROM invoice_item;
        DELETE FROM invoice;
        DELETE FROM product;
        DELETE FROM customer;
        DELETE FROM vehicle;
        DELETE FROM driver;
        DELETE FROM transporter;
        DELETE FROM settings;
        DELETE FROM users;
        DELETE FROM company;
    """)

    # ── Company ──
    conn.execute("""INSERT INTO company (id, name, address, gstin, phone, email, website,
                    bank_name, bank_account, bank_ifsc, pan, invoice_prefix,
                    footer_line1, footer_line2)
                    VALUES (1, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            "Kal Quarry",
            "S.F. No. 123/2B, Periyanayakkanpalayam,\nCoimbatore - 641 107,\nTamil Nadu",
            "33AABCU1234D1Z5",
            "98765 43210",
            "info@kalquarry.com",
            "www.kalquarry.com",
            "Indian Bank, Coimbatore Main Branch",
            "1234567890123456",
            "IBKL0001234",
            "AABCU1234D",
            "INV",
            "★  E. & O. E.  ★",
            "Thank you for your business!",
        ),
    )

    # ── Users ──
    pw_hash = hashlib.sha256(b"admin123").hexdigest()
    conn.execute(
        "INSERT INTO users (username, password_hash, full_name, role) VALUES (?, ?, ?, ?)",
        ("admin", pw_hash, "Administrator", "admin"),
    )

    # ── Customers ──
    customers = [
        ("Sri Balaji Constructions", "98422 12345", "12, Gandhi Nagar, Coimbatore - 641012", "33AABCS1234E1Z2"),
        ("M/s Anand Builders", "98422 23456", "45, Sathyamangalam Road, Erode - 638001", "33AABA5678F1Z3"),
        ("Karthik Traders", "98422 34567", "89, Mettupalayam Road, Coimbatore - 641043", "33AABK9012G1Z4"),
        ("Star Infrastructure Pvt Ltd", "98422 45678", "Plot 5, Avinashi Road, Tiruppur - 641603", "33AACS3456H1Z5"),
        ("Ganapathy Materials", "98422 56789", "3/167, Trichy Road, Salem - 636007", ""),
    ]
    for name, mobile, address, gstin in customers:
        conn.execute(
            "INSERT INTO customer (name, mobile, address, gstin) VALUES (?, ?, ?, ?)",
            (name, mobile, address, gstin),
        )

    # ── Products (stone quarry materials) ──
    products = [
        ("20mm Blue Metal", "Crushed granite 20mm size for concrete", "Ton", "2517", 1850),
        ("40mm Blue Metal", "Crushed granite 40mm size for base course", "Ton", "2517", 1650),
        ("6mm Blue Metal", "Crushed granite 6mm (chips) for flooring", "Ton", "2517", 1950),
        ("M-Sand", "Manufactured sand for plastering & concreting", "Ton", "2517", 1450),
        ("P-Sand", "Plastering sand fine grade", "Ton", "2517", 1350),
        ("Boulder", "Granite boulders for crushing", "Ton", "2517", 950),
        ("Rubble Stone", "Random rubble for foundation work", "Cubic Feet", "2517", 85),
        ("Hard Broken Stone", "Hand broken stones for masonry", "Cubic Feet", "2517", 95),
    ]
    for name, desc, unit, hsn, rate in products:
        conn.execute(
            "INSERT INTO product (name, description, unit, hsn_code, rate) VALUES (?, ?, ?, ?, ?)",
            (name, desc, unit, hsn, rate),
        )

    # ── Vehicles ──
    vehicles = [
        ("TN38AB1234", "Rajesh Transport", "98765 11111", "20 Ton", "Tipper"),
        ("TN38CD5678", "Kumar Logistics", "98765 22222", "25 Ton", "Tipper"),
        ("TN38EF9012", "Siva Enterprises", "98765 33333", "15 Ton", "Lorry"),
        ("TN38GH3456", "Murugan Transports", "98765 44444", "20 Ton", "Tipper"),
        ("TN38IJ7890", "Ganesh Carry", "98765 55555", "10 Ton", "Mini Truck"),
    ]
    for vno, owner, mob, cap, vtype in vehicles:
        conn.execute(
            "INSERT INTO vehicle (vehicle_no, owner_name, mobile, capacity, vehicle_type) VALUES (?, ?, ?, ?, ?)",
            (vno, owner, mob, cap, vtype),
        )

    # ── Drivers ──
    drivers = [
        ("Mohan", "98765 11111", "TN38 20240010001", "12, Gandhipuram, Coimbatore"),
        ("Suresh", "98765 22222", "TN38 20240010002", "45, R.S. Puram, Coimbatore"),
        ("Selvam", "98765 33333", "TN38 20240010003", "78, Ramanathapuram, Coimbatore"),
        ("Venkatesh", "98765 44444", "TN38 20240010004", "23, Uppilipalayam, Coimbatore"),
    ]
    for name, mob, lic, addr in drivers:
        conn.execute(
            "INSERT INTO driver (name, mobile, license_no, address) VALUES (?, ?, ?, ?)",
            (name, mob, lic, addr),
        )

    # ── Transporters ──
    transporters = [
        ("Rajesh Transport Co.", "98765 11111", "12, Sathy Road, Coimbatore", "33AABRT1234E1Z6"),
        ("Kumar Logistics Pvt Ltd", "98765 22222", "45, Avinashi Road, Coimbatore", "33AAKL5678F1Z7"),
        ("Siva Roadways", "98765 33333", "78, Mettupalayam Road, Coimbatore", ""),
    ]
    for name, mob, addr, gstin in transporters:
        conn.execute(
            "INSERT INTO transporter (name, mobile, address, gstin) VALUES (?, ?, ?, ?)",
            (name, mob, addr, gstin),
        )

    conn.commit()

    # ── Sample Invoices ──
    from datetime import date, timedelta
    today = date.today()

    sample_invoices = [
        {
            "customer_id": 1,
            "customer_name": "Sri Balaji Constructions",
            "customer_mobile": "98422 12345",
            "customer_gstin": "33AABCS1234E1Z2",
            "gst_type": "intra",
            "gst_rate": 5,
            "items": [(1, 12.500, 1850), (4, 8.000, 1450)],
        },
        {
            "customer_id": 2,
            "customer_name": "M/s Anand Builders",
            "customer_mobile": "98422 23456",
            "customer_gstin": "33AABA5678F1Z3",
            "gst_type": "intra",
            "gst_rate": 5,
            "items": [(2, 15.000, 1650), (5, 10.000, 1350)],
        },
        {
            "customer_id": 3,
            "customer_name": "Karthik Traders",
            "customer_mobile": "98422 34567",
            "customer_gstin": "33AABK9012G1Z4",
            "gst_type": "intra",
            "gst_rate": 12,
            "items": [(1, 20.000, 1850), (3, 5.500, 1950), (8, 120, 95)],
        },
    ]

    for idx, inv in enumerate(sample_invoices):
        inv_date = today - timedelta(days=idx)
        inv_no = f"INV-{inv_date.year}-{idx + 1:04d}"

        subtotal = 0.0
        item_rows = []
        for pid, qty, rate in inv["items"]:
            p_row = conn.execute("SELECT name, unit FROM product WHERE id=?", (pid,)).fetchone()
            if not p_row:
                print(f"  ⚠ Product id={pid} not found, skipping")
                continue
            p = dict(p_row)
            amount = round(qty * rate, 2)
            subtotal += amount
            item_rows.append((pid, p["name"], "", qty, p["unit"], rate, amount))

        gst_amount = round(subtotal * inv["gst_rate"] / 100, 2)
        half = round(gst_amount / 2, 2)
        cgst = half
        sgst = gst_amount - half
        grand_total = round(subtotal + gst_amount)
        round_off = round(grand_total - (subtotal + gst_amount), 2)

        from decimal import Decimal, ROUND_HALF_UP

        conn.execute(
            """INSERT INTO invoice (invoice_no, customer_id, customer_name, customer_mobile,
               customer_gstin, invoice_date, gst_type, subtotal, gst_rate,
               cgst_amount, sgst_amount, igst_amount, round_off, grand_total, amount_in_words)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, ?, ?, '')""",
            (
                inv_no, inv["customer_id"], inv["customer_name"],
                inv["customer_mobile"], inv["customer_gstin"],
                inv_date.isoformat(), inv["gst_type"],
                round(subtotal, 2), inv["gst_rate"],
                cgst, sgst, round_off, grand_total,
            ),
        )
        invoice_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]

        for pid, pname, hsn, qty, unit, rate, amount in item_rows:
            conn.execute(
                """INSERT INTO invoice_item (invoice_id, product_id, product_name,
                   description, quantity, unit, rate, amount)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (invoice_id, pid, pname, "", qty, unit, rate, amount),
            )

    conn.commit()
    print("✅ Database seeded successfully!")
    print(f"   Company: Kal Quarry")
    print(f"   Customers: {len(customers)}")
    print(f"   Products: {len(products)}")
    print(f"   Vehicles: {len(vehicles)}")
    print(f"   Drivers: {len(drivers)}")
    print(f"   Transporters: {len(transporters)}")
    print(f"   Sample Invoices: {len(sample_invoices)}")


if __name__ == "__main__":
    seed()
