"""
Analiz sonuçları için veri modeli
"""
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Optional, Dict, Any, List
from enum import Enum


class TrendType(str, Enum):
    """Trend tipleri"""
    BULLISH = "BULLISH"    # Yükseliş
    BEARISH = "BEARISH"    # Düşüş
    NEUTRAL = "NEUTRAL"    # Yatay


class TrendStrength(str, Enum):
    """Trend gücü"""
    STRONG = "STRONG"      # Güçlü
    MODERATE = "MODERATE"  # Orta
    WEAK = "WEAK"         # Zayıf


@dataclass
class SupportResistanceLevel:
    """Destek/Direnç seviyesi"""
    level: Decimal
    strength: str  # Güçlü, Orta, Zayıf
    touches: int   # Kaç kez test edildi
    last_test: Optional[datetime] = None


@dataclass
class TechnicalIndicators:
    """Teknik göstergeler"""
    # RSI
    rsi: Optional[float] = None
    rsi_signal: Optional[str] = None  # Overbought, Oversold, Neutral
    
    # Moving Averages
    ma_short: Optional[Decimal] = None
    ma_long: Optional[Decimal] = None
    ma_cross: Optional[str] = None  # Golden Cross, Death Cross, None
    
    # MACD
    macd_line: Optional[float] = None
    macd_signal: Optional[float] = None
    macd_histogram: Optional[float] = None
    macd_crossover: Optional[str] = None  # BULLISH_CROSSOVER, BEARISH_CROSSOVER
    macd_trend: Optional[str] = None
    
    # Bollinger Bands
    bb_upper: Optional[float] = None
    bb_middle: Optional[float] = None
    bb_lower: Optional[float] = None
    bb_percent_b: Optional[float] = None
    bb_squeeze: Optional[bool] = None
    bb_signal: Optional[str] = None
    
    # Stochastic
    stoch_k: Optional[float] = None
    stoch_d: Optional[float] = None
    stoch_zone: Optional[str] = None  # OVERBOUGHT, OVERSOLD, NEUTRAL
    stoch_signal: Optional[str] = None
    
    # ATR
    atr: Optional[float] = None
    atr_percent: Optional[float] = None
    volatility_level: Optional[str] = None  # VERY_LOW, LOW, NORMAL, HIGH, EXTREME
    
    # Pattern Recognition
    patterns: Optional[List[Dict[str, Any]]] = None
    strongest_pattern: Optional[str] = None
    pattern_signal: Optional[str] = None
    
    # Genel
    volume_trend: Optional[str] = None
    momentum: Optional[float] = None


