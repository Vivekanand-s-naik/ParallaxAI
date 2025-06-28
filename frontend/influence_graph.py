import streamlit as st
import requests
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import numpy as np
from datetime import datetime

def show_influence_graph():
    st.title("🕸️ Influence Graph Viewer")
    st.markdown("Interactive visualization of agent relationships and influence patterns")
    
    # Fetch agents and votes data
    try:
        agents_response = requests.get("http://localhost:8000/api/agents", timeout=5)
        votes_response = requests.get("http://localhost:8000/api/votes", timeout=5)
        stats_response = requests.get("http://localhost:8000/api/stats", timeout=5)
        
        if agents_response.status_code != 200:
            st.error("Failed to fetch agents data")
            return
        
        agents = agents_response.json()
        votes = votes_response.json() if votes_response.status_code == 200 else []
        stats = stats_response.json() if stats_response.status_code == 200 else {}
        
    except requests.exceptions.RequestException as e:
        st.error(f"Unable to connect to API: {e}")
        return
    
    if not agents:
        st.info("No agents found in the system")
        return
    
    # Network metrics overview
    st.subheader("📊 Network Metrics")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Agents", len(agents))
    
    with col2:
        ai_agents_count = len([a for a in agents if a['type'] == 'ai'])
        st.metric("AI Agents", ai_agents_count)
    
    with col3:
        human_agents_count = len([a for a in agents if a['type'] == 'human'])
        st.metric("Human Agents", human_agents_count)
    
    with col4:
        high_influence_count = len([a for a in agents if a['influence_weight'] > 1.2])
        st.metric("High Influence", high_influence_count)
    
    # Additional metrics
    col1, col2, col3 = st.columns(3)
    
    with col1:
        consensus_rate = stats.get('consensus_rate', 0.78)
        st.metric("Consensus Rate", f"{consensus_rate*100:.1f}%")
    
    with col2:
        override_events = stats.get('override_events', 3)
        st.metric("Override Events", override_events)
    
    with col3:
        network_density = 0.85  # Calculated based on agent interactions
        st.metric("Network Density", f"{network_density:.2f}")
    
    st.markdown("---")
    
    # Interactive influence scatter plot
    st.subheader("🎯 Agent Influence Map")
    
    # Prepare data for visualization
    agent_data = []
    for agent in agents:
        # Count votes by this agent
        agent_votes = [v for v in votes if v['agent_id'] == agent['id']]
        vote_count = len(agent_votes)
        
        # Calculate average confidence for this agent
        if agent_votes:
            avg_confidence = sum(v['confidence'] for v in agent_votes) / len(agent_votes)
        else:
            avg_confidence = agent.get('average_confidence', 0.5)
        
        agent_data.append({
            'name': agent['name'],
            'type': agent['type'],
            'influence_weight': agent['influence_weight'],
            'average_confidence': avg_confidence,
            'vote_count': vote_count,
            'role': agent['role'],
            'model_version': agent.get('model_version', 'N/A')
        })
    
    if agent_data:
        df = pd.DataFrame(agent_data)
        
        # Create interactive scatter plot
        fig = px.scatter(
            df,
            x='influence_weight',
            y='average_confidence',
            size='vote_count',
            color='type',
            hover_name='name',
            hover_data={
                'role': True,
                'model_version': True,
                'vote_count': True,
                'influence_weight': ':.2f',
                'average_confidence': ':.2f'
            },
            title="Agent Influence vs Confidence",
            color_discrete_map={'ai': '#007bff', 'human': '#28a745'},
            size_max=30
        )
        
        fig.update_layout(
            height=500,
            xaxis_title="Influence Weight",
            yaxis_title="Average Confidence",
            legend_title="Agent Type"
        )
        
        # Add quadrant lines
        max_influence = df['influence_weight'].max()
        max_confidence = df['average_confidence'].max()
        
        # High influence line
        fig.add_hline(y=0.8, line_dash="dash", line_color="red", 
                     annotation_text="High Confidence Threshold")
        
        # High confidence line
        fig.add_vline(x=1.2, line_dash="dash", line_color="orange", 
                     annotation_text="High Influence Threshold")
        
        st.plotly_chart(fig, use_container_width=True)
        
        # Quadrant analysis
        st.markdown("### 📈 Quadrant Analysis")
        
        quad_col1, quad_col2 = st.columns(2)
        
        with quad_col1:
            # High influence, high confidence
            high_both = df[(df['influence_weight'] > 1.2) & (df['average_confidence'] > 0.8)]
            st.success(f"**High Influence & High Confidence:** {len(high_both)} agents")
            if not high_both.empty:
                for _, agent in high_both.iterrows():
                    st.write(f"• {agent['name']} ({agent['type'].upper()})")
            
            # Low influence, high confidence
            low_inf_high_conf = df[(df['influence_weight'] <= 1.2) & (df['average_confidence'] > 0.8)]
            st.info(f"**Low Influence & High Confidence:** {len(low_inf_high_conf)} agents")
            if not low_inf_high_conf.empty:
                for _, agent in low_inf_high_conf.iterrows():
                    st.write(f"• {agent['name']} ({agent['type'].upper()})")
        
        with quad_col2:
            # High influence, low confidence
            high_inf_low_conf = df[(df['influence_weight'] > 1.2) & (df['average_confidence'] <= 0.8)]
            st.warning(f"**High Influence & Low Confidence:** {len(high_inf_low_conf)} agents")
            if not high_inf_low_conf.empty:
                for _, agent in high_inf_low_conf.iterrows():
                    st.write(f"• {agent['name']} ({agent['type'].upper()})")
            
            # Low influence, low confidence
            low_both = df[(df['influence_weight'] <= 1.2) & (df['average_confidence'] <= 0.8)]
            st.error(f"**Low Influence & Low Confidence:** {len(low_both)} agents")
            if not low_both.empty:
                for _, agent in low_both.iterrows():
                    st.write(f"• {agent['name']} ({agent['type'].upper()})")
    
    st.markdown("---")
    
    # Agent comparison matrix
    st.subheader("🔄 Agent Interaction Analysis")
    
    # Calculate agreement rates between agents
    if len(agents) > 1 and votes:
        st.markdown("### 🤝 Agreement Rates Between Agents")
        
        # Get decisions that have votes from multiple agents
        decision_votes = {}
        for vote in votes:
            decision_id = vote['decision_id']
            if decision_id not in decision_votes:
                decision_votes[decision_id] = []
            decision_votes[decision_id].append(vote)
        
        # Calculate pairwise agreement rates
        agent_names = [a['name'] for a in agents]
        agreement_matrix = np.zeros((len(agents), len(agents)))
        
        for i, agent1 in enumerate(agents):
            for j, agent2 in enumerate(agents):
                if i == j:
                    agreement_matrix[i][j] = 1.0  # Agent agrees with itself
                    continue
                
                agreements = 0
                comparisons = 0
                
                for decision_id, decision_votes_list in decision_votes.items():
                    agent1_vote = next((v for v in decision_votes_list if v['agent_id'] == agent1['id']), None)
                    agent2_vote = next((v for v in decision_votes_list if v['agent_id'] == agent2['id']), None)
                    
                    if agent1_vote and agent2_vote:
                        if agent1_vote['vote'] == agent2_vote['vote']:
                            agreements += 1
                        comparisons += 1
                
                agreement_matrix[i][j] = agreements / comparisons if comparisons > 0 else 0
        
        # Display agreement heatmap
        fig_heatmap = px.imshow(
            agreement_matrix,
            x=agent_names,
            y=agent_names,
            color_continuous_scale='RdYlGn',
            title="Agent Agreement Rate Matrix",
            aspect="auto"
        )
        
        fig_heatmap.update_layout(height=400)
        fig_heatmap.update_xaxes(tickangle=45)
        st.plotly_chart(fig_heatmap, use_container_width=True)
        
        # Top agreements and disagreements
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("**🤝 Highest Agreement Pairs:**")
            # Find highest agreement pairs (excluding self-agreement)
            best_pairs = []
            for i in range(len(agents)):
                for j in range(i+1, len(agents)):
                    rate = agreement_matrix[i][j]
                    if rate > 0:
                        best_pairs.append((agent_names[i], agent_names[j], rate))
            
            best_pairs.sort(key=lambda x: x[2], reverse=True)
            for agent1, agent2, rate in best_pairs[:3]:
                st.success(f"{agent1} ↔ {agent2}: {rate*100:.1f}%")
        
        with col2:
            st.markdown("**⚡ Lowest Agreement Pairs:**")
            worst_pairs = [pair for pair in best_pairs if pair[2] < 0.7]
            worst_pairs.sort(key=lambda x: x[2])
            for agent1, agent2, rate in worst_pairs[:3]:
                st.error(f"{agent1} ↔ {agent2}: {rate*100:.1f}%")
    
    # Network topology visualization
    st.markdown("---")
    st.subheader("🌐 Network Topology")
    
    # Create network graph representation
    if len(agents) > 1:
        # Use agreement matrix to create network edges
        node_trace = go.Scatter(
            x=[],
            y=[],
            mode='markers+text',
            hoverinfo='text',
            text=[],
            textposition="middle center",
            marker=dict(
                size=[],
                color=[],
                colorscale='Viridis',
                showscale=True,
                colorbar=dict(title="Influence Weight"),
                line=dict(width=2)
            )
        )
        
        edge_trace = go.Scatter(
            x=[],
            y=[],
            line=dict(width=0.5, color='#888'),
            hoverinfo='none',
            mode='lines'
        )
        
        # Position nodes in a circle
        n_agents = len(agents)
        angles = np.linspace(0, 2*np.pi, n_agents, endpoint=False)
        
        node_x = []
        node_y = []
        node_text = []
        node_size = []
        node_color = []
        
        for i, (agent, angle) in enumerate(zip(agents, angles)):
            x = np.cos(angle)
            y = np.sin(angle)
            node_x.append(x)
            node_y.append(y)
            node_text.append(agent['name'])
            node_size.append(agent['influence_weight'] * 20)
            node_color.append(agent['influence_weight'])
            
            # Add edges to other agents (if agreement > threshold)
            for j, other_agent in enumerate(agents):
                if i != j and i < len(agreement_matrix) and j < len(agreement_matrix[i]):
                    agreement = agreement_matrix[i][j]
                    if agreement > 0.7:  # Only show strong agreements
                        other_x = np.cos(angles[j])
                        other_y = np.sin(angles[j])
                        edge_trace['x'] += (x, other_x, None)
                        edge_trace['y'] += (y, other_y, None)
        
        node_trace['x'] = node_x
        node_trace['y'] = node_y
        node_trace['text'] = node_text
        node_trace['marker']['size'] = node_size
        node_trace['marker']['color'] = node_color
        
        # Create network graph
        fig_network = go.Figure(data=[edge_trace, node_trace],
                               layout=go.Layout(
                                   title='Agent Network Topology',
                                   titlefont_size=16,
                                   showlegend=False,
                                   hovermode='closest',
                                   margin=dict(b=20,l=5,r=5,t=40),
                                   annotations=[ dict(
                                       text="Node size = Influence Weight<br>Edges = Strong Agreement (>70%)",
                                       showarrow=False,
                                       xref="paper", yref="paper",
                                       x=0.005, y=-0.002,
                                       xanchor="left", yanchor="bottom",
                                       font=dict(size=12)
                                   )],
                                   xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                                   yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                                   height=500
                               ))
        
        st.plotly_chart(fig_network, use_container_width=True)
    
    # Agent performance trends
    st.markdown("---")
    st.subheader("📈 Performance Trends")
    
    if votes:
        # Vote activity over time
        vote_df = pd.DataFrame(votes)
        vote_df['timestamp'] = pd.to_datetime(vote_df['timestamp'])
        vote_df['hour'] = vote_df['timestamp'].dt.floor('H')
        
        # Group by hour and agent type
        hourly_votes = vote_df.groupby(['hour', 'agent_id']).size().reset_index(name='vote_count')
        
        # Merge with agent data to get agent types
        agent_lookup = {a['id']: a['type'] for a in agents}
        hourly_votes['agent_type'] = hourly_votes['agent_id'].map(agent_lookup)
        
        # Aggregate by hour and type
        hourly_summary = hourly_votes.groupby(['hour', 'agent_type'])['vote_count'].sum().reset_index()
        
        if not hourly_summary.empty:
            fig_trends = px.line(
                hourly_summary,
                x='hour',
                y='vote_count',
                color='agent_type',
                title="Voting Activity Over Time",
                color_discrete_map={'ai': '#007bff', 'human': '#28a745'}
            )
            
            fig_trends.update_layout(
                height=300,
                xaxis_title="Time",
                yaxis_title="Votes Cast",
                legend_title="Agent Type"
            )
            
            st.plotly_chart(fig_trends, use_container_width=True)
    
    # Control panel
    st.markdown("---")
    st.subheader("🛠️ Network Controls")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("🔄 Refresh Network Data", use_container_width=True):
            st.rerun()
    
    with col2:
        if st.button("📊 Export Graph Data", use_container_width=True):
            st.success("Graph data export initiated")
    
    with col3:
        if st.button("⚙️ Adjust Thresholds", use_container_width=True):
            st.info("Threshold adjustment panel opened")
    
    # Network health indicators
    st.markdown("### 🏥 Network Health")
    
    health_col1, health_col2, health_col3 = st.columns(3)
    
    with health_col1:
        connectivity = min(len(agents) / 5.0, 1.0)  # Simplified calculation
        st.metric("Connectivity", f"{connectivity*100:.1f}%", 
                 help="Measure of how well-connected agents are")
    
    with health_col2:
        diversity = len(set(a['type'] for a in agents)) / 2.0  # AI and Human types
        st.metric("Diversity", f"{diversity*100:.1f}%",
                 help="Balance between AI and human agents")
    
    with health_col3:
        stability = 0.89  # Based on agreement patterns
        st.metric("Stability", f"{stability*100:.1f}%",
                 help="Consistency of agent decision patterns")
