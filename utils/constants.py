"""
Ortak sabitler ve yapılandırmalar
"""
from enum import Enum
from typing import Dict, Tuple

# Sinyal türleri
class SignalType(Enum):
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"

# Risk seviyeleri
class RiskLevel(Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    EXTREME = "EXTREME"

# Güç seviyeleri
class StrengthLevel(Enum):
    WEAK = "WEAK"
    MODERATE = "MODERATE"
    STRONG = "STRONG"

# Trend yönleri
class TrendDirection(Enum):
    BULLISH = "BULLISH"
    BEARISH = "BEARISH"
    NEUTRAL = "NEUTRAL"

# Sinyal güç çarpanları
SIGNAL_STRENGTH_MULTIPLIERS: Dict[str, float] = {
    "STRONG": 1.0,
    "MODERATE": 0.7,
    "WEAK": 0.5
}

# Risk seviyesi pozisyon çarpanları
RISK_POSITION_MULTIPLIERS: Dict[str, float] = {
    "LOW": 1.0,
    "MEDIUM": 0.8,
    "HIGH": 0.5,
    "EXTREME": 0.3
}

# Güven seviyesi pozisyon çarpanları
CONFIDENCE_POSITION_MULTIPLIERS: Dict[Tuple[float, float], float] = {
    # (min_confidence, max_confidence): multiplier
    (0.7, 1.0): 1.0,
    (0.5, 0.7): 0.8,
    (0.3, 0.5): 0.6,
    (0.0, 0.3): 0.5
}

# Teknik gösterge ağırlıkları
INDICATOR_WEIGHTS: Dict[str, float] = {
    "rsi": 2.0,
    "macd": 3.0,
    "bollinger": 2.0,
    "stochastic": 1.0,
    "pattern": 2.0,
    "trend": 1.0
}

# Varsayılan ATR değeri
DEFAULT_ATR = 10.0

# Mum sayısı gereksinimleri
CANDLE_REQUIREMENTS: Dict[str, int] = {
    "15m": 35,   # 35 mum = 8.75 saat veri
    "1h": 26,    # 26 mum = 26 saat veri
    "4h": 20,    # 20 mum = 3.3 gün veri
    "1d": 20     # 20 mum = 20 gün veri
}

# Analiz aralıkları (dakika)
ANALYSIS_INTERVALS: Dict[str, int] = {
    "15m": 15,
    "1h": 60,
    "4h": 240,
    "1d": 1440
}

# Interval mapping for candles
INTERVAL_MINUTES_TO_STR: Dict[int, str] = {
    15: "15m",
    60: "1h",
    240: "4h",
    1440: "1d"
}

# Timeframe bazlı minimum güven eşikleri - Yüksek işlem maliyeti için optimize edildi
MIN_CONFIDENCE_THRESHOLDS: Dict[str, float] = {
    "15m": 0.80,  # %80 - Yüksek işlem maliyeti için artırıldı
    "1h": 0.75,   # %75 - Daha büyük hareketler için
    "4h": 0.70,   # %70 - Uzun vadeli pozisyonlar için
    "1d": 0.65    # %65 - En uzun vadeli, en güvenilir sinyaller
}

# Minimum volatilite eşiği (%) - Yüksek işlem maliyeti için artırıldı
MIN_VOLATILITY_THRESHOLD = 0.5  # %0.5 - Sadece yeterli volatilitede işlem yapılsın

# Global trend uyumsuzluk cezası - Global trend ağırlıklı olduğu için azaltıldı
GLOBAL_TREND_MISMATCH_PENALTY = 0.85  # Güven skoru %85'e düşer (önceki: %70)