"""Delivery Challan CRUD."""

from database import get_connection


def create_delivery_challan(
    dc_no: str,
    invoice_no: str,
    customer_id: int,
    customer_name: str,
    customer_mobile: str,
    customer_gstin: str,
    challan_date: str,
    vehicle_no: str = "",
    vehicle_owner: str = "",
    driver_name: str = "",
    driver_mobile: str = "",
    transporter_name: str = "",
    transporter_gstin: str = "",
    delivery_address: str = "",
    notes: str = "",
    items: list[dict] | None = None,
) -> int:
    conn = get_connection()
    cur = conn.execute(
        """INSERT INTO delivery_challan (dc_no, invoice_no, customer_id, customer_name,
           customer_mobile, customer_gstin, challan_date, vehicle_no, vehicle_owner,
           driver_name, driver_mobile, transporter_name, transporter_gstin,
           delivery_address, notes)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            dc_no, invoice_no, customer_id, customer_name, customer_mobile,
            customer_gstin, challan_date, vehicle_no, vehicle_owner,
            driver_name, driver_mobile, transporter_name, transporter_gstin,
            delivery_address, notes,
        ),
    )
    challan_id = cur.lastrowid

    if items:
        for item in items:
            conn.execute(
                """INSERT INTO delivery_challan_item (challan_id, product_id, product_name,
                   description, quantity, unit, rate, amount)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    challan_id,
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
    return challan_id


def get_delivery_challan(dc_id: int) -> dict | None:
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM delivery_challan WHERE id=?", (dc_id,)
    ).fetchone()
    return dict(row) if row else None


def get_delivery_challan_items(dc_id: int) -> list[dict]:
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM delivery_challan_item WHERE challan_id=? ORDER BY id",
        (dc_id,),
    ).fetchall()
    return [dict(r) for r in rows]


def search_delivery_challans(
    query: str = "",
    date_from: str = "",
    date_to: str = "",
    status: str = "active",
) -> list[dict]:
    conn = get_connection()
    sql = "SELECT * FROM delivery_challan WHERE status=? "
    params: list = [status]

    if query:
        sql += "AND (dc_no LIKE ? OR invoice_no LIKE ? OR customer_name LIKE ? OR customer_mobile LIKE ?) "
        params.extend([f"%{query}%", f"%{query}%", f"%{query}%", f"%{query}%"])
    if date_from:
        sql += "AND challan_date >= ? "
        params.append(date_from)
    if date_to:
        sql += "AND challan_date <= ? "
        params.append(date_to)

    sql += "ORDER BY id DESC"
    rows = conn.execute(sql, params).fetchall()
    return [dict(r) for r in rows]


def get_delivery_challan_by_invoice(invoice_no: str) -> list[dict]:
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM delivery_challan WHERE invoice_no=? AND status='active' ORDER BY id DESC",
        (invoice_no,),
    ).fetchall()
    return [dict(r) for r in rows]


def cancel_delivery_challan(dc_id: int):
    conn = get_connection()
    conn.execute(
        "UPDATE delivery_challan SET status='cancelled' WHERE id=?",
        (dc_id,),
    )
    conn.commit()
