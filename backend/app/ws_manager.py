from typing import Dict
from fastapi import WebSocket


class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}

    async def connect(self, websocket: WebSocket, client_id: str):
        await websocket.accept()
        self.active_connections[client_id] = websocket

    def disconnect(self, client_id: str):
        self.active_connections.pop(client_id, None)

    async def send_personal_message(self, message: str, client_id: str):
        ws = self.active_connections.get(client_id)
        if ws:
            await ws.send_text(message)

    async def broadcast(self, message: str):
        for ws in list(self.active_connections.values()):
            await ws.send_text(message)

manager = ConnectionManager()