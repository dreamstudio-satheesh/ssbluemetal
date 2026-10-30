"""Invoice creation shared by the API layer."""

import sqlite3
from datetime import date

from customer import get_customer
from database import get_connection, get_next_invoice_no
from invoice import create_invoice
from printer import _amount_in_words
from product import get_product
from settings import get_company

GST_RATE = 5.0


class InvalidInvoice(ValueError):
    pass


def build_lines(items) -> tuple[list[dict], float]:
    lines: list[dict] = []
    subtotal = 0.0
    for item in items:
        product = get_product(item.product_id)
        if not product:
            raise InvalidInvoice(f"Unknown product: {item.product_id}")
        rate = item.rate if item.rate is not None else float(product["rate"] or 0)
        amount = round(item.quantity * rate, 2)
        subtotal += amount
        lines.append(
            {
                "product_id": product["id"],
                "product_name": product["name"],
                "description": product.get("description", ""),
                "quantity": item.quantity,
                "unit": product.get("unit", ""),
                "rate": rate,
                "amount": amount,
            }
        )
    return lines, round(subtotal, 2)


def create_invoice_from_payload(payload) -> dict:
    customer = get_customer(payload.customer_id)
    if not customer:
        raise InvalidInvoice(f"Unknown customer: {payload.customer_id}")

    lines, subtotal = build_lines(payload.items)
    gst = round(subtotal * GST_RATE / 100, 2)
    cgst = round(gst / 2, 2)
    sgst = round(gst - cgst, 2)
    payable = round(subtotal + gst, 2)

    if payload.round_off:
        grand_total = float(round(payable))
        round_off_value = round(grand_total - payable, 2)
    else:
        grand_total = payable
        round_off_value = 0.0

    invoice_date = (payload.invoice_date or date.today()).isoformat()
    prefix = get_company().get("invoice_prefix") or "INV"
    conn = get_connection()

    for _ in range(5):
        invoice_no = get_next_invoice_no(prefix)
        try:
            invoice_id = create_invoice(
                invoice_no=invoice_no,
                customer_id=customer["id"],
                customer_name=customer["name"],
                customer_mobile=customer.get("mobile", ""),
                customer_gstin=customer.get("gstin", ""),
                invoice_date=invoice_date,
                subtotal=subtotal,
                gst_rate=GST_RATE,
                cgst_amount=cgst,
                sgst_amount=sgst,
                round_off=round_off_value,
                grand_total=grand_total,
                amount_in_words=_amount_in_words(grand_total),
                notes=payload.notes.strip(),
                vehicle_no=payload.vehicle_no.strip(),
                driver_name=payload.driver_name.strip(),
                items=lines,
            )
            return {
                "id": invoice_id,
                "invoice_no": invoice_no,
                "subtotal": subtotal,
                "cgst_amount": cgst,
                "sgst_amount": sgst,
                "round_off": round_off_value,
                "grand_total": grand_total,
                "amount_in_words": _amount_in_words(grand_total),
            }
        except sqlite3.IntegrityError:
            conn.rollback()

    raise InvalidInvoice("Invoice number is busy, please retry")
