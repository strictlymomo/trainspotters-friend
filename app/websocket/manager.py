import json
from typing import Dict, Set
from fastapi import WebSocket


class ConnectionManager:
    def __init__(self):
        # job_id -> set of WebSocket connections
        self.active_connections: Dict[str, Set[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, job_id: str):
        await websocket.accept()
        if job_id not in self.active_connections:
            self.active_connections[job_id] = set()
        self.active_connections[job_id].add(websocket)

    def disconnect(self, websocket: WebSocket, job_id: str):
        if job_id in self.active_connections:
            self.active_connections[job_id].discard(websocket)
            if not self.active_connections[job_id]:
                del self.active_connections[job_id]

    async def send_message(self, job_id: str, message: dict):
        if job_id in self.active_connections:
            message_json = json.dumps(message)
            for connection in self.active_connections[job_id]:
                try:
                    await connection.send_text(message_json)
                except Exception as e:
                    print(f"Error sending message to WebSocket: {e}")

    async def broadcast_progress(
        self,
        job_id: str,
        message_type: str,
        data: dict
    ):
        message = {
            "type": message_type,
            "data": data
        }
        await self.send_message(job_id, message)


# Global instance
manager = ConnectionManager()
