import os
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    # API Keys
    GROQ_API_KEY: str
    PINECONE_API_KEY: str
    GEMINI_API_KEY: str
    CAL_API_KEY: str
    VAPI_SECRET: str = os.getenv("VAPI_SECRET", "my_super_secure_scaler_secret_123")
    # App Configs
    PINECONE_INDEX_NAME: str = "scaler-rag"
    CAL_EVENT_TYPE_ID: str = ""  # Populated via Cal.com event dashboard
    
    # Configuration to load directly from your root .env file
    model_config = SettingsConfigDict(
        env_file=os.path.join(os.path.dirname(__file__), "../.env"),
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()