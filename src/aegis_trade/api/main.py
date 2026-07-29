import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from typing import Dict, Any

from aegis_trade.api.routers import system, portfolio, orders, positions, risk
from aegis_trade.api.ws.manager import ws_router

app = FastAPI(
    title="Aegis Quant OS - Trading Control Center",
    version="1.0.0",
    description="Local API for the Aegis Dashboard"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Local-First architecture
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(system.router, prefix="/api/system", tags=["System"])
app.include_router(portfolio.router, prefix="/api/portfolio", tags=["Portfolio"])
app.include_router(orders.router, prefix="/api/orders", tags=["Orders"])
app.include_router(positions.router, prefix="/api/positions", tags=["Positions"])
app.include_router(risk.router, prefix="/api/risk", tags=["Risk"])
app.include_router(ws_router, prefix="/ws", tags=["WebSocket"])

@app.get("/")
def read_root() -> Dict[str, Any]:
    return {"status": "Aegis API is running"}

def start():
    """Start the Uvicorn server."""
    uvicorn.run("aegis_trade.api.main:app", host="127.0.0.1", port=8000, reload=True)
