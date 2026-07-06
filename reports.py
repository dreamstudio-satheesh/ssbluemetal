"""Daily sales, summary reports, GSTR-1, and HSN summary."""

from database import get_connection


def daily_sales(date: str | None = None) -> list[dict]:
    """Return all active invoices for a given date (default today)."""
    from datetime import date as dt_date
    if date is None:
        date = dt_date.today().isoformat()
    conn = get_connection()
    rows = conn.execute(
        """SELECT id, invoice_no, customer_name, grand_total, gst_type
           FROM invoice WHERE invoice_date=? AND status='active'
           ORDER BY id""",
        (date,),
    ).fetchall()
    return [dict(r) for r in rows]


def date_range_sales(from_date: str, to_date: str) -> list[dict]:
    conn = get_connection()
    rows = conn.execute(
        """SELECT invoice_date, COUNT(*) as count, SUM(grand_total) as total
           FROM invoice WHERE invoice_date BETWEEN ? AND ? AND status='active'
           GROUP BY invoice_date ORDER BY invoice_date""",
        (from_date, to_date),
    ).fetchall()
    return [dict(r) for r in rows]


def customer_sales_report(customer_id: int) -> list[dict]:
    conn = get_connection()
    rows = conn.execute(
        """SELECT invoice_no, invoice_date, grand_total, status
           FROM invoice WHERE customer_id=? ORDER BY id DESC""",
        (customer_id,),
    ).fetchall()
    return [dict(r) for r in rows]


def product_sales_report(product_id: int) -> list[dict]:
    conn = get_connection()
    rows = conn.execute(
        """SELECT i.invoice_no, i.invoice_date, ii.quantity, ii.unit,
                  ii.rate, ii.amount
           FROM invoice_item ii
           JOIN invoice i ON i.id = ii.invoice_id
           WHERE ii.product_id=? AND i.status='active'
           ORDER BY i.id DESC""",
        (product_id,),
    ).fetchall()
    return [dict(r) for r in rows]


def top_products(limit: int = 10) -> list[dict]:
    conn = get_connection()
    rows = conn.execute(
        """SELECT ii.product_name, SUM(ii.quantity) as qty, ii.unit,
                  SUM(ii.amount) as total
           FROM invoice_item ii
           JOIN invoice i ON i.id = ii.invoice_id
           WHERE i.status='active'
           GROUP BY ii.product_name ORDER BY total DESC LIMIT ?""",
        (limit,),
    ).fetchall()
    return [dict(r) for r in rows]


# ═══════════════════════════════════════════════════════════════════
#  SALES REGISTER (day-wise / month-wise)
# ═══════════════════════════════════════════════════════════════════

def sales_register(from_date: str, to_date: str, period: str = "day") -> list[dict]:
    """Aggregated sales grouped by day or month.

    Returns list of dicts with keys depending on period:
      day:   date, invoice_count, taxable, cgst, sgst, igst, total
      month: month, invoice_count, taxable, cgst, sgst, igst, total
    """
    conn = get_connection()
    if period == "month":
        group_col = "strftime('%Y-%m', invoice_date)"
        label_col = group_col + " AS period"
        order = group_col
    else:
        group_col = "invoice_date"
        label_col = group_col + " AS period"
        order = group_col

    sql = f"""
        SELECT {label_col},
               COUNT(*) as invoice_count,
               ROUND(SUM(subtotal), 2) as taxable,
               ROUND(SUM(cgst_amount), 2) as cgst,
               ROUND(SUM(sgst_amount), 2) as sgst,
               ROUND(SUM(igst_amount), 2) as igst,
               ROUND(SUM(grand_total), 2) as total
        FROM invoice
        WHERE invoice_date BETWEEN ? AND ? AND status='active'
        GROUP BY {group_col}
        ORDER BY {order}
    """
    rows = conn.execute(sql, (from_date, to_date)).fetchall()
    return [dict(r) for r in rows]


# ═══════════════════════════════════════════════════════════════════
#  HSN SUMMARY
# ═══════════════════════════════════════════════════════════════════

