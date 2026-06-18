
import os
import django
import secrets

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from prisma import Prisma

def create_sentiment_model():
    db = Prisma()
    db.connect()
    
    try:
        # Find OpenAI provider first
        provider = db.aiprovider.find_first(
            where={
                "name": {"contains": "OpenAI"}
            }
        )
        
        if not provider:
            # Create dummy provider if needed (though usually we should use real one)
            # Assuming user has one. IF not, get ANY provider.
            provider = db.aiprovider.find_first()
            
        if not provider:
            print("No AI Provider found. Please create one in Admin Panel first.")
            return

        # Check if model already exists
        MODEL_NAME = "Sentiment Orchestrator"
        
        existing = db.aimodel.find_first(
            where={"name": MODEL_NAME}
        )
        
        if existing:
            print(f"Model '{MODEL_NAME}' already exists. Updating isSentiment...")
            db.aimodel.update(
                where={"id": existing.id},
                data={"isSentiment": True}
            )
        else:
            print(f"Creating new model '{MODEL_NAME}'...")
            db.aimodel.create(
                data={
                    "name": MODEL_NAME,
                    "providerId": provider.id,
                    "providerModelId": "gpt-4o-mini", # Fallback model
                    "costPerInputToken": 0.0,
                    "costPerOutputToken": 0.0,
                    "isSentiment": True,
                    "description": "Orquestrador de Sentimentos (5 Pilares)",
                    "isPublic": True
                }
            )
            
        print("Success! Sentiment model is ready.")
        
    except Exception as e:
        print(f"Error: {e}")
    finally:
        db.disconnect()

if __name__ == "__main__":
    create_sentiment_model()
