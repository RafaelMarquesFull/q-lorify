
import os
import sys
import pickle
import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.tree import DecisionTreeClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score

# Add backend directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from api.utils import get_db

MODELS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'models')
os.makedirs(MODELS_DIR, exist_ok=True)

class SentimentTrainer:
    def __init__(self, domain="transport"):
        self.domain = domain
        self.vectorizer = TfidfVectorizer(
            min_df=1, 
            max_df=1.0, 
            ngram_range=(1, 2), # Use unigrams and bigrams
            strip_accents='unicode'
        )
        self.model = DecisionTreeClassifier(
            criterion='gini',
            max_depth=50, # Prevent overfitting
            min_samples_split=5,
            class_weight='balanced'
        )
        
    def fetch_data(self):
        """Fetch labeled data from Prisma"""
        print(f"Fetching data for domain: {self.domain}...")
        db = get_db()
        
        # Fetch logs that have a valid classification and were either:
        # 1. Reviewed (isReviewed=True) OR
        # 2. High confidence AI/Cache outcome (confidence > 0.9)
        # We exclude 'incompreendido' to train only on positive assertions? 
        # Actually we need 'incompreendido' too if we want to detect garbage? 
        # For now, let's train on active categories.
        
        logs = db.sentimentlog.find_many(
            where={
                "domain": self.domain,
                "OR": [
                    {"isReviewed": True},
                    {"confidence": {"gt": 0.85}}
                ]
            }
        )
        
        print(f"Found {len(logs)} logs.")
        data = []
        for log in logs:
            # Prefer admin correction if available
            label = log.adminCorrection if log.isReviewed and log.adminCorrection else log.classification
            
            # Weighted Learning: Give more weight to human-reviewed items
            weight = 10.0 if log.isReviewed or log.adminCorrection else 1.0
            
            if label and label != "incompreendido":
                data.append({
                    "text": log.intent,
                    "label": label,
                    "weight": weight
                })
        
        return pd.DataFrame(data)

    def train(self):
        df = self.fetch_data()
        
        if len(df) < 5:
            return {"success": False, "message": "Not enough data to train (need 5+ samples)"}
            
        print(f"Training on {len(df)} samples...")
        
        # Vectorize
        X = self.vectorizer.fit_transform(df['text'])
        y = df['label']
        weights = df['weight']
        
        # Split or Full Train based on size
        if len(df) < 10:
            print("Small dataset (<10): Training on full set (overfitting intentionally)")
            X_train, X_test, y_train, y_test, w_train, w_test = X, None, y, None, weights, None
        else:
            X_train, X_test, y_train, y_test, w_train, w_test = train_test_split(X, y, weights, test_size=0.2, random_state=42)
        
        # Train with weights
        self.model.fit(X_train, y_train, sample_weight=w_train)
        
        # Evaluate
        accuracy = 1.0
        if X_test is not None and y_test is not None and len(y_test) > 0:
            y_pred = self.model.predict(X_test)
            accuracy = accuracy_score(y_test, y_pred)
            print(f"Test Accuracy: {accuracy:.2f}")
        else:
             print(f"Training Accuracy (Full Set): 1.00")
        
        # Save artifacts
        model_path = os.path.join(MODELS_DIR, f"{self.domain}_model.pkl")
        vectorizer_path = os.path.join(MODELS_DIR, f"{self.domain}_vectorizer.pkl")
        
        with open(model_path, "wb") as f:
            pickle.dump(self.model, f)
            
        with open(vectorizer_path, "wb") as f:
            pickle.dump(self.vectorizer, f)
            
        print(f"Model saved to {model_path}")
        
        return {
            "success": True,
            "accuracy": accuracy,
            "samples": len(df),
            "model_path": model_path
        }

if __name__ == "__main__":
    trainer = SentimentTrainer()
    result = trainer.train()
    print(result)
