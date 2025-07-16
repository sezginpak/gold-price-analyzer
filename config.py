"""
Configuration module for Gold Price Analyzer
"""
import os
from typing import Optional
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

load_dotenv()


class Settings(BaseSettings):
    # API Configuration
    api_base_url: str = os.getenv("API_BASE_URL", "http://localhost:8000")
    api_key: Optional[str] = os.getenv("API_KEY")
    
    # MongoDB Configuration
    mongodb_url: str = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
    mongodb_db: str = os.getenv("MONGODB_DB", "gold_price_analyzer")
    
    # Redis Configuration
    redis_url: str = os.getenv("REDIS_URL", "redis://localhost:6379")
    redis_db: int = int(os.getenv("REDIS_DB", "0"))
    
    # Data Collection
    collection_interval: int = int(os.getenv("COLLECTION_INTERVAL", "5"))
    data_retention_raw: int = int(os.getenv("DATA_RETENTION_RAW", "7"))
    data_retention_compressed: int = int(os.getenv("DATA_RETENTION_COMPRESSED", "30"))
    
    # Analysis Settings
    support_resistance_lookback: int = int(os.getenv("SUPPORT_RESISTANCE_LOOKBACK", "100"))
    rsi_period: int = int(os.getenv("RSI_PERIOD", "14"))
    ma_short_period: int = int(os.getenv("MA_SHORT_PERIOD", "20"))
    ma_long_period: int = int(os.getenv("MA_LONG_PERIOD", "50"))
    
    # Signal Settings
    min_confidence_score: float = float(os.getenv("MIN_CONFIDENCE_SCORE", "0.7"))
    risk_tolerance: str = os.getenv("RISK_TOLERANCE", "medium")
    
    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()