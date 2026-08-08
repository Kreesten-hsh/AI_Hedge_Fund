import asyncio
from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect, status
from typing import List, Dict, Optional
from pydantic import BaseModel

from aegis_trade.api.security import ALLOWED_WS_TOPICS, token_is_valid

ws_router = APIRouter()

class WebSocketManager:
    def __init__(self) -> None:
        # topic -> list of connections
        self.active_connections: Dict[str, List[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, topic: str) -> None:
        await websocket.accept()
        if topic not in self.active_connections:
            self.active_connections[topic] = []
        self.active_connections[topic].append(websocket)

    def disconnect(self, websocket: WebSocket, topic: str) -> None:
        connections = self.active_connections.get(topic)
        if connections and websocket in connections:
            connections.remove(websocket)

    async def broadcast(self, topic: str, message: BaseModel) -> None:
        if topic in self.active_connections:
            disconnected = []
            for connection in self.active_connections[topic]:
                try:
                    await connection.send_json({"topic": topic, "data": message.model_dump()})
                except Exception:
                    disconnected.append(connection)

            for conn in disconnected:
                self.disconnect(conn, topic)

manager = WebSocketManager()

@ws_router.websocket("/dashboard/{topic}")
async def websocket_endpoint(
    websocket: WebSocket,
    topic: str,
    token: Optional[str] = Query(default=None),
) -> None:
    """Flux de supervision. Refuse avant `accept()` : un client non autorisé ne
    doit jamais voir l'état du portefeuille, même une fraction de seconde.

    Le jeton passe en paramètre d'URL parce que l'API WebSocket du navigateur
    n'autorise pas d'en-tête personnalisé ; l'API n'écoute que sur la boucle
    locale, l'URL ne traverse donc aucun proxy.
    """
    if topic not in ALLOWED_WS_TOPICS:
        await websocket.close(
            code=status.WS_1008_POLICY_VIOLATION,
            reason=f"Sujet inconnu : {topic}",
        )
        return

    if not token_is_valid(token):
        await websocket.close(
            code=status.WS_1008_POLICY_VIOLATION,
            reason="Jeton local manquant ou invalide.",
        )
        return

    await manager.connect(websocket, topic)
    try:
        while True:
            # Le client n'a rien à envoyer ; la lecture maintient la connexion
            # ouverte et détecte la déconnexion.
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket, topic)
