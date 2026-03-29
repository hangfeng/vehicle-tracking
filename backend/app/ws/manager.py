from fastapi import WebSocket
from collections import defaultdict
import json

class ConnectionManager:
    def __init__(self):
        self.connections: dict[str, list[WebSocket]] = defaultdict(list)

    async def connect(self, factory_id: str, ws: WebSocket):
        await ws.accept()
        self.connections[factory_id].append(ws)

    def disconnect(self, factory_id: str, ws: WebSocket):
        if ws in self.connections[factory_id]:
            self.connections[factory_id].remove(ws)

    async def broadcast(self, factory_id: str, data: dict):
        message = json.dumps(data)
        dead = []
        for ws in self.connections[factory_id]:
            try:
                await ws.send_text(message)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.connections[factory_id].remove(ws)

manager = ConnectionManager()
