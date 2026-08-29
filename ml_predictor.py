"""
ML-based Recovery Success Predictor

Uses scikit-learn to predict recovery probability
based on transaction features.
"""

from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, precision_score, recall_score
import pandas as pd
import numpy as np
from database import Database

db = Database()


def train_model():
    """Train ML model on transaction data."""
    # Fetch all transactions with recovery outcomes
    transactions = db.fetch_all("""
        SELECT t.*, 
               CASE WHEN r.success = 1 THEN 1 ELSE 0 END as recovered
        FROM transactions t
        LEFT JOIN recovery_actions r ON t.id = r.transaction_id
        WHERE t.status = 'failed'
    """)
    
    if len(transactions) < 20:
        print("Not enough data to train model")
        return None
    
    # Convert to DataFrame
    df = pd.DataFrame([dict(t) for t in transactions])
    
    # Feature engineering
    df['is_high_value'] = df['amount'].apply(lambda x: 1 if x > 5000 else 0)
    df['is_enterprise'] = df['customer_id'].apply(lambda x: 1 if 'enterprise' in str(x) else 0)
    
    # Encode error codes
    error_mapping = {
        'upi_timeout': 1,
        'network_error': 2,
        'card_declined': 3,
        'insufficient_funds': 4,
        'otp_expired': 5,
        'risk_block': 6,
    }
    df['error_encoded'] = df['error_code'].map(error_mapping).fillna(0)
    
    # Features and target
    features = ['amount', 'is_high_value', 'error_encoded', 'recovery_attempts']
    X = df[features].values
    y = df['recovered'].values
    
    # Train/test split
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.3, random_state=42)
    
    # Train model
    model = RandomForestClassifier(n_estimators=100, random_state=42)
    model.fit(X_train, y_train)
    
    # Evaluate
    y_pred = model.predict(X_test)
    accuracy = accuracy_score(y_test, y_pred)
    precision = precision_score(y_test, y_pred, zero_division=0)
    recall = recall_score(y_test, y_pred, zero_division=0)
    
    print(f"Model Accuracy: {accuracy:.2f}")
    print(f"Precision: {precision:.2f}")
    print(f"Recall: {recall:.2f}")
    
    return model


def predict_recovery_probability(model, transaction):
    """Predict recovery probability for a transaction."""
    if model is None:
        return 0.5  # Default
    
    features = [
        transaction['amount'],
        1 if transaction['amount'] > 5000 else 0,
        transaction.get('error_code', 'unknown'),
        transaction.get('recovery_attempts', 0),
    ]
    
    return model.predict_proba([features])[0][1]


if __name__ == "__main__":
    model = train_model()
    if model:
        print("\nModel ready for predictions")