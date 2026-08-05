import streamlit as st
import time
from datetime import datetime

# Page configuration — must be the very first Streamlit call
st.set_page_config(
    page_title="ParallaxAI - Human-AI Co-Governance Platform",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Auth gate — import before anything that renders UI
from frontend.auth import is_authenticated, show_login_page, render_user_info, get_auth_headers, is_admin

if not is_authenticated():
    show_login_page()
    st.stop()

# --- Now we know the user is authenticated ---

from frontend import dashboard, voting, influence_graph, bias_scanner, governance, audit_log, notifications

# Custom CSS
st.markdown("""
<style>
.metric-card {
    background: white;
    padding: 1rem;
    border-radius: 0.5rem;
    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    margin: 0.5rem 0;
}
.status-approved { background-color: #28a745; }
.status-rejected { background-color: #dc3545; }
.status-review   { background-color: #ffc107; }
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


# ──────────────────────────────────────────
# Backend init (embedded)
# ──────────────────────────────────────────

@st.cache_resource
def init_backend_components():
    try:
        from backend.data_store import DataStore
        from backend.ml_bias_detector import MLBiasDetector
        from backend.ai_integration import AIIntegration

        data_store = DataStore()
        data_store.initialize_sample_data()
        ml_bias_detector = MLBiasDetector()
        ai_integration = AIIntegration()

        return {
            'data_store': data_store,
            'ml_bias_detector': ml_bias_detector,
            'ai_integration': ai_integration,
            'status': 'connected',
        }
    except Exception as e:
        return {'status': 'disconnected', 'error': str(e)}


def check_api_connection() -> bool:
    import requests
    try:
        r = requests.get("http://localhost:8000/health", timeout=3)
        return r.status_code == 200
    except Exception:
        return False


# ──────────────────────────────────────────
# Sidebar
# ──────────────────────────────────────────

st.sidebar.title("🤖 ParallaxAI")
st.sidebar.markdown("---")

# User info + logout
render_user_info()
st.sidebar.markdown("---")

# API status
api_ok = check_api_connection()
st.sidebar.markdown(
    f"**API:** {'🟢 Online' if api_ok else '🔴 Offline'}"
)

# Navigation
pages = {
    "📊 Dashboard":          "dashboard",
    "🗳️ Multi-Agent Voting": "voting",
    "🕸️ Influence Graph":   "influence_graph",
    "🛡️ Bias Scanner":      "bias_scanner",
    "⚙️ Governance Console": "governance",
    "📋 Audit Log":          "audit_log",
    "🔔 Notifications":      "notifications",
}

selected_page = st.sidebar.selectbox("Navigate to:", list(pages.keys()))
page_key = pages[selected_page]

st.sidebar.markdown("---")

# Real-time refresh toggle
real_time = st.sidebar.checkbox("Real-time Updates", value=True)

if real_time:
    st.sidebar.success("🔄 Live updates enabled")
    refresh_interval = st.sidebar.slider("Refresh (seconds)", 5, 30, 10)
    if 'last_refresh' not in st.session_state:
        st.session_state.last_refresh = time.time()
    if time.time() - st.session_state.last_refresh > refresh_interval:
        st.session_state.last_refresh = time.time()
        st.rerun()
else:
    st.sidebar.info("⏸️ Live updates paused")

st.sidebar.markdown("---")
st.sidebar.markdown("**System Info**")
st.sidebar.text(f"Updated: {datetime.now().strftime('%H:%M:%S')}")

# ──────────────────────────────────────────
# Main content area
# ──────────────────────────────────────────

if not api_ok:
    st.error("⚠️ Backend API is not responding. Please wait or restart the application.")
    st.info("The FastAPI backend should be running on port 8000.")
    st.stop()

# Route to the selected page
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
