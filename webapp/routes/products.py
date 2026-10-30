from fastapi import APIRouter, Depends, HTTPException

from product import (
    add_product,
    delete_product,
    get_all_products,
    get_product,
    search_products,
    update_product,
)
from webapp.auth import admin_user, current_user
from webapp.schemas import ProductIn

router = APIRouter(prefix="/products", tags=["products"])


@router.get("")
def list_products(q: str = "", limit: int = 200, _user: dict = Depends(current_user)):
    rows = search_products(q.strip()) if q.strip() else get_all_products()
    return rows[: max(1, min(limit, 500))]


@router.get("/{product_id}")
def get_one(product_id: int, _user: dict = Depends(current_user)):
    row = get_product(product_id)
    if not row:
        raise HTTPException(status_code=404, detail="Product not found")
    return row


@router.post("", status_code=201)
def create(payload: ProductIn, _user: dict = Depends(current_user)):
    return {
        "id": add_product(
            payload.name.strip(),
            payload.unit.strip() or "Ton",
            payload.rate,
            payload.description.strip(),
            payload.hsn_code.strip(),
        )
    }


@router.put("/{product_id}")
def update(product_id: int, payload: ProductIn, _user: dict = Depends(current_user)):
    if not get_product(product_id):
        raise HTTPException(status_code=404, detail="Product not found")
    update_product(
        product_id,
        payload.name.strip(),
        payload.unit.strip() or "Ton",
        payload.rate,
        payload.description.strip(),
        payload.hsn_code.strip(),
    )
    return get_product(product_id)


@router.delete("/{product_id}", status_code=204)
def remove(product_id: int, _user: dict = Depends(admin_user)):
    if not get_product(product_id):
        raise HTTPException(status_code=404, detail="Product not found")
    delete_product(product_id)
