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
from app.api.v1.receivables import router as receivables_router
from app.api.v1.ops import router as ops_router
from app.api.v1.hr import router as hr_router
from app.api.v1.gallery import router as gallery_router
from app.api.v1.analytics import router as analytics_router

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
api_router.include_router(receivables_router)
api_router.include_router(ops_router)
api_router.include_router(hr_router)
api_router.include_router(gallery_router)
api_router.include_router(analytics_router)


