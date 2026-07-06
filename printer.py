"""Generate A4 GST invoice PDF using ReportLab."""

import os
import platform
import subprocess

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm, cm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, HRFlowable,
)
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

from settings import get_company, get_db_setting
from invoice import get_invoice, get_invoice_items
from delivery_challan import get_delivery_challan, get_delivery_challan_items
from receipt import get_receipt
from database import get_connection


# ── Colour palette ──
NAVY = colors.HexColor("#1a237e")
LIGHT_NAVY = colors.HexColor("#e8eaf6")
GREY = colors.HexColor("#757575")
LIGHT_GREY = colors.HexColor("#f5f5f5")
BORDER = colors.HexColor("#cccccc")
WHITE = colors.white
BLACK = colors.black

# ── Layout constants (all PDFs) ──
MARGIN_LR = 12*mm
MARGIN_TOP = 8*mm
MARGIN_BOTTOM = 10*mm
USABLE_WIDTH = A4[0] - 2*MARGIN_LR  # 186 mm
HALF_WIDTH = USABLE_WIDTH / 2         # 93 mm (per column)

ASSETS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets")
PDF_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "pdf_output")


def _find_font() -> str:
    """Find best available professional font (Arial/Liberation Sans first)."""
    # Priority: Arial-compatible → Noto (Unicode) → Calibri → DejaVu (fallback)
    candidates = [
        # Linux — Liberation Sans (Arial metric), professional look
        "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
        # Linux — Noto Sans (good Unicode, Tamil support)
        "/usr/share/fonts/truetype/noto/NotoSans-Regular.ttf",
        "/usr/share/fonts/truetype/noto/NotoSansTamil-Regular.ttf",
        "/usr/share/fonts/opentype/noto/NotoSansTamil-Regular.otf",
        # Windows
        os.path.expandvars(r"%WINDIR%\Fonts\Arial.ttf"),
        os.path.expandvars(r"%WINDIR%\Fonts\Calibri.ttf"),
        os.path.expandvars(r"%WINDIR%\Fonts\segoeui.ttf"),
        # macOS
        "/Library/Fonts/Arial.ttf",
        "/System/Library/Fonts/Supplemental/Arial.ttf",
        # Linux fallback — DejaVu (always available, good Unicode)
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        # Downloaded fallback
        os.path.join(ASSETS_DIR, "DejaVuSans.ttf"),
    ]
    for path in candidates:
        if os.path.exists(path):
            return path
    return ""


def _download_dejavu() -> str:
    """Download DejaVuSans as last-resort fallback."""
    bundled = os.path.join(ASSETS_DIR, "DejaVuSans.ttf")
    if os.path.exists(bundled):
        return bundled
    url = "https://github.com/dejavu-fonts/dejavu-fonts/raw/master/ttf/DejaVuSans.ttf"
    try:
        os.makedirs(ASSETS_DIR, exist_ok=True)
        print(f"[printer] Downloading DejaVuSans ...")
        from urllib.request import urlopen
        with urlopen(url, timeout=30) as resp:
            data = resp.read()
        with open(bundled, "wb") as f:
            f.write(data)
        return bundled
    except Exception as e:
        print(f"[printer] Font download failed: {e}")
        return ""


def _try_register_font() -> str:
    """Register the best available font. Returns font name usable in styles."""
    path = _find_font()
    if not path:
        path = _download_dejavu()
    if path:
        try:
            pdfmetrics.registerFont(TTFont("AppFont", path))
            return "AppFont"
        except Exception:
            pass
    return "Helvetica"


FONT_NAME = _try_register_font()


def _amount_in_words(amount: float) -> str:
    """Convert number to Indian Rupees in words."""
    if amount == 0:
        return "Zero Rupees Only"

    units = ["", "One", "Two", "Three", "Four", "Five", "Six", "Seven", "Eight", "Nine"]
    teens = ["Ten", "Eleven", "Twelve", "Thirteen", "Fourteen", "Fifteen",
             "Sixteen", "Seventeen", "Eighteen", "Nineteen"]
    tens = ["", "", "Twenty", "Thirty", "Forty", "Fifty", "Sixty", "Seventy", "Eighty", "Ninety"]

    def _under_1000(n):
        res = ""
        if n >= 100:
            res += units[n // 100] + " Hundred "
            n %= 100
        if 10 < n < 20:
            res += teens[n - 10] + " "
        else:
            if n >= 20:
                res += tens[n // 10] + " "
                n %= 10
            if n > 0:
                res += units[n] + " "
        return res.strip()

    amt = int(round(amount))
    if amt >= 10000000:
        return "Very Large Amount"

    words = ""
    if amt >= 100000:
        lakhs = amt // 100000
        words += _under_1000(lakhs) + " Lakh "
        amt %= 100000
    if amt >= 1000:
        thousands = amt // 1000
        words += _under_1000(thousands) + " Thousand "
        amt %= 1000
    if amt > 0:
        words += _under_1000(amt)

    return words.strip() + " Rupees Only"


def _get_product_hsn(product_id: int) -> str:
    """Look up HSN code from the product table."""
    if not product_id:
        return ""
    conn = get_connection()
    row = conn.execute(
        "SELECT hsn_code FROM product WHERE id=?", (product_id,)
    ).fetchone()
    return row["hsn_code"] if row and row["hsn_code"] else ""


def _header_block(company: dict) -> Table:
    """Professional letterhead block with border — name, address, reg details."""
    USABLE = 186*mm
    rows = []

    # Company name
    rows.append([Paragraph(
        company.get("name", "").upper(),
        ParagraphStyle("H1", fontName=FONT_NAME, fontSize=16, alignment=TA_CENTER,
                        spaceBefore=4, spaceAfter=2, textColor=NAVY, leading=20),
    )])

    # Address
    addr = company.get("address", "")
    if addr:
        rows.append([Paragraph(
            addr.replace("\n", "<br/>"),
            ParagraphStyle("H2", fontName=FONT_NAME, fontSize=8.5, alignment=TA_CENTER,
                            leading=12, textColor=BLACK),
        )])

    # Thin separator inside header
    rows.append([HRFlowable(width="60%", thickness=0.5, color=NAVY, spaceAfter=2, spaceBefore=2)])

    # Registration line
    reg_parts = []
    if company.get("gstin"):
        reg_parts.append(f"GSTIN: {company['gstin']}")
    if company.get("phone"):
        reg_parts.append(f"Phone: {company['phone']}")
    if company.get("email"):
        reg_parts.append(f"Email: {company['email']}")
    if reg_parts:
        rows.append([Paragraph(
            " | ".join(reg_parts),
            ParagraphStyle("Reg", fontName=FONT_NAME, fontSize=7.5, alignment=TA_CENTER,
                            textColor=GREY, leading=10),
        )])
    pan = company.get("pan", "")
    if pan:
        rows.append([Paragraph(
            f"PAN: {pan}",
            ParagraphStyle("Pan", fontName=FONT_NAME, fontSize=7.5, alignment=TA_CENTER,
                            textColor=GREY, leading=10),
        )])

    tbl = Table(rows, colWidths=[USABLE])
    tbl.setStyle(TableStyle([
        ("BOX", (0, 0), (-1, -1), 0.6, NAVY),
        ("TOPPADDING", (0, 0), (-1, -1), 2),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))
    return tbl


def _title_band(text: str) -> Table:
    """Navy band with white title text."""
    band = Table(
        [[Paragraph(text, ParagraphStyle(
            "Band", fontName=FONT_NAME, fontSize=14, alignment=TA_CENTER,
            textColor=WHITE, spaceBefore=2, spaceAfter=2,
        ))]],
        colWidths=[USABLE_WIDTH],
    )
    band.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), NAVY),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
    ]))
    return band


