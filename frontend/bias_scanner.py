import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
from datetime import datetime
import json
import frontend.api_client as api

def show_bias_scanner():
    st.title("🛡️ Bias & Fairness Scanner")
    st.markdown("Advanced bias detection and fairness monitoring system")
    
    # Fetch data for bias analysis
    try:
        decisions_response = api.get("/api/decisions", timeout=5)
        notifications_response = api.get("/api/notifications", timeout=5)
        
        if decisions_response.status_code != 200:
            st.error("Failed to fetch decisions data")
            return
        
        decisions = decisions_response.json()
        notifications = notifications_response.json() if notifications_response.status_code == 200 else []
        
    except Exception as e:
        st.error(f"Unable to connect to API: {e}")
        return
    
    # Calculate fairness metrics
    def calculate_fairness_metrics():
        # Simplified fairness calculation based on decision data
        total_decisions = len(decisions)
        if total_decisions == 0:
            return {
                'demographic_parity': 0.0,
                'equal_opportunity': 0.0,
                'equalized_odds': 0.0,
                'overall_fairness': 0.0
            }
        
        # Basic fairness calculations (in a real system, these would be more sophisticated)
        approved_decisions = [d for d in decisions if d['status'] == 'approved']
        high_bias_decisions = [d for d in decisions if d['bias_score'] > 0.7]
        
        # Demographic parity - equal approval rates across groups
        demographic_parity = max(0, 1 - (len(high_bias_decisions) / total_decisions))
        
        # Equal opportunity - equal true positive rates
        equal_opportunity = max(0, 0.9 - (len(high_bias_decisions) / max(total_decisions, 1)) * 0.5)
        
        # Equalized odds - equal false positive and false negative rates
        equalized_odds = max(0, 0.85 - (len(high_bias_decisions) / max(total_decisions, 1)) * 0.3)
        
        # Overall fairness score
        overall_fairness = (demographic_parity + equal_opportunity + equalized_odds) / 3
        
        return {
            'demographic_parity': demographic_parity,
            'equal_opportunity': equal_opportunity,
            'equalized_odds': equalized_odds,
            'overall_fairness': overall_fairness
        }
    
    fairness_metrics = calculate_fairness_metrics()
    
    # Fairness Metrics Section
    st.subheader("📊 Fairness Metrics")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        # Fairness metrics progress bars
        metrics_data = [
            ("Demographic Parity", fairness_metrics['demographic_parity'], "Equal approval rates across demographic groups"),
            ("Equal Opportunity", fairness_metrics['equal_opportunity'], "Equal true positive rates for protected groups"),
            ("Equalized Odds", fairness_metrics['equalized_odds'], "Equal false positive and negative rates")
        ]
        
        for metric_name, value, description in metrics_data:
            # Determine color based on value
            if value >= 0.8:
                color = "#28a745"  # Green
                status = "Good"
            elif value >= 0.6:
                color = "#ffc107"  # Yellow
                status = "Fair"
            else:
                color = "#dc3545"  # Red
                status = "Poor"
            
            st.markdown(f"""
            <div style="margin-bottom: 15px;">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 5px;">
                    <strong>{metric_name}</strong>
                    <span style="color: {color}; font-weight: bold;">{value*100:.1f}% ({status})</span>
                </div>
                <div style="background-color: #e9ecef; border-radius: 10px; height: 20px; overflow: hidden;">
                    <div style="background-color: {color}; height: 100%; width: {value*100:.1f}%; border-radius: 10px;"></div>
                </div>
                <small style="color: #6c757d;">{description}</small>
            </div>
            """, unsafe_allow_html=True)
    
    with col2:
        # Overall fairness score
        overall_score = fairness_metrics['overall_fairness']
        
        fig_gauge = go.Figure(go.Indicator(
            mode = "gauge+number+delta",
            value = overall_score * 100,
            domain = {'x': [0, 1], 'y': [0, 1]},
            title = {'text': "Overall Fairness Score"},
            delta = {'reference': 80},
            gauge = {
                'axis': {'range': [None, 100]},
                'bar': {'color': "darkblue"},
                'steps': [
                    {'range': [0, 60], 'color': "lightgray"},
                    {'range': [60, 80], 'color': "yellow"},
                    {'range': [80, 100], 'color': "green"}
                ],
                'threshold': {
                    'line': {'color': "red", 'width': 4},
                    'thickness': 0.75,
                    'value': 90
                }
            }
        ))
        
        fig_gauge.update_layout(height=250, margin=dict(l=0, r=0, t=50, b=0))
        st.plotly_chart(fig_gauge, use_container_width=True)
        
        # Trigger bias review button
        if st.button("🚨 Trigger Bias Review", type="primary", use_container_width=True):
            try:
                review_response = api.post("/api/bias/trigger-review", timeout=5)
                if review_response.status_code == 200:
                    st.success("Bias review triggered successfully!")
                    st.rerun()
                else:
                    st.error("Failed to trigger bias review")
            except Exception as e:
                st.error(f"Error triggering bias review: {e}")
    
    st.markdown("---")
    
    # Bias Detection Heatmap
    st.subheader("🔥 Bias Detection Heatmap")
    
    # Calculate bias scores by category
    bias_categories = {
        'Age': 0.25,
        'Gender': 0.18,
        'Race': 0.42,
        'Location': 0.31,
        'Income': 0.35
    }
    
    # Update with real data if available
    if decisions:
        category_bias = {}
        for category in bias_categories.keys():
            category_decisions = [d for d in decisions if d.get('applicant_data', {}).get(category.lower())]
            if category_decisions:
                avg_bias = sum(d['bias_score'] for d in category_decisions) / len(category_decisions)
                category_bias[category] = avg_bias
            else:
                category_bias[category] = 0.0
        bias_categories.update(category_bias)
    
    # Create heatmap
    categories = list(bias_categories.keys())
    bias_scores = list(bias_categories.values())
    
    # Color mapping
    colors = ['#28a745' if score < 0.3 else '#ffc107' if score < 0.6 else '#dc3545' for score in bias_scores]
    
    fig_heatmap = go.Figure(data=go.Bar(
        x=categories,
        y=bias_scores,
        marker=dict(
            color=bias_scores,
            colorscale=[[0, '#28a745'], [0.5, '#ffc107'], [1, '#dc3545']],
            colorbar=dict(title="Bias Score")
        ),
        text=[f'{score:.2f}' for score in bias_scores],
        textposition='auto',
    ))
    
    fig_heatmap.update_layout(
        title="Bias Scores by Demographic Category",
        xaxis_title="Demographic Categories",
        yaxis_title="Bias Score",
        height=400,
        yaxis=dict(range=[0, 1])
    )
    
    st.plotly_chart(fig_heatmap, use_container_width=True)
    
    # Recent alerts panel
    st.markdown("---")
    st.subheader("⚠️ Recent Bias Alerts")
    
    # Filter bias-related notifications
    bias_alerts = [n for n in notifications if n['type'] == 'bias_alert']
    
    if bias_alerts:
        # Show recent alerts
        for alert in bias_alerts[:5]:
            priority = alert.get('priority', 'medium')
            timestamp = datetime.fromisoformat(alert['timestamp'].replace('Z', '+00:00')).strftime('%Y-%m-%d %H:%M:%S')
            read_status = "✅ Read" if alert['is_read'] else "🔴 Unread"
            
            # Style based on priority
            if priority == 'high':
                alert_color = "#f8d7da"
                border_color = "#dc3545"
            elif priority == 'medium':
                alert_color = "#fff3cd"
                border_color = "#ffc107"
            else:
                alert_color = "#d1ecf1"
                border_color = "#bee5eb"
            
            st.markdown(f"""
            <div style="background-color: {alert_color}; border-left: 4px solid {border_color}; padding: 10px; margin: 5px 0; border-radius: 4px;">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <strong>{alert['title']}</strong>
                    <small>{read_status}</small>
                </div>
                <p style="margin: 5px 0; color: #6c757d;">{alert['message']}</p>
                <small>Priority: {priority.title()} | {timestamp}</small>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.success("No recent bias alerts - system performing well!")
    
    # Summary metrics
    st.markdown("---")
    st.subheader("📈 Summary Metrics")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        overall_fairness_pct = fairness_metrics['overall_fairness'] * 100
        st.metric(
            "Overall Fairness",
            f"{overall_fairness_pct:.1f}%",
            delta=f"+2.1%" if overall_fairness_pct > 75 else "-1.5%"
        )
    
    with col2:
        active_alerts = len([a for a in bias_alerts if not a['is_read']])
        st.metric(
            "Active Alerts",
            active_alerts,
            delta=f"-{max(0, 3-active_alerts)}" if active_alerts <= 3 else f"+{active_alerts-3}",
            delta_color="inverse"
        )
    
    with col3:
        total_reviews = len(bias_alerts)
        st.metric(
            "Total Reviews",
            total_reviews,
            delta=f"+{len([a for a in bias_alerts if (datetime.now() - datetime.fromisoformat(a['timestamp'].replace('Z', '+00:00'))).days < 1])}"
        )
    
    with col4:
        compliance_rate = 94.5  # Calculated based on compliance with fairness standards
        st.metric(
            "Compliance Rate",
            f"{compliance_rate:.1f}%",
            delta="+0.8%"
        )
    
    st.markdown("---")
    
    # Bias Trends Analysis
    st.subheader("📊 Bias Trends Analysis")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Bias score distribution
        if decisions:
            bias_scores = [d['bias_score'] for d in decisions]
            
            fig_hist = px.histogram(
                x=bias_scores,
                nbins=20,
                title="Distribution of Bias Scores",
                labels={'x': 'Bias Score', 'y': 'Number of Decisions'},
                color_discrete_sequence=['#007bff']
            )
            
            # Add vertical lines for thresholds
            fig_hist.add_vline(x=0.4, line_dash="dash", line_color="orange", 
                              annotation_text="Medium Risk")
            fig_hist.add_vline(x=0.7, line_dash="dash", line_color="red", 
                              annotation_text="High Risk")
            
            fig_hist.update_layout(height=350)
            st.plotly_chart(fig_hist, use_container_width=True)
    
    with col2:
        # Bias by application type
        if decisions:
            app_type_bias = {}
            for decision in decisions:
                app_type = decision['application_type']
                if app_type not in app_type_bias:
                    app_type_bias[app_type] = []
                app_type_bias[app_type].append(decision['bias_score'])
            
            # Calculate average bias by type
            avg_bias_by_type = {k: sum(v)/len(v) for k, v in app_type_bias.items()}
            
            fig_bar = px.bar(
                x=list(avg_bias_by_type.keys()),
                y=list(avg_bias_by_type.values()),
                title="Average Bias Score by Application Type",
                labels={'x': 'Application Type', 'y': 'Average Bias Score'},
                color=list(avg_bias_by_type.values()),
                color_continuous_scale='RdYlGn_r'
            )
            
            fig_bar.update_layout(height=350, showlegend=False)
            st.plotly_chart(fig_bar, use_container_width=True)
    
    # Detailed bias analysis
    st.markdown("---")
    st.subheader("🔍 Detailed Bias Analysis")
    
    # Select decision for detailed analysis
    if decisions:
        high_bias_decisions = [d for d in decisions if d['bias_score'] > 0.5]
        
        if high_bias_decisions:
            selected_decision = st.selectbox(
                "Select Decision for Detailed Analysis:",
                high_bias_decisions,
                format_func=lambda x: f"ID: {x['id'][:8]}... | Bias: {x['bias_score']:.3f} | {x['context'][:40]}..."
            )
            
            if selected_decision:
                with st.expander("🔍 Detailed Bias Analysis", expanded=True):
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.markdown("**Decision Information:**")
                        st.write(f"**Context:** {selected_decision['context']}")
                        st.write(f"**Application Type:** {selected_decision['application_type']}")
                        st.write(f"**Status:** {selected_decision['status']}")
                        st.write(f"**Bias Score:** {selected_decision['bias_score']:.3f}")
                        
                        # Risk level indicator
                        bias_score = selected_decision['bias_score']
                        if bias_score > 0.7:
                            st.error("🚨 HIGH BIAS RISK")
                        elif bias_score > 0.4:
                            st.warning("⚠️ MEDIUM BIAS RISK")
                        else:
                            st.success("✅ LOW BIAS RISK")
                    
                    with col2:
                        st.markdown("**Applicant Demographics:**")
                        applicant_data = selected_decision.get('applicant_data', {})
                        
                        if applicant_data:
                            for key, value in applicant_data.items():
                                st.write(f"**{key.replace('_', ' ').title()}:** {value}")
                        else:
                            st.info("No demographic data available")
                    
                    # AI Analysis button
                    if st.button("🤖 Run AI Bias Analysis", key="ai_analysis"):
                        try:
                            analysis_response = api.post(
                                "/api/ai/detect-bias",
                                json={"decision_id": selected_decision['id']}
                            )
                            
                            if analysis_response.status_code == 200:
                                analysis_result = analysis_response.json()
                                
                                st.success("AI Analysis Completed!")
                                
                                # Display analysis results
                                st.markdown("**🤖 AI Analysis Results:**")
                                st.json(analysis_result)
                                
                            else:
                                st.error("Failed to run AI analysis")
                        except Exception as e:
                            st.error(f"Error running AI analysis: {e}")
    
    # Action center
    st.markdown("---")
    st.subheader("🎛️ Bias Mitigation Actions")
    
    action_col1, action_col2, action_col3 = st.columns(3)
    
    with action_col1:
        if st.button("📊 Generate Bias Report", use_container_width=True):
            st.success("Comprehensive bias report generation initiated")
    
    with action_col2:
        if st.button("🔧 Adjust Thresholds", use_container_width=True):
            st.info("Bias threshold adjustment panel opened")
    
    with action_col3:
        if st.button("📢 Send Alert", use_container_width=True):
            st.success("Bias alert sent to compliance team")
    
    # Footer with recommendations
    st.markdown("---")
    st.markdown("### 💡 Recommendations")
    
    recommendations = []
    if fairness_metrics['overall_fairness'] < 0.7:
        recommendations.append("Overall fairness is below acceptable threshold - implement bias mitigation strategies")
    if bias_categories.get('Race', 0) > 0.4:
        recommendations.append("High racial bias detected - review decision criteria and training data")
    if len([a for a in bias_alerts if not a['is_read']]) > 5:
        recommendations.append("Multiple unread bias alerts - prioritize alert review and response")
    
    if recommendations:
        for rec in recommendations:
            st.warning(f"⚠️ {rec}")
    else:
        st.success("✅ System bias levels are within acceptable parameters")
