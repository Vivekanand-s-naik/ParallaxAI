#!/usr/bin/env python3
"""
ParallaxAI Application Launcher
Starts both FastAPI backend and Streamlit frontend concurrently
"""

import os
import sys
import subprocess
import signal
import time
import threading
import asyncio
from concurrent.futures import ThreadPoolExecutor
import uvicorn
from pathlib import Path

class ParallaxAILauncher:
    def __init__(self):
        self.backend_process = None
        self.frontend_process = None
        self.running = False
        self.shutdown_event = threading.Event()
        
    def check_dependencies(self):
        """Check if required dependencies are available"""
        # Map package names to their import names
        required_packages = {
            'fastapi': 'fastapi',
            'uvicorn': 'uvicorn', 
            'streamlit': 'streamlit',
            'plotly': 'plotly',
            'pandas': 'pandas',
            'requests': 'requests',
            'pydantic': 'pydantic',
            'scikit-learn': 'sklearn',  # scikit-learn imports as sklearn
            'openai': 'openai',
            'anthropic': 'anthropic'
        }
        
        missing_packages = []
        for package_name, import_name in required_packages.items():
            try:
                __import__(import_name)
            except ImportError:
                missing_packages.append(package_name)
        
        if missing_packages:
            print(f"❌ Missing required packages: {', '.join(missing_packages)}")
            print("Please install them using: pip install " + " ".join(missing_packages))
            return False
        
        print("✅ All required packages are available")
        return True
    
    def check_environment(self):
        """Check environment variables and configuration"""
        print("🔍 Checking environment configuration...")
        
        # Check for API keys (optional but recommended)
        openai_key = os.getenv('OPENAI_API_KEY')
        anthropic_key = os.getenv('ANTHROPIC_API_KEY')
        
        if not openai_key:
            print("⚠️  OPENAI_API_KEY not found in environment variables")
            print("   AI analysis features will be limited")
        else:
            print("✅ OpenAI API key found")
        
        if not anthropic_key:
            print("⚠️  ANTHROPIC_API_KEY not found in environment variables")
            print("   AI analysis features will be limited")
        else:
            print("✅ Anthropic API key found")
        
        # Ensure required directories exist
        os.makedirs("ml_models", exist_ok=True)
        os.makedirs(".streamlit", exist_ok=True)
        
        print("✅ Environment check completed")
        return True
    
    def start_backend(self):
        """Start FastAPI backend server"""
        print("🚀 Starting FastAPI backend on port 8000...")
        
        try:
            # Import and run the FastAPI app
            os.chdir(Path(__file__).parent)
            
            # Start uvicorn server programmatically
            config = uvicorn.Config(
                "backend.app:app",
                host="0.0.0.0",
                port=8000,
                reload=False,  # Disable reload in production
                log_level="info",
                access_log=True
            )
            
            server = uvicorn.Server(config)
            
            # Run server in background thread
            def run_server():
                asyncio.run(server.serve())
            
            self.backend_thread = threading.Thread(target=run_server, daemon=True)
            self.backend_thread.start()
            
            # Wait a moment for server to start
            time.sleep(3)
            
            # Check if server is running
            import requests
            try:
                response = requests.get("http://localhost:8000/health", timeout=5)
                if response.status_code == 200:
                    print("✅ FastAPI backend started successfully")
                    return True
                else:
                    print("❌ FastAPI backend health check failed")
                    return False
            except requests.exceptions.RequestException:
                print("❌ FastAPI backend is not responding")
                return False
                
        except Exception as e:
            print(f"❌ Failed to start FastAPI backend: {e}")
            return False
    
    def start_frontend(self):
        """Start Streamlit frontend"""
        print("🎨 Starting Streamlit frontend on port 5000...")
        
        try:
            # Ensure Streamlit config exists
            config_path = Path(".streamlit/config.toml")
            if not config_path.exists():
                print("⚠️  Streamlit config not found, creating default...")
                config_content = """[server]
headless = true
address = "0.0.0.0"
port = 5000

[theme]
primaryColor = "#1f77b4"
backgroundColor = "#ffffff"
secondaryBackgroundColor = "#f0f2f6"
textColor = "#262730"
"""
                with open(config_path, 'w') as f:
                    f.write(config_content)
            
            # Start Streamlit process
            cmd = [
                sys.executable, "-m", "streamlit", "run", "main.py",
                "--server.port", "5000",
                "--server.address", "0.0.0.0",
                "--server.headless", "true"
            ]
            
            self.frontend_process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
                universal_newlines=True
            )
            
            # Wait for Streamlit to start
            print("⏳ Waiting for Streamlit to initialize...")
            time.sleep(5)
            
            # Check if Streamlit is running
            if self.frontend_process.poll() is None:
                print("✅ Streamlit frontend started successfully")
                return True
            else:
                stdout, stderr = self.frontend_process.communicate()
                print(f"❌ Streamlit failed to start:")
                print(f"STDOUT: {stdout}")
                print(f"STDERR: {stderr}")
                return False
                
        except Exception as e:
            print(f"❌ Failed to start Streamlit frontend: {e}")
            return False
    
    def monitor_processes(self):
        """Monitor both processes and restart if needed"""
        print("👁️  Starting process monitor...")
        
        while self.running and not self.shutdown_event.is_set():
            try:
                # Check frontend process
                if self.frontend_process and self.frontend_process.poll() is not None:
                    print("⚠️  Streamlit frontend has stopped")
                    if self.running:
                        print("🔄 Restarting Streamlit frontend...")
                        self.start_frontend()
                
                # Check backend thread
                if hasattr(self, 'backend_thread') and not self.backend_thread.is_alive():
                    print("⚠️  FastAPI backend thread has stopped")
                    if self.running:
                        print("🔄 Restarting FastAPI backend...")
                        self.start_backend()
                
                # Wait before next check
                self.shutdown_event.wait(30)  # Check every 30 seconds
                
            except Exception as e:
                print(f"❌ Error in process monitor: {e}")
                time.sleep(10)
    
    def setup_signal_handlers(self):
        """Setup signal handlers for graceful shutdown"""
        def signal_handler(signum, frame):
            print(f"\n🛑 Received signal {signum}, initiating graceful shutdown...")
            self.shutdown()
            sys.exit(0)
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        if hasattr(signal, 'SIGUSR1'):
            signal.signal(signal.SIGUSR1, signal_handler)
    
    def shutdown(self):
        """Gracefully shutdown both services"""
        print("🛑 Shutting down ParallaxAI...")
        self.running = False
        self.shutdown_event.set()
        
        # Stop frontend process
        if self.frontend_process:
            print("⏹️  Stopping Streamlit frontend...")
            try:
                self.frontend_process.terminate()
                self.frontend_process.wait(timeout=10)
                print("✅ Streamlit frontend stopped")
            except subprocess.TimeoutExpired:
                print("⚠️  Force killing Streamlit frontend...")
                self.frontend_process.kill()
            except Exception as e:
                print(f"❌ Error stopping frontend: {e}")
        
        # Backend will stop when the main thread exits
        print("⏹️  Stopping FastAPI backend...")
        
        print("✅ ParallaxAI shutdown complete")
    
    def run(self):
        """Main run method"""
        print("=" * 60)
        print("🤖 ParallaxAI - Human-AI Co-Governance Platform")
        print("=" * 60)
        
        # Check dependencies and environment
        if not self.check_dependencies():
            sys.exit(1)
        
        if not self.check_environment():
            sys.exit(1)
        
        # Setup signal handlers
        self.setup_signal_handlers()
        
        self.running = True
        
        try:
            # Start backend
            if not self.start_backend():
                print("❌ Failed to start backend, exiting...")
                sys.exit(1)
            
            # Start frontend
            if not self.start_frontend():
                print("❌ Failed to start frontend, exiting...")
                self.shutdown()
                sys.exit(1)
            
            print("=" * 60)
            print("✅ ParallaxAI is now running!")
            print("📊 Dashboard: http://localhost:5000")
            print("🔧 API: http://localhost:8000")
            print("📚 API Docs: http://localhost:8000/docs")
            print("🔗 WebSocket: ws://localhost:8000/ws")
            print("=" * 60)
            print("Press Ctrl+C to stop...")
            
            # Start monitoring in a separate thread
            monitor_thread = threading.Thread(target=self.monitor_processes, daemon=True)
            monitor_thread.start()
            
            # Keep main thread alive
            try:
                while self.running:
                    time.sleep(1)
            except KeyboardInterrupt:
                pass
            
        except Exception as e:
            print(f"❌ Critical error: {e}")
            self.shutdown()
            sys.exit(1)
        finally:
            self.shutdown()

def main():
    """Main entry point"""
    launcher = ParallaxAILauncher()
    launcher.run()

if __name__ == "__main__":
    main()
