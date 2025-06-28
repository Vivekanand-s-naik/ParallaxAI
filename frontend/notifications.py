import streamlit as st
import requests
from datetime import datetime, timedelta
import json

def show_notifications():
    st.title("🔔 Notifications Center")
    st.markdown("Real-time alerts and system notifications")
    
    # Fetch notifications
    try:
        notifications_response = requests.get("http://localhost:8000/api/notifications", timeout=5)
        if notifications_response.status_code != 200:
            st.error("Failed to fetch notifications")
            return
        
        notifications = notifications_response.json()
        
    except requests.exceptions.RequestException as e:
        st.error(f"Unable to connect to API: {e}")
        return
    
    # Notification overview
    st.subheader("📊 Notification Overview")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        total_notifications = len(notifications)
        st.metric("Total Notifications", total_notifications)
    
    with col2:
        unread_notifications = len([n for n in notifications if not n['is_read']])
        st.metric("Unread", unread_notifications, delta_color="off")
    
    with col3:
        high_priority = len([n for n in notifications if n.get('priority', 'medium') == 'high'])
        st.metric("High Priority", high_priority, delta_color="inverse")
    
    with col4:
        recent_notifications = len([n for n in notifications 
                                  if (datetime.now() - datetime.fromisoformat(n['timestamp'].replace('Z', '+00:00'))).hours < 24])
        st.metric("Last 24 Hours", recent_notifications)
    
    st.markdown("---")
    
    # Notification filters
    st.subheader("🔍 Filter Notifications")
    
    filter_col1, filter_col2, filter_col3, filter_col4 = st.columns(4)
    
    with filter_col1:
        status_filter = st.selectbox(
            "Status",
            ["All", "Unread", "Read"],
            index=0
        )
    
    with filter_col2:
        type_filter = st.selectbox(
            "Type",
            ["All", "bias_alert", "human_override", "decision_approved", "rule_violation", "system_alert"],
            index=0
        )
    
    with filter_col3:
        priority_filter = st.selectbox(
            "Priority",
            ["All", "high", "medium", "low"],
            index=0
        )
    
    with filter_col4:
        time_filter = st.selectbox(
            "Time Range",
            ["All Time", "Last Hour", "Last 24 Hours", "Last 7 Days"],
            index=0
        )
    
    # Apply filters
    filtered_notifications = notifications.copy()
    
    # Status filter
    if status_filter == "Unread":
        filtered_notifications = [n for n in filtered_notifications if not n['is_read']]
    elif status_filter == "Read":
        filtered_notifications = [n for n in filtered_notifications if n['is_read']]
    
    # Type filter
    if type_filter != "All":
        filtered_notifications = [n for n in filtered_notifications if n['type'] == type_filter]
    
    # Priority filter
    if priority_filter != "All":
        filtered_notifications = [n for n in filtered_notifications if n.get('priority', 'medium') == priority_filter]
    
    # Time filter
    if time_filter != "All Time":
        now = datetime.now()
        if time_filter == "Last Hour":
            cutoff = now - timedelta(hours=1)
        elif time_filter == "Last 24 Hours":
            cutoff = now - timedelta(days=1)
        elif time_filter == "Last 7 Days":
            cutoff = now - timedelta(days=7)
        
        filtered_notifications = [n for n in filtered_notifications 
                                if datetime.fromisoformat(n['timestamp'].replace('Z', '+00:00')) >= cutoff]
    
    # Quick actions
    action_col1, action_col2, action_col3 = st.columns(3)
    
    with action_col1:
        if st.button("✅ Mark All as Read", use_container_width=True):
            # Mark all filtered notifications as read
            for notification in filtered_notifications:
                if not notification['is_read']:
                    try:
                        requests.put(f"http://localhost:8000/api/notifications/{notification['id']}/read", timeout=5)
                    except:
                        pass
            st.success("All notifications marked as read!")
            st.rerun()
    
    with action_col2:
        if st.button("🔄 Refresh", use_container_width=True):
            st.rerun()
    
    with action_col3:
        if st.button("🗑️ Clear Read", use_container_width=True):
            st.info("Clear read notifications functionality would be implemented here")
    
    st.markdown("---")
    
    # Notifications display
    st.subheader(f"📋 Notifications ({len(filtered_notifications)} items)")
    
    if filtered_notifications:
        # Sort by timestamp (newest first) and priority
        def sort_key(notification):
            priority_weight = {'high': 3, 'medium': 2, 'low': 1}
            timestamp = datetime.fromisoformat(notification['timestamp'].replace('Z', '+00:00'))
            priority = priority_weight.get(notification.get('priority', 'medium'), 2)
            read_weight = 0 if notification['is_read'] else 1
            return (read_weight, priority, timestamp)
        
        sorted_notifications = sorted(filtered_notifications, key=sort_key, reverse=True)
        
        # Display notifications
        for notification in sorted_notifications:
            # Determine notification styling
            notification_type = notification['type']
            priority = notification.get('priority', 'medium')
            is_read = notification['is_read']
            
            # Icon mapping
            type_icons = {
                'bias_alert': '🚨',
                'human_override': '👤',
                'decision_approved': '✅',
                'rule_violation': '⚠️',
                'system_alert': '🔧'
            }
            icon = type_icons.get(notification_type, '📢')
            
            # Priority styling
            if priority == 'high':
                border_color = "#dc3545"
                bg_color = "#f8d7da"
            elif priority == 'medium':
                border_color = "#ffc107"
                bg_color = "#fff3cd"
            else:
                border_color = "#17a2b8"
                bg_color = "#d1ecf1"
            
            # Read status styling
            if is_read:
                opacity = "0.7"
                read_indicator = ""
            else:
                opacity = "1.0"
                read_indicator = '<span style="background-color: #dc3545; color: white; border-radius: 50%; padding: 2px 6px; font-size: 12px; margin-left: 10px;">NEW</span>'
            
            # Format timestamp
            timestamp = datetime.fromisoformat(notification['timestamp'].replace('Z', '+00:00'))
            time_ago = datetime.now() - timestamp
            
            if time_ago.days > 0:
                time_str = f"{time_ago.days} day(s) ago"
            elif time_ago.seconds > 3600:
                time_str = f"{time_ago.seconds // 3600} hour(s) ago"
            elif time_ago.seconds > 60:
                time_str = f"{time_ago.seconds // 60} minute(s) ago"
            else:
                time_str = "Just now"
            
            # Notification card
            with st.container():
                st.markdown(f"""
                <div style="border-left: 4px solid {border_color}; background-color: {bg_color}; padding: 15px; margin: 10px 0; border-radius: 4px; opacity: {opacity};">
                    <div style="display: flex; justify-content: between; align-items: center; margin-bottom: 8px;">
                        <div style="display: flex; align-items: center;">
                            <span style="font-size: 1.2em; margin-right: 10px;">{icon}</span>
                            <strong style="color: #333;">{notification['title']}</strong>
                            {read_indicator}
                        </div>
                        <div style="display: flex; align-items: center; gap: 10px;">
                            <small style="color: #6c757d;">{time_str}</small>
                            <span style="background-color: {border_color}; color: white; padding: 2px 8px; border-radius: 12px; font-size: 0.8em;">{priority.upper()}</span>
                        </div>
                    </div>
                    <p style="margin: 8px 0; color: #555;">{notification['message']}</p>
                    <div style="display: flex; justify-content: between; align-items: center; margin-top: 10px;">
                        <small style="color: #6c757d;">
                            Type: {notification_type.replace('_', ' ').title()} | 
                            ID: {notification['id'][:8]}...
                        </small>
                    </div>
                </div>
                """, unsafe_allow_html=True)
                
                # Action buttons for each notification
                notification_col1, notification_col2, notification_col3, notification_col4 = st.columns([1, 1, 1, 3])
                
                with notification_col1:
                    if not is_read:
                        if st.button("✅ Mark Read", key=f"read_{notification['id']}", use_container_width=True):
                            try:
                                read_response = requests.put(
                                    f"http://localhost:8000/api/notifications/{notification['id']}/read",
                                    timeout=5
                                )
                                if read_response.status_code == 200:
                                    st.success("Marked as read!")
                                    st.rerun()
                                else:
                                    st.error("Failed to mark as read")
                            except Exception as e:
                                st.error(f"Error: {e}")
                    else:
                        st.write("Read ✓")
                
                with notification_col2:
                    if st.button("📋 Details", key=f"details_{notification['id']}", use_container_width=True):
                        st.session_state[f"show_details_{notification['id']}"] = True
                
                with notification_col3:
                    if notification_type in ['bias_alert', 'rule_violation']:
                        if st.button("🔍 Investigate", key=f"investigate_{notification['id']}", use_container_width=True):
                            st.info("Investigation panel would open here")
                
                # Show detailed information if requested
                if st.session_state.get(f"show_details_{notification['id']}", False):
                    with st.expander("📋 Notification Details", expanded=True):
                        detail_col1, detail_col2 = st.columns(2)
                        
                        with detail_col1:
                            st.write(f"**Notification ID:** {notification['id']}")
                            st.write(f"**Type:** {notification['type']}")
                            st.write(f"**Priority:** {notification.get('priority', 'medium')}")
                            st.write(f"**Created:** {notification['timestamp']}")
                            st.write(f"**Read Status:** {'Read' if notification['is_read'] else 'Unread'}")
                        
                        with detail_col2:
                            if notification.get('metadata'):
                                st.write("**Metadata:**")
                                st.json(notification['metadata'])
                            else:
                                st.info("No additional metadata available")
                        
                        if st.button("❌ Close Details", key=f"close_{notification['id']}"):
                            st.session_state[f"show_details_{notification['id']}"] = False
                            st.rerun()
                
                st.markdown("---")
    else:
        st.info("No notifications match the current filters")
    
    st.markdown("---")
    
    # Notification analytics
    st.subheader("📈 Notification Analytics")
    
    if notifications:
        analytics_col1, analytics_col2 = st.columns(2)
        
        with analytics_col1:
            # Notification type distribution
            type_counts = {}
            for notification in notifications:
                notif_type = notification['type']
                type_counts[notif_type] = type_counts.get(notif_type, 0) + 1
            
            if type_counts:
                import plotly.express as px
                
                # Format type names for display
                display_names = [name.replace('_', ' ').title() for name in type_counts.keys()]
                
                fig_types = px.pie(
                    values=list(type_counts.values()),
                    names=display_names,
                    title="Notifications by Type"
                )
                fig_types.update_layout(height=350)
                st.plotly_chart(fig_types, use_container_width=True)
        
        with analytics_col2:
            # Priority distribution
            priority_counts = {}
            for notification in notifications:
                priority = notification.get('priority', 'medium')
                priority_counts[priority] = priority_counts.get(priority, 0) + 1
            
            if priority_counts:
                import plotly.express as px
                
                fig_priority = px.bar(
                    x=list(priority_counts.keys()),
                    y=list(priority_counts.values()),
                    title="Notifications by Priority",
                    color=list(priority_counts.keys()),
                    color_discrete_map={'high': '#dc3545', 'medium': '#ffc107', 'low': '#28a745'}
                )
                fig_priority.update_layout(height=350, showlegend=False)
                st.plotly_chart(fig_priority, use_container_width=True)
        
        # Notification timeline
        if len(notifications) > 1:
            st.markdown("### 📅 Notification Timeline")
            
            # Group notifications by hour for timeline view
            timeline_data = {}
            for notification in notifications:
                timestamp = datetime.fromisoformat(notification['timestamp'].replace('Z', '+00:00'))
                hour_key = timestamp.replace(minute=0, second=0, microsecond=0)
                
                if hour_key not in timeline_data:
                    timeline_data[hour_key] = {'total': 0, 'high_priority': 0, 'unread': 0}
                
                timeline_data[hour_key]['total'] += 1
                if notification.get('priority') == 'high':
                    timeline_data[hour_key]['high_priority'] += 1
                if not notification['is_read']:
                    timeline_data[hour_key]['unread'] += 1
            
            if timeline_data:
                import plotly.graph_objects as go
                
                times = sorted(timeline_data.keys())
                total_counts = [timeline_data[t]['total'] for t in times]
                high_priority_counts = [timeline_data[t]['high_priority'] for t in times]
                unread_counts = [timeline_data[t]['unread'] for t in times]
                
                fig_timeline = go.Figure()
                
                fig_timeline.add_trace(go.Scatter(
                    x=times,
                    y=total_counts,
                    mode='lines+markers',
                    name='Total Notifications',
                    line=dict(color='#007bff')
                ))
                
                fig_timeline.add_trace(go.Scatter(
                    x=times,
                    y=high_priority_counts,
                    mode='lines+markers',
                    name='High Priority',
                    line=dict(color='#dc3545')
                ))
                
                fig_timeline.add_trace(go.Scatter(
                    x=times,
                    y=unread_counts,
                    mode='lines+markers',
                    name='Unread',
                    line=dict(color='#ffc107')
                ))
                
                fig_timeline.update_layout(
                    title="Notification Activity Over Time",
                    xaxis_title="Time",
                    yaxis_title="Number of Notifications",
                    height=400,
                    hovermode='x unified'
                )
                
                st.plotly_chart(fig_timeline, use_container_width=True)
    
    # Notification settings
    st.markdown("---")
    st.subheader("⚙️ Notification Settings")
    
    settings_col1, settings_col2 = st.columns(2)
    
    with settings_col1:
        st.markdown("**Alert Preferences:**")
        
        email_alerts = st.checkbox("Email Notifications", value=True)
        push_alerts = st.checkbox("Push Notifications", value=True)
        sms_alerts = st.checkbox("SMS for High Priority", value=False)
        
        st.markdown("**Auto-Mark Read:**")
        auto_read_bias = st.checkbox("Auto-mark bias alerts after 24h", value=False)
        auto_read_system = st.checkbox("Auto-mark system alerts after 1h", value=True)
    
    with settings_col2:
        st.markdown("**Priority Thresholds:**")
        
        bias_threshold = st.slider("Bias Alert Threshold", 0.0, 1.0, 0.7, 0.01)
        override_threshold = st.slider("Override Alert Threshold", 1, 10, 3)
        
        st.markdown("**Notification Retention:**")
        retention_days = st.number_input("Keep notifications for (days)", min_value=1, max_value=365, value=30)
        
        if st.button("💾 Save Settings", type="primary"):
            st.success("Notification settings saved!")
    
    # Create new notification (for testing)
    st.markdown("---")
    st.subheader("🧪 Create Test Notification")
    
    with st.expander("Create Test Notification"):
        test_col1, test_col2 = st.columns(2)
        
        with test_col1:
            test_type = st.selectbox("Type", ["bias_alert", "human_override", "decision_approved", "rule_violation", "system_alert"])
            test_priority = st.selectbox("Priority", ["low", "medium", "high"])
            test_title = st.text_input("Title", value="Test Notification")
        
        with test_col2:
            test_message = st.text_area("Message", value="This is a test notification created from the UI.")
            
            if st.button("📤 Send Test Notification", type="primary"):
                try:
                    test_notification_data = {
                        "type": test_type,
                        "title": test_title,
                        "message": test_message,
                        "priority": test_priority
                    }
                    
                    test_response = requests.post(
                        "http://localhost:8000/api/notifications",
                        json=test_notification_data,
                        timeout=5
                    )
                    
                    if test_response.status_code == 200:
                        st.success("Test notification created successfully!")
                        st.rerun()
                    else:
                        st.error("Failed to create test notification")
                        
                except Exception as e:
                    st.error(f"Error creating test notification: {e}")
    
    # Footer
    st.markdown("---")
    st.caption(f"Notifications Center | {len(notifications)} total notifications | Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
