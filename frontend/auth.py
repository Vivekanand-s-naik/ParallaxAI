"""
Authentication frontend for ParallaxAI Streamlit app
"""

import streamlit as st
import requests
import hashlib
import time

API_BASE = "http://localhost:8000"


def show_login_page():
    """Render the login form and return True if the user authenticated successfully."""

    # --- Page styling ---
    st.markdown("""
    <style>
    .login-box {
        max-width: 420px;
        margin: 0 auto;
        padding: 2.5rem;
        border-radius: 12px;
        box-shadow: 0 4px 24px rgba(0,0,0,0.10);
        background: #fff;
    }
    .login-header {
        text-align: center;
        margin-bottom: 1.5rem;
    }
    .login-header h1 {
        font-size: 2rem;
        margin-bottom: 0.25rem;
    }
    .login-header p {
        color: #6c757d;
        font-size: 0.95rem;
    }
    .demo-creds {
        background: #f0f4ff;
        border: 1px solid #b8c8ff;
        border-radius: 8px;
        padding: 0.75rem 1rem;
        margin-top: 1.25rem;
        font-size: 0.85rem;
    }
    </style>
    """, unsafe_allow_html=True)

    # Centre the form
    _, centre, _ = st.columns([1, 2, 1])

    with centre:
        st.markdown("""
        <div class="login-header">
            <h1>🤖 ParallaxAI</h1>
            <p>Human-AI Co-Governance Platform</p>
        </div>
        """, unsafe_allow_html=True)

        with st.form("login_form", clear_on_submit=False):
            st.markdown("### 🔐 Sign In")
            username = st.text_input("Username", placeholder="Enter username")
            password = st.text_input("Password", type="password", placeholder="Enter password")
            submitted = st.form_submit_button("Sign In", type="primary", use_container_width=True)

            if submitted:
                if not username or not password:
                    st.error("Please enter both username and password.")
                else:
                    with st.spinner("Authenticating…"):
                        success = _do_login(username.strip(), password)
                    if success:
                        st.success("Login successful! Redirecting…")
                        time.sleep(0.4)
                        st.rerun()
                    else:
                        st.error("❌ Invalid username or password.")

        # Demo credentials hint
        st.markdown("""
        <div class="demo-creds">
            <strong>Demo accounts</strong><br>
            👑 <code>admin</code> / <code>admin123</code> &nbsp;·&nbsp; Full access<br>
            📊 <code>analyst</code> / <code>analyst123</code> &nbsp;·&nbsp; Read + analyse<br>
            👁️ <code>reviewer</code> / <code>reviewer123</code> &nbsp;·&nbsp; Review only
        </div>
        """, unsafe_allow_html=True)


def _do_login(username: str, password: str) -> bool:
    """Call the backend auth endpoint and store the token in session_state."""
    try:
        resp = requests.post(
            f"{API_BASE}/api/auth/login",
            json={"username": username, "password": password},
            timeout=5,
        )
        if resp.status_code == 200:
            data = resp.json()
            st.session_state["auth_token"] = data["token"]
            st.session_state["auth_user"] = data["user"]
            st.session_state["auth_role"] = data["user"]["role"]
            return True
        return False
    except Exception as e:
        st.error(f"Auth service error: {e}")
        return False


def is_authenticated() -> bool:
    """Return True if a valid session is active."""
    return bool(st.session_state.get("auth_token"))


def get_auth_headers() -> dict:
    """Return Authorization header dict for requests."""
    token = st.session_state.get("auth_token", "")
    return {"Authorization": f"Bearer {token}"} if token else {}


def get_current_user() -> dict:
    """Return the current user info dict."""
    return st.session_state.get("auth_user", {})


def get_role() -> str:
    return st.session_state.get("auth_role", "")


def is_admin() -> bool:
    return get_role() == "admin"


def logout():
    """Clear auth state."""
    for key in ["auth_token", "auth_user", "auth_role"]:
        st.session_state.pop(key, None)
    st.rerun()


def render_user_info():
    """Render the logged-in user badge + logout button in the sidebar."""
    user = get_current_user()
    role = get_role()

    role_badge = {
        "admin": "👑 Admin",
        "analyst": "📊 Analyst",
        "reviewer": "👁️ Reviewer",
    }.get(role, role)

    st.sidebar.markdown(f"""
    <div style="background:#f0f4ff;border-radius:8px;padding:0.6rem 0.8rem;margin-bottom:0.5rem;">
        <strong>{user.get('full_name', user.get('username', ''))}</strong><br>
        <span style="font-size:0.82rem;color:#555;">{role_badge}</span>
    </div>
    """, unsafe_allow_html=True)

    if st.sidebar.button("🚪 Logout", use_container_width=True):
        logout()
