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
                'amount': t.amount,
                'is_foreign': 1 if t.location_data.get('country', 'domestic') != 'domestic' else 0,
                'hour_of_day': t.timestamp.hour,
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
        # 1. Rule-based checks
        rules = FraudDetectionRule.objects.filter(is_active=True)
        for rule in rules:
            if self._check_rule(transaction, rule.condition_logic):
                FraudAlert.objects.create(
                    transaction=transaction,
                    rule=rule,
                    score=0.99, # High score for rule-based trigger
                    notes=f"Triggered by rule: {rule.name}"
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
                    FraudAlert.objects.create(
                        transaction=transaction,
                        score=score,
                        notes=f"Potential anomaly detected by ML model (score: {score:.2f})."
                    )
                    logger.info(f"Fraud alert created for transaction {transaction.id} by ML model (score: {score:.2f})")

    def _check_rule(self, transaction: Transaction, logic: dict) -> bool:
        """Evaluates if a transaction matches the conditions in a rule."""
        for field, condition in logic.items():
            transaction_value = getattr(transaction, field, None)
            if transaction_value is None:
                continue

            for op, value in condition.items():
                if op == 'gt' and not transaction_value > value:
                    return False
                if op == 'lt' and not transaction_value < value:
                    return False
                if op == 'eq' and not transaction_value == value:
                    return False
                # Add more operators as needed
        return True

# Instantiate the engine as a singleton
fraud_engine = FraudDetectionEngine()
logger.info("FraudDetectionEngine initialized.")
