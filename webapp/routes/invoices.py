import os

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse

from invoice import cancel_invoice, delete_invoice, get_invoice, get_invoice_items, search_invoices
from printer import generate_invoice_pdf
from webapp.auth import admin_user, current_user
from webapp.schemas import InvoiceCreatedOut, InvoiceIn
from webapp.services import InvalidInvoice, create_invoice_from_payload

PDF_DIR = os.environ.get("PDF_OUTPUT_DIR") or os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "pdf_output",
)

router = APIRouter(prefix="/invoices", tags=["invoices"])


@router.get("")
def list_invoices(
    q: str = "",
    date_from: str = "",
    date_to: str = "",
    status: str = "active",
    page: int = 1,
    page_size: int = 25,
    _user: dict = Depends(current_user),
):
    page = max(page, 1)
    page_size = max(1, min(page_size, 100))
    rows, total = search_invoices(
        query=q.strip(),
        date_from=date_from.strip(),
        date_to=date_to.strip(),
        status=status,
        page=page,
        page_size=page_size,
    )
    return {"items": rows, "total": total, "page": page, "page_size": page_size}


@router.post("", response_model=InvoiceCreatedOut, status_code=201)
def create(payload: InvoiceIn, _user: dict = Depends(current_user)):
    try:
        return create_invoice_from_payload(payload)
    except InvalidInvoice as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("/{invoice_id}")
def get_one(invoice_id: int, _user: dict = Depends(current_user)):
    invoice = get_invoice(invoice_id)
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    invoice["items"] = get_invoice_items(invoice_id)
    return invoice


@router.get("/{invoice_id}/pdf")
def pdf(invoice_id: int, _user: dict = Depends(current_user)):
    invoice = get_invoice(invoice_id)
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    os.makedirs(PDF_DIR, exist_ok=True)
    safe_no = invoice["invoice_no"].replace("/", "-")
    path = os.path.join(PDF_DIR, f"{safe_no}.pdf")
    generate_invoice_pdf(invoice_id, output_path=path)
    return FileResponse(path, media_type="application/pdf", filename=f"{safe_no}.pdf")


@router.post("/{invoice_id}/cancel")
def cancel(invoice_id: int, _user: dict = Depends(admin_user)):
    if not get_invoice(invoice_id):
        raise HTTPException(status_code=404, detail="Invoice not found")
    cancel_invoice(invoice_id)
    return {"id": invoice_id, "status": "cancelled"}


@router.delete("/{invoice_id}", status_code=204)
def remove(invoice_id: int, _user: dict = Depends(admin_user)):
    if not get_invoice(invoice_id):
        raise HTTPException(status_code=404, detail="Invoice not found")
    delete_invoice(invoice_id)
