import asyncio
import json
import websockets
from datetime import datetime
import streamlit as st
import threading
import time

class WebSocketClient:
    def __init__(self):
        self.websocket = None
        self.connected = False
        self.client_id = None
        self.subscriptions = set()
        self.message_queue = []
        self.connection_thread = None
        self.running = False
        
    async def connect(self, url="ws://localhost:8000/ws"):
        """Connect to WebSocket server"""
        try:
            self.websocket = await websockets.connect(url)
            self.connected = True
            print(f"WebSocket connected to {url}")
            
            # Listen for messages
            await self.listen_for_messages()
            
        except Exception as e:
            print(f"WebSocket connection failed: {e}")
            self.connected = False
            
    async def listen_for_messages(self):
        """Listen for incoming WebSocket messages"""
        try:
            async for message in self.websocket:
                data = json.loads(message)
                await self.handle_message(data)
                
        except websockets.exceptions.ConnectionClosed:
            print("WebSocket connection closed")
            self.connected = False
        except Exception as e:
            print(f"Error listening for messages: {e}")
            self.connected = False
    
    async def handle_message(self, data):
        """Handle incoming WebSocket message"""
        try:
            message_type = data.get("type")
            
            if message_type == "connection_established":
                self.client_id = data.get("client_id")
                print(f"WebSocket client ID: {self.client_id}")
                
            elif message_type == "pong":
                print("Received pong from server")
                
            elif message_type in ["decision_created", "decision_updated", "vote_created", 
                                "governance_rule_created", "governance_rule_updated",
                                "notification_created", "notification_updated"]:
                # Add to message queue for UI updates
                self.message_queue.append({
                    "type": message_type,
                    "data": data.get("data"),
                    "timestamp": datetime.now().isoformat()
                })
                
                # Trigger UI update if connected to Streamlit
                if hasattr(st, 'session_state'):
                    if 'ws_messages' not in st.session_state:
                        st.session_state.ws_messages = []
                    st.session_state.ws_messages.append(data)
                    
            elif message_type == "bias_review_triggered":
                print("Bias review triggered via WebSocket")
                self.message_queue.append({
                    "type": "bias_alert",
                    "data": data.get("data"),
                    "timestamp": datetime.now().isoformat()
                })
                
            else:
                print(f"Unknown message type: {message_type}")
                
        except Exception as e:
            print(f"Error handling WebSocket message: {e}")
    
    async def send_message(self, message):
        """Send message to WebSocket server"""
        if self.websocket and self.connected:
            try:
                await self.websocket.send(json.dumps(message))
            except Exception as e:
                print(f"Error sending WebSocket message: {e}")
                self.connected = False
    
    async def subscribe(self, subscription_type):
        """Subscribe to specific message types"""
        if subscription_type not in self.subscriptions:
            self.subscriptions.add(subscription_type)
            await self.send_message({
                "type": "subscribe",
                "subscription": subscription_type
            })
            print(f"Subscribed to: {subscription_type}")
    
    async def unsubscribe(self, subscription_type):
        """Unsubscribe from specific message types"""
        if subscription_type in self.subscriptions:
            self.subscriptions.remove(subscription_type)
            await self.send_message({
                "type": "unsubscribe",
                "subscription": subscription_type
            })
            print(f"Unsubscribed from: {subscription_type}")
    
    async def ping(self):
        """Send ping to server"""
        await self.send_message({
            "type": "ping",
            "timestamp": datetime.now().isoformat()
        })
    
    async def request_update(self, update_type):
        """Request specific data update"""
        await self.send_message({
            "type": "request_update",
            "update_type": update_type
        })
    
    def start_connection_thread(self):
        """Start WebSocket connection in background thread"""
        if not self.running:
            self.running = True
            self.connection_thread = threading.Thread(target=self._run_connection)
            self.connection_thread.daemon = True
            self.connection_thread.start()
    
    def _run_connection(self):
        """Run WebSocket connection in thread"""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        while self.running:
            try:
                if not self.connected:
                    print("Attempting WebSocket connection...")
                    loop.run_until_complete(self.connect())
                else:
                    # Send periodic ping
                    loop.run_until_complete(self.ping())
                    time.sleep(30)  # Ping every 30 seconds
                    
            except Exception as e:
                print(f"WebSocket connection error: {e}")
                self.connected = False
                time.sleep(5)  # Wait before reconnecting
    
    def stop_connection(self):
        """Stop WebSocket connection"""
        self.running = False
        self.connected = False
        
        if self.websocket:
            asyncio.create_task(self.websocket.close())
        
        if self.connection_thread:
            self.connection_thread.join(timeout=5)
    
    def get_recent_messages(self, limit=10):
        """Get recent messages from queue"""
        return self.message_queue[-limit:] if self.message_queue else []
    
    def clear_message_queue(self):
        """Clear message queue"""
        self.message_queue.clear()
    
    def get_connection_status(self):
        """Get current connection status"""
        return {
            "connected": self.connected,
            "client_id": self.client_id,
            "subscriptions": list(self.subscriptions),
            "message_count": len(self.message_queue),
            "last_message": self.message_queue[-1] if self.message_queue else None
        }

