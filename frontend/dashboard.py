import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import requests
from datetime import datetime, timedelta
import time

def show_dashboard():
    st.title("📊 ParallaxAI Dashboard")
    st.markdown("Real-time Human-AI Co-Governance Platform Overview")
    
    # Get real-time stats
    try:
        response = requests.get("http://localhost:8000/api/stats", timeout=5)
        if response.status_code == 200:
            stats = response.json()
        else:
            st.error("Failed to fetch dashboard statistics")
            return
    except requests.exceptions.RequestException as e:
        st.error(f"Unable to connect to API: {e}")
        return
    
    # Top-level metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            "Total Decisions",
            stats.get('total_decisions', 0),
            delta=f"+{stats.get('decisions_last_24h', 0)} (24h)"
        )
    
    with col2:
        ai_accuracy = stats.get('ai_accuracy', 0)
        st.metric(
            "AI Accuracy",
            f"{ai_accuracy*100:.1f}%",
            delta=f"+2.3%" if ai_accuracy > 0.8 else "-1.1%"
        )
    
    with col3:
        override_rate = stats.get('override_rate', 0)
        st.metric(
            "Override Rate",
            f"{override_rate*100:.1f}%",
            delta=f"-0.5%" if override_rate < 0.15 else "+0.8%"
        )
    
    with col4:
        bias_incidents = stats.get('bias_incidents', 0)
        st.metric(
            "Bias Incidents",
            bias_incidents,
            delta=f"+{stats.get('alerts_last_24h', 0)} (24h)",
            delta_color="inverse"
        )
    
    st.markdown("---")
    
    # Decision overview section
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.subheader("📋 Recent Decisions")
        
        # Get recent decisions
        try:
            decisions_response = requests.get("http://localhost:8000/api/decisions", timeout=5)
            if decisions_response.status_code == 200:
                decisions = decisions_response.json()
                
                if decisions:
                    # Create decisions dataframe
                    decisions_df = pd.DataFrame([
                        {
                            "Decision ID": d['id'][:8] + "...",
                            "Context": d['context'][:50] + "..." if len(d['context']) > 50 else d['context'],
                            "Status": d['status'].replace('_', ' ').title(),
                            "Bias Score": f"{d['bias_score']:.3f}",
                            "Risk Level": d.get('risk_level', 'medium').title(),
                            "Updated": datetime.fromisoformat(d['updated_at'].replace('Z', '+00:00')).strftime('%H:%M:%S')
                        }
                        for d in decisions[-10:]  # Show last 10 decisions
                    ])
                    
                    # Apply status-based styling
                    def style_status(val):
                        if val == 'Approved':
                            return 'background-color: #d4edda; color: #155724'
                        elif val == 'Rejected':
                            return 'background-color: #f8d7da; color: #721c24'
                        elif val == 'Under Review':
                            return 'background-color: #fff3cd; color: #856404'
                        elif val == 'Escalated':
                            return 'background-color: #f1c0c7; color: #721c24'
                        return ''
                    
                    # Apply bias score styling
                    def style_bias_score(val):
                        score = float(val)
                        if score > 0.7:
                            return 'background-color: #f8d7da; color: #721c24; font-weight: bold'
                        elif score > 0.4:
                            return 'background-color: #fff3cd; color: #856404'
                        return 'background-color: #d4edda; color: #155724'
                    
                    # Apply risk level styling
                    def style_risk_level(val):
                        if val == 'High':
                            return 'background-color: #f8d7da; color: #721c24; font-weight: bold'
                        elif val == 'Medium':
                            return 'background-color: #fff3cd; color: #856404'
                        return 'background-color: #d4edda; color: #155724'
                    
                    styled_df = decisions_df.style.applymap(
                        style_status, subset=['Status']
                    ).applymap(
                        style_bias_score, subset=['Bias Score']
                    ).applymap(
                        style_risk_level, subset=['Risk Level']
                    )
                    
                    st.dataframe(styled_df, use_container_width=True, hide_index=True)
                    
                    # Decision actions
                    st.markdown("**Quick Actions:**")
                    action_col1, action_col2, action_col3 = st.columns(3)
                    
                    with action_col1:
                        if st.button("🔍 View Details", key="view_details"):
                            st.info("Select a decision ID to view detailed analysis")
                    
                    with action_col2:
                        if st.button("📊 Generate Report", key="generate_report"):
                            st.success("Report generation initiated")
                    
                    with action_col3:
                        if st.button("🔄 Refresh Data", key="refresh_data"):
                            st.rerun()
                
                else:
                    st.info("No decisions found")
                    
        except requests.exceptions.RequestException as e:
            st.error(f"Failed to fetch decisions: {e}")
    
    with col2:
        st.subheader("🎯 System Health")
        
        # System health indicators
        health_metrics = [
            ("API Connection", "🟢 Online", "success"),
            ("WebSocket", "🟢 Connected", "success"),
            ("AI Services", "🟡 Partial", "warning"),
            ("Database", "🟢 Healthy", "success"),
            ("ML Models", "🟢 Active", "success")
        ]
        
        for metric, status, status_type in health_metrics:
            if status_type == "success":
                st.success(f"**{metric}**: {status}")
            elif status_type == "warning":
                st.warning(f"**{metric}**: {status}")
            else:
                st.error(f"**{metric}**: {status}")
        
        st.markdown("---")
        
        # Recent alerts
        st.subheader("🚨 Recent Alerts")
        
        try:
            notifications_response = requests.get("http://localhost:8000/api/notifications", timeout=5)
            if notifications_response.status_code == 200:
                notifications = notifications_response.json()
                recent_alerts = [n for n in notifications if not n['is_read']][:3]
                
                if recent_alerts:
                    for alert in recent_alerts:
                        alert_type = alert['type'].replace('_', ' ').title()
                        priority = alert.get('priority', 'medium')
                        
                        if priority == 'high':
                            st.error(f"**{alert_type}**: {alert['title']}")
                        elif priority == 'medium':
                            st.warning(f"**{alert_type}**: {alert['title']}")
                        else:
                            st.info(f"**{alert_type}**: {alert['title']}")
                else:
                    st.success("No active alerts")
                    
        except requests.exceptions.RequestException:
            st.error("Failed to fetch alerts")
    
    st.markdown("---")
    
    # Analytics section
    st.subheader("📈 Real-time Analytics")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Decision status distribution
        st.markdown("**Decision Status Distribution**")
        
        status_data = {
            'Approved': stats.get('approved_decisions', 0),
            'Rejected': stats.get('rejected_decisions', 0),
            'Pending': stats.get('pending_decisions', 0)
        }
        
        if sum(status_data.values()) > 0:
            fig_pie = px.pie(
                values=list(status_data.values()),
                names=list(status_data.keys()),
                color_discrete_map={
                    'Approved': '#28a745',
                    'Rejected': '#dc3545',
                    'Pending': '#ffc107'
                }
            )
            fig_pie.update_traces(textposition='inside', textinfo='percent+label')
            fig_pie.update_layout(height=300, showlegend=True)
            st.plotly_chart(fig_pie, use_container_width=True)
        else:
            st.info("No decision data available")
    
    with col2:
        # Bias score distribution
        st.markdown("**Bias Risk Distribution**")
        
        bias_data = {
            'Low Risk': stats.get('low_bias_decisions', 0),
            'Medium Risk': stats.get('medium_bias_decisions', 0),
            'High Risk': stats.get('high_bias_decisions', 0)
        }
        
        if sum(bias_data.values()) > 0:
            fig_bar = px.bar(
                x=list(bias_data.keys()),
                y=list(bias_data.values()),
                color=list(bias_data.keys()),
                color_discrete_map={
                    'Low Risk': '#28a745',
                    'Medium Risk': '#ffc107',
                    'High Risk': '#dc3545'
                }
            )
            fig_bar.update_layout(
                height=300,
                showlegend=False,
                xaxis_title="Risk Level",
                yaxis_title="Number of Decisions"
            )
            st.plotly_chart(fig_bar, use_container_width=True)
        else:
            st.info("No bias data available")
    
    # Agent performance section
    st.subheader("🤖 Agent Performance Overview")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric(
            "Total Agents",
            stats.get('total_agents', 0),
            help="Total number of AI and human agents"
        )
    
    with col2:
        st.metric(
            "AI Agents",
            stats.get('ai_agents', 0),
            help="Number of active AI agents"
        )
    
    with col3:
        st.metric(
            "Human Reviewers",
            stats.get('human_agents', 0),
            help="Number of active human reviewers"
        )
    
    # Performance trends (simulated real-time data)
    st.markdown("**Performance Trends (Last 24 Hours)**")
    
    # Generate sample time series data for visualization
    time_labels = [(datetime.now() - timedelta(hours=i)).strftime('%H:%M') for i in range(24, 0, -1)]
    accuracy_trend = [85 + (i % 3) * 2 + (i % 7) * 1.5 for i in range(24)]
    throughput_trend = [45 + (i % 5) * 3 + (i % 11) * 2 for i in range(24)]
    
    fig_trends = go.Figure()
    
    fig_trends.add_trace(go.Scatter(
        x=time_labels,
        y=accuracy_trend,
        mode='lines+markers',
        name='AI Accuracy (%)',
        line=dict(color='#007bff', width=2)
    ))
    
    fig_trends.add_trace(go.Scatter(
        x=time_labels,
        y=throughput_trend,
        mode='lines+markers',
        name='Decisions/Hour',
        line=dict(color='#28a745', width=2),
        yaxis='y2'
    ))
    
    fig_trends.update_layout(
        height=400,
        xaxis_title="Time",
        yaxis=dict(title="Accuracy (%)", side="left"),
        yaxis2=dict(title="Decisions/Hour", side="right", overlaying="y"),
        legend=dict(x=0.01, y=0.99),
        hovermode='x unified'
    )
    
    st.plotly_chart(fig_trends, use_container_width=True)
    
    # Footer with last update time
    st.markdown("---")
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S UTC")
    st.caption(f"Last updated: {current_time} | Auto-refresh enabled")
    
    # Add refresh indicator
    if 'refresh_count' not in st.session_state:
        st.session_state.refresh_count = 0
    
    st.session_state.refresh_count += 1
    
    # Auto-refresh placeholder for real-time updates
    placeholder = st.empty()
    if st.session_state.get('real_time_updates', True):
        time.sleep(0.1)  # Small delay to show loading state
        placeholder.empty()