def _info_pair(label: str, value: str) -> list:
    """Return a [label, value] row for side-by-side info tables."""
    return [
        Paragraph(f"<b>{label}</b>",
                  ParagraphStyle("IL", fontName=FONT_NAME, fontSize=9, textColor=GREY)),
        Paragraph(value,
                  ParagraphStyle("IV", fontName=FONT_NAME, fontSize=9, textColor=BLACK)),
    ]


def generate_invoice_pdf(invoice_id: int, output_path: str | None = None) -> str:
    """Professional A4 GST invoice — clean, print-friendly layout."""
    inv = get_invoice(invoice_id)
    if not inv:
        raise ValueError(f"Invoice {invoice_id} not found")

    items = get_invoice_items(invoice_id)
    company = get_company()

    if output_path is None:
        os.makedirs(PDF_DIR, exist_ok=True)
        safe_no = inv['invoice_no'].replace("/", "_")
        output_path = os.path.join(
            PDF_DIR,
            f"invoice_{safe_no}.pdf",
        )

    doc = SimpleDocTemplate(
        output_path, pagesize=A4,
        leftMargin=12*mm, rightMargin=12*mm,
        topMargin=8*mm, bottomMargin=10*mm,
    )
    styles = getSampleStyleSheet()
    elements = []

    # ═══════════════════════════════════════════════════════════════
    #  1. LETTERHEAD
    # ═══════════════════════════════════════════════════════════════
    elements.append(_header_block(company))
    elements.append(Spacer(1, 3*mm))

    # ═══════════════════════════════════════════════════════════════
    #  2. TITLE BAND
    # ═══════════════════════════════════════════════════════════════
    elements.append(_title_band("TAX INVOICE"))
    elements.append(Spacer(1, 4*mm))

    # ═══════════════════════════════════════════════════════════════
    #  3. TWO-COLUMN INFO: Invoice details (left) + Customer (right)
    # ═══════════════════════════════════════════════════════════════
    left_rows = [
        _info_pair("Invoice No", f"<b>{inv['invoice_no']}</b>"),
        _info_pair("Date", f"<b>{inv['invoice_date']}</b>"),
        _info_pair("Place of Supply", f"<b>{inv.get('driver_name') or 'Tamil Nadu'}</b>"),
    ]
    if inv.get("vehicle_no"):
        left_rows.append(_info_pair("Vehicle No", f"<b>{inv['vehicle_no']}</b>"))
    left_tbl = Table(left_rows, colWidths=[32*mm, 56*mm])
    left_tbl.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 1),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 1),
    ]))
    # Wrap left in a box
    left_wrap = Table([[left_tbl]], colWidths=[88*mm])
    left_wrap.setStyle(TableStyle([
        ("BOX", (0, 0), (-1, -1), 0.4, BORDER),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
    ]))

    # Customer box
    cust_lines = [f"<b>{inv['customer_name']}</b>"]
    if inv.get("customer_mobile"):
        cust_lines.append(f"Mobile: {inv['customer_mobile']}")
    if inv.get("customer_gstin"):
        cust_lines.append(f"GSTIN: {inv['customer_gstin']}")
    cust_text = "<br/>".join(cust_lines)

    right_rows = [
        [Paragraph("<b>Bill To</b>",
                   ParagraphStyle("BL", fontName=FONT_NAME, fontSize=9, textColor=GREY)),
         Paragraph(cust_text,
                   ParagraphStyle("BV", fontName=FONT_NAME, fontSize=9, textColor=BLACK))],
    ]
    right_tbl = Table(right_rows, colWidths=[20*mm, 68*mm])
    right_tbl.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 1),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 1),
    ]))
    right_wrap = Table([[right_tbl]], colWidths=[88*mm])
    right_wrap.setStyle(TableStyle([
        ("BOX", (0, 0), (-1, -1), 0.4, BORDER),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
    ]))

    info_table = Table([[left_wrap, right_wrap]], colWidths=[88*mm, 88*mm])
    info_table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
    ]))
    elements.append(info_table)
    elements.append(Spacer(1, 4*mm))

    # ═══════════════════════════════════════════════════════════════
    #  4. ITEMS TABLE
    # ═══════════════════════════════════════════════════════════════
    hdr = ["#", "Description", "HSN/SAC", "Qty", "Unit", "Rate", "Amount"]
    cw = [7*mm, 56*mm, 22*mm, 16*mm, 14*mm, 22*mm, 24*mm]

    data = [hdr]
    for idx, item in enumerate(items, 1):
        hsn = _get_product_hsn(item.get("product_id")) or ""
        data.append([
            str(idx),
            item.get("product_name", ""),
            hsn,
            f"{item['quantity']:.3f}",
            item.get("unit", ""),
            f"{item['rate']:.2f}",
            f"{item['amount']:.2f}",
        ])

    # Totals section
    data.append(["", "", "", "", "", "", ""])  # spacer
    gst_rate = 5.0
    data.append(["", "", "", "", "", "Subtotal", f"{inv['subtotal']:.2f}"])
    if gst_rate > 0:
        hr = gst_rate / 2
        data.append(["", "", "", "", "", f"CGST @ {hr:.2f}%", f"{inv['cgst_amount']:.2f}"])
        data.append(["", "", "", "", "", f"SGST @ {hr:.2f}%", f"{inv['sgst_amount']:.2f}"])
    ro = inv.get("round_off", 0)
    if ro != 0:
        data.append(["", "", "", "", "", "Round Off", f"{ro:+.2f}"])
    data.append(["", "", "", "", "", "Grand Total", f"{inv['grand_total']:.2f}"])

    total_n = 2 + (2 if gst_rate > 0 else 0) + (1 if ro != 0 else 0)
    total_start = -total_n

    tbl = Table(data, colWidths=cw, repeatRows=1)
    style_cmds = [
        ("BACKGROUND", (0, 0), (-1, 0), NAVY),
        ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
        ("FONTNAME", (0, 0), (-1, -1), FONT_NAME),
        ("FONTSIZE", (0, 0), (-1, 0), 8),
        ("FONTSIZE", (0, 1), (-1, -1), 8),
        ("FONTSIZE", (0, -1), (-1, -1), 11),
        ("ALIGN", (0, 0), (-1, 0), "CENTER"),
        ("ALIGN", (0, 1), (0, -1), "CENTER"),
        ("ALIGN", (3, 1), (-1, -1), "RIGHT"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("GRID", (0, 1), (-1, total_start - 1), 0.3, BORDER),
        ("LINEABOVE", (0, total_start), (-1, total_start), 0.6, NAVY),
        ("LINEABOVE", (0, -1), (-1, -1), 1.0, NAVY),
        ("BACKGROUND", (0, -1), (-1, -1), LIGHT_NAVY),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("LEFTPADDING", (0, 0), (-1, -1), 3),
        ("RIGHTPADDING", (0, 0), (-1, -1), 3),
    ]
    for i in range(total_start, 0):
        if i < 0:
            style_cmds.append(("ALIGN", (5, i), (5, i), "LEFT"))
    tbl.setStyle(TableStyle(style_cmds))
    elements.append(tbl)
    elements.append(Spacer(1, 4*mm))

    # ═══════════════════════════════════════════════════════════════
    #  5. AMOUNT IN WORDS
    # ═══════════════════════════════════════════════════════════════
    words = inv.get("amount_in_words") or _amount_in_words(inv["grand_total"])
    aw_tbl = Table(
        [[Paragraph("<b>Amount in Words:</b>",
                     ParagraphStyle("AWL", fontName=FONT_NAME, fontSize=9, textColor=NAVY)),
          Paragraph(words,
                     ParagraphStyle("AWV", fontName=FONT_NAME, fontSize=9, textColor=NAVY, leading=13))]],
        colWidths=[30*mm, 132*mm],
    )
    aw_tbl.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("BOX", (0, 0), (-1, -1), 0.4, BORDER),
        ("BACKGROUND", (0, 0), (-1, -1), LIGHT_GREY),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
    ]))
    elements.append(aw_tbl)
    elements.append(Spacer(1, 1*mm))

    # ═══════════════════════════════════════════════════════════════
    #  6. BANK DETAILS
    # ═══════════════════════════════════════════════════════════════
    bank_parts = []
    if company.get("bank_name"):
        bank_parts.append(f"Bank: {company['bank_name']}")
    if company.get("bank_account"):
        bank_parts.append(f"A/C: {company['bank_account']}")
    if company.get("bank_ifsc"):
        bank_parts.append(f"IFSC: {company['bank_ifsc']}")
    if bank_parts:
        bank_text = "&nbsp;&nbsp;|&nbsp;&nbsp;".join(bank_parts)
        bk_tbl = Table(
            [[Paragraph("<b>Bank Details:</b>",
                         ParagraphStyle("BKL", fontName=FONT_NAME, fontSize=9, textColor=GREY)),
              Paragraph(bank_text,
                         ParagraphStyle("BKV", fontName=FONT_NAME, fontSize=9, textColor=BLACK))]],
            colWidths=[26*mm, 136*mm],
        )
        bk_tbl.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING", (0, 0), (-1, -1), 2),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
        ]))
        elements.append(bk_tbl)
        elements.append(Spacer(1, 0.5*mm))

    # ═══════════════════════════════════════════════════════════════
    #  7. TERMS & CONDITIONS + SIGNATURE
    # ═══════════════════════════════════════════════════════════════
    cname = company.get("name", "S.S. BLUE METAL")
    terms_text = get_db_setting("terms",
        "1. All disputes subject to Coimbatore jurisdiction.\n"
        "2. Payment due within 15 days from invoice date.\n"
        "3. Interest @ 18% p.a. charged on overdue payments.\n"
        "4. Goods once sold will not be taken back.")
    terms_html = terms_text.replace("\n", "<br/>")

    terms_tbl = Table(
        [[Paragraph("<b>Terms &amp; Conditions</b>",
                     ParagraphStyle("TL", fontName=FONT_NAME, fontSize=8, textColor=GREY)),
          Paragraph(terms_html,
                     ParagraphStyle("TV", fontName=FONT_NAME, fontSize=8, textColor=BLACK, leading=11))]],
        colWidths=[28*mm, 66*mm],
    )
    terms_tbl.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("BOX", (0, 0), (-1, -1), 0.3, BORDER),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("BACKGROUND", (0, 0), (-1, 0), LIGHT_GREY),
    ]))

    sig_text = (
        f"For <b>{cname}</b><br/><br/>"
        f"_________________________<br/>"
        f"Authorised Signatory"
    )
    sig_tbl = Table(
        [[Paragraph(sig_text,
                     ParagraphStyle("SV", fontName=FONT_NAME, fontSize=9,
                                     alignment=TA_RIGHT, textColor=BLACK, leading=16))]],
        colWidths=[80*mm],
    )
    sig_tbl.setStyle(TableStyle([
        ("ALIGN", (0, 0), (-1, -1), "RIGHT"),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
    ]))

    bottom = Table([[terms_tbl, sig_tbl]], colWidths=[94*mm, 92*mm])
    bottom.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "BOTTOM"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
    ]))
    elements.append(bottom)
    elements.append(Spacer(1, 3*mm))

    # ═══════════════════════════════════════════════════════════════
    #  8. FOOTER
    # ═══════════════════════════════════════════════════════════════
    elements.append(HRFlowable(width="100%", thickness=0.3, color=BORDER, spaceAfter=2*mm))
    if company.get("footer_line1"):
        elements.append(Paragraph(company["footer_line1"],
                                   ParagraphStyle("F1", fontName=FONT_NAME, fontSize=7,
                                                   alignment=TA_CENTER, textColor=GREY)))
    if company.get("footer_line2"):
        elements.append(Paragraph(company["footer_line2"],
                                   ParagraphStyle("F2", fontName=FONT_NAME, fontSize=7,
                                                   alignment=TA_CENTER, textColor=GREY)))
    elements.append(Paragraph(
        "This is a computer-generated invoice.",
        ParagraphStyle("F3", fontName=FONT_NAME, fontSize=7, alignment=TA_CENTER, textColor=GREY),
    ))

    doc.build(elements)
    return output_path


