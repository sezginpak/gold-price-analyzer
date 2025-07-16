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
    rsi: Optional[float] = None
    rsi_signal: Optional[str] = None  # Overbought, Oversold, Neutral
    ma_short: Optional[Decimal] = None
    ma_long: Optional[Decimal] = None
    ma_cross: Optional[str] = None  # Golden Cross, Death Cross, None
    volume_trend: Optional[str] = None
    momentum: Optional[float] = None


@dataclass
class AnalysisResult:
    """Analiz sonucu"""
    id: Optional[int] = None
    timestamp: datetime = None
    
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
                "rsi": self.indicators.rsi if self.indicators else None,
                "rsi_signal": self.indicators.rsi_signal if self.indicators else None,
                "ma_short": float(self.indicators.ma_short) if self.indicators and self.indicators.ma_short else None,
                "ma_long": float(self.indicators.ma_long) if self.indicators and self.indicators.ma_long else None,
                "ma_cross": self.indicators.ma_cross if self.indicators else None,
            } if self.indicators else None,
            "risk_level": self.risk_level,
            "stop_loss": float(self.stop_loss) if self.stop_loss else None,
            "take_profit": float(self.take_profit) if self.take_profit else None,
            "analysis_details": self.analysis_details
        }