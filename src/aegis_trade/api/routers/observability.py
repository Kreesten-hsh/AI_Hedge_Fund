from fastapi import APIRouter
from fastapi.responses import PlainTextResponse
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST, Counter, Gauge

router = APIRouter()

# Setup some basic metrics
HTTP_REQUESTS_TOTAL = Counter('http_requests_total', 'Total HTTP Requests', ['method', 'endpoint'])
SYSTEM_CPU_USAGE = Gauge('system_cpu_usage_percent', 'Current CPU usage percent')
PORTFOLIO_EQUITY = Gauge('aegis_portfolio_equity', 'Current portfolio equity')

@router.get("/metrics")
def get_metrics():
    """
    Exposes Prometheus-compatible metrics.
    """
    # Note: In a real system we'd pull from MonitoringEngine here before generating
    return PlainTextResponse(generate_latest(), media_type=CONTENT_TYPE_LATEST)

@router.get("/health/live")
def liveness_probe():
    return {"status": "alive"}

@router.get("/health/ready")
def readiness_probe():
    # Example logic: check if EventBus and DB are up
    return {"status": "ready"}