# ═══════════════════════════════════════════════════════════════════
#  BLANK / HANDWRITTEN INVOICE PDF
# ═══════════════════════════════════════════════════════════════════

def generate_blank_invoice_pdf(
    invoice_no: str = "",
    invoice_date: str = "",
    output_path: str | None = None,
) -> str:
    """Blank A4 invoice form for handwritten use — no customer, no items."""
    company = get_company()

    if output_path is None:
        os.makedirs(PDF_DIR, exist_ok=True)
        safe_no = invoice_no.replace("/", "_") if invoice_no else "blank"
        output_path = os.path.join(
            PDF_DIR,
            f"blank_invoice_{safe_no}.pdf",
        )

    doc = SimpleDocTemplate(
        output_path, pagesize=A4,
        leftMargin=12*mm, rightMargin=12*mm,
        topMargin=8*mm, bottomMargin=10*mm,
    )
    elements = []

    # 1. LETTERHEAD
    elements.append(_header_block(company))
    elements.append(Spacer(1, 3*mm))

    # 2. TITLE BAND
    elements.append(_title_band("BLANK INVOICE  (Handwritten)"))
    elements.append(Spacer(1, 4*mm))

    # 3. TWO-COLUMN INFO: Invoice details (left) + Customer blanks (right)
    left_rows = [
        _info_pair("Invoice No",
                   f"<b>{invoice_no}</b>  ____________________" if invoice_no
                   else "____________________"),
        _info_pair("Date",
                   f"<b>{invoice_date}</b>  ____________________" if invoice_date
                   else "____________________"),
        _info_pair("Vehicle No", "____________________"),
        _info_pair("Designation", "____________________"),
    ]
    left_tbl = Table(left_rows, colWidths=[32*mm, 56*mm])
    left_tbl.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 1),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 1),
    ]))
    left_wrap = Table([[left_tbl]], colWidths=[88*mm])
    left_wrap.setStyle(TableStyle([
        ("BOX", (0, 0), (-1, -1), 0.4, BORDER),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
    ]))

    # Customer box (blank)
    blank_cust = ("Name: _____________________________<br/>"
                  "Mobile: ___________________________<br/>"
                  "GSTIN: ____________________________")
    right_rows = [
        [Paragraph("<b>Bill To</b>",
                   ParagraphStyle("BL", fontName=FONT_NAME, fontSize=9, textColor=GREY)),
         Paragraph(blank_cust,
                   ParagraphStyle("BV", fontName=FONT_NAME, fontSize=9, textColor=BLACK, leading=16))],
    ]
    right_tbl = Table(right_rows, colWidths=[20*mm, 68*mm])
    right_tbl.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 1),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 1),
    ]))
    right_wrap = Table([[right_tbl]], colWidths=[88*mm])
    right_wrap.setStyle(TableStyle([
        ("BOX", (0, 0), (-1, -1), 0.4, BORDER),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
    ]))

    info_table = Table([[left_wrap, right_wrap]], colWidths=[88*mm, 88*mm])
    info_table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
    ]))
    elements.append(info_table)
    elements.append(Spacer(1, 4*mm))

    # 4. ITEMS TABLE — headers + 6 blank rows
    hdr = ["#", "Description", "HSN/SAC", "Qty", "Unit", "Rate", "Amount"]
    cw = [7*mm, 56*mm, 22*mm, 16*mm, 14*mm, 22*mm, 24*mm]

    data = [hdr]
    for i in range(1, 7):
        data.append([str(i), "", "", "", "", "", ""])

    # Totals section (blank)
    data.append(["", "", "", "", "", "", ""])
    data.append(["", "", "", "", "", "Subtotal", "__________"])
    data.append(["", "", "", "", "", "CGST @ ___%", "__________"])
    data.append(["", "", "", "", "", "SGST @ ___%", "__________"])
    data.append(["", "", "", "", "", "Round Off", "__________"])
    data.append(["", "", "", "", "", "Grand Total", "__________"])

    tbl = Table(data, colWidths=cw, repeatRows=1)
    style_cmds = [
        ("BACKGROUND", (0, 0), (-1, 0), NAVY),
        ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
        ("FONTNAME", (0, 0), (-1, -1), FONT_NAME),
        ("FONTSIZE", (0, 0), (-1, 0), 8),
        ("FONTSIZE", (0, 1), (-1, -1), 8),
        ("FONTSIZE", (0, -1), (-1, -1), 11),
        ("ALIGN", (0, 0), (-1, 0), "CENTER"),
        ("ALIGN", (0, 1), (0, -1), "CENTER"),
        ("ALIGN", (3, 1), (-1, -1), "RIGHT"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("GRID", (0, 1), (-1, -7), 0.3, BORDER),       # grid for blank rows
        ("LINEABOVE", (0, -6), (-1, -6), 0.6, NAVY),     # line before totals
        ("LINEABOVE", (0, -1), (-1, -1), 1.0, NAVY),
        ("BACKGROUND", (0, -1), (-1, -1), LIGHT_NAVY),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("LEFTPADDING", (0, 0), (-1, -1), 3),
        ("RIGHTPADDING", (0, 0), (-1, -1), 3),
    ]
    # Left-align the total labels
    for i in range(-6, 0):
        style_cmds.append(("ALIGN", (5, i), (5, i), "LEFT"))
    tbl.setStyle(TableStyle(style_cmds))
    elements.append(tbl)
    elements.append(Spacer(1, 4*mm))

    # 5. AMOUNT IN WORDS (blank)
    aw_tbl = Table(
        [[Paragraph("<b>Amount in Words:</b>",
                     ParagraphStyle("AWL", fontName=FONT_NAME, fontSize=9, textColor=NAVY)),
          Paragraph("_______________________________________________________",
                     ParagraphStyle("AWV", fontName=FONT_NAME, fontSize=9, textColor=NAVY, leading=13))]],
        colWidths=[30*mm, 132*mm],
    )
    aw_tbl.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("BOX", (0, 0), (-1, -1), 0.4, BORDER),
        ("BACKGROUND", (0, 0), (-1, -1), LIGHT_GREY),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
    ]))
    elements.append(aw_tbl)
    elements.append(Spacer(1, 1*mm))

    # 6. BANK DETAILS
    bank_parts = []
    if company.get("bank_name"):
        bank_parts.append(f"Bank: {company['bank_name']}")
    if company.get("bank_account"):
        bank_parts.append(f"A/C: {company['bank_account']}")
    if company.get("bank_ifsc"):
        bank_parts.append(f"IFSC: {company['bank_ifsc']}")
    if bank_parts:
        bank_text = "&nbsp;&nbsp;|&nbsp;&nbsp;".join(bank_parts)
        bk_tbl = Table(
            [[Paragraph("<b>Bank Details:</b>",
                         ParagraphStyle("BKL", fontName=FONT_NAME, fontSize=9, textColor=GREY)),
              Paragraph(bank_text,
                         ParagraphStyle("BKV", fontName=FONT_NAME, fontSize=9, textColor=BLACK))]],
            colWidths=[26*mm, 136*mm],
        )
        bk_tbl.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING", (0, 0), (-1, -1), 2),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
        ]))
        elements.append(bk_tbl)
        elements.append(Spacer(1, 0.5*mm))

    # 7. TERMS & CONDITIONS + SIGNATURE
    cname = company.get("name", "S.S. BLUE METAL")
    terms_text = get_db_setting("terms",
        "1. All disputes subject to Coimbatore jurisdiction.\n"
        "2. Payment due within 15 days from invoice date.\n"
        "3. Interest @ 18% p.a. charged on overdue payments.\n"
        "4. Goods once sold will not be taken back.")
    terms_html = terms_text.replace("\n", "<br/>")

    terms_tbl = Table(
        [[Paragraph("<b>Terms &amp; Conditions</b>",
                     ParagraphStyle("TL", fontName=FONT_NAME, fontSize=8, textColor=GREY)),
          Paragraph(terms_html,
                     ParagraphStyle("TV", fontName=FONT_NAME, fontSize=8, textColor=BLACK, leading=11))]],
        colWidths=[28*mm, 66*mm],
    )
    terms_tbl.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("BOX", (0, 0), (-1, -1), 0.3, BORDER),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("BACKGROUND", (0, 0), (-1, 0), LIGHT_GREY),
    ]))

    sig_text = (
        f"For <b>{cname}</b><br/><br/>"
        f"_________________________<br/>"
        f"Authorised Signatory"
    )
    sig_tbl = Table(
        [[Paragraph(sig_text,
                     ParagraphStyle("SV", fontName=FONT_NAME, fontSize=9,
                                     alignment=TA_RIGHT, textColor=BLACK, leading=16))]],
        colWidths=[80*mm],
    )
    sig_tbl.setStyle(TableStyle([
        ("ALIGN", (0, 0), (-1, -1), "RIGHT"),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
    ]))

    bottom = Table([[terms_tbl, sig_tbl]], colWidths=[94*mm, 92*mm])
    bottom.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "BOTTOM"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
    ]))
    elements.append(bottom)
    elements.append(Spacer(1, 3*mm))

    # 8. FOOTER
    elements.append(HRFlowable(width="100%", thickness=0.3, color=BORDER, spaceAfter=2*mm))
    if company.get("footer_line1"):
        elements.append(Paragraph(company["footer_line1"],
                                   ParagraphStyle("F1", fontName=FONT_NAME, fontSize=7,
                                                   alignment=TA_CENTER, textColor=GREY)))
    if company.get("footer_line2"):
        elements.append(Paragraph(company["footer_line2"],
                                   ParagraphStyle("F2", fontName=FONT_NAME, fontSize=7,
                                                   alignment=TA_CENTER, textColor=GREY)))
    elements.append(Paragraph(
        "This is a blank invoice form for handwritten use.",
        ParagraphStyle("F3", fontName=FONT_NAME, fontSize=7, alignment=TA_CENTER, textColor=GREY),
    ))

    doc.build(elements)
    return output_path


