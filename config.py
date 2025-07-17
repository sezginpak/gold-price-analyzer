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
    collection_interval: int = int(os.getenv("COLLECTION_INTERVAL", "1"))  # Dakika cinsinden veri toplama (her dakika fiyat kaydet)
    analysis_interval_15m: int = int(os.getenv("ANALYSIS_INTERVAL_15M", "15"))  # 15 dakikalık analiz
    analysis_interval_1h: int = int(os.getenv("ANALYSIS_INTERVAL_1H", "60"))  # 1 saatlik analiz
    analysis_interval_4h: int = int(os.getenv("ANALYSIS_INTERVAL_4H", "240"))  # 4 saatlik analiz
    analysis_interval_daily: int = int(os.getenv("ANALYSIS_INTERVAL_DAILY", "1440"))  # Günlük analiz
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
    
    # Log Management Settings
    log_max_size_mb: int = int(os.getenv("LOG_MAX_SIZE_MB", "100"))  # Toplam log boyutu limiti
    log_max_age_days: int = int(os.getenv("LOG_MAX_AGE_DAYS", "7"))  # Log saklama süresi
    log_compress_after_days: int = int(os.getenv("LOG_COMPRESS_AFTER_DAYS", "1"))  # Sıkıştırma süresi
    log_check_interval_minutes: int = int(os.getenv("LOG_CHECK_INTERVAL_MINUTES", "60"))  # Kontrol sıklığı
    
    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()