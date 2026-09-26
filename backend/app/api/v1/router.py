from fastapi import APIRouter
from app.api.v1.auth import router as auth_router
from app.api.v1.health import router as health_router
from app.api.v1.purchase import router as purchase_router
from app.api.v1.production import router as production_router
from app.api.v1.stock import router as stock_router
from app.api.v1.sales import router as sales_router
from app.api.v1.invoices import router as invoice_router
from app.api.v1.reports import router as reports_router
from app.api.v1.backup import router as backup_router
# NOTE: Tally Prime router removed from Phase 1 — not client-requested, not in scope.
# Archived at: backend/_unscoped/tally-export/tally.py
# May be pitched to client as a paid add-on in a later phase.

api_router = APIRouter()
api_router.include_router(health_router)
api_router.include_router(auth_router)
api_router.include_router(purchase_router)
api_router.include_router(production_router)
api_router.include_router(stock_router)
api_router.include_router(sales_router)
api_router.include_router(invoice_router)
api_router.include_router(reports_router)
api_router.include_router(backup_router)

