import asyncio
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from typing import List, Dict
from pydantic import BaseModel

ws_router = APIRouter()

class WebSocketManager:
    def __init__(self):
        # topic -> list of connections
        self.active_connections: Dict[str, List[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, topic: str):
        await websocket.accept()
        if topic not in self.active_connections:
            self.active_connections[topic] = []
        self.active_connections[topic].append(websocket)

    def disconnect(self, websocket: WebSocket, topic: str):
        if topic in self.active_connections:
            self.active_connections[topic].remove(websocket)

    async def broadcast(self, topic: str, message: BaseModel):
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
async def websocket_endpoint(websocket: WebSocket, topic: str):
    await manager.connect(websocket, topic)
    try:
        while True:
            # Client doesn't need to send anything, but we keep connection open
            data = await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket, topic)
