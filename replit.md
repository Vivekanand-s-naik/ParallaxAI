# ParallaxAI - Human-AI Co-Governance Platform

## Overview

ParallaxAI is a comprehensive Human-AI Co-Governance Platform that facilitates collaborative decision-making between AI agents and human operators. The system provides real-time monitoring, bias detection, voting mechanisms, and governance controls to ensure fair and transparent automated decision-making processes.

The platform consists of a FastAPI backend serving RESTful APIs and WebSocket connections, paired with a Streamlit frontend providing interactive dashboards and management interfaces.

## System Architecture

### Backend Architecture
- **Framework**: FastAPI with Python 3.11+ and async/await support
- **API Design**: RESTful endpoints with CORS middleware for cross-origin requests
- **WebSocket Support**: Real-time bidirectional communication for live updates
- **Data Models**: Pydantic-based models for type safety and validation
- **AI Integration**: Multi-provider AI support (OpenAI GPT-4o, Anthropic Claude-4)
- **ML Components**: Scikit-learn based bias detection and anomaly detection

### Frontend Architecture
- **Framework**: Streamlit with custom CSS styling
- **Visualization**: Plotly for interactive charts and graphs
- **Layout**: Multi-page application with sidebar navigation
- **Real-time Updates**: WebSocket client for live data synchronization
- **Responsive Design**: Professional styling with metric cards and status indicators

### Data Storage
- **Type**: In-memory storage using Python dictionaries
- **Models**: Structured data using Pydantic models
- **Persistence**: File-based model storage for ML components
- **Sample Data**: Pre-populated demonstration data for immediate functionality

## Key Components

### Core Modules

#### Backend Services
1. **FastAPI Application** (`backend/app.py`)
   - Main API server with health checks
   - CORS configuration for frontend integration
   - WebSocket endpoint management

2. **Data Store** (`backend/data_store.py`)
   - In-memory data management
   - Sample data initialization
   - CRUD operations for all entities

3. **AI Integration** (`backend/ai_integration.py`)
   - OpenAI GPT-4o integration
   - Anthropic Claude-4 (claude-sonnet-4-20250514) integration
   - Rate limiting and error handling
   - Multi-provider AI voting and analysis

4. **ML Bias Detector** (`backend/ml_bias_detector.py`)
   - Random Forest classifier for bias detection
   - Isolation Forest for anomaly detection
   - Fairness metrics calculation
   - Model persistence and training

5. **WebSocket Manager** (`backend/websocket_manager.py`)
   - Real-time connection management
   - Message broadcasting
   - Client subscription handling

#### Frontend Pages
1. **Dashboard** (`frontend/dashboard.py`)
   - Real-time metrics display
   - Decision overview tables
   - Status indicators and progress tracking

2. **Multi-Agent Voting** (`frontend/voting.py`)
   - Interactive voting interface
   - Agent status visualization
   - Vote progress tracking

3. **Influence Graph** (`frontend/influence_graph.py`)
   - Network visualization using Plotly
   - Agent relationship mapping
   - Influence weight analysis

4. **Bias Scanner** (`frontend/bias_scanner.py`)
   - Fairness metrics dashboard
   - Bias detection heatmaps
   - Alert management system

5. **Governance Console** (`frontend/governance.py`)
   - Rule management interface
   - YAML-based rule configuration
   - Policy activation controls

6. **Audit Log** (`frontend/audit_log.py`)
   - Compliance tracking
   - Audit trail visualization
   - Historical analysis

7. **Notifications** (`frontend/notifications.py`)
   - Real-time alert system
   - Priority-based filtering
   - Notification management

### Data Models

#### Core Entities
- **Agent**: AI and human participants with roles, influence weights, and performance metrics
- **Decision**: Application cases with context, metadata, and status tracking
- **Vote**: Individual agent decisions with confidence scores and justifications
- **GovernanceRule**: System policies and rules with YAML definitions
- **AuditLog**: Compliance tracking and historical records
- **Notification**: System alerts and user notifications

#### Enumerations
- **AgentType**: AI vs Human classification
- **DecisionStatus**: Workflow states (pending, approved, rejected, etc.)
- **VoteDecision**: Accept/Reject choices
- **NotificationType**: Alert categories and priorities

## Data Flow

### Decision Processing Workflow
1. **Decision Creation**: New applications enter the system with context and metadata
2. **Agent Assignment**: AI and human agents are assigned based on rules and availability
3. **Voting Process**: Agents submit votes with confidence scores and justifications
4. **Bias Analysis**: ML models analyze decisions for potential bias and fairness issues
5. **Status Updates**: Real-time WebSocket updates notify clients of progress
6. **Final Decision**: Consensus algorithm determines approval/rejection
7. **Audit Logging**: All actions are logged for compliance and analysis

### Real-time Communication
- WebSocket connections provide live updates for voting progress
- Client subscriptions allow targeted message delivery
- Message broadcasting ensures all connected clients receive updates
- Connection management handles client lifecycle events

## External Dependencies

### AI Service Providers
- **OpenAI API**: GPT-4o model integration for AI decision-making
- **Anthropic API**: Claude-4 (claude-sonnet-4-20250514) for secondary AI opinions
- **Environment Variables**: API keys required for external service access

### Python Packages
- **FastAPI**: Web framework and API server
- **Streamlit**: Frontend framework
- **Plotly**: Interactive visualizations
- **Pandas**: Data manipulation and analysis
- **Scikit-learn**: Machine learning and bias detection
- **Pydantic**: Data validation and serialization
- **WebSockets**: Real-time communication
- **Requests**: HTTP client for API calls
- **YAML**: Configuration file parsing

### Development Tools
- **Uvicorn**: ASGI server for FastAPI
- **Concurrent Execution**: Multi-process launcher for backend and frontend

## Deployment Strategy

### Local Development
- **Concurrent Launch**: Single script (`start_app.py`) launches both services
- **Port Configuration**: Backend on 8000, Frontend on 8501
- **Environment Setup**: Automated dependency checking and validation
- **Process Management**: Graceful shutdown handling and error recovery

### Service Architecture
- **Backend Service**: FastAPI server with WebSocket support
- **Frontend Service**: Streamlit application with API integration
- **Real-time Layer**: WebSocket connections for live updates
- **ML Services**: Integrated bias detection and AI analysis

### Configuration Requirements
- Environment variables for AI service API keys
- Network connectivity for real-time WebSocket communication
- File system access for ML model persistence
- CORS configuration for cross-origin requests

## User Preferences

Preferred communication style: Simple, everyday language.

## Changelog

Changelog:
- June 28, 2025. Initial setup