---
name: ParallaxAI port configuration
description: Which ports each service must use — root cause of the WebSocket errors
---

## Correct port mapping
- Streamlit frontend: **port 5000** (Replit external port 5000 → internal 5000)
- FastAPI backend: **port 8000** (Replit external port 80 → internal 8000)
- Old Streamlit port 8501 was exposed on external 3000 but the default preview was port 5000

## Root cause of "Client Error: WebSocket onerror" flood
Streamlit was configured to run on 8501 (both in .streamlit/config.toml and start_app.py), but Replit's preview iframe pointed at port 5000. Streamlit's own WebSocket handshake failed because no Streamlit server was listening there.

**Fix applied:** .streamlit/config.toml → port = 5000; start_app.py → "--server.port", "5000"

**Why:** Always check that the Replit external port 5000 maps to whatever port the primary app actually listens on.
