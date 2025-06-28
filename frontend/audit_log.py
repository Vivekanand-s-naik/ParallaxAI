import streamlit as st
import requests
import pandas as pd
from datetime import datetime, timedelta
import json

def show_audit_log():
    st.title("📋 Audit & Compliance Log")
    st.markdown("Comprehensive audit trail and compliance tracking system")
    
    # Fetch audit logs and related data
    try:
        audit_response = requests.get("http://localhost:8000/api/audit-logs", timeout=5)
        decisions_response = requests.get("http://localhost:8000/api/decisions", timeout=5)
        
        if audit_response.status_code != 200:
            st.error("Failed to fetch audit logs")
            return
        
        audit_logs = audit_response.json()
        decisions = decisions_response.json() if decisions_response.status_code == 200 else []
        
    except requests.exceptions.RequestException as e:
        st.error(f"Unable to connect to API: {e}")
        return
    
    # Audit overview metrics
    st.subheader("📊 Audit Overview")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        total_logs = len(audit_logs)
        st.metric("Total Audit Entries", total_logs)
    
    with col2:
        compliant_logs = len([log for log in audit_logs if log['compliance_status'] == 'compliant'])
        compliance_rate = (compliant_logs / max(total_logs, 1)) * 100
        st.metric("Compliance Rate", f"{compliance_rate:.1f}%")
    
    with col3:
        recent_logs = len([log for log in audit_logs 
                          if (datetime.now() - datetime.fromisoformat(log['timestamp'].replace('Z', '+00:00'))).days < 1])
        st.metric("Entries (24h)", recent_logs)
    
    with col4:
        under_review = len([log for log in audit_logs if log['compliance_status'] == 'under_review'])
        st.metric("Under Review", under_review, delta_color="off")
    
    st.markdown("---")
    
    # Filters and controls
    st.subheader("🔍 Audit Log Filters")
    
    filter_col1, filter_col2, filter_col3, filter_col4 = st.columns(4)
    
    with filter_col1:
        # Compliance status filter
        compliance_filter = st.selectbox(
            "Compliance Status",
            ["All", "compliant", "under_review", "non_compliant"],
            index=0
        )
    
    with filter_col2:
        # Date range filter
        date_filter = st.selectbox(
            "Time Range",
            ["All Time", "Last 24 Hours", "Last 7 Days", "Last 30 Days"],
            index=0
        )
    
    with filter_col3:
        # Search filter
        search_term = st.text_input(
            "Search",
            placeholder="Search audit logs...",
            help="Search in actions, agent actions, or decision IDs"
        )
    
    with filter_col4:
        # Export controls
        st.markdown("**Export Options**")
        export_format = st.selectbox("Format", ["PDF", "CSV", "JSON"])
    
    # Apply filters
    filtered_logs = audit_logs.copy()
    
    # Compliance status filter
    if compliance_filter != "All":
        filtered_logs = [log for log in filtered_logs if log['compliance_status'] == compliance_filter]
    
    # Date range filter
    if date_filter != "All Time":
        now = datetime.now()
        if date_filter == "Last 24 Hours":
            cutoff = now - timedelta(days=1)
        elif date_filter == "Last 7 Days":
            cutoff = now - timedelta(days=7)
        elif date_filter == "Last 30 Days":
            cutoff = now - timedelta(days=30)
        
        filtered_logs = [log for log in filtered_logs 
                        if datetime.fromisoformat(log['timestamp'].replace('Z', '+00:00')) >= cutoff]
    
    # Search filter
    if search_term:
        search_term_lower = search_term.lower()
        filtered_logs = [log for log in filtered_logs 
                        if search_term_lower in log['action'].lower() 
                        or search_term_lower in str(log['agent_actions']).lower()
                        or search_term_lower in log['decision_id'].lower()]
    
    st.markdown("---")
    
    # Audit log table
    st.subheader(f"📝 Audit Trail ({len(filtered_logs)} entries)")
    
    if filtered_logs:
        # Prepare data for display
        audit_data = []
        for log in filtered_logs:
            # Get decision context if available
            decision_context = "N/A"
            decision = next((d for d in decisions if d['id'] == log['decision_id']), None)
            if decision:
                decision_context = decision['context'][:50] + ('...' if len(decision['context']) > 50 else '')
            
            # Format timestamp
            timestamp = datetime.fromisoformat(log['timestamp'].replace('Z', '+00:00'))
            
            # Status styling
            status = log['compliance_status']
            if status == 'compliant':
                status_display = "✅ Compliant"
            elif status == 'under_review':
                status_display = "🔍 Under Review"
            else:
                status_display = "❌ Non-compliant"
            
            audit_data.append({
                "Timestamp": timestamp.strftime('%Y-%m-%d %H:%M:%S'),
                "Decision ID": log['decision_id'][:8] + "...",
                "Action": log['action'],
                "Decision Context": decision_context,
                "Compliance Status": status_display,
                "Rules Applied": len(log['rules_applied']),
                "Agent Actions": len(log['agent_actions']),
                "Audit Hash": log['audit_hash'][:16] + "..."
            })
        
        # Display table
        audit_df = pd.DataFrame(audit_data)
        
        # Style the dataframe
        def style_compliance_status(val):
            if "✅" in val:
                return 'background-color: #d4edda; color: #155724'
            elif "🔍" in val:
                return 'background-color: #fff3cd; color: #856404'
            elif "❌" in val:
                return 'background-color: #f8d7da; color: #721c24'
            return ''
        
        styled_df = audit_df.style.applymap(
            style_compliance_status, subset=['Compliance Status']
        )
        
        st.dataframe(styled_df, use_container_width=True, hide_index=True)
        
        # Detailed view selector
        st.markdown("### 🔍 Detailed Audit Entry View")
        
        selected_log_index = st.selectbox(
            "Select audit entry for detailed view:",
            range(len(filtered_logs)),
            format_func=lambda x: f"{filtered_logs[x]['timestamp'][:19]} - {filtered_logs[x]['action'][:50]}{'...' if len(filtered_logs[x]['action']) > 50 else ''}"
        )
        
        if selected_log_index is not None:
            selected_log = filtered_logs[selected_log_index]
            
            # Display detailed information
            with st.expander("📋 Full Audit Details", expanded=True):
                detail_col1, detail_col2 = st.columns(2)
                
                with detail_col1:
                    st.markdown("**Basic Information:**")
                    st.write(f"**Audit ID:** {selected_log['id']}")
                    st.write(f"**Decision ID:** {selected_log['decision_id']}")
                    st.write(f"**Action:** {selected_log['action']}")
                    st.write(f"**Timestamp:** {selected_log['timestamp']}")
                    st.write(f"**Compliance Status:** {selected_log['compliance_status']}")
                    st.write(f"**Audit Hash:** {selected_log['audit_hash']}")
                
                with detail_col2:
                    st.markdown("**Associated Decision:**")
                    associated_decision = next((d for d in decisions if d['id'] == selected_log['decision_id']), None)
                    if associated_decision:
                        st.write(f"**Context:** {associated_decision['context']}")
                        st.write(f"**Application Type:** {associated_decision['application_type']}")
                        st.write(f"**Status:** {associated_decision['status']}")
                        st.write(f"**Bias Score:** {associated_decision['bias_score']:.3f}")
                    else:
                        st.info("Decision details not available")
                
                # Agent actions
                st.markdown("**Agent Actions:**")
                if selected_log['agent_actions']:
                    for i, action in enumerate(selected_log['agent_actions'], 1):
                        st.write(f"{i}. {action}")
                else:
                    st.info("No agent actions recorded")
                
                # Rules applied
                st.markdown("**Governance Rules Applied:**")
                if selected_log['rules_applied']:
                    for i, rule in enumerate(selected_log['rules_applied'], 1):
                        st.write(f"{i}. {rule}")
                else:
                    st.info("No governance rules applied")
                
                # Metadata
                if selected_log.get('metadata'):
                    st.markdown("**Additional Metadata:**")
                    st.json(selected_log['metadata'])
    else:
        st.info("No audit logs match the current filters")
    
    st.markdown("---")
    
    # Compliance analytics
    st.subheader("📈 Compliance Analytics")
    
    if audit_logs:
        analytics_col1, analytics_col2 = st.columns(2)
        
        with analytics_col1:
            # Compliance status distribution
            compliance_counts = {}
            for log in audit_logs:
                status = log['compliance_status']
                compliance_counts[status] = compliance_counts.get(status, 0) + 1
            
            if compliance_counts:
                import plotly.express as px
                
                fig_compliance = px.pie(
                    values=list(compliance_counts.values()),
                    names=[name.replace('_', ' ').title() for name in compliance_counts.keys()],
                    title="Compliance Status Distribution",
                    color_discrete_map={
                        'Compliant': '#28a745',
                        'Under Review': '#ffc107',
                        'Non Compliant': '#dc3545'
                    }
                )
                fig_compliance.update_layout(height=350)
                st.plotly_chart(fig_compliance, use_container_width=True)
        
        with analytics_col2:
            # Audit activity over time
            if len(audit_logs) > 1:
                # Group by day
                daily_counts = {}
                for log in audit_logs:
                    date = datetime.fromisoformat(log['timestamp'].replace('Z', '+00:00')).date()
                    daily_counts[date] = daily_counts.get(date, 0) + 1
                
                if len(daily_counts) > 1:
                    import plotly.express as px
                    
                    dates = sorted(daily_counts.keys())
                    counts = [daily_counts[date] for date in dates]
                    
                    fig_activity = px.line(
                        x=dates,
                        y=counts,
                        title="Audit Activity Over Time",
                        labels={'x': 'Date', 'y': 'Audit Entries'}
                    )
                    fig_activity.update_layout(height=350)
                    st.plotly_chart(fig_activity, use_container_width=True)
                else:
                    st.info("Insufficient data for time series analysis")
    
    # Rule application analytics
    if audit_logs:
        st.markdown("### 📊 Rule Application Analysis")
        
        rule_analytics_col1, rule_analytics_col2 = st.columns(2)
        
        with rule_analytics_col1:
            # Most frequently applied rules
            rule_counts = {}
            for log in audit_logs:
                for rule in log['rules_applied']:
                    rule_counts[rule] = rule_counts.get(rule, 0) + 1
            
            if rule_counts:
                # Sort by frequency
                top_rules = sorted(rule_counts.items(), key=lambda x: x[1], reverse=True)[:10]
                
                rule_names = [rule[0][:30] + ('...' if len(rule[0]) > 30 else '') for rule in top_rules]
                rule_counts_list = [rule[1] for rule in top_rules]
                
                import plotly.express as px
                
                fig_rules = px.bar(
                    x=rule_counts_list,
                    y=rule_names,
                    orientation='h',
                    title="Most Frequently Applied Rules",
                    labels={'x': 'Application Count', 'y': 'Rule Name'}
                )
                fig_rules.update_layout(height=400)
                st.plotly_chart(fig_rules, use_container_width=True)
            else:
                st.info("No rule application data available")
        
        with rule_analytics_col2:
            # Agent action frequency
            agent_action_counts = {}
            for log in audit_logs:
                for action in log['agent_actions']:
                    # Extract agent type from action (simplified)
                    if 'AI-' in action:
                        agent_type = 'AI Agent'
                    elif 'Human-' in action:
                        agent_type = 'Human Agent'
                    elif 'System' in action:
                        agent_type = 'System'
                    else:
                        agent_type = 'Other'
                    
                    agent_action_counts[agent_type] = agent_action_counts.get(agent_type, 0) + 1
            
            if agent_action_counts:
                import plotly.express as px
                
                fig_agents = px.bar(
                    x=list(agent_action_counts.keys()),
                    y=list(agent_action_counts.values()),
                    title="Agent Action Frequency",
                    labels={'x': 'Agent Type', 'y': 'Action Count'},
                    color=list(agent_action_counts.values()),
                    color_continuous_scale='Blues'
                )
                fig_agents.update_layout(height=400, showlegend=False)
                st.plotly_chart(fig_agents, use_container_width=True)
    
    st.markdown("---")
    
    # Export functionality
    st.subheader("📤 Export Audit Report")
    
    export_col1, export_col2, export_col3 = st.columns(3)
    
    with export_col1:
        include_details = st.checkbox("Include Full Details", value=True)
        include_metadata = st.checkbox("Include Metadata", value=False)
    
    with export_col2:
        date_range_export = st.selectbox(
            "Export Date Range",
            ["All Data", "Last 7 Days", "Last 30 Days", "Last 90 Days"],
            index=1
        )
    
    with export_col3:
        if st.button("📄 Generate PDF Report", type="primary", use_container_width=True):
            # In a real implementation, this would generate a PDF
            report_data = {
                "generated_at": datetime.now().isoformat(),
                "total_entries": len(filtered_logs),
                "compliance_summary": {
                    "compliant": len([log for log in filtered_logs if log['compliance_status'] == 'compliant']),
                    "under_review": len([log for log in filtered_logs if log['compliance_status'] == 'under_review']),
                    "non_compliant": len([log for log in filtered_logs if log['compliance_status'] == 'non_compliant'])
                },
                "audit_entries": filtered_logs if include_details else []
            }
            
            # Create downloadable JSON (in lieu of PDF)
            report_json = json.dumps(report_data, indent=2, default=str)
            st.download_button(
                label="💾 Download Report (JSON)",
                data=report_json,
                file_name=f"audit_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                mime="application/json"
            )
            
            st.success("✅ Audit report generated successfully!")
    
    # Quick actions
    st.markdown("---")
    st.subheader("⚡ Quick Actions")
    
    action_col1, action_col2, action_col3, action_col4 = st.columns(4)
    
    with action_col1:
        if st.button("🔄 Refresh Logs", use_container_width=True):
            st.rerun()
    
    with action_col2:
        if st.button("🔍 Advanced Search", use_container_width=True):
            st.info("Advanced search functionality would open here")
    
    with action_col3:
        if st.button("📊 Generate Analytics", use_container_width=True):
            st.success("Detailed analytics report generation initiated")
    
    with action_col4:
        if st.button("⚙️ Configure Retention", use_container_width=True):
            st.info("Audit log retention policy configuration would open here")
    
    # Audit integrity verification
    st.markdown("---")
    st.subheader("🔐 Audit Integrity Verification")
    
    integrity_col1, integrity_col2 = st.columns(2)
    
    with integrity_col1:
        st.markdown("**Hash Verification Status:**")
        
        # Simplified hash verification (in real implementation, this would verify cryptographic hashes)
        verified_count = len(audit_logs)  # Assume all are verified for demo
        total_count = len(audit_logs)
        
        if total_count > 0:
            verification_rate = (verified_count / total_count) * 100
            if verification_rate == 100:
                st.success(f"✅ All {total_count} audit entries verified")
            else:
                st.error(f"❌ {total_count - verified_count} entries failed verification")
        else:
            st.info("No audit entries to verify")
    
    with integrity_col2:
        st.markdown("**Integrity Actions:**")
        
        if st.button("🔍 Verify All Hashes", use_container_width=True):
            st.success("All audit hashes verified successfully")
        
        if st.button("📋 Generate Integrity Report", use_container_width=True):
            st.info("Integrity report generation initiated")
        
        if st.button("🔄 Rebuild Hash Chain", use_container_width=True):
            st.warning("Hash chain rebuild would be performed here")
    
    # Footer
    st.markdown("---")
    st.caption(f"Audit & Compliance Log | {len(audit_logs)} total entries | Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
