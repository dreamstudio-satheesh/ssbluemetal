from fastapi import APIRouter, Depends, HTTPException, Request

from invoice import get_dashboard_data
from settings import get_company, get_db_setting
from webapp.auth import (
    authenticate,
    change_password,
    clear_failures,
    client_ip,
    create_token,
    current_user,
    is_blocked,
    register_failure,
)
from webapp.schemas import LoginIn, PasswordChangeIn, TokenOut, UserOut

router = APIRouter(tags=["meta"])


@router.post("/auth/login", response_model=TokenOut)
def login(payload: LoginIn, request: Request):
    ip = client_ip(request)
    if is_blocked(ip):
        raise HTTPException(status_code=429, detail="Too many failed attempts, try later")
    user = authenticate(payload.username, payload.password)
    if not user:
        register_failure(ip)
        raise HTTPException(status_code=401, detail="Invalid username or password")
    clear_failures(ip)
    token, expires_in = create_token(user)
    return TokenOut(access_token=token, expires_in=expires_in, user=UserOut(**user))


@router.post("/auth/change-password")
def update_password(
    payload: PasswordChangeIn,
    user: dict = Depends(current_user),
):
    if not change_password(user["id"], payload.current_password, payload.new_password):
        raise HTTPException(status_code=400, detail="Current password is incorrect")
    return {"ok": True}


@router.get("/auth/me", response_model=UserOut)
def me(user: dict = Depends(current_user)):
    return UserOut(**user)


@router.get("/dashboard")
def dashboard(_user: dict = Depends(current_user)):
    return get_dashboard_data()


@router.get("/company")
def company(_user: dict = Depends(current_user)):
    data = get_company()
    data["gst_rate"] = 5.0
    data["default_unit"] = get_db_setting("default_unit", "Ton")
    return data
