"""Transporter CRUD."""

from database import get_connection


def search_transporters(query: str = "") -> list[dict]:
    conn = get_connection()
    if query:
        rows = conn.execute(
            """SELECT * FROM transporter
               WHERE name LIKE ? OR mobile LIKE ? OR gstin LIKE ?
               ORDER BY name""",
            (f"%{query}%", f"%{query}%", f"%{query}%"),
        ).fetchall()
    else:
        rows = conn.execute("SELECT * FROM transporter ORDER BY name").fetchall()
    return [dict(r) for r in rows]


def get_transporter(transporter_id: int) -> dict | None:
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM transporter WHERE id=?", (transporter_id,)
    ).fetchone()
    return dict(row) if row else None


def add_transporter(
    name: str, mobile: str = "", address: str = "", gstin: str = "",
) -> int:
    conn = get_connection()
    cur = conn.execute(
        "INSERT INTO transporter (name, mobile, address, gstin) VALUES (?, ?, ?, ?)",
        (name.strip(), mobile.strip(), address.strip(), gstin.strip()),
    )
    conn.commit()
    return cur.lastrowid


def update_transporter(
    transporter_id: int, name: str, mobile: str = "",
    address: str = "", gstin: str = "",
):
    conn = get_connection()
    conn.execute(
        """UPDATE transporter SET name=?, mobile=?, address=?, gstin=?,
           updated_at=CURRENT_TIMESTAMP WHERE id=?""",
        (name.strip(), mobile.strip(), address.strip(), gstin.strip(), transporter_id),
    )
    conn.commit()


def delete_transporter(transporter_id: int):
    conn = get_connection()
    conn.execute("DELETE FROM transporter WHERE id=?", (transporter_id,))
    conn.commit()


def get_all_transporters() -> list[dict]:
    conn = get_connection()
    rows = conn.execute(
        "SELECT id, name, mobile FROM transporter ORDER BY name"
    ).fetchall()
    return [dict(r) for r in rows]
