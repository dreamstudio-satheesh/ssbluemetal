"""Product/Material CRUD."""

from database import get_connection


def search_products(query: str = "") -> list[dict]:
    conn = get_connection()
    if query:
        rows = conn.execute(
            """SELECT * FROM product
               WHERE name LIKE ? OR hsn_code LIKE ?
               ORDER BY name""",
            (f"%{query}%", f"%{query}%"),
        ).fetchall()
    else:
        rows = conn.execute("SELECT * FROM product ORDER BY name").fetchall()
    return [dict(r) for r in rows]


def get_product(product_id: int) -> dict | None:
    conn = get_connection()
    row = conn.execute("SELECT * FROM product WHERE id=?", (product_id,)).fetchone()
    return dict(row) if row else None


def add_product(name: str, unit: str, rate: float, description: str = "", hsn_code: str = "") -> int:
    conn = get_connection()
    cur = conn.execute(
        "INSERT INTO product (name, unit, rate, description, hsn_code) VALUES (?, ?, ?, ?, ?)",
        (name.strip(), unit.strip(), rate, description.strip(), hsn_code.strip()),
    )
    conn.commit()
    return cur.lastrowid


def update_product(product_id: int, name: str, unit: str, rate: float, description: str = "", hsn_code: str = ""):
    conn = get_connection()
    conn.execute(
        """UPDATE product SET name=?, unit=?, rate=?, description=?, hsn_code=?,
           updated_at=CURRENT_TIMESTAMP WHERE id=?""",
        (name.strip(), unit.strip(), rate, description.strip(), hsn_code.strip(), product_id),
    )
    conn.commit()


def delete_product(product_id: int):
    conn = get_connection()
    conn.execute("DELETE FROM product WHERE id=?", (product_id,))
    conn.commit()


def get_all_products() -> list[dict]:
    conn = get_connection()
    rows = conn.execute("SELECT id, name, unit, rate FROM product ORDER BY name").fetchall()
    return [dict(r) for r in rows]