# Streamlit integration functions
def init_websocket_client():
    """Initialize WebSocket client for Streamlit"""
    if 'ws_client' not in st.session_state:
        st.session_state.ws_client = WebSocketClient()
        st.session_state.ws_client.start_connection_thread()
    
    return st.session_state.ws_client

def display_websocket_status():
    """Display WebSocket connection status in Streamlit"""
    if 'ws_client' in st.session_state:
        client = st.session_state.ws_client
        status = client.get_connection_status()
        
        if status['connected']:
            st.success(f"🔗 WebSocket Connected (ID: {status['client_id'][:8]}...)")
            
            # Show recent messages if any
            recent_messages = client.get_recent_messages(3)
            if recent_messages:
                with st.expander("Recent WebSocket Messages"):
                    for msg in recent_messages:
                        st.write(f"**{msg['type']}** - {msg['timestamp']}")
                        if msg.get('data'):
                            st.json(msg['data'])
        else:
            st.warning("🔗 WebSocket Disconnected")
    else:
        st.info("🔗 WebSocket Not Initialized")

def handle_websocket_messages():
    """Handle WebSocket messages for UI updates"""
    if 'ws_client' in st.session_state:
        client = st.session_state.ws_client
        
        # Check for new messages
        if hasattr(st.session_state, 'ws_messages') and st.session_state.ws_messages:
            # Process new messages
            for message in st.session_state.ws_messages:
                message_type = message.get('type')
                
                if message_type in ['decision_created', 'decision_updated']:
                    st.toast("📋 Decision updated!", icon="📋")
                elif message_type == 'vote_created':
                    st.toast("🗳️ New vote cast!", icon="🗳️")
                elif message_type == 'notification_created':
                    st.toast("🔔 New notification!", icon="🔔")
                elif message_type == 'bias_review_triggered':
                    st.toast("🚨 Bias review triggered!", icon="🚨")
            
            # Clear processed messages
            st.session_state.ws_messages = []

def subscribe_to_updates(subscription_types):
    """Subscribe to specific WebSocket updates"""
    if 'ws_client' in st.session_state:
        client = st.session_state.ws_client
        if client.connected:
            for sub_type in subscription_types:
                asyncio.create_task(client.subscribe(sub_type))

def send_websocket_message(message):
    """Send message via WebSocket"""
    if 'ws_client' in st.session_state:
        client = st.session_state.ws_client
        if client.connected:
            asyncio.create_task(client.send_message(message))
            return True
    return False

# Auto-reconnection mechanism
def ensure_websocket_connection():
    """Ensure WebSocket connection is active"""
    if 'ws_client' in st.session_state:
        client = st.session_state.ws_client
        if not client.connected and not client.running:
            client.start_connection_thread()
