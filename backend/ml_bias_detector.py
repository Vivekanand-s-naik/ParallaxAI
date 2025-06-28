import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier, IsolationForest
from sklearn.preprocessing import LabelEncoder, StandardScaler
from sklearn.metrics import accuracy_score, precision_score, recall_score
from sklearn.model_selection import train_test_split
import pickle
import os
from typing import Dict, List, Tuple, Any
from datetime import datetime, timedelta
import joblib

from backend.models import Decision, Vote, Agent

class MLBiasDetector:
    def __init__(self):
        self.bias_classifier = None
        self.anomaly_detector = None
        self.scaler = StandardScaler()
        self.label_encoders = {}
        self.is_trained = False
        self.bias_threshold = 0.7
        self.model_path = "ml_models/"
        
        # Demographic categories for bias detection
        self.demographic_categories = ["age", "gender", "race", "location", "income"]
        
        # Initialize or load models
        self._initialize_models()
    
    def _initialize_models(self):
        """Initialize ML models for bias detection"""
        try:
            if os.path.exists(f"{self.model_path}bias_classifier.pkl"):
                self.bias_classifier = joblib.load(f"{self.model_path}bias_classifier.pkl")
                self.scaler = joblib.load(f"{self.model_path}scaler.pkl")
                self.is_trained = True
                print("Loaded pre-trained bias detection models")
            else:
                self._train_initial_models()
        except Exception as e:
            print(f"Error loading models, training new ones: {e}")
            self._train_initial_models()
    
    def _train_initial_models(self):
        """Train initial bias detection models with synthetic data"""
        # Generate synthetic training data for bias detection
        synthetic_data = self._generate_synthetic_training_data()
        
        if len(synthetic_data) > 0:
            X, y = self._prepare_training_data(synthetic_data)
            
            # Train bias classifier
            self.bias_classifier = RandomForestClassifier(
                n_estimators=100,
                random_state=42,
                class_weight='balanced'
            )
            
            # Train anomaly detector
            self.anomaly_detector = IsolationForest(
                contamination=0.1,
                random_state=42
            )
            
            # Scale features
            X_scaled = self.scaler.fit_transform(X)
            
            # Split data
            X_train, X_test, y_train, y_test = train_test_split(
                X_scaled, y, test_size=0.2, random_state=42
            )
            
            # Train models
            self.bias_classifier.fit(X_train, y_train)
            self.anomaly_detector.fit(X_train)
            
            # Evaluate
            y_pred = self.bias_classifier.predict(X_test)
            accuracy = accuracy_score(y_test, y_pred)
            
            print(f"Bias detector trained with accuracy: {accuracy:.3f}")
            
            self.is_trained = True
            self._save_models()
    
    def _generate_synthetic_training_data(self) -> List[Dict]:
        """Generate synthetic training data for bias detection"""
        np.random.seed(42)
        synthetic_data = []
        
        # Generate 1000 synthetic decision records
        for i in range(1000):
            # Simulate applicant demographics
            age = np.random.normal(35, 10)
            gender = np.random.choice(['male', 'female', 'other'])
            race = np.random.choice(['white', 'black', 'asian', 'hispanic', 'other'])
            location = np.random.choice(['urban', 'suburban', 'rural'])
            income = np.random.normal(50000, 20000)
            
            # Simulate voting patterns with potential bias
            ai_votes = []
            human_votes = []
            
            # AI votes (may have systematic bias)
            for j in range(3):  # 3 AI agents
                confidence = np.random.uniform(0.6, 0.95)
                
                # Introduce potential bias based on demographics
                bias_factor = 1.0
                if race in ['black', 'hispanic'] and income < 40000:
                    bias_factor = 0.7  # Lower approval rate
                if gender == 'female' and age > 45:
                    bias_factor = 0.8
                
                vote = 'accept' if np.random.random() * bias_factor > 0.4 else 'reject'
                ai_votes.append({
                    'vote': vote,
                    'confidence': confidence
                })
            
            # Human votes (less biased)
            for j in range(2):  # 2 human reviewers
                confidence = np.random.uniform(0.7, 0.9)
                vote = 'accept' if np.random.random() > 0.3 else 'reject'
                human_votes.append({
                    'vote': vote,
                    'confidence': confidence
                })
            
            # Calculate bias score (1 = high bias, 0 = no bias)
            ai_accept_rate = sum(1 for v in ai_votes if v['vote'] == 'accept') / len(ai_votes)
            human_accept_rate = sum(1 for v in human_votes if v['vote'] == 'accept') / len(human_votes)
            
            bias_score = abs(ai_accept_rate - human_accept_rate)
            has_bias = bias_score > 0.3
            
            synthetic_data.append({
                'age': age,
                'gender': gender,
                'race': race,
                'location': location,
                'income': income,
                'ai_votes': ai_votes,
                'human_votes': human_votes,
                'bias_score': bias_score,
                'has_bias': has_bias
            })
        
        return synthetic_data
    
    def _prepare_training_data(self, data: List[Dict]) -> Tuple[np.ndarray, np.ndarray]:
        """Prepare training data for ML models"""
        features = []
        labels = []
        
        for record in data:
            # Extract features
            feature_vector = []
            
            # Demographic features
            feature_vector.append(record['age'])
            feature_vector.append(record['income'])
            
            # Encode categorical variables
            for cat in ['gender', 'race', 'location']:
                if cat not in self.label_encoders:
                    self.label_encoders[cat] = LabelEncoder()
                    # Fit on all possible values
                    self.label_encoders[cat].fit(['male', 'female', 'other'] if cat == 'gender' 
                                               else ['white', 'black', 'asian', 'hispanic', 'other'] if cat == 'race'
                                               else ['urban', 'suburban', 'rural'])
                
                encoded_val = self.label_encoders[cat].transform([record[cat]])[0]
                feature_vector.append(encoded_val)
            
            # Voting pattern features
            ai_votes = record['ai_votes']
            human_votes = record['human_votes']
            
            # AI voting statistics
            ai_accept_rate = sum(1 for v in ai_votes if v['vote'] == 'accept') / len(ai_votes)
            ai_avg_confidence = np.mean([v['confidence'] for v in ai_votes])
            
            # Human voting statistics
            human_accept_rate = sum(1 for v in human_votes if v['vote'] == 'accept') / len(human_votes)
            human_avg_confidence = np.mean([v['confidence'] for v in human_votes])
            
            # Disagreement metrics
            vote_disagreement = abs(ai_accept_rate - human_accept_rate)
            confidence_gap = abs(ai_avg_confidence - human_avg_confidence)
            
            feature_vector.extend([
                ai_accept_rate, ai_avg_confidence,
                human_accept_rate, human_avg_confidence,
                vote_disagreement, confidence_gap
            ])
            
            features.append(feature_vector)
            labels.append(record['has_bias'])
        
        return np.array(features), np.array(labels)
    
    def calculate_bias_score(self, decision: Decision, votes: List[Vote]) -> float:
        """Calculate bias score for a decision using ML models"""
        if not self.is_trained or not votes:
            return 0.0
        
        try:
            # Extract features from decision and votes
            features = self._extract_decision_features(decision, votes)
            
            if features is None:
                return 0.0
            
            # Scale features
            features_scaled = self.scaler.transform([features])
            
            # Predict bias probability
            bias_probability = self.bias_classifier.predict_proba(features_scaled)[0][1]
            
            # Check for anomalies
            anomaly_score = self.anomaly_detector.decision_function(features_scaled)[0]
            
            # Combine scores
            final_score = min(bias_probability + max(0, -anomaly_score * 0.1), 1.0)
            
            return round(final_score, 3)
            
        except Exception as e:
            print(f"Error calculating bias score: {e}")
            return 0.0
    
    def _extract_decision_features(self, decision: Decision, votes: List[Vote]) -> List[float]:
        """Extract features from decision and votes for bias detection"""
        try:
            # Get applicant data
            applicant_data = decision.applicant_data or {}
            
            # Default values if data is missing
            age = applicant_data.get('age', 35)
            income = applicant_data.get('income', 50000)
            gender = applicant_data.get('gender', 'unknown')
            race = applicant_data.get('race', 'unknown')
            location = applicant_data.get('location', 'unknown')
            
            features = [age, income]
            
            # Encode categorical variables
            for cat, value in [('gender', gender), ('race', race), ('location', location)]:
                if cat in self.label_encoders:
                    try:
                        encoded_val = self.label_encoders[cat].transform([value])[0]
                    except ValueError:
                        # Handle unknown values
                        encoded_val = 0
                    features.append(encoded_val)
                else:
                    features.append(0)
            
            # Separate AI and human votes
            ai_votes = [v for v in votes if v.agent_id.startswith('ai_')]
            human_votes = [v for v in votes if not v.agent_id.startswith('ai_')]
            
            if not ai_votes and not human_votes:
                return None
            
            # AI voting statistics
            if ai_votes:
                ai_accept_rate = sum(1 for v in ai_votes if v.vote == 'accept') / len(ai_votes)
                ai_avg_confidence = np.mean([v.confidence for v in ai_votes])
            else:
                ai_accept_rate = 0.5
                ai_avg_confidence = 0.5
            
            # Human voting statistics
            if human_votes:
                human_accept_rate = sum(1 for v in human_votes if v.vote == 'accept') / len(human_votes)
                human_avg_confidence = np.mean([v.confidence for v in human_votes])
            else:
                human_accept_rate = 0.5
                human_avg_confidence = 0.5
            
            # Disagreement metrics
            vote_disagreement = abs(ai_accept_rate - human_accept_rate)
            confidence_gap = abs(ai_avg_confidence - human_avg_confidence)
            
            features.extend([
                ai_accept_rate, ai_avg_confidence,
                human_accept_rate, human_avg_confidence,
                vote_disagreement, confidence_gap
            ])
            
            return features
            
        except Exception as e:
            print(f"Error extracting features: {e}")
            return None
    
    def detect_bias(self, decision: Decision, votes: List[Vote]) -> Dict[str, Any]:
        """Comprehensive bias detection analysis"""
        bias_analysis = {
            'overall_bias_score': 0.0,
            'bias_categories': {},
            'fairness_metrics': {},
            'recommendations': [],
            'confidence': 0.0
        }
        
        try:
            # Calculate overall bias score
            bias_score = self.calculate_bias_score(decision, votes)
            bias_analysis['overall_bias_score'] = bias_score
            
            # Analyze bias by demographic categories
            applicant_data = decision.applicant_data or {}
            
            for category in self.demographic_categories:
                if category in applicant_data:
                    category_bias = self._analyze_category_bias(
                        category, applicant_data[category], votes
                    )
                    bias_analysis['bias_categories'][category] = category_bias
            
            # Calculate fairness metrics
            fairness_metrics = self._calculate_fairness_metrics(decision, votes)
            bias_analysis['fairness_metrics'] = fairness_metrics
            
            # Generate recommendations
            recommendations = self._generate_bias_recommendations(bias_score, bias_analysis)
            bias_analysis['recommendations'] = recommendations
            
            # Calculate confidence in the analysis
            confidence = min(len(votes) / 5.0, 1.0)  # More votes = higher confidence
            bias_analysis['confidence'] = confidence
            
        except Exception as e:
            print(f"Error in bias detection: {e}")
        
        return bias_analysis
    
    def _analyze_category_bias(self, category: str, value: Any, votes: List[Vote]) -> float:
        """Analyze bias for a specific demographic category"""
        try:
            # Simple heuristic-based bias detection for categories
            ai_votes = [v for v in votes if v.agent_id.startswith('ai_')]
            human_votes = [v for v in votes if not v.agent_id.startswith('ai_')]
            
            if not ai_votes or not human_votes:
                return 0.0
            
            ai_accept_rate = sum(1 for v in ai_votes if v.vote == 'accept') / len(ai_votes)
            human_accept_rate = sum(1 for v in human_votes if v.vote == 'accept') / len(human_votes)
            
            # Higher disagreement suggests potential bias
            disagreement = abs(ai_accept_rate - human_accept_rate)
            
            # Apply category-specific bias detection rules
            bias_multiplier = 1.0
            
            if category == 'race' and value in ['black', 'hispanic']:
                bias_multiplier = 1.2
            elif category == 'gender' and value == 'female':
                bias_multiplier = 1.1
            elif category == 'age' and (value < 25 or value > 55):
                bias_multiplier = 1.15
            
            category_bias = min(disagreement * bias_multiplier, 1.0)
            return round(category_bias, 3)
            
        except Exception as e:
            print(f"Error analyzing category bias for {category}: {e}")
            return 0.0
    
    def _calculate_fairness_metrics(self, decision: Decision, votes: List[Vote]) -> Dict[str, float]:
        """Calculate standard fairness metrics"""
        metrics = {
            'demographic_parity': 0.8,
            'equal_opportunity': 0.75,
            'equalized_odds': 0.82
        }
        
        try:
            # Simplified fairness metric calculation
            # In a real implementation, these would be calculated based on historical data
            
            ai_votes = [v for v in votes if v.agent_id.startswith('ai_')]
            human_votes = [v for v in votes if not v.agent_id.startswith('ai_')]
            
            if ai_votes and human_votes:
                ai_accept_rate = sum(1 for v in ai_votes if v.vote == 'accept') / len(ai_votes)
                human_accept_rate = sum(1 for v in human_votes if v.vote == 'accept') / len(human_votes)
                
                # Adjust metrics based on agreement
                agreement = 1 - abs(ai_accept_rate - human_accept_rate)
                
                metrics['demographic_parity'] = min(0.9, 0.6 + agreement * 0.3)
                metrics['equal_opportunity'] = min(0.85, 0.55 + agreement * 0.3)
                metrics['equalized_odds'] = min(0.88, 0.58 + agreement * 0.3)
            
        except Exception as e:
            print(f"Error calculating fairness metrics: {e}")
        
        return metrics
    
    def _generate_bias_recommendations(self, bias_score: float, analysis: Dict) -> List[str]:
        """Generate recommendations based on bias analysis"""
        recommendations = []
        
        if bias_score > 0.7:
            recommendations.append("High bias detected - Require human review")
            recommendations.append("Consider additional training data for AI models")
            recommendations.append("Implement bias mitigation strategies")
        elif bias_score > 0.4:
            recommendations.append("Moderate bias detected - Monitor closely")
            recommendations.append("Review decision criteria for potential bias")
        else:
            recommendations.append("Low bias detected - Continue monitoring")
        
        # Category-specific recommendations
        bias_categories = analysis.get('bias_categories', {})
        for category, score in bias_categories.items():
            if score > 0.5:
                recommendations.append(f"Review {category}-based decision patterns")
        
        return recommendations
    
    def _save_models(self):
        """Save trained models to disk"""
        try:
            os.makedirs(self.model_path, exist_ok=True)
            joblib.dump(self.bias_classifier, f"{self.model_path}bias_classifier.pkl")
            joblib.dump(self.scaler, f"{self.model_path}scaler.pkl")
            joblib.dump(self.label_encoders, f"{self.model_path}label_encoders.pkl")
            print("Models saved successfully")
        except Exception as e:
            print(f"Error saving models: {e}")
    
    def retrain_models(self, new_data: List[Dict]):
        """Retrain models with new data"""
        try:
            if len(new_data) < 50:  # Need minimum data for retraining
                print("Insufficient data for retraining")
                return False
            
            X, y = self._prepare_training_data(new_data)
            X_scaled = self.scaler.fit_transform(X)
            
            # Retrain models
            self.bias_classifier.fit(X_scaled, y)
            self.anomaly_detector.fit(X_scaled)
            
            self._save_models()
            print("Models retrained successfully")
            return True
            
        except Exception as e:
            print(f"Error retraining models: {e}")
            return False
