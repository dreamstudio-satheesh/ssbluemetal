"""Request/response models for the mobile API."""

from datetime import date

from pydantic import BaseModel, Field


class LoginIn(BaseModel):
    username: str = Field(min_length=1)
    password: str = Field(min_length=1)


class PasswordChangeIn(BaseModel):
    current_password: str = Field(min_length=1)
    new_password: str = Field(min_length=8)


class UserOut(BaseModel):
    id: int
    username: str
    full_name: str = ""
    role: str = "user"


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserOut


class CustomerIn(BaseModel):
    name: str = Field(min_length=1)
    mobile: str = ""
    address: str = ""
    gstin: str = ""


class ProductIn(BaseModel):
    name: str = Field(min_length=1)
    unit: str = "Ton"
    rate: float = Field(default=0, ge=0)
    description: str = ""
    hsn_code: str = ""


class InvoiceItemIn(BaseModel):
    product_id: int
    quantity: float = Field(gt=0)
    rate: float | None = Field(default=None, ge=0)


class InvoiceIn(BaseModel):
    customer_id: int
    invoice_date: date | None = None
    items: list[InvoiceItemIn] = Field(min_length=1)
    vehicle_no: str = ""
    driver_name: str = ""
    notes: str = ""
    round_off: bool = False


class InvoiceCreatedOut(BaseModel):
    id: int
    invoice_no: str
    subtotal: float
    cgst_amount: float
    sgst_amount: float
    round_off: float
    grand_total: float
    amount_in_words: str
