"""
Trading Strategy Constants - Dip/Tepe yakalama için optimize edilmiş sabitler
"""

# Minimum güven eşikleri (timeframe bazında) - makul sinyal üretimi için optimize edildi
MIN_CONFIDENCE_THRESHOLDS = {
    "15m": 0.45,  # Kısa vadeli işlemler için daha esnek
    "1h": 0.50,   # Saatlik analizler için dengeli
    "4h": 0.55,   # 4 saatlik için orta seviye
    "1d": 0.60    # Günlük için daha güvenli
}

# RSI seviyeleri - erken sinyal tespiti için
RSI_OVERSOLD = 40    # 30'dan yükseltildi
RSI_OVERBOUGHT = 60  # 70'ten düşürüldü
RSI_EXTREME_OVERSOLD = 25
RSI_EXTREME_OVERBOUGHT = 75

# Sinyal birleştirme eşikleri
SIGNAL_WEIGHT_THRESHOLD = 0.30  # 0.25'ten yükseltildi

# Bollinger Bands pozisyon eşikleri
BB_LOWER_THRESHOLD = 0.05  # Alt bandın %5'i içinde
BB_UPPER_THRESHOLD = 0.05  # Üst bandın %5'i içinde

# MACD histogram momentumu
MACD_HISTOGRAM_THRESHOLD = 0.1
MACD_SIGNAL_THRESHOLD = 0.05

# Volume spike tespiti
VOLUME_SPIKE_MULTIPLIER = 1.5  # Ortalama volume'nin 1.5 katı
VOLUME_LOOKBACK_PERIODS = 20

# Divergence tespiti
DIVERGENCE_LOOKBACK_PERIODS = 10
DIVERGENCE_MIN_PRICE_SWING = 0.005  # %0.5 minimum fiyat hareketi

# Pattern güvenilirlik skorları
PATTERN_RELIABILITY_SCORES = {
    "head_and_shoulders": 0.85,
    "inverse_head_and_shoulders": 0.85,
    "double_top": 0.75,
    "double_bottom": 0.75,
    "triple_top": 0.80,
    "triple_bottom": 0.80,
    "ascending_triangle": 0.70,
    "descending_triangle": 0.70,
    "symmetrical_triangle": 0.65,
    "flag": 0.60,
    "pennant": 0.60,
    "wedge": 0.65
}

# Dip/Tepe yakalama kriterleri
DIP_DETECTION_CRITERIA = {
    "rsi_oversold_threshold": RSI_OVERSOLD,
    "bollinger_lower_threshold": BB_LOWER_THRESHOLD,
    "volume_spike_required": True,
    "divergence_bonus": 0.15,  # %15 ekstra güven
    "support_level_proximity": 0.01,  # %1 mesafede destek
    "min_combined_score": 0.60
}

PEAK_DETECTION_CRITERIA = {
    "rsi_overbought_threshold": RSI_OVERBOUGHT,
    "bollinger_upper_threshold": BB_UPPER_THRESHOLD,
    "volume_spike_required": False,  # Tepe için volume zorunlu değil
    "divergence_bonus": 0.15,
    "resistance_level_proximity": 0.01,
    "min_combined_score": 0.60
}

# Multi-timeframe ağırlıkları
TIMEFRAME_WEIGHTS = {
    "15m": 0.20,
    "1h": 0.30,
    "4h": 0.35,
    "1d": 0.15
}

# Risk yönetimi sabitleri
MAX_POSITION_SIZE = 1.0  # %100 maksimum pozisyon
MIN_POSITION_SIZE = 0.1  # %10 minimum pozisyon

# Stop-loss mesafeleri (ATR katı)
STOP_LOSS_ATR_MULTIPLIER = 1.5  # 2.0'dan düşürüldü
TAKE_PROFIT_ATR_MULTIPLIER = 3.0

# İşlem maliyeti
TRANSACTION_COST_PERCENTAGE = 0.45  # %0.45 işlem maliyeti

# Risk/Reward oranları
MIN_RISK_REWARD_RATIO = 1.5
IDEAL_RISK_REWARD_RATIO = 2.5

# Volatilite ayarlamaları
LOW_VOLATILITY_THRESHOLD = 0.5   # %0.5
HIGH_VOLATILITY_THRESHOLD = 1.5  # %1.5

# Momentum göstergeleri
MOMENTUM_THRESHOLD = 0.6
MOMENTUM_EXTREME_THRESHOLD = 0.8