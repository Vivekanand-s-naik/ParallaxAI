"""
Authenticated API client for ParallaxAI frontend.
Wraps `requests` to automatically inject the Bearer token from session state.
"""

import streamlit as st
import requests as _requests
from typing import Any, Optional

API_BASE = "http://localhost:8000"
DEFAULT_TIMEOUT = 5


def _headers() -> dict:
    token = st.session_state.get("auth_token", "")
    return {"Authorization": f"Bearer {token}"} if token else {}


def get(path: str, params: Optional[dict] = None, timeout: int = DEFAULT_TIMEOUT) -> _requests.Response:
    return _requests.get(f"{API_BASE}{path}", params=params, headers=_headers(), timeout=timeout)


def post(path: str, json: Any = None, timeout: int = DEFAULT_TIMEOUT) -> _requests.Response:
    return _requests.post(f"{API_BASE}{path}", json=json, headers=_headers(), timeout=timeout)


def put(path: str, json: Any = None, timeout: int = DEFAULT_TIMEOUT) -> _requests.Response:
    return _requests.put(f"{API_BASE}{path}", json=json, headers=_headers(), timeout=timeout)


def delete(path: str, timeout: int = DEFAULT_TIMEOUT) -> _requests.Response:
    return _requests.delete(f"{API_BASE}{path}", headers=_headers(), timeout=timeout)
