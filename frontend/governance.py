import streamlit as st
import requests
import yaml
import json
from datetime import datetime

def show_governance():
    st.title("⚙️ Governance Console")
    st.markdown("Rule management and policy configuration system")
    
    # Fetch governance rules
    try:
        rules_response = requests.get("http://localhost:8000/api/governance-rules", timeout=5)
        if rules_response.status_code != 200:
            st.error("Failed to fetch governance rules")
            return
        
        rules = rules_response.json()
        
    except requests.exceptions.RequestException as e:
        st.error(f"Unable to connect to API: {e}")
        return
    
    # Governance overview
    st.subheader("📊 Governance Overview")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        total_rules = len(rules)
        st.metric("Total Rules", total_rules)
    
    with col2:
        active_rules = len([r for r in rules if r['is_active']])
        st.metric("Active Rules", active_rules)
    
    with col3:
        inactive_rules = len([r for r in rules if not r['is_active']])
        st.metric("Inactive Rules", inactive_rules)
    
    with col4:
        # Calculate total applications (simplified)
        total_applications = sum(r.get('applied_count', 0) for r in rules)
        st.metric("Total Applications", total_applications)
    
    st.markdown("---")
    
    # Two-column layout for rule editor and active rules
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.subheader("📝 Rule Editor")
        
        # Rule creation/editing form
        with st.form("rule_form", clear_on_submit=True):
            st.markdown("**Create New Governance Rule**")
            
            rule_name = st.text_input(
                "Rule Name*",
                placeholder="e.g., High Value Transaction Review",
                help="Enter a descriptive name for the rule"
            )
            
            rule_description = st.text_area(
                "Description*",
                placeholder="Describe what this rule does and when it applies...",
                help="Provide a clear description of the rule's purpose"
            )
            
            rule_context = st.selectbox(
                "Context*",
                ["general", "financial", "hiring", "healthcare", "legal", "risk_assessment"],
                help="Select the application context for this rule"
            )
            
            st.markdown("**Rule Definition (YAML)**")
            rule_definition = st.text_area(
                "YAML Configuration*",
                value="""conditions:
  - bias_score > 0.7
  - transaction_amount > 100000
actions:
  - require_human_review: true
  - escalate_to: senior_reviewer
  - notify: compliance_team
priority: 1
metadata:
  created_by: system_admin
  version: "1.0"
""",
                height=200,
                help="Define the rule logic in YAML format"
            )
            
            rule_priority = st.slider(
                "Priority Level",
                min_value=1,
                max_value=10,
                value=5,
                help="Higher numbers indicate higher priority"
            )
            
            is_active = st.checkbox("Activate Rule Immediately", value=True)
            
            # Form submission
            col_submit, col_validate = st.columns(2)
            
            with col_submit:
                submitted = st.form_submit_button("💾 Save Rule", type="primary", use_container_width=True)
            
            with col_validate:
                validate_yaml = st.form_submit_button("✅ Validate YAML", use_container_width=True)
            
            # Validate YAML
            if validate_yaml:
                try:
                    yaml.safe_load(rule_definition)
                    st.success("✅ YAML syntax is valid!")
                except yaml.YAMLError as e:
                    st.error(f"❌ YAML syntax error: {e}")
            
            # Submit rule
            if submitted:
                if rule_name and rule_description and rule_definition:
                    # Validate YAML before submission
                    try:
                        yaml.safe_load(rule_definition)
                        
                        # Create rule data
                        rule_data = {
                            "name": rule_name,
                            "description": rule_description,
                            "context": rule_context,
                            "rule_definition": rule_definition,
                            "is_active": is_active,
                            "priority": rule_priority
                        }
                        
                        # Submit to API
                        create_response = requests.post(
                            "http://localhost:8000/api/governance-rules",
                            json=rule_data,
                            timeout=5
                        )
                        
                        if create_response.status_code == 200:
                            st.success("✅ Rule created successfully!")
                            st.rerun()
                        else:
                            st.error("❌ Failed to create rule")
                            
                    except yaml.YAMLError as e:
                        st.error(f"❌ Invalid YAML syntax: {e}")
                    except Exception as e:
                        st.error(f"❌ Error creating rule: {e}")
                else:
                    st.warning("⚠️ Please fill in all required fields")
    
    with col2:
        st.subheader("📋 Active Rules")
        
        if rules:
            # Filter and sort rules
            show_all = st.checkbox("Show Inactive Rules", value=False)
            
            if show_all:
                display_rules = rules
            else:
                display_rules = [r for r in rules if r['is_active']]
            
            # Sort by priority and name
            display_rules.sort(key=lambda x: (-x.get('priority', 1), x['name']))
            
            # Display rules
            for rule in display_rules:
                with st.expander(f"{'🟢' if rule['is_active'] else '🔴'} {rule['name']}", expanded=False):
                    # Rule details
                    col_info, col_actions = st.columns([2, 1])
                    
                    with col_info:
                        st.write(f"**Description:** {rule['description']}")
                        st.write(f"**Context:** {rule['context'].replace('_', ' ').title()}")
                        st.write(f"**Priority:** {rule.get('priority', 1)}")
                        st.write(f"**Applied Count:** {rule.get('applied_count', 0)} times")
                        
                        created_at = datetime.fromisoformat(rule['created_at'].replace('Z', '+00:00'))
                        updated_at = datetime.fromisoformat(rule['updated_at'].replace('Z', '+00:00'))
                        
                        st.write(f"**Created:** {created_at.strftime('%Y-%m-%d %H:%M')}")
                        st.write(f"**Updated:** {updated_at.strftime('%Y-%m-%d %H:%M')}")
                    
                    with col_actions:
                        # Toggle active status
                        current_status = rule['is_active']
                        new_status = st.toggle(
                            "Active",
                            value=current_status,
                            key=f"toggle_{rule['id']}"
                        )
                        
                        if new_status != current_status:
                            try:
                                update_response = requests.put(
                                    f"http://localhost:8000/api/governance-rules/{rule['id']}",
                                    json={"is_active": new_status},
                                    timeout=5
                                )
                                
                                if update_response.status_code == 200:
                                    st.success("Status updated!")
                                    st.rerun()
                                else:
                                    st.error("Update failed")
                            except Exception as e:
                                st.error(f"Error: {e}")
                        
                        # Edit button
                        if st.button("✏️ Edit", key=f"edit_{rule['id']}", use_container_width=True):
                            st.session_state[f"editing_{rule['id']}"] = True
                        
                        # Delete button
                        if st.button("🗑️ Delete", key=f"delete_{rule['id']}", use_container_width=True, type="secondary"):
                            st.warning(f"Delete rule '{rule['name']}'?")
                    
                    # Rule definition display
                    st.markdown("**Rule Definition:**")
                    try:
                        # Parse and format YAML
                        parsed_yaml = yaml.safe_load(rule['rule_definition'])
                        st.code(yaml.dump(parsed_yaml, default_flow_style=False), language='yaml')
                    except:
                        st.code(rule['rule_definition'], language='yaml')
                    
                    # Edit mode
                    if st.session_state.get(f"editing_{rule['id']}", False):
                        st.markdown("---")
                        st.markdown("**Edit Rule:**")
                        
                        with st.form(f"edit_form_{rule['id']}"):
                            edit_name = st.text_input("Name", value=rule['name'])
                            edit_description = st.text_area("Description", value=rule['description'])
                            edit_context = st.selectbox(
                                "Context",
                                ["general", "financial", "hiring", "healthcare", "legal", "risk_assessment"],
                                index=["general", "financial", "hiring", "healthcare", "legal", "risk_assessment"].index(rule['context'])
                            )
                            edit_definition = st.text_area("Rule Definition", value=rule['rule_definition'], height=150)
                            edit_priority = st.slider("Priority", 1, 10, rule.get('priority', 1))
                            
                            col_save, col_cancel = st.columns(2)
                            
                            with col_save:
                                save_edit = st.form_submit_button("💾 Save Changes", type="primary")
                            
                            with col_cancel:
                                cancel_edit = st.form_submit_button("❌ Cancel")
                            
                            if save_edit:
                                try:
                                    yaml.safe_load(edit_definition)
                                    
                                    update_data = {
                                        "name": edit_name,
                                        "description": edit_description,
                                        "context": edit_context,
                                        "rule_definition": edit_definition,
                                        "priority": edit_priority
                                    }
                                    
                                    update_response = requests.put(
                                        f"http://localhost:8000/api/governance-rules/{rule['id']}",
                                        json=update_data,
                                        timeout=5
                                    )
                                    
                                    if update_response.status_code == 200:
                                        st.success("Rule updated successfully!")
                                        st.session_state[f"editing_{rule['id']}"] = False
                                        st.rerun()
                                    else:
                                        st.error("Failed to update rule")
                                        
                                except yaml.YAMLError as e:
                                    st.error(f"Invalid YAML: {e}")
                                except Exception as e:
                                    st.error(f"Error updating rule: {e}")
                            
                            if cancel_edit:
                                st.session_state[f"editing_{rule['id']}"] = False
                                st.rerun()
        else:
            st.info("No governance rules found. Create your first rule using the form on the left.")
    
    st.markdown("---")
    
    # Rule templates section
    st.subheader("📚 Rule Templates")
    
    # Predefined rule templates
    templates = {
        "High Value Decision Review": {
            "description": "Require human review for high-value decisions",
            "context": "financial",
            "rule_definition": """conditions:
  - transaction_amount > 100000
  - risk_level: high
actions:
  - require_human_review: true
  - escalate_to: senior_reviewer
  - notify: compliance_team
priority: 1"""
        },
        "Bias Detection Trigger": {
            "description": "Automatically trigger bias review when bias score is high",
            "context": "general",
            "rule_definition": """conditions:
  - bias_score > 0.7
actions:
  - trigger_bias_review: true
  - notify: bias_review_committee
  - flag_for_audit: true
priority: 2"""
        },
        "AI Consensus Requirement": {
            "description": "Require consensus among AI agents before approval",
            "context": "general",
            "rule_definition": """conditions:
  - ai_consensus_rate < 0.8
  - decision_type: approval
actions:
  - require_additional_review: true
  - escalate_to: human_reviewer
priority: 3"""
        },
        "Emergency Override": {
            "description": "Allow emergency override with proper justification",
            "context": "general",
            "rule_definition": """conditions:
  - emergency_flag: true
  - override_requested: true
actions:
  - allow_override: true
  - require_justification: true
  - notify: emergency_response_team
  - create_audit_log: true
priority: 10"""
        }
    }
    
    template_cols = st.columns(2)
    
    for i, (template_name, template_data) in enumerate(templates.items()):
        with template_cols[i % 2]:
            with st.expander(f"📄 {template_name}"):
                st.write(f"**Description:** {template_data['description']}")
                st.write(f"**Context:** {template_data['context']}")
                st.code(template_data['rule_definition'], language='yaml')
                
                if st.button(f"Use Template", key=f"template_{i}", use_container_width=True):
                    # Pre-fill the form with template data
                    st.session_state['template_name'] = template_name
                    st.session_state['template_description'] = template_data['description']
                    st.session_state['template_context'] = template_data['context']
                    st.session_state['template_definition'] = template_data['rule_definition']
                    st.success(f"Template '{template_name}' loaded! Scroll up to the rule editor.")
    
    # Rule analytics
    st.markdown("---")
    st.subheader("📈 Rule Analytics")
    
    if rules:
        analytics_col1, analytics_col2 = st.columns(2)
        
        with analytics_col1:
            # Rule usage chart
            rule_usage = {r['name'][:20] + ('...' if len(r['name']) > 20 else ''): r.get('applied_count', 0) for r in rules}
            
            if any(usage > 0 for usage in rule_usage.values()):
                import plotly.express as px
                
                fig_usage = px.bar(
                    x=list(rule_usage.values()),
                    y=list(rule_usage.keys()),
                    orientation='h',
                    title="Rule Application Frequency",
                    labels={'x': 'Application Count', 'y': 'Rule Name'}
                )
                fig_usage.update_layout(height=300)
                st.plotly_chart(fig_usage, use_container_width=True)
            else:
                st.info("No rule application data available yet")
        
        with analytics_col2:
            # Rule context distribution
            context_counts = {}
            for rule in rules:
                context = rule['context']
                context_counts[context] = context_counts.get(context, 0) + 1
            
            if context_counts:
                import plotly.express as px
                
                fig_context = px.pie(
                    values=list(context_counts.values()),
                    names=list(context_counts.keys()),
                    title="Rules by Context"
                )
                fig_context.update_layout(height=300)
                st.plotly_chart(fig_context, use_container_width=True)
    
    # Quick actions
    st.markdown("---")
    st.subheader("⚡ Quick Actions")
    
    action_col1, action_col2, action_col3, action_col4 = st.columns(4)
    
    with action_col1:
        if st.button("📊 Export Rules", use_container_width=True):
            # Create downloadable rules export
            rules_export = json.dumps(rules, indent=2, default=str)
            st.download_button(
                label="💾 Download Rules JSON",
                data=rules_export,
                file_name=f"governance_rules_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                mime="application/json"
            )
    
    with action_col2:
        if st.button("🔄 Refresh Rules", use_container_width=True):
            st.rerun()
    
    with action_col3:
        if st.button("✅ Validate All Rules", use_container_width=True):
            valid_count = 0
            invalid_count = 0
            
            for rule in rules:
                try:
                    yaml.safe_load(rule['rule_definition'])
                    valid_count += 1
                except:
                    invalid_count += 1
            
            if invalid_count == 0:
                st.success(f"✅ All {valid_count} rules are valid!")
            else:
                st.warning(f"⚠️ Found {invalid_count} invalid rules out of {len(rules)} total")
    
    with action_col4:
        if st.button("🚨 Emergency Disable All", use_container_width=True, type="secondary"):
            st.warning("This will disable all governance rules. Are you sure?")
            if st.button("Confirm Emergency Disable", type="secondary"):
                st.error("Emergency disable functionality would be implemented here")
    
    # Footer with system info
    st.markdown("---")
    st.caption(f"Governance Console | {len(rules)} total rules | Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
