from fastapi import APIRouter, Depends, HTTPException

from customer import (
    add_customer,
    delete_customer,
    get_all_customers,
    get_customer,
    search_customers,
    update_customer,
)
from webapp.auth import admin_user, current_user
from webapp.schemas import CustomerIn

router = APIRouter(prefix="/customers", tags=["customers"])


@router.get("")
def list_customers(q: str = "", limit: int = 200, _user: dict = Depends(current_user)):
    rows = search_customers(q.strip()) if q.strip() else get_all_customers()
    return rows[: max(1, min(limit, 500))]


@router.get("/{customer_id}")
def get_one(customer_id: int, _user: dict = Depends(current_user)):
    row = get_customer(customer_id)
    if not row:
        raise HTTPException(status_code=404, detail="Customer not found")
    return row


@router.post("", status_code=201)
def create(payload: CustomerIn, _user: dict = Depends(current_user)):
    return {"id": add_customer(payload.name.strip(), payload.mobile.strip(), payload.address.strip(), payload.gstin.strip())}


@router.put("/{customer_id}")
def update(customer_id: int, payload: CustomerIn, _user: dict = Depends(current_user)):
    if not get_customer(customer_id):
        raise HTTPException(status_code=404, detail="Customer not found")
    update_customer(customer_id, payload.name.strip(), payload.mobile.strip(), payload.address.strip(), payload.gstin.strip())
    return get_customer(customer_id)


@router.delete("/{customer_id}", status_code=204)
def remove(customer_id: int, _user: dict = Depends(admin_user)):
    if not get_customer(customer_id):
        raise HTTPException(status_code=404, detail="Customer not found")
    delete_customer(customer_id)
