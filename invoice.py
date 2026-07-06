"""Invoice CRUD."""

from database import get_connection


def create_invoice(
    invoice_no: str,
    customer_id: int,
    customer_name: str,
    customer_mobile: str,
    customer_gstin: str,
    invoice_date: str,
    subtotal: float,
    gst_rate: float,
    cgst_amount: float,
    sgst_amount: float,
    round_off: float,
    grand_total: float,
    amount_in_words: str,
    notes: str = "",
    vehicle_id: int | None = None,
    vehicle_no: str = "",
    driver_name: str = "",
    items: list[dict] | None = None,
) -> int:
    conn = get_connection()
    cur = conn.execute(
        """INSERT INTO invoice (invoice_no, customer_id, customer_name, customer_mobile,
           customer_gstin, invoice_date, gst_type, subtotal, gst_rate,
           cgst_amount, sgst_amount, igst_amount, round_off, grand_total,
           amount_in_words, notes, vehicle_id, vehicle_no, driver_name)
           VALUES (?, ?, ?, ?, ?, ?, 'intra', ?, ?,
           ?, ?, 0, ?, ?, ?, ?, ?, ?, ?)""",
        (
            invoice_no, customer_id, customer_name, customer_mobile,
            customer_gstin, invoice_date, subtotal, gst_rate,
            cgst_amount, sgst_amount, round_off, grand_total,
            amount_in_words, notes, vehicle_id, vehicle_no, driver_name,
        ),
    )
    invoice_id = cur.lastrowid

    if items:
        for item in items:
            conn.execute(
                """INSERT INTO invoice_item (invoice_id, product_id, product_name,
                   description, quantity, unit, rate, amount)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    invoice_id,
                    item.get("product_id"),
                    item.get("product_name", ""),
                    item.get("description", ""),
                    item.get("quantity", 0),
                    item.get("unit", ""),
                    item.get("rate", 0),
                    item.get("amount", 0),
                ),
            )
    conn.commit()
    return invoice_id


def get_invoice(invoice_id: int) -> dict | None:
    conn = get_connection()
    row = conn.execute("SELECT * FROM invoice WHERE id=?", (invoice_id,)).fetchone()
    return dict(row) if row else None


def get_invoice_items(invoice_id: int) -> list[dict]:
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM invoice_item WHERE invoice_id=? ORDER BY id", (invoice_id,)
    ).fetchall()
    return [dict(r) for r in rows]


def search_invoices(
    query: str = "",
    date_from: str = "",
    date_to: str = "",
    status: str = "active",
) -> list[dict]:
    conn = get_connection()
    sql = "SELECT * FROM invoice WHERE status=? "
    params: list = [status]

    if query:
        sql += "AND (invoice_no LIKE ? OR customer_name LIKE ? OR customer_mobile LIKE ?) "
        params.extend([f"%{query}%", f"%{query}%", f"%{query}%"])
    if date_from:
        sql += "AND invoice_date >= ? "
        params.append(date_from)
    if date_to:
        sql += "AND invoice_date <= ? "
        params.append(date_to)

    sql += "ORDER BY id DESC"
    rows = conn.execute(sql, params).fetchall()
    return [dict(r) for r in rows]


def cancel_invoice(invoice_id: int):
    conn = get_connection()
    conn.execute("UPDATE invoice SET status='cancelled' WHERE id=?", (invoice_id,))
    conn.commit()


def get_today_sales() -> float:
    conn = get_connection()
    from datetime import date
    today = date.today().isoformat()
    row = conn.execute(
        "SELECT COALESCE(SUM(grand_total), 0) FROM invoice WHERE invoice_date=? AND status='active'",
        (today,),
    ).fetchone()
    return row[0]


def get_dashboard_data() -> dict:
    conn = get_connection()
    today_sales = conn.execute(
        "SELECT COALESCE(SUM(grand_total), 0) FROM invoice WHERE invoice_date=date('now') AND status='active'"
    ).fetchone()[0]
    total_customers = conn.execute("SELECT COUNT(*) FROM customer").fetchone()[0]
    total_products = conn.execute("SELECT COUNT(*) FROM product").fetchone()[0]
    total_invoices = conn.execute(
        "SELECT COUNT(*) FROM invoice WHERE status='active'"
    ).fetchone()[0]
    recent = conn.execute(
        "SELECT id, invoice_no, customer_name, grand_total, invoice_date FROM invoice WHERE status='active' ORDER BY id DESC LIMIT 5"
    ).fetchall()
    return {
        "today_sales": today_sales,
        "total_customers": total_customers,
        "total_products": total_products,
        "total_invoices": total_invoices,
        "recent_invoices": [dict(r) for r in recent],
    }
