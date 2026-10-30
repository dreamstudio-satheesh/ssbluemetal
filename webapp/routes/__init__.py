from fastapi import APIRouter

from webapp.routes import customers, invoices, meta, products, reports

api = APIRouter(prefix="/api")
api.include_router(meta.router)
api.include_router(customers.router)
api.include_router(products.router)
api.include_router(invoices.router)
api.include_router(reports.router)
