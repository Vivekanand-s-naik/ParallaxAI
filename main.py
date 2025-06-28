import streamlit as st
import asyncio
import json
import time
from datetime import datetime
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import requests
from frontend.websocket_client import WebSocketClient
from frontend import dashboard, voting, influence_graph, bias_scanner, governance, audit_log, notifications

# Initialize WebSocket client
if 'ws_client' not in st.session_state:
    st.session_state.ws_client = WebSocketClient()

# Initialize connection status
if 'api_connected' not in st.session_state:
    st.session_state.api_connected = False

# Page configuration
st.set_page_config(
    page_title="ParallaxAI - Human-AI Co-Governance Platform",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for professional styling
st.markdown("""
<style>
.metric-card {
    background: white;
    padding: 1rem;
    border-radius: 0.5rem;
    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    margin: 0.5rem 0;
}

.status-indicator {
    display: inline-block;
    width: 10px;
    height: 10px;
    border-radius: 50%;
    margin-right: 8px;
}

.status-approved { background-color: #28a745; }
.status-rejected { background-color: #dc3545; }
.status-review { background-color: #ffc107; }

.notification-badge {
    background-color: #dc3545;
    color: white;
    border-radius: 50%;
    padding: 2px 6px;
    font-size: 12px;
    margin-left: 5px;
}

.agent-card {
    border: 1px solid #ddd;
    border-radius: 8px;
    padding: 10px;
    margin: 5px;
    background: #f8f9fa;
}

.bias-alert {
    background-color: #fff3cd;
    border: 1px solid #ffeaa7;
    border-radius: 4px;
    padding: 10px;
    margin: 5px 0;
}
</style>
""", unsafe_allow_html=True)

# Check API connection
def check_api_connection():
    try:
        response = requests.get("http://localhost:8000/health", timeout=2)
        return response.status_code == 200
    except:
        return False

# Sidebar navigation
st.sidebar.title("🤖 ParallaxAI")
st.sidebar.markdown("---")

# Connection status
api_status = check_api_connection()
status_color = "🟢" if api_status else "🔴"
status_text = "Connected" if api_status else "Disconnected"
st.sidebar.markdown(f"**API Status:** {status_color} {status_text}")

# Navigation
pages = {
    "📊 Dashboard": "dashboard",
    "🗳️ Multi-Agent Voting": "voting", 
    "🕸️ Influence Graph": "influence_graph",
    "🛡️ Bias Scanner": "bias_scanner",
    "⚙️ Governance Console": "governance",
    "📋 Audit Log": "audit_log",
    "🔔 Notifications": "notifications"
}

selected_page = st.sidebar.selectbox("Navigate to:", list(pages.keys()))
page_key = pages[selected_page]

st.sidebar.markdown("---")

# Real-time updates toggle
real_time_updates = st.sidebar.checkbox("Real-time Updates", value=True)

if real_time_updates:
    st.sidebar.success("🔄 Live updates enabled")
else:
    st.sidebar.info("⏸️ Live updates paused")

# Auto-refresh interval
if real_time_updates:
    refresh_interval = st.sidebar.slider("Refresh Interval (seconds)", 1, 10, 3)
    
    # Auto-refresh mechanism
    if 'last_refresh' not in st.session_state:
        st.session_state.last_refresh = time.time()
    
    if time.time() - st.session_state.last_refresh > refresh_interval:
        st.session_state.last_refresh = time.time()
        st.rerun()

st.sidebar.markdown("---")
st.sidebar.markdown("**System Info**")
st.sidebar.text(f"Last Updated: {datetime.now().strftime('%H:%M:%S')}")

# Main content area
if not api_status:
    st.error("⚠️ Backend API is not available. Please ensure the FastAPI server is running on port 8000.")
    st.info("To start the backend, run: `python start_app.py`")
    st.stop()

# Route to appropriate page
if page_key == "dashboard":
    dashboard.show_dashboard()
elif page_key == "voting":
    voting.show_voting()
elif page_key == "influence_graph":
    influence_graph.show_influence_graph()
elif page_key == "bias_scanner":
    bias_scanner.show_bias_scanner()
elif page_key == "governance":
    governance.show_governance()
elif page_key == "audit_log":
    audit_log.show_audit_log()
elif page_key == "notifications":
    notifications.show_notifications()

# WebSocket status in footer
if st.session_state.ws_client.connected:
    st.sidebar.success("🔗 WebSocket Connected")
else:
    st.sidebar.warning("🔗 WebSocket Disconnected")
