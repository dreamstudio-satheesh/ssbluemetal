"""Customer CRUD."""

from database import get_connection


def search_customers(query: str = "") -> list[dict]:
    conn = get_connection()
    if query:
        rows = conn.execute(
            """SELECT * FROM customer
               WHERE name LIKE ? OR mobile LIKE ?
               ORDER BY name""",
            (f"%{query}%", f"%{query}%"),
        ).fetchall()
    else:
        rows = conn.execute("SELECT * FROM customer ORDER BY name").fetchall()
    return [dict(r) for r in rows]


def get_customer(customer_id: int) -> dict | None:
    conn = get_connection()
    row = conn.execute("SELECT * FROM customer WHERE id=?", (customer_id,)).fetchone()
    return dict(row) if row else None


def add_customer(name: str, mobile: str = "", address: str = "", gstin: str = "") -> int:
    conn = get_connection()
    cur = conn.execute(
        "INSERT INTO customer (name, mobile, address, gstin) VALUES (?, ?, ?, ?)",
        (name.strip(), mobile.strip(), address.strip(), gstin.strip()),
    )
    conn.commit()
    return cur.lastrowid


def update_customer(customer_id: int, name: str, mobile: str = "", address: str = "", gstin: str = ""):
    conn = get_connection()
    conn.execute(
        """UPDATE customer SET name=?, mobile=?, address=?, gstin=?,
           updated_at=CURRENT_TIMESTAMP WHERE id=?""",
        (name.strip(), mobile.strip(), address.strip(), gstin.strip(), customer_id),
    )
    conn.commit()


def delete_customer(customer_id: int):
    conn = get_connection()
    conn.execute("DELETE FROM customer WHERE id=?", (customer_id,))
    conn.commit()


def get_all_customers() -> list[dict]:
    conn = get_connection()
    rows = conn.execute("SELECT id, name, mobile FROM customer ORDER BY name").fetchall()
    return [dict(r) for r in rows]


# ── Customer Vehicles ──────────────────────────────────────────

def get_customer_vehicles(customer_id: int) -> list[dict]:
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM customer_vehicle WHERE customer_id=? ORDER BY vehicle_no",
        (customer_id,),
    ).fetchall()
    return [dict(r) for r in rows]


def add_customer_vehicle(customer_id: int, vehicle_no: str,
                         vehicle_type: str = "Tipper", capacity: str = "") -> int:
    conn = get_connection()
    cur = conn.execute(
        "INSERT INTO customer_vehicle (customer_id, vehicle_no, vehicle_type, capacity) VALUES (?, ?, ?, ?)",
        (customer_id, vehicle_no.strip(), vehicle_type, capacity.strip()),
    )
    conn.commit()
    return cur.lastrowid


def update_customer_vehicle(vehicle_id: int, vehicle_no: str,
                            vehicle_type: str = "Tipper", capacity: str = ""):
    conn = get_connection()
    conn.execute(
        "UPDATE customer_vehicle SET vehicle_no=?, vehicle_type=?, capacity=? WHERE id=?",
        (vehicle_no.strip(), vehicle_type, capacity.strip(), vehicle_id),
    )
    conn.commit()


def delete_customer_vehicle(vehicle_id: int):
    conn = get_connection()
    conn.execute("DELETE FROM customer_vehicle WHERE id=?", (vehicle_id,))
    conn.commit()
