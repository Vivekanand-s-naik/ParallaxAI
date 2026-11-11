"""
Shared runtime singleton instances for WebSocketManager, MLBiasDetector, and AIIntegration.
"""

from backend.ai_integration import AIIntegration
from backend.ml_bias_detector import MLBiasDetector
from backend.websocket_manager import WebSocketManager

websocket_manager = WebSocketManager()
ml_bias_detector = MLBiasDetector()
ai_integration = AIIntegration()

