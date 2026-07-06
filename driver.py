"""Driver CRUD."""

from database import get_connection


def search_drivers(query: str = "") -> list[dict]:
    conn = get_connection()
    if query:
        rows = conn.execute(
            """SELECT * FROM driver
               WHERE name LIKE ? OR mobile LIKE ? OR license_no LIKE ?
               ORDER BY name""",
            (f"%{query}%", f"%{query}%", f"%{query}%"),
        ).fetchall()
    else:
        rows = conn.execute("SELECT * FROM driver ORDER BY name").fetchall()
    return [dict(r) for r in rows]


def get_driver(driver_id: int) -> dict | None:
    conn = get_connection()
    row = conn.execute("SELECT * FROM driver WHERE id=?", (driver_id,)).fetchone()
    return dict(row) if row else None


def add_driver(
    name: str, mobile: str = "", license_no: str = "", address: str = "",
) -> int:
    conn = get_connection()
    cur = conn.execute(
        "INSERT INTO driver (name, mobile, license_no, address) VALUES (?, ?, ?, ?)",
        (name.strip(), mobile.strip(), license_no.strip().upper(), address.strip()),
    )
    conn.commit()
    return cur.lastrowid


def update_driver(
    driver_id: int, name: str, mobile: str = "",
    license_no: str = "", address: str = "",
):
    conn = get_connection()
    conn.execute(
        """UPDATE driver SET name=?, mobile=?, license_no=?, address=?,
           updated_at=CURRENT_TIMESTAMP WHERE id=?""",
        (name.strip(), mobile.strip(), license_no.strip().upper(),
         address.strip(), driver_id),
    )
    conn.commit()


def delete_driver(driver_id: int):
    conn = get_connection()
    conn.execute("DELETE FROM driver WHERE id=?", (driver_id,))
    conn.commit()


def get_all_drivers() -> list[dict]:
    conn = get_connection()
    rows = conn.execute(
        "SELECT id, name, mobile FROM driver ORDER BY name"
    ).fetchall()
    return [dict(r) for r in rows]