@dataclass
class AnalysisResult:
    """Analiz sonucu"""
    id: Optional[int] = None
    timestamp: datetime = None
    timeframe: str = "15m"  # 15m, 1h, 4h, 1d
    
    # Fiyat bilgileri
    price: Decimal = None
    price_change: Decimal = None
    price_change_pct: float = None
    
    # Trend analizi
    trend: TrendType = TrendType.NEUTRAL
    trend_strength: TrendStrength = TrendStrength.WEAK
    
    # Destek/Direnç
    support_levels: List[SupportResistanceLevel] = None
    resistance_levels: List[SupportResistanceLevel] = None
    nearest_support: Optional[Decimal] = None
    nearest_resistance: Optional[Decimal] = None
    
    # Sinyal
    signal: Optional[str] = None  # BUY, SELL, HOLD
    signal_strength: Optional[float] = None  # 0-1 arası
    confidence: float = 0.0  # 0-1 arası
    
    # Teknik göstergeler
    indicators: Optional[TechnicalIndicators] = None
    
    # Risk değerlendirmesi
    risk_level: Optional[str] = None  # LOW, MEDIUM, HIGH
    stop_loss: Optional[Decimal] = None
    take_profit: Optional[Decimal] = None
    
    # Analiz detayları
    analysis_details: Optional[Dict[str, Any]] = None
    
    def __post_init__(self):
        """Varsayılan değerleri ayarla"""
        if self.timestamp is None:
            self.timestamp = datetime.now()
        if self.support_levels is None:
            self.support_levels = []
        if self.resistance_levels is None:
            self.resistance_levels = []
        if self.analysis_details is None:
            self.analysis_details = {}
    
    def to_dict(self) -> Dict[str, Any]:
        """Dictionary'e dönüştür"""
        return {
            "id": self.id,
            "timestamp": self.timestamp.isoformat(),
            "timeframe": self.timeframe,
            "price": float(self.price) if self.price else None,
            "price_change": float(self.price_change) if self.price_change else None,
            "price_change_pct": self.price_change_pct,
            "trend": self.trend.value,
            "trend_strength": self.trend_strength.value,
            "support_levels": [
                {
                    "level": float(s.level),
                    "strength": s.strength,
                    "touches": s.touches
                } for s in self.support_levels
            ],
            "resistance_levels": [
                {
                    "level": float(r.level),
                    "strength": r.strength,
                    "touches": r.touches
                } for r in self.resistance_levels
            ],
            "nearest_support": float(self.nearest_support) if self.nearest_support else None,
            "nearest_resistance": float(self.nearest_resistance) if self.nearest_resistance else None,
            "signal": self.signal,
            "signal_strength": self.signal_strength,
            "confidence": self.confidence,
            "indicators": {
                # RSI
                "rsi": self.indicators.rsi if self.indicators else None,
                "rsi_signal": self.indicators.rsi_signal if self.indicators else None,
                # Moving Averages
                "ma_short": float(self.indicators.ma_short) if self.indicators and self.indicators.ma_short else None,
                "ma_long": float(self.indicators.ma_long) if self.indicators and self.indicators.ma_long else None,
                "ma_cross": self.indicators.ma_cross if self.indicators else None,
                # MACD
                "macd_line": self.indicators.macd_line if self.indicators else None,
                "macd_signal": self.indicators.macd_signal if self.indicators else None,
                "macd_histogram": self.indicators.macd_histogram if self.indicators else None,
                "macd_crossover": self.indicators.macd_crossover if self.indicators else None,
                "macd_trend": self.indicators.macd_trend if self.indicators else None,
                # Bollinger Bands
                "bb_upper": self.indicators.bb_upper if self.indicators else None,
                "bb_middle": self.indicators.bb_middle if self.indicators else None,
                "bb_lower": self.indicators.bb_lower if self.indicators else None,
                "bb_percent_b": self.indicators.bb_percent_b if self.indicators else None,
                "bb_squeeze": self.indicators.bb_squeeze if self.indicators else None,
                "bb_signal": self.indicators.bb_signal if self.indicators else None,
                # Stochastic
                "stoch_k": self.indicators.stoch_k if self.indicators else None,
                "stoch_d": self.indicators.stoch_d if self.indicators else None,
                "stoch_zone": self.indicators.stoch_zone if self.indicators else None,
                "stoch_signal": self.indicators.stoch_signal if self.indicators else None,
                # ATR
                "atr": self.indicators.atr if self.indicators else None,
                "atr_percent": self.indicators.atr_percent if self.indicators else None,
                "volatility_level": self.indicators.volatility_level if self.indicators else None,
                # Pattern Recognition
                "patterns": self.indicators.patterns if self.indicators else None,
                "strongest_pattern": self.indicators.strongest_pattern if self.indicators else None,
                "pattern_signal": self.indicators.pattern_signal if self.indicators else None,
                # Genel
                "volume_trend": self.indicators.volume_trend if self.indicators else None,
                "momentum": self.indicators.momentum if self.indicators else None,
            } if self.indicators else None,
            "risk_level": self.risk_level,
            "stop_loss": float(self.stop_loss) if self.stop_loss else None,
            "take_profit": float(self.take_profit) if self.take_profit else None,
            "analysis_details": self.analysis_details
        }