# ═══════════════════════════════════════════════════════════════════
#  DELIVERY CHALLAN PDF
# ═══════════════════════════════════════════════════════════════════

def generate_delivery_challan_pdf(dc_id: int, output_path: str | None = None) -> str:
    """Professional A4 Delivery Challan — matches invoice layout."""
    dc = get_delivery_challan(dc_id)
    if not dc:
        raise ValueError(f"Delivery Challan {dc_id} not found")

    items = get_delivery_challan_items(dc_id)
    company = get_company()

    if output_path is None:
        os.makedirs(PDF_DIR, exist_ok=True)
        output_path = os.path.join(
            PDF_DIR,
            f"delivery_challan_{dc['dc_no'].replace('/', '_')}.pdf",
        )

    doc = SimpleDocTemplate(
        output_path, pagesize=A4,
        leftMargin=12*mm, rightMargin=12*mm,
        topMargin=8*mm, bottomMargin=10*mm,
    )
    styles = getSampleStyleSheet()
    elements = []

    # 1. LETTERHEAD
    elements.append(_header_block(company))
    elements.append(Spacer(1, 3*mm))

    # 2. TITLE BAND
    elements.append(_title_band("DELIVERY CHALLAN"))
    elements.append(Spacer(1, 4*mm))

    # 3. TWO-COLUMN INFO: DC details (left) + Customer (right)
    left_rows = [
        _info_pair("DC No", f"<b>{dc['dc_no']}</b>"),
        _info_pair("Date", f"<b>{dc['challan_date']}</b>"),
        _info_pair("Reference Invoice", f"<b>{dc['invoice_no']}</b>"),
    ]
    left_tbl = Table(left_rows, colWidths=[32*mm, 56*mm])
    left_tbl.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 1),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 1),
    ]))
    left_wrap = Table([[left_tbl]], colWidths=[88*mm])
    left_wrap.setStyle(TableStyle([
        ("BOX", (0, 0), (-1, -1), 0.4, BORDER),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
    ]))

    cust_lines = [f"<b>{dc['customer_name']}</b>"]
    if dc.get("customer_mobile"):
        cust_lines.append(f"Mobile: {dc['customer_mobile']}")
    if dc.get("customer_gstin"):
        cust_lines.append(f"GSTIN: {dc['customer_gstin']}")
    cust_text = "<br/>".join(cust_lines)
    right_rows = [
        [Paragraph("<b>Deliver To</b>",
                   ParagraphStyle("BL", fontName=FONT_NAME, fontSize=9, textColor=GREY)),
         Paragraph(cust_text,
                   ParagraphStyle("BV", fontName=FONT_NAME, fontSize=9, textColor=BLACK))],
    ]
    right_tbl = Table(right_rows, colWidths=[22*mm, 66*mm])
    right_tbl.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 1),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 1),
    ]))
    right_wrap = Table([[right_tbl]], colWidths=[88*mm])
    right_wrap.setStyle(TableStyle([
        ("BOX", (0, 0), (-1, -1), 0.4, BORDER),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
    ]))
    info_table = Table([[left_wrap, right_wrap]], colWidths=[88*mm, 88*mm])
    info_table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
    ]))
    elements.append(info_table)
    elements.append(Spacer(1, 4*mm))

    # 4. TRANSPORT DETAILS
    if dc.get("vehicle_no") or dc.get("driver_name") or dc.get("transporter_name"):
        rows = []
        rows.append([Paragraph("<b>Transport Details</b>",
                                ParagraphStyle("TDH", fontName=FONT_NAME, fontSize=9, textColor=NAVY)),
                     Paragraph("", ParagraphStyle("TD", fontName=FONT_NAME, fontSize=9))])
        if dc.get("vehicle_no"):
            rows.append(_info_pair("Vehicle No", f"<b>{dc['vehicle_no']}</b>"))
        if dc.get("vehicle_owner"):
            rows.append(_info_pair("Vehicle Owner", dc["vehicle_owner"]))
        if dc.get("driver_name"):
            m = f" ({dc['driver_mobile']})" if dc.get("driver_mobile") else ""
            rows.append(_info_pair("Driver", f"<b>{dc['driver_name']}</b>{m}"))
        if dc.get("transporter_name"):
            g = f" GST: {dc['transporter_gstin']}" if dc.get("transporter_gstin") else ""
            rows.append(_info_pair("Transporter", f"{dc['transporter_name']}{g}"))
        tr_tbl = Table(rows, colWidths=[28*mm, 60*mm])
        tr_tbl.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("TOPPADDING", (0, 0), (-1, -1), 1),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 1),
            ("BOX", (0, 0), (-1, -1), 0.4, BORDER),
            ("LEFTPADDING", (0, 0), (-1, -1), 4),
            ("BACKGROUND", (0, 0), (-1, 0), LIGHT_GREY),
        ]))
        elements.append(tr_tbl)
        elements.append(Spacer(1, 3*mm))

    # 5. DELIVERY ADDRESS
    if dc.get("delivery_address"):
        addr_rows = [[
            Paragraph("<b>Delivery Address:</b>",
                      ParagraphStyle("DAL", fontName=FONT_NAME, fontSize=9, textColor=GREY)),
            Paragraph(dc["delivery_address"].replace("\n", "<br/>"),
                      ParagraphStyle("DAV", fontName=FONT_NAME, fontSize=9, textColor=BLACK)),
        ]]
        da_tbl = Table(addr_rows, colWidths=[28*mm, 60*mm])
        da_tbl.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("BOX", (0, 0), (-1, -1), 0.4, BORDER),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ]))
        elements.append(da_tbl)
        elements.append(Spacer(1, 3*mm))

    # 6. ITEMS TABLE
    hdr = ["#", "Description", "Qty", "Unit", "Rate", "Amount"]
    cw = [8*mm, 78*mm, 22*mm, 18*mm, 22*mm, 28*mm]
    data = [hdr]
    for idx, item in enumerate(items, 1):
        data.append([str(idx), item.get("product_name", ""),
                     f"{item['quantity']:.3f}", item.get("unit", ""),
                     f"{item['rate']:.2f}", f"{item['amount']:.2f}"])
    data.append(["", "", "", "", "", ""])
    data.append(["", "", "", "", "Total Amount", f"{sum(it['amount'] for it in items):.2f}"])

    tbl = Table(data, colWidths=cw, repeatRows=1)
    style = [
        ("BACKGROUND", (0, 0), (-1, 0), NAVY),
        ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
        ("FONTNAME", (0, 0), (-1, -1), FONT_NAME),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("FONTSIZE", (0, -1), (-1, -1), 10),
        ("ALIGN", (0, 0), (-1, 0), "CENTER"),
        ("ALIGN", (0, 1), (0, -1), "CENTER"),
        ("ALIGN", (3, 1), (-1, -1), "RIGHT"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("GRID", (0, 1), (-1, -3), 0.3, BORDER),
        ("LINEABOVE", (0, -2), (-1, -2), 0.6, NAVY),
        ("LINEABOVE", (0, -1), (-1, -1), 1.0, NAVY),
        ("BACKGROUND", (0, -1), (-1, -1), LIGHT_NAVY),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("LEFTPADDING", (0, 0), (-1, -1), 3),
        ("RIGHTPADDING", (0, 0), (-1, -1), 3),
    ]
    tbl.setStyle(TableStyle(style))
    elements.append(tbl)
    elements.append(Spacer(1, 4*mm))

    # 7. AMOUNT IN WORDS
    total_amount = sum(it["amount"] for it in items)
    words = _amount_in_words(total_amount)
    aw_tbl = Table(
        [[Paragraph("<b>Amount in Words:</b>",
                     ParagraphStyle("AWL", fontName=FONT_NAME, fontSize=9, textColor=NAVY)),
          Paragraph(words,
                     ParagraphStyle("AWV", fontName=FONT_NAME, fontSize=9, textColor=NAVY, leading=13))]],
        colWidths=[28*mm, 134*mm],
    )
    aw_tbl.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("BOX", (0, 0), (-1, -1), 0.4, BORDER),
        ("BACKGROUND", (0, 0), (-1, -1), LIGHT_GREY),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
    ]))
    elements.append(aw_tbl)
    elements.append(Spacer(1, 4*mm))

    # 8. NOTES
    if dc.get("notes"):
        nt = Table(
            [[Paragraph("<b>Notes:</b>",
                         ParagraphStyle("NL", fontName=FONT_NAME, fontSize=9, textColor=GREY)),
              Paragraph(dc["notes"],
                         ParagraphStyle("NV", fontName=FONT_NAME, fontSize=9, textColor=BLACK))]],
            colWidths=[24*mm, 138*mm],
        )
        nt.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("BOX", (0, 0), (-1, -1), 0.3, BORDER),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ]))
        elements.append(nt)
        elements.append(Spacer(1, 4*mm))

    # 9. SIGNATURE
    cname = company.get("name", "S.S. BLUE METAL")
    sig_text = (
        f"Received the above materials in good condition.<br/><br/>"
        f"Receiver's Signature: _________________________<br/><br/>"
        f"For <b>{cname}</b><br/><br/>"
        f"_________________________<br/>"
        f"Authorised Signatory"
    )
    sig_tbl = Table(
        [[Paragraph(sig_text,
                     ParagraphStyle("SV", fontName=FONT_NAME, fontSize=9,
                                     alignment=TA_RIGHT, textColor=BLACK, leading=16))]],
        colWidths=[90*mm],
    )
    sig_tbl.setStyle(TableStyle([
        ("ALIGN", (0, 0), (-1, -1), "RIGHT"),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
    ]))
    elements.append(sig_tbl)
    elements.append(Spacer(1, 4*mm))

    # 10. FOOTER
    elements.append(HRFlowable(width="100%", thickness=0.3, color=BORDER, spaceAfter=2*mm))
    if company.get("footer_line1"):
        elements.append(Paragraph(company["footer_line1"],
                                   ParagraphStyle("F1", fontName=FONT_NAME, fontSize=7,
                                                   alignment=TA_CENTER, textColor=GREY)))
    if company.get("footer_line2"):
        elements.append(Paragraph(company["footer_line2"],
                                   ParagraphStyle("F2", fontName=FONT_NAME, fontSize=7,
                                                   alignment=TA_CENTER, textColor=GREY)))
    elements.append(Paragraph(
        "This is a computer-generated delivery challan.",
        ParagraphStyle("F3", fontName=FONT_NAME, fontSize=7, alignment=TA_CENTER, textColor=GREY),
    ))

    doc.build(elements)
    return output_path


