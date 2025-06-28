from typing import Dict, Any, List
from datetime import datetime, timedelta
import uuid
import json

from models import *

class DataStore:
    def __init__(self):
        # In-memory storage
        self.decisions: Dict[str, Decision] = {}
        self.agents: Dict[str, Agent] = {}
        self.votes: Dict[str, Vote] = {}
        self.governance_rules: Dict[str, GovernanceRule] = {}
        self.audit_logs: Dict[str, AuditLog] = {}
        self.notifications: Dict[str, Notification] = {}
        
    def initialize_sample_data(self):
        """Initialize with sample data for demonstration"""
        
        # Create sample agents
        ai_agents = [
            {
                'id': 'ai_gpt4',
                'name': 'GPT-4',
                'type': 'ai',
                'model_version': 'gpt-4o',
                'role': 'Primary AI Reviewer',
                'influence_weight': 1.2,
                'vote_count': 150,
                'average_confidence': 0.87
            },
            {
                'id': 'ai_claude',
                'name': 'Claude-4',
                'type': 'ai',
                'model_version': 'claude-sonnet-4-20250514',
                'role': 'Secondary AI Reviewer',
                'influence_weight': 1.1,
                'vote_count': 140,
                'average_confidence': 0.82
            },
            {
                'id': 'ai_bert',
                'name': 'BERT-Legal',
                'type': 'ai',
                'model_version': 'bert-large-legal',
                'role': 'Specialized Legal AI',
                'influence_weight': 0.9,
                'vote_count': 120,
                'average_confidence': 0.78
            }
        ]
        
        human_agents = [
            {
                'id': 'human_sarah',
                'name': 'Sarah Chen',
                'type': 'human',
                'role': 'Senior Compliance Officer',
                'influence_weight': 1.5,
                'vote_count': 95,
                'average_confidence': 0.91
            },
            {
                'id': 'human_mike',
                'name': 'Mike Rodriguez',
                'type': 'human',
                'role': 'Risk Assessment Specialist',
                'influence_weight': 1.3,
                'vote_count': 88,
                'average_confidence': 0.85
            },
            {
                'id': 'human_alex',
                'name': 'Alex Kim',
                'type': 'human',
                'role': 'Bias Review Expert',
                'influence_weight': 1.4,
                'vote_count': 72,
                'average_confidence': 0.89
            }
        ]
        
        # Create agent objects
        for agent_data in ai_agents + human_agents:
            agent = Agent(
                id=agent_data['id'],
                name=agent_data['name'],
                type=agent_data['type'],
                model_version=agent_data.get('model_version'),
                role=agent_data['role'],
                influence_weight=agent_data['influence_weight'],
                vote_count=agent_data['vote_count'],
                average_confidence=agent_data['average_confidence'],
                created_at=datetime.now() - timedelta(days=30),
                updated_at=datetime.now()
            )
            self.agents[agent.id] = agent
        
        # Create sample governance rules
        sample_rules = [
            {
                'name': 'High Value Decision Review',
                'description': 'Require human review for decisions involving high-value transactions',
                'context': 'financial',
                'rule_definition': '''
conditions:
  - transaction_amount > 100000
actions:
  - require_human_review: true
  - escalate_to: senior_reviewer
priority: 1
'''
            },
            {
                'name': 'Bias Detection Threshold',
                'description': 'Trigger bias review when bias score exceeds threshold',
                'context': 'general',
                'rule_definition': '''
conditions:
  - bias_score > 0.7
actions:
  - trigger_bias_review: true
  - notify: bias_review_committee
priority: 2
'''
            },
            {
                'name': 'AI Consensus Requirement',
                'description': 'Require consensus among AI agents for approval',
                'context': 'general',
                'rule_definition': '''
conditions:
  - ai_consensus_rate < 0.8
actions:
  - require_additional_review: true
  - escalate_to: human_reviewer
priority: 3
'''
            }
        ]
        
        for rule_data in sample_rules:
            rule = GovernanceRule(
                id=str(uuid.uuid4()),
                name=rule_data['name'],
                description=rule_data['description'],
                context=rule_data['context'],
                rule_definition=rule_data['rule_definition'],
                is_active=True,
                created_at=datetime.now() - timedelta(days=15),
                updated_at=datetime.now(),
                applied_count=0
            )
            self.governance_rules[rule.id] = rule
        
        # Create sample decisions
        sample_decisions = [
            {
                'context': 'Loan Application Review for Business Expansion',
                'application_type': 'lending',
                'status': 'approved',
                'bias_score': 0.15,
                'applicant_data': {
                    'age': 35,
                    'gender': 'female',
                    'race': 'asian',
                    'location': 'urban',
                    'income': 85000,
                    'credit_score': 720,
                    'business_type': 'technology'
                }
            },
            {
                'context': 'Hiring Decision for Software Engineer Position',
                'application_type': 'hiring',
                'status': 'under_review',
                'bias_score': 0.65,
                'applicant_data': {
                    'age': 28,
                    'gender': 'male',
                    'race': 'hispanic',
                    'location': 'suburban',
                    'education': 'bachelors',
                    'experience_years': 5
                }
            },
            {
                'context': 'Insurance Risk Assessment for Property Coverage',
                'application_type': 'risk_assessment',
                'status': 'rejected',
                'bias_score': 0.32,
                'applicant_data': {
                    'age': 45,
                    'gender': 'male',
                    'race': 'black',
                    'location': 'rural',
                    'property_value': 250000,
                    'claim_history': 2
                }
            },
            {
                'context': 'Medical Treatment Authorization',
                'application_type': 'healthcare',
                'status': 'escalated',
                'bias_score': 0.78,
                'applicant_data': {
                    'age': 67,
                    'gender': 'female',
                    'race': 'white',
                    'location': 'urban',
                    'condition': 'chronic',
                    'treatment_cost': 50000
                }
            },
            {
                'context': 'Legal Case Priority Assessment',
                'application_type': 'legal',
                'status': 'approved',
                'bias_score': 0.22,
                'applicant_data': {
                    'age': 42,
                    'gender': 'other',
                    'race': 'asian',
                    'location': 'urban',
                    'case_type': 'civil',
                    'complexity': 'medium'
                }
            }
        ]
        
        for decision_data in sample_decisions:
            decision = Decision(
                id=str(uuid.uuid4()),
                context=decision_data['context'],
                application_type=decision_data['application_type'],
                applicant_data=decision_data['applicant_data'],
                metadata={'created_by': 'system', 'priority': 'normal'},
                status=decision_data['status'],
                bias_score=decision_data['bias_score'],
                risk_level='high' if decision_data['bias_score'] > 0.7 else 'medium' if decision_data['bias_score'] > 0.4 else 'low',
                created_at=datetime.now() - timedelta(hours=24, minutes=30),
                updated_at=datetime.now() - timedelta(minutes=15)
            )
            self.decisions[decision.id] = decision
        
        # Create sample votes for decisions
        decision_ids = list(self.decisions.keys())
        agent_ids = list(self.agents.keys())
        
        vote_patterns = [
            ('accept', 0.85), ('accept', 0.82), ('reject', 0.75),  # AI votes
            ('accept', 0.90), ('reject', 0.88)  # Human votes
        ]
        
        for decision_id in decision_ids[:3]:  # Add votes for first 3 decisions
            for i, (vote_decision, confidence) in enumerate(vote_patterns):
                if i < len(agent_ids):
                    vote = Vote(
                        id=str(uuid.uuid4()),
                        agent_id=agent_ids[i],
                        decision_id=decision_id,
                        vote=vote_decision,
                        confidence=confidence,
                        justification=f"Based on analysis of criteria and risk factors. Confidence: {confidence*100:.1f}%",
                        timestamp=datetime.now() - timedelta(minutes=45-i*5),
                        bias_indicators=['demographic_disparity'] if vote_decision == 'reject' and confidence < 0.8 else []
                    )
                    self.votes[vote.id] = vote
        
        # Create sample audit logs
        for decision_id in decision_ids[:2]:
            audit_log = AuditLog(
                id=str(uuid.uuid4()),
                decision_id=decision_id,
                action=f"Decision processed and {self.decisions[decision_id].status}",
                timestamp=datetime.now() - timedelta(minutes=20),
                agent_actions=[
                    "AI-GPT-4: Analyzed application data",
                    "AI-Claude: Reviewed risk factors",
                    "Human-Sarah: Final approval review",
                    "System: Applied governance rules"
                ],
                rules_applied=[
                    "High Value Decision Review",
                    "Bias Detection Threshold"
                ],
                compliance_status='compliant',
                audit_hash=f"hash_{decision_id}_{datetime.now().timestamp()}",
                metadata={'processor': 'automated_system', 'review_time_minutes': 25}
            )
            self.audit_logs[audit_log.id] = audit_log
        
        # Create sample notifications
        sample_notifications = [
            {
                'type': 'bias_alert',
                'title': 'High Bias Score Detected',
                'message': 'Decision ID ending in ...8394 has a bias score of 0.78, requiring immediate review.',
                'priority': 'high',
                'is_read': False
            },
            {
                'type': 'human_override',
                'title': 'Human Override Applied',
                'message': 'Sarah Chen overrode AI recommendation for lending decision.',
                'priority': 'medium',
                'is_read': False
            },
            {
                'type': 'decision_approved',
                'title': 'Decision Approved',
                'message': 'Hiring decision for Software Engineer position has been approved.',
                'priority': 'low',
                'is_read': True
            },
            {
                'type': 'rule_violation',
                'title': 'Governance Rule Violation',
                'message': 'High Value Decision Review rule was bypassed in recent transaction.',
                'priority': 'high',
                'is_read': False
            },
            {
                'type': 'system_alert',
                'title': 'System Maintenance Scheduled',
                'message': 'ParallaxAI system maintenance scheduled for tonight at 2 AM UTC.',
                'priority': 'medium',
                'is_read': True
            }
        ]
        
        for notif_data in sample_notifications:
            notification = Notification(
                id=str(uuid.uuid4()),
                type=notif_data['type'],
                title=notif_data['title'],
                message=notif_data['message'],
                is_read=notif_data['is_read'],
                timestamp=datetime.now() - timedelta(hours=2, minutes=30),
                metadata={'source': 'system', 'category': 'governance'},
                priority=notif_data['priority']
            )
            self.notifications[notification.id] = notification
    
    def get_stats(self) -> Dict[str, Any]:
        """Get comprehensive statistics"""
        decisions = list(self.decisions.values())
        agents = list(self.agents.values())
        votes = list(self.votes.values())
        notifications = list(self.notifications.values())
        rules = list(self.governance_rules.values())
        
        # Basic counts
        total_decisions = len(decisions)
        total_agents = len(agents)
        ai_agents = len([a for a in agents if a.type == 'ai'])
        human_agents = len([a for a in agents if a.type == 'human'])
        
        # Decision status breakdown
        approved_decisions = len([d for d in decisions if d.status == 'approved'])
        rejected_decisions = len([d for d in decisions if d.status == 'rejected'])
        pending_decisions = len([d for d in decisions if d.status in ['pending', 'under_review']])
        
        # Bias metrics
        high_bias_decisions = len([d for d in decisions if d.bias_score > 0.7])
        medium_bias_decisions = len([d for d in decisions if 0.4 < d.bias_score <= 0.7])
        low_bias_decisions = len([d for d in decisions if d.bias_score <= 0.4])
        
        # Calculate rates
        approval_rate = approved_decisions / max(total_decisions, 1)
        ai_accuracy = 0.85  # Simplified calculation
        override_rate = 0.12  # Simplified calculation
        
        # Notification metrics
        unread_notifications = len([n for n in notifications if not n.is_read])
        bias_alerts = len([n for n in notifications if n.type == 'bias_alert'])
        
        # Agent influence metrics
        high_influence_agents = len([a for a in agents if a.influence_weight > 1.2])
        
        # Governance metrics
        active_rules = len([r for r in rules if r.is_active])
        
        return {
            # Core metrics
            'total_decisions': total_decisions,
            'approved_decisions': approved_decisions,
            'rejected_decisions': rejected_decisions,
            'pending_decisions': pending_decisions,
            'approval_rate': round(approval_rate, 3),
            
            # Agent metrics
            'total_agents': total_agents,
            'ai_agents': ai_agents,
            'human_agents': human_agents,
            'high_influence_agents': high_influence_agents,
            
            # Bias metrics
            'high_bias_decisions': high_bias_decisions,
            'medium_bias_decisions': medium_bias_decisions,
            'low_bias_decisions': low_bias_decisions,
            'bias_incidents': bias_alerts,
            'ai_accuracy': ai_accuracy,
            'override_rate': override_rate,
            
            # System metrics
            'unread_notifications': unread_notifications,
            'total_notifications': len(notifications),
            'active_rules': active_rules,
            'total_rules': len(rules),
            'compliance_rate': 0.94,  # Simplified calculation
            
            # Real-time metrics
            'consensus_rate': 0.78,  # Simplified calculation
            'average_processing_time': 25.5,  # minutes
            'override_events': 3,  # Simplified calculation
            'network_density': 0.85,  # Simplified calculation
            
            # Time-based metrics
            'decisions_last_24h': len([d for d in decisions 
                                     if (datetime.now() - d.created_at).days < 1]),
            'votes_last_24h': len([v for v in votes 
                                 if (datetime.now() - v.timestamp).days < 1]),
            'alerts_last_24h': len([n for n in notifications 
                                  if (datetime.now() - n.timestamp).days < 1 and not n.is_read])
        }
    
    def search_decisions(self, query: str = "", status: str = "", 
                        application_type: str = "") -> List[Decision]:
        """Search decisions with filters"""
        decisions = list(self.decisions.values())
        
        if status:
            decisions = [d for d in decisions if d.status == status]
        
        if application_type:
            decisions = [d for d in decisions if d.application_type == application_type]
        
        if query:
            query_lower = query.lower()
            decisions = [d for d in decisions 
                        if query_lower in d.context.lower() 
                        or query_lower in str(d.applicant_data).lower()]
        
        return sorted(decisions, key=lambda x: x.updated_at, reverse=True)
    
    def get_decision_votes(self, decision_id: str) -> List[Vote]:
        """Get all votes for a specific decision"""
        return [vote for vote in self.votes.values() 
                if vote.decision_id == decision_id]
    
    def get_agent_votes(self, agent_id: str, limit: int = 50) -> List[Vote]:
        """Get recent votes by an agent"""
        agent_votes = [vote for vote in self.votes.values() 
                      if vote.agent_id == agent_id]
        return sorted(agent_votes, key=lambda x: x.timestamp, reverse=True)[:limit]
    
    def get_recent_audit_logs(self, limit: int = 20) -> List[AuditLog]:
        """Get recent audit logs"""
        return sorted(self.audit_logs.values(), 
                     key=lambda x: x.timestamp, reverse=True)[:limit]
    
    def get_unread_notifications(self) -> List[Notification]:
        """Get unread notifications"""
        return sorted([n for n in self.notifications.values() if not n.is_read],
                     key=lambda x: x.timestamp, reverse=True)
    
    def mark_notification_read(self, notification_id: str) -> bool:
        """Mark a notification as read"""
        if notification_id in self.notifications:
            self.notifications[notification_id].is_read = True
            return True
        return False
    
    def cleanup_old_data(self, days_to_keep: int = 90):
        """Clean up old data to maintain performance"""
        cutoff_date = datetime.now() - timedelta(days=days_to_keep)
        
        # Remove old audit logs
        old_audit_ids = [id for id, log in self.audit_logs.items() 
                        if log.timestamp < cutoff_date]
        for id in old_audit_ids:
            del self.audit_logs[id]
        
        # Remove old notifications
        old_notif_ids = [id for id, notif in self.notifications.items() 
                        if notif.timestamp < cutoff_date and notif.is_read]
        for id in old_notif_ids:
            del self.notifications[id]
        
        print(f"Cleaned up {len(old_audit_ids)} old audit logs and {len(old_notif_ids)} old notifications")
