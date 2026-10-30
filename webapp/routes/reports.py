from fastapi import APIRouter, Depends

from reports import (
    daily_sales,
    date_range_sales,
    gstr1_export,
    hsn_summary,
    top_products,
)
from webapp.auth import current_user

router = APIRouter(prefix="/reports", tags=["reports"])


@router.get("/daily")
def daily(date: str = "", _user: dict = Depends(current_user)):
    d = date.strip() or None
    rows = daily_sales(d)
    return {"date": d, "items": rows, "total": round(sum(float(r["grand_total"] or 0) for r in rows), 2)}


@router.get("/range")
def range_report(from_date: str, to_date: str, _user: dict = Depends(current_user)):
    rows = date_range_sales(from_date, to_date)
    return {
        "from": from_date,
        "to": to_date,
        "items": rows,
        "count": sum(int(r["count"] or 0) for r in rows),
        "total": round(sum(float(r["total"] or 0) for r in rows), 2),
    }


@router.get("/top-products")
def best(limit: int = 10, _user: dict = Depends(current_user)):
    return top_products(max(1, min(limit, 100)))


@router.get("/gstr1")
def gstr1(from_date: str, to_date: str, _user: dict = Depends(current_user)):
    return gstr1_export(from_date, to_date)


@router.get("/hsn")
def hsn(from_date: str, to_date: str, _user: dict = Depends(current_user)):
    return hsn_summary(from_date, to_date)
