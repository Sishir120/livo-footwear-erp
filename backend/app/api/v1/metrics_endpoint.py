from fastapi import APIRouter, Response
from app.core.metrics import metrics

router = APIRouter(tags=["Metrics & Monitoring"])

@router.get("/metrics")
def get_metrics():
    """
    Exposes Prometheus-compatible metrics in standard plain-text exposition format.
    Supports Prometheus scraping and internal SRE monitoring agents.
    """
    body = metrics.export_prometheus()
    return Response(content=body, media_type="text/plain; version=0.0.4; charset=utf-8")

@router.get("/metrics/json")
def get_metrics_json():
    """Returns metrics as a structured JSON object for dashboards and diagnostics."""
    return metrics.export_json()
