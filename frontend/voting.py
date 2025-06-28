import streamlit as st
import requests
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
from datetime import datetime
import json

def show_voting():
    st.title("🗳️ Multi-Agent Voting Interface")
    st.markdown("Real-time voting system for AI and human agents")
    
    # Get current decisions for voting
    try:
        decisions_response = requests.get("http://localhost:8000/api/decisions", timeout=5)
        if decisions_response.status_code != 200:
            st.error("Failed to fetch decisions")
            return
        
        decisions = decisions_response.json()
        pending_decisions = [d for d in decisions if d['status'] in ['pending', 'under_review']]
        
    except requests.exceptions.RequestException as e:
        st.error(f"Unable to connect to API: {e}")
        return
    
    if not pending_decisions:
        st.info("No decisions currently available for voting")
        st.markdown("### 📋 Recent Completed Decisions")
        
        completed_decisions = [d for d in decisions if d['status'] in ['approved', 'rejected']]
        if completed_decisions:
            for decision in completed_decisions[:3]:
                with st.expander(f"Decision: {decision['context'][:60]}..."):
                    st.json(decision)
        return
    
    # Decision selection
    st.subheader("📋 Current Decision for Review")
    
    selected_decision = st.selectbox(
        "Select Decision to Review:",
        options=pending_decisions,
        format_func=lambda x: f"{x['id'][:8]}... - {x['context'][:50]}{'...' if len(x['context']) > 50 else ''}",
        key="decision_selector"
    )
    
    if not selected_decision:
        return
    
    # Display decision details
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.markdown("### 📄 Decision Details")
        
        # Decision information card
        st.markdown(f"""
        <div style="background: #f8f9fa; padding: 1rem; border-radius: 0.5rem; border-left: 4px solid #007bff;">
            <h4>{selected_decision['context']}</h4>
            <p><strong>Application Type:</strong> {selected_decision['application_type'].replace('_', ' ').title()}</p>
            <p><strong>Current Status:</strong> <span style="color: #ffc107;">{selected_decision['status'].replace('_', ' ').title()}</span></p>
            <p><strong>Bias Score:</strong> <span style="color: {'#dc3545' if selected_decision['bias_score'] > 0.7 else '#ffc107' if selected_decision['bias_score'] > 0.4 else '#28a745'};">{selected_decision['bias_score']:.3f}</span></p>
            <p><strong>Created:</strong> {datetime.fromisoformat(selected_decision['created_at'].replace('Z', '+00:00')).strftime('%Y-%m-%d %H:%M:%S')}</p>
        </div>
        """, unsafe_allow_html=True)
        
        # Applicant data
        if selected_decision.get('applicant_data'):
            st.markdown("### 👤 Applicant Information")
            applicant_data = selected_decision['applicant_data']
            
            info_cols = st.columns(3)
            for i, (key, value) in enumerate(applicant_data.items()):
                with info_cols[i % 3]:
                    st.metric(key.replace('_', ' ').title(), str(value))
    
    with col2:
        st.markdown("### 📊 Voting Progress")
        
        # Get votes for this decision
        try:
            votes_response = requests.get(f"http://localhost:8000/api/votes?decision_id={selected_decision['id']}", timeout=5)
            if votes_response.status_code == 200:
                votes = votes_response.json()
            else:
                votes = []
        except:
            votes = []
        
        # Get all agents
        try:
            agents_response = requests.get("http://localhost:8000/api/agents", timeout=5)
            if agents_response.status_code == 200:
                agents = agents_response.json()
            else:
                agents = []
        except:
            agents = []
        
        # Calculate voting progress
        total_agents = len(agents)
        votes_cast = len(votes)
        progress = votes_cast / max(total_agents, 1)
        
        st.progress(progress)
        st.metric("Voting Progress", f"{votes_cast}/{total_agents}", f"{progress*100:.1f}% Complete")
        
        # Voting summary
        if votes:
            accept_votes = len([v for v in votes if v['vote'] == 'accept'])
            reject_votes = len([v for v in votes if v['vote'] == 'reject'])
            
            st.markdown("**Current Tally:**")
            st.success(f"✅ Accept: {accept_votes}")
            st.error(f"❌ Reject: {reject_votes}")
        
        # Quick actions
        st.markdown("### ⚡ Quick Actions")
        
        if st.button("🔄 Refresh Votes", use_container_width=True):
            st.rerun()
        
        if st.button("📧 Notify Pending Agents", use_container_width=True):
            st.success("Notifications sent to pending agents")
        
        if st.button("⚠️ Escalate Decision", use_container_width=True):
            try:
                escalate_response = requests.put(
                    f"http://localhost:8000/api/decisions/{selected_decision['id']}/status",
                    json={"status": "escalated"},
                    timeout=5
                )
                if escalate_response.status_code == 200:
                    st.success("Decision escalated successfully")
                    st.rerun()
                else:
                    st.error("Failed to escalate decision")
            except:
                st.error("Error escalating decision")
    
    st.markdown("---")
    
    # Agent voting interface
    st.subheader("🤖 Agent Voting Status")
    
    # Create agent grid
    if agents:
        # Group agents by type
        ai_agents = [a for a in agents if a['type'] == 'ai']
        human_agents = [a for a in agents if a['type'] == 'human']
        
        st.markdown("### 🤖 AI Agents")
        ai_cols = st.columns(min(len(ai_agents), 3))
        
        for i, agent in enumerate(ai_agents):
            with ai_cols[i % 3]:
                # Find vote for this agent
                agent_vote = next((v for v in votes if v['agent_id'] == agent['id']), None)
                
                # Agent card
                if agent_vote:
                    vote_color = "#28a745" if agent_vote['vote'] == 'accept' else "#dc3545"
                    status_icon = "✅" if agent_vote['vote'] == 'accept' else "❌"
                    confidence = agent_vote['confidence']
                    justification = agent_vote['justification'][:100] + "..." if len(agent_vote['justification']) > 100 else agent_vote['justification']
                else:
                    vote_color = "#6c757d"
                    status_icon = "⏳"
                    confidence = 0
                    justification = "Vote pending..."
                
                st.markdown(f"""
                <div style="border: 1px solid {vote_color}; border-radius: 8px; padding: 10px; margin: 5px 0; background: #f8f9fa;">
                    <h5 style="margin: 0; color: {vote_color};">{status_icon} {agent['name']}</h5>
                    <p style="margin: 5px 0; font-size: 0.9em;"><strong>Role:</strong> {agent['role']}</p>
                    <p style="margin: 5px 0; font-size: 0.9em;"><strong>Confidence:</strong> {confidence*100:.1f}%</p>
                    <p style="margin: 5px 0; font-size: 0.8em; color: #6c757d;">{justification}</p>
                </div>
                """, unsafe_allow_html=True)
        
        st.markdown("### 👥 Human Reviewers")
        human_cols = st.columns(min(len(human_agents), 3))
        
        for i, agent in enumerate(human_agents):
            with human_cols[i % 3]:
                # Find vote for this agent
                agent_vote = next((v for v in votes if v['agent_id'] == agent['id']), None)
                
                # Agent card
                if agent_vote:
                    vote_color = "#28a745" if agent_vote['vote'] == 'accept' else "#dc3545"
                    status_icon = "✅" if agent_vote['vote'] == 'accept' else "❌"
                    confidence = agent_vote['confidence']
                    justification = agent_vote['justification'][:100] + "..." if len(agent_vote['justification']) > 100 else agent_vote['justification']
                else:
                    vote_color = "#6c757d"
                    status_icon = "⏳"
                    confidence = 0
                    justification = "Vote pending..."
                
                st.markdown(f"""
                <div style="border: 1px solid {vote_color}; border-radius: 8px; padding: 10px; margin: 5px 0; background: #f8f9fa;">
                    <h5 style="margin: 0; color: {vote_color};">{status_icon} {agent['name']}</h5>
                    <p style="margin: 5px 0; font-size: 0.9em;"><strong>Role:</strong> {agent['role']}</p>
                    <p style="margin: 5px 0; font-size: 0.9em;"><strong>Confidence:</strong> {confidence*100:.1f}%</p>
                    <p style="margin: 5px 0; font-size: 0.8em; color: #6c757d;">{justification}</p>
                </div>
                """, unsafe_allow_html=True)
    
    # Voting analytics
    if votes and agents:
        st.markdown("---")
        st.subheader("📈 Voting Analytics")
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Vote distribution pie chart
            vote_counts = {'Accept': len([v for v in votes if v['vote'] == 'accept']),
                          'Reject': len([v for v in votes if v['vote'] == 'reject'])}
            
            if sum(vote_counts.values()) > 0:
                fig_pie = px.pie(
                    values=list(vote_counts.values()),
                    names=list(vote_counts.keys()),
                    title="Vote Distribution",
                    color_discrete_map={'Accept': '#28a745', 'Reject': '#dc3545'}
                )
                fig_pie.update_traces(textposition='inside', textinfo='percent+label')
                fig_pie.update_layout(height=300)
                st.plotly_chart(fig_pie, use_container_width=True)
        
        with col2:
            # Confidence levels
            if votes:
                vote_df = pd.DataFrame(votes)
                agent_df = pd.DataFrame(agents)
                
                # Merge to get agent types
                merged_df = pd.merge(vote_df, agent_df[['id', 'type']], left_on='agent_id', right_on='id', how='left')
                
                if not merged_df.empty:
                    fig_bar = px.bar(
                        merged_df,
                        x='agent_id',
                        y='confidence',
                        color='type',
                        title="Agent Confidence Levels",
                        color_discrete_map={'ai': '#007bff', 'human': '#28a745'}
                    )
                    fig_bar.update_layout(height=300, xaxis_title="Agent", yaxis_title="Confidence")
                    fig_bar.update_xaxes(tickangle=45)
                    st.plotly_chart(fig_bar, use_container_width=True)
    
    # Manual voting interface (for testing/admin)
    st.markdown("---")
    st.subheader("🛠️ Manual Vote Submission")
    
    with st.expander("Submit Manual Vote (Admin Only)"):
        if agents:
            vote_agent = st.selectbox("Select Agent:", agents, format_func=lambda x: f"{x['name']} ({x['type'].upper()})")
            vote_decision = st.selectbox("Vote Decision:", ["accept", "reject"])
            vote_confidence = st.slider("Confidence Level:", 0.0, 1.0, 0.8, 0.01)
            vote_justification = st.text_area("Justification:", placeholder="Provide reasoning for this vote...")
            
            if st.button("Submit Vote", type="primary"):
                if vote_justification:
                    try:
                        vote_data = {
                            "agent_id": vote_agent['id'],
                            "decision_id": selected_decision['id'],
                            "vote": vote_decision,
                            "confidence": vote_confidence,
                            "justification": vote_justification
                        }
                        
                        vote_response = requests.post(
                            "http://localhost:8000/api/votes",
                            json=vote_data,
                            timeout=5
                        )
                        
                        if vote_response.status_code == 200:
                            st.success("Vote submitted successfully!")
                            st.rerun()
                        else:
                            st.error("Failed to submit vote")
                    except Exception as e:
                        st.error(f"Error submitting vote: {e}")
                else:
                    st.warning("Please provide justification for the vote")
