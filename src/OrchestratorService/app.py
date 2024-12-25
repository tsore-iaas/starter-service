from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from pydantic import BaseModel
from typing import List

app = FastAPI()

# Modèle pour les notifications
class Notification(BaseModel):
    pc_id: str
    vm_id: str
    message: str

# Gestion des WebSocket clients
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def send_message(self, message: str):
        for connection in self.active_connections:
            await connection.send_text(message)

manager = ConnectionManager()

@app.post("/notify")
async def notify_clients(notification: Notification):
    """
    Reçoit une notification du service Load Balancing et informe les clients connectés.
    """
    message = f"[Notification] VM {notification.vm_id} allocated to PC {notification.pc_id}"
    await manager.send_message(message)
    return {"message": "Notification sent to clients"}

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint pour les clients.
    """
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            print(f"Received message from client: {data}")
    except WebSocketDisconnect:
        manager.disconnect(websocket)
