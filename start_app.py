#!/usr/bin/env python3
"""
ParallaxAI Application Launcher
Starts FastAPI backend on port 8000 and Streamlit frontend on port 5000
"""

import os
import sys
import subprocess
import signal
import time
import threading
import asyncio
from pathlib import Path
import uvicorn


class ParallaxAILauncher:
    def __init__(self):
        self.frontend_process = None
        self.running = False
        self.shutdown_event = threading.Event()

    def check_dependencies(self):
        """Check if required dependencies are available."""
        required = {
            'fastapi': 'fastapi',
            'uvicorn': 'uvicorn',
            'streamlit': 'streamlit',
            'plotly': 'plotly',
            'pandas': 'pandas',
            'requests': 'requests',
            'pydantic': 'pydantic',
            'scikit-learn': 'sklearn',
            'openai': 'openai',
            'anthropic': 'anthropic',
        }
        missing = []
        for pkg, imp in required.items():
            try:
                __import__(imp)
            except ImportError:
                missing.append(pkg)

        if missing:
            print(f"❌ Missing packages: {', '.join(missing)}")
            return False
        print("✅ All required packages are available")
        return True

    def check_environment(self):
        """Check environment variables and configuration."""
        print("🔍 Checking environment configuration...")
        for key in ('OPENAI_API_KEY', 'ANTHROPIC_API_KEY', 'SESSION_SECRET'):
            val = os.getenv(key)
            if val:
                print(f"✅ {key} found")
            else:
                print(f"⚠️  {key} not set — some features may be limited")

        os.makedirs("ml_models", exist_ok=True)
        os.makedirs(".streamlit", exist_ok=True)
        print("✅ Environment check completed")
        return True

    def start_backend(self):
        """Start FastAPI backend on port 8000."""
        print("🚀 Starting FastAPI backend on port 8000...")
        try:
            os.chdir(Path(__file__).parent)

            config = uvicorn.Config(
                "backend.app:app",
                host="0.0.0.0",
                port=8000,
                reload=False,
                log_level="info",
                access_log=True,
            )
            server = uvicorn.Server(config)

            def run_server():
                asyncio.run(server.serve())

            self.backend_thread = threading.Thread(target=run_server, daemon=True)
            self.backend_thread.start()

            # Wait for server to be ready
            import requests as req
            for attempt in range(15):
                time.sleep(1)
                try:
                    r = req.get("http://localhost:8000/health", timeout=2)
                    if r.status_code == 200:
                        print("✅ FastAPI backend started successfully")
                        return True
                except Exception:
                    pass
                print(f"   Waiting… ({attempt + 1}/15)")

            print("❌ FastAPI backend did not become healthy in time")
            return False

        except Exception as e:
            print(f"❌ Failed to start FastAPI backend: {e}")
            return False

    def start_frontend(self):
        """Start Streamlit frontend on port 5000."""
        print("🎨 Starting Streamlit frontend on port 5000...")
        try:
            cmd = [
                sys.executable, "-m", "streamlit", "run", "main.py",
                "--server.port", "5000",
                "--server.address", "0.0.0.0",
                "--server.headless", "true",
                "--server.enableCORS", "false",
                "--server.enableWebsocketCompression", "false",
            ]

            self.frontend_process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                universal_newlines=True,
            )

            print("⏳ Waiting for Streamlit to initialise…")
            for attempt in range(20):
                time.sleep(1)
                if self.frontend_process.poll() is not None:
                    out, _ = self.frontend_process.communicate()
                    print(f"❌ Streamlit exited early:\n{out}")
                    return False
                try:
                    import requests as req
                    r = req.get("http://localhost:5000", timeout=2)
                    if r.status_code < 500:
                        print("✅ Streamlit frontend started successfully")
                        return True
                except Exception:
                    pass
                print(f"   Waiting… ({attempt + 1}/20)")

            if self.frontend_process.poll() is None:
                print("✅ Streamlit frontend process running (health check timed out but process is alive)")
                return True

            print("❌ Streamlit failed to start")
            return False

        except Exception as e:
            print(f"❌ Failed to start Streamlit frontend: {e}")
            return False

    def monitor_processes(self):
        """Restart services if they crash."""
        print("👁️  Starting process monitor…")
        while self.running and not self.shutdown_event.is_set():
            try:
                if self.frontend_process and self.frontend_process.poll() is not None:
                    print("⚠️  Streamlit frontend has stopped — restarting…")
                    self.start_frontend()

                if hasattr(self, 'backend_thread') and not self.backend_thread.is_alive():
                    print("⚠️  FastAPI backend thread has stopped — restarting…")
                    self.start_backend()

                self.shutdown_event.wait(30)
            except Exception as e:
                print(f"❌ Monitor error: {e}")
                time.sleep(10)

    def setup_signal_handlers(self):
        def handler(signum, frame):
            print(f"\n🛑 Received signal {signum} — shutting down…")
            self.shutdown()
            sys.exit(0)

        signal.signal(signal.SIGINT, handler)
        signal.signal(signal.SIGTERM, handler)

    def shutdown(self):
        print("🛑 Shutting down ParallaxAI…")
        self.running = False
        self.shutdown_event.set()
        if self.frontend_process:
            try:
                self.frontend_process.terminate()
                self.frontend_process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                self.frontend_process.kill()
            except Exception:
                pass
        print("✅ Shutdown complete")

    def run(self):
        print("=" * 60)
        print("🤖 ParallaxAI - Human-AI Co-Governance Platform")
        print("=" * 60)

        if not self.check_dependencies():
            sys.exit(1)

        if not self.check_environment():
            sys.exit(1)

        self.setup_signal_handlers()
        self.running = True

        try:
            if not self.start_backend():
                print("❌ Failed to start backend — exiting")
                sys.exit(1)

            if not self.start_frontend():
                print("❌ Failed to start frontend — exiting")
                self.shutdown()
                sys.exit(1)

            print("=" * 60)
            print("✅ ParallaxAI is now running!")
            print("📊 Dashboard:  http://localhost:5000")
            print("🔧 API:        http://localhost:8000")
            print("📚 API Docs:   http://localhost:8000/docs")
            print("🔗 WebSocket:  ws://localhost:8000/ws")
            print("=" * 60)
            print("Press Ctrl+C to stop…")

            monitor = threading.Thread(target=self.monitor_processes, daemon=True)
            monitor.start()

            while self.running:
                time.sleep(1)

        except KeyboardInterrupt:
            pass
        except Exception as e:
            print(f"❌ Critical error: {e}")
        finally:
            self.shutdown()


if __name__ == "__main__":
    ParallaxAILauncher().run()