# ═══════════════════════════════════════════════════════════════════
#  RECEIPT PDF
# ═══════════════════════════════════════════════════════════════════

def generate_receipt_pdf(receipt_id: int, output_path: str | None = None) -> str:
    """Professional A4 Payment Receipt — matches invoice layout."""
    rec = get_receipt(receipt_id)
    if not rec:
        raise ValueError(f"Receipt {receipt_id} not found")

    company = get_company()

    if output_path is None:
        os.makedirs(PDF_DIR, exist_ok=True)
        output_path = os.path.join(
            PDF_DIR,
            f"receipt_{rec['receipt_no'].replace('/', '_')}.pdf",
        )

    doc = SimpleDocTemplate(
        output_path, pagesize=A4,
        leftMargin=12*mm, rightMargin=12*mm,
        topMargin=8*mm, bottomMargin=10*mm,
    )
    styles = getSampleStyleSheet()
    elements = []

    # 1. LETTERHEAD
    elements.append(_header_block(company))
    elements.append(Spacer(1, 3*mm))

    # 2. TITLE BAND
    elements.append(_title_band("PAYMENT RECEIPT"))
    elements.append(Spacer(1, 4*mm))

    # 3. TWO-COLUMN INFO: Receipt details (left) + Customer (right)
    left_rows = [
        _info_pair("Receipt No", f"<b>{rec['receipt_no']}</b>"),
        _info_pair("Date", f"<b>{rec['receipt_date']}</b>"),
        _info_pair("Against Invoice", f"<b>{rec['invoice_no'] or 'N/A'}</b>"),
        _info_pair("Payment Mode", f"<b>{rec.get('mode', 'Cash')}</b>"),
    ]
    if rec.get("reference_no"):
        left_rows.append(_info_pair("Reference No", rec["reference_no"]))
    left_tbl = Table(left_rows, colWidths=[30*mm, 58*mm])
    left_tbl.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 1),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 1),
    ]))
    left_wrap = Table([[left_tbl]], colWidths=[88*mm])
    left_wrap.setStyle(TableStyle([
        ("BOX", (0, 0), (-1, -1), 0.4, BORDER),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
    ]))

    cust_lines = [f"<b>{rec['customer_name']}</b>"]
    if rec.get("customer_mobile"):
        cust_lines.append(f"Mobile: {rec['customer_mobile']}")
    cust_text = "<br/>".join(cust_lines)
    right_rows = [
        [Paragraph("<b>Received From</b>",
                    ParagraphStyle("BL", fontName=FONT_NAME, fontSize=9, textColor=GREY)),
         Paragraph(cust_text,
                    ParagraphStyle("BV", fontName=FONT_NAME, fontSize=9, textColor=BLACK))],
    ]
    right_tbl = Table(right_rows, colWidths=[24*mm, 64*mm])
    right_tbl.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 1),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 1),
    ]))
    right_wrap = Table([[right_tbl]], colWidths=[88*mm])
    right_wrap.setStyle(TableStyle([
        ("BOX", (0, 0), (-1, -1), 0.4, BORDER),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
    ]))
    info_table = Table([[left_wrap, right_wrap]], colWidths=[88*mm, 88*mm])
    info_table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
    ]))
    elements.append(info_table)
    elements.append(Spacer(1, 6*mm))

    # 4. AMOUNT BOX (centered, prominent)
    amt_label = Paragraph("<b>Amount Received</b>",
                          ParagraphStyle("AmtLabel", fontName=FONT_NAME, fontSize=12,
                                          alignment=TA_CENTER, textColor=NAVY))
    amt_band = Table([[amt_label]], colWidths=[100*mm])
    amt_band.setStyle(TableStyle([
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("BOX", (0, 0), (-1, -1), 1.5, NAVY),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("BACKGROUND", (0, 0), (-1, -1), LIGHT_NAVY),
    ]))
    amt_wrap = Table([[amt_band]], colWidths=[176*mm])
    amt_wrap.setStyle(TableStyle([("ALIGN", (0, 0), (-1, -1), "CENTER")]))
    elements.append(amt_wrap)
    elements.append(Spacer(1, 2*mm))

    elements.append(Paragraph(
        f"₹ {rec['amount']:,.2f}",
        ParagraphStyle("BigAmt", fontName=FONT_NAME, fontSize=28,
                        alignment=TA_CENTER, textColor=NAVY, spaceBefore=2, spaceAfter=2),
    ))
    words = rec.get("amount_in_words") or _amount_in_words(rec["amount"])
    elements.append(Paragraph(
        f"<i>{words}</i>",
        ParagraphStyle("Words", fontName=FONT_NAME, fontSize=10,
                        alignment=TA_CENTER, textColor=GREY, spaceAfter=6*mm),
    ))

    # 5. NOTES
    if rec.get("notes"):
        nt = Table(
            [[Paragraph("<b>Notes:</b>",
                         ParagraphStyle("NL", fontName=FONT_NAME, fontSize=9, textColor=GREY)),
              Paragraph(rec["notes"],
                         ParagraphStyle("NV", fontName=FONT_NAME, fontSize=9, textColor=BLACK))]],
            colWidths=[24*mm, 138*mm],
        )
        nt.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("BOX", (0, 0), (-1, -1), 0.3, BORDER),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ]))
        elements.append(nt)
        elements.append(Spacer(1, 6*mm))
    else:
        elements.append(Spacer(1, 6*mm))

    # 6. SIGNATURE + THANK YOU
    cname = company.get("name", "S.S. BLUE METAL")
    sig_text = (
        f"Thank you for your payment!<br/><br/><br/>"
        f"For <b>{cname}</b><br/><br/>"
        f"_________________________<br/>"
        f"Authorised Signatory"
    )
    sig_tbl = Table(
        [[Paragraph(sig_text,
                     ParagraphStyle("SV", fontName=FONT_NAME, fontSize=9,
                                     alignment=TA_RIGHT, textColor=BLACK, leading=16))]],
        colWidths=[90*mm],
    )
    sig_tbl.setStyle(TableStyle([
        ("ALIGN", (0, 0), (-1, -1), "RIGHT"),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
    ]))
    elements.append(sig_tbl)
    elements.append(Spacer(1, 4*mm))

    # 7. FOOTER
    elements.append(HRFlowable(width="100%", thickness=0.3, color=BORDER, spaceAfter=2*mm))
    if company.get("footer_line1"):
        elements.append(Paragraph(company["footer_line1"],
                                   ParagraphStyle("F1", fontName=FONT_NAME, fontSize=7,
                                                   alignment=TA_CENTER, textColor=GREY)))
    if company.get("footer_line2"):
        elements.append(Paragraph(company["footer_line2"],
                                   ParagraphStyle("F2", fontName=FONT_NAME, fontSize=7,
                                                   alignment=TA_CENTER, textColor=GREY)))
    elements.append(Paragraph(
        "This is a computer-generated receipt.",
        ParagraphStyle("F3", fontName=FONT_NAME, fontSize=7, alignment=TA_CENTER, textColor=GREY),
    ))

    doc.build(elements)
    return output_path


def open_pdf(filepath: str):
    """Open the PDF with the system default viewer."""
    try:
        if platform.system() == "Windows":
            os.startfile(filepath)
        elif platform.system() == "Darwin":
            subprocess.run(["open", filepath])
        else:
            subprocess.run(["xdg-open", filepath])
    except Exception:
        pass
