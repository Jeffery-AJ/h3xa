import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
from core.models import Transaction
from .models import FraudAlert, FraudDetectionRule
import logging

logger = logging.getLogger(__name__)

class FraudDetectionEngine:
    def __init__(self):
        self.model = IsolationForest(contamination=0.01, random_state=42)
        self.scaler = StandardScaler()
        self.is_trained = False

    def _preprocess_data(self, transactions):
        if not transactions:
            return pd.DataFrame()

        data = [
            {
                'amount': float(t.amount),
                'is_foreign': 1 if t.metadata.get('country', 'US') != 'US' else 0,
                'hour_of_day': t.transaction_date.hour,
            }
            for t in transactions
        ]
        df = pd.DataFrame(data)
        
        # Handle cases with single transaction or no variance
        if df.shape[0] < 2:
            return None

        # Scale the features
        scaled_features = self.scaler.fit_transform(df)
        return pd.DataFrame(scaled_features, columns=df.columns)

    def train(self, transactions=None):
        """Train the Isolation Forest model on historical transaction data."""
        if transactions is None:
            transactions = Transaction.objects.filter(status='completed').order_by('-timestamp')[:10000]
        
        if len(transactions) < 100: # Minimum data for training
            logger.warning("Not enough transaction data to train fraud detection model.")
            self.is_trained = False
            return

        preprocessed_data = self._preprocess_data(list(transactions))
        
        if preprocessed_data is not None and not preprocessed_data.empty:
            self.model.fit(preprocessed_data)
            self.is_trained = True
            logger.info("Fraud detection model trained successfully.")
        else:
            self.is_trained = False
            logger.warning("Could not train fraud detection model due to lack of suitable data.")

    def analyze_transaction(self, transaction: Transaction):
        """Analyze a single transaction for fraud using rules and ML model."""
        try:
            # 1. Rule-based checks
            rules = FraudDetectionRule.objects.filter(is_active=True)
            for rule in rules:
                if self._check_rule(transaction, rule):
                    FraudAlert.objects.create(
                        transaction=transaction,
                        rule=rule,
                        company=transaction.company,
                        risk_score=99.0, # High score for rule-based trigger
                        confidence_score=95.0,
                        alert_reason=f"Triggered by rule: {rule.name}",
                        anomaly_factors=[rule.rule_type],
                        risk_indicators=rule.parameters
                    )
                    logger.info(f"Fraud alert created for transaction {transaction.id} by rule '{rule.name}'")
                    return # Stop further analysis if a rule is matched

            # 2. ML-based anomaly detection
            if not self.is_trained:
                self.train() # Attempt to train if not already trained

            if self.is_trained:
                df = self._preprocess_data([transaction])
                if df is not None and not df.empty:
                    score = self.model.decision_function(df)[0]
                    prediction = self.model.predict(df)[0]

                    # Anomaly score is negative, prediction is -1 for anomalies
                    if prediction == -1:
                        # Convert negative score to positive risk score (0-100)
                        risk_score = min(100, max(0, abs(score) * 50))
                        FraudAlert.objects.create(
                            transaction=transaction,
                            company=transaction.company,
                            risk_score=risk_score,
                            confidence_score=75.0,
                            alert_reason=f"Potential anomaly detected by ML model (score: {score:.2f}).",
                            anomaly_factors=["ML_ANOMALY"],
                            risk_indicators={"ml_score": float(score), "prediction": int(prediction)}
                        )
                        logger.info(f"Fraud alert created for transaction {transaction.id} by ML model (score: {score:.2f})")
        except Exception as e:
            logger.error(f"Error in auto-analysis for transaction {transaction.id}: {str(e)}")

    def _check_rule(self, transaction: Transaction, rule: FraudDetectionRule) -> bool:
        """Evaluates if a transaction matches the conditions in a rule."""
        if rule.rule_type == 'AMOUNT_THRESHOLD':
            threshold = rule.thresholds.get('max_amount', 10000)
            return float(transaction.amount) > threshold
        elif rule.rule_type == 'VELOCITY':
            # Check transaction velocity (number of transactions in a time period)
            time_window = rule.parameters.get('time_window_minutes', 60)
            max_count = rule.thresholds.get('max_transactions', 5)
            from django.utils import timezone
            from datetime import timedelta
            
            recent_transactions = Transaction.objects.filter(
                account=transaction.account,
                transaction_date__gte=timezone.now() - timedelta(minutes=time_window)
            ).count()
            return recent_transactions > max_count
        elif rule.rule_type == 'TIME_ANOMALY':
            # Check if transaction is outside normal hours
            normal_hours = rule.parameters.get('normal_hours', [6, 22])  # 6 AM to 10 PM
            current_hour = transaction.transaction_date.hour
            return current_hour < normal_hours[0] or current_hour > normal_hours[1]
        elif rule.rule_type == 'AMOUNT_ANOMALY':
            # Check if amount is significantly different from user's normal amounts
            threshold_multiplier = rule.thresholds.get('amount_multiplier', 10)
            avg_amount = rule.parameters.get('user_avg_amount', 100)
            return float(transaction.amount) > (avg_amount * threshold_multiplier)
        
        return False

# Instantiate the engine as a singleton
fraud_engine = FraudDetectionEngine()
logger.info("FraudDetectionEngine initialized.")
