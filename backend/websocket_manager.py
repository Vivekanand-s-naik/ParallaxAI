import json
import asyncio
from typing import Any, Dict, List, Optional, Set
from datetime import datetime
from fastapi import WebSocket
import uuid


class WebSocketManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.client_subscriptions: Dict[str, Set[str]] = {}
        self.client_metadata: Dict[str, Dict[str, Any]] = {}
        self.total_messages_sent: int = 0

    async def connect(
        self, websocket: WebSocket, metadata: Optional[Dict[str, Any]] = None
    ):
        await websocket.accept()
        client_id = str(uuid.uuid4())
        self.active_connections[client_id] = websocket
        self.client_subscriptions[client_id] = set()
        self.client_metadata[client_id] = metadata or {}

        # Send welcome message
        await self.send_personal_message(
            {
                "type": "connection_established",
                "client_id": client_id,
                "authenticated": bool((metadata or {}).get("authenticated", False)),
                "timestamp": datetime.now().isoformat(),
            },
            websocket,
        )

    def disconnect(self, websocket: WebSocket):
        client_id = None
        for cid, ws in self.active_connections.items():
            if ws == websocket:
                client_id = cid
                break

        if client_id:
            del self.active_connections[client_id]
            self.client_subscriptions.pop(client_id, None)
            self.client_metadata.pop(client_id, None)

    async def send_personal_message(self, message: dict, websocket: WebSocket):
        try:
            await websocket.send_text(json.dumps(message))
            self.total_messages_sent += 1
        except Exception as e:
            print(f"Error sending personal message: {e}")

    async def broadcast(self, message: dict):
        if not self.active_connections:
            return

        message["timestamp"] = datetime.now().isoformat()
        disconnected_clients = []

        for client_id, websocket in self.active_connections.items():
            try:
                await websocket.send_text(json.dumps(message))
                self.total_messages_sent += 1
            except Exception as e:
                print(f"Error broadcasting to client {client_id}: {e}")
                disconnected_clients.append(client_id)

        # Clean up disconnected clients
        for client_id in disconnected_clients:
            self.active_connections.pop(client_id, None)
            self.client_subscriptions.pop(client_id, None)
            self.client_metadata.pop(client_id, None)

    async def broadcast_to_subscribed(self, message: dict, subscription_type: str):
        if not self.active_connections:
            return

        message["timestamp"] = datetime.now().isoformat()
        disconnected_clients = []

        for client_id, websocket in self.active_connections.items():
            if subscription_type in self.client_subscriptions.get(client_id, set()):
                try:
                    await websocket.send_text(json.dumps(message))
                    self.total_messages_sent += 1
                except Exception as e:
                    print(f"Error broadcasting to subscribed client {client_id}: {e}")
                    disconnected_clients.append(client_id)

        # Clean up disconnected clients
        for client_id in disconnected_clients:
            self.active_connections.pop(client_id, None)
            self.client_subscriptions.pop(client_id, None)
            self.client_metadata.pop(client_id, None)

    async def handle_message(self, websocket: WebSocket, message: dict):
        """Handle incoming WebSocket messages from clients"""
        try:
            msg_type = message.get("type")
            client_id = self.get_client_id(websocket)

            if msg_type == "subscribe":
                subscription = message.get("subscription")
                if client_id and subscription:
                    self.client_subscriptions[client_id].add(subscription)
                    await self.send_personal_message(
                        {
                            "type": "subscription_confirmed",
                            "subscription": subscription,
                        },
                        websocket,
                    )

            elif msg_type == "unsubscribe":
                subscription = message.get("subscription")
                if client_id and subscription:
                    self.client_subscriptions[client_id].discard(subscription)
                    await self.send_personal_message(
                        {
                            "type": "subscription_removed",
                            "subscription": subscription,
                        },
                        websocket,
                    )

            elif msg_type == "ping":
                await self.send_personal_message(
                    {"type": "pong", "timestamp": datetime.now().isoformat()},
                    websocket,
                )

            elif msg_type == "request_update":
                update_type = message.get("update_type")
                if update_type == "dashboard":
                    await self.send_dashboard_update(websocket)
                elif update_type == "notifications":
                    await self.send_notifications_update(websocket)
                elif update_type == "decisions":
                    await self.send_decisions_update(websocket)

        except Exception as e:
            print(f"Error handling WebSocket message: {e}")
            await self.send_personal_message(
                {"type": "error", "message": "Error processing message"}, websocket
            )

    def get_client_id(self, websocket: WebSocket) -> Optional[str]:
        """Get client ID for a given websocket"""
        for client_id, ws in self.active_connections.items():
            if ws == websocket:
                return client_id
        return None

    async def send_dashboard_update(self, websocket: WebSocket):
        await self.send_personal_message(
            {
                "type": "dashboard_update",
                "data": {
                    "timestamp": datetime.now().isoformat(),
                    "metrics_updated": True,
                },
            },
            websocket,
        )

    async def send_notifications_update(self, websocket: WebSocket):
        await self.send_personal_message(
            {
                "type": "notifications_update",
                "data": {
                    "timestamp": datetime.now().isoformat(),
                    "new_notifications": True,
                },
            },
            websocket,
        )

    async def send_decisions_update(self, websocket: WebSocket):
        await self.send_personal_message(
            {
                "type": "decisions_update",
                "data": {
                    "timestamp": datetime.now().isoformat(),
                    "decisions_updated": True,
                },
            },
            websocket,
        )

    def get_connection_stats(self) -> dict:
        """Get current connection statistics"""
        return {
            "active_connections": len(self.active_connections),
            "total_connections": len(self.active_connections),
            "total_subscriptions": sum(
                len(subs) for subs in self.client_subscriptions.values()
            ),
            "total_messages_sent": self.total_messages_sent,
            "timestamp": datetime.now().isoformat(),
        }