def hsn_summary(from_date: str, to_date: str) -> list[dict]:
    """Aggregate sales by HSN code.

    Returns: hsn_code, description, uqc (unit), total_qty, taxable, gst_rate,
             cgst, sgst, igst, total
    """
    conn = get_connection()
    rows = conn.execute(
        """SELECT p.hsn_code,
                   p.name AS description,
                   ii.unit AS uqc,
                   ROUND(SUM(ii.quantity), 3) AS total_qty,
                   ROUND(SUM(ii.amount), 2) AS taxable,
                   i.gst_rate,
                   ROUND(SUM(ii.amount) * i.gst_rate / 100 / 2, 2) AS cgst,
                   ROUND(SUM(ii.amount) * i.gst_rate / 100 / 2, 2) AS sgst,
                   ROUND(SUM(ii.amount) * i.gst_rate / 100, 2) AS igst,
                   ROUND(SUM(ii.amount) * (1 + i.gst_rate / 100), 2) AS total
            FROM invoice_item ii
            JOIN invoice i ON i.id = ii.invoice_id
            JOIN product p ON p.id = ii.product_id
            WHERE i.invoice_date BETWEEN ? AND ? AND i.status='active'
            GROUP BY p.hsn_code, i.gst_rate
            ORDER BY p.hsn_code""",
        (from_date, to_date),
    ).fetchall()
    return [dict(r) for r in rows]


# ═══════════════════════════════════════════════════════════════════
#  GSTR-1 EXPORT (invoice-level B2B format)
# ═══════════════════════════════════════════════════════════════════

def gstr1_export(from_date: str, to_date: str) -> list[dict]:
    """Invoice-level data in GSTR-1 B2B format columns.

    Columns in order:
      Invoice Number, Invoice Date, Customer Name, Customer GSTIN,
      State, Place of Supply, HSN Code, Item Description, Quantity,
      Unit, Taxable Value, GST Rate, CGST, SGST, IGST, Invoice Total
    """
    conn = get_connection()
    rows = conn.execute(
        """SELECT i.invoice_no,
                   i.invoice_date,
                   i.customer_name,
                   i.customer_gstin AS customer_gstin,
                   'Tamil Nadu' AS state,
                   'Tamil Nadu' AS place_of_supply,
                   p.hsn_code,
                   ii.product_name AS item_description,
                   ii.quantity,
                   ii.unit,
                   ROUND(ii.amount, 2) AS taxable_value,
                   i.gst_rate,
                   CASE WHEN i.gst_type='intra' THEN ROUND(ii.amount * i.gst_rate / 100 / 2, 2) ELSE 0 END AS cgst,
                   CASE WHEN i.gst_type='intra' THEN ROUND(ii.amount * i.gst_rate / 100 / 2, 2) ELSE 0 END AS sgst,
                   CASE WHEN i.gst_type='inter' THEN ROUND(ii.amount * i.gst_rate / 100, 2) ELSE 0 END AS igst,
                   ROUND(ii.amount * (1 + i.gst_rate / 100), 2) AS invoice_total
            FROM invoice_item ii
            JOIN invoice i ON i.id = ii.invoice_id
            JOIN product p ON p.id = ii.product_id
            WHERE i.invoice_date BETWEEN ? AND ? AND i.status='active'
            ORDER BY i.invoice_date, i.id""",
        (from_date, to_date),
    ).fetchall()
    result = [dict(r) for r in rows]

    # Add a total row
    if result:
        total_row = {
            "invoice_no": "",
            "invoice_date": "",
            "customer_name": "",
            "customer_gstin": "",
            "state": "",
            "place_of_supply": "",
            "hsn_code": "TOTAL",
            "item_description": "",
            "quantity": sum(r["quantity"] or 0 for r in result),
            "unit": "",
            "taxable_value": round(sum(r["taxable_value"] or 0 for r in result), 2),
            "gst_rate": "",
            "cgst": round(sum(r["cgst"] or 0 for r in result), 2),
            "sgst": round(sum(r["sgst"] or 0 for r in result), 2),
            "igst": round(sum(r["igst"] or 0 for r in result), 2),
            "invoice_total": round(sum(r["invoice_total"] or 0 for r in result), 2),
        }
        result.append(total_row)

    return result
