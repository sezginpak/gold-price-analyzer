"""
Birleşik piyasa verisi modeli - Gram altın odaklı
"""
from datetime import datetime
from decimal import Decimal
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field


class MarketData(BaseModel):
    """Tüm piyasa verilerini içeren ana model"""
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    # Ana fiyatlar
    gram_altin: Decimal = Field(..., description="Gram altın TRY fiyatı - ANA FİYAT")
    ons_usd: Decimal = Field(..., description="ONS/USD fiyatı - Global trend için")
    usd_try: Decimal = Field(..., description="USD/TRY kuru - Risk hesaplama için")
    ons_try: Decimal = Field(..., description="ONS/TRY fiyatı - Kayıt amaçlı")
    
    # Ek bilgiler
    source: str = Field(default="haremaltin", description="Veri kaynağı")
    
    class Config:
        json_encoders = {
            Decimal: str,
            datetime: lambda v: v.isoformat()
        }
    
    def to_dict(self) -> Dict[str, Any]:
        """Veritabanı için dict formatı"""
        return {
            "timestamp": self.timestamp,
            "gram_altin": float(self.gram_altin),
            "ons_usd": float(self.ons_usd),
            "usd_try": float(self.usd_try),
            "ons_try": float(self.ons_try),
            "source": self.source
        }
    
    @property
    def gram_to_ons_ratio(self) -> Decimal:
        """Gram altın / ONS oranı (teorik olması gereken: ~31.1035)"""
        return self.ons_try / self.gram_altin
    
    @property
    def is_gram_premium(self) -> bool:
        """Gram altın primli mi? (Normal: 31.1035 gram = 1 ons)"""
        return self.gram_to_ons_ratio < Decimal("31.1035")


class GramAltinCandle(BaseModel):
    """Gram altın için OHLC mum verisi"""
    timestamp: datetime
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: Optional[int] = Field(None, description="İşlem adedi")
    interval: str  # "15m", "1h", "4h", "1d"
    
    class Config:
        json_encoders = {
            Decimal: str,
            datetime: lambda v: v.isoformat()
        }


class GlobalTrendData(BaseModel):
    """ONS/USD global trend verisi"""
    timestamp: datetime
    ons_usd: Decimal
    trend: str  # BULLISH, BEARISH, SIDEWAYS
    strength: str  # STRONG, MODERATE, WEAK
    ma50: Optional[Decimal] = None
    ma200: Optional[Decimal] = None
    
    @property
    def is_golden_cross(self) -> bool:
        """MA50 > MA200 (Golden Cross)"""
        if self.ma50 and self.ma200:
            return self.ma50 > self.ma200
        return False


class CurrencyRiskData(BaseModel):
    """USD/TRY risk değerlendirme verisi"""
    timestamp: datetime
    usd_try: Decimal
    volatility: Decimal  # Yüzde olarak
    risk_level: str  # LOW, MEDIUM, HIGH, EXTREME
    intervention_risk: bool = Field(False, description="Müdahale riski var mı?")
    
    @property
    def position_size_multiplier(self) -> Decimal:
        """Risk seviyesine göre pozisyon çarpanı"""
        multipliers = {
            "LOW": Decimal("1.0"),
            "MEDIUM": Decimal("0.7"),
            "HIGH": Decimal("0.5"),
            "EXTREME": Decimal("0.3")
        }
        return multipliers.get(self.risk_level, Decimal("0.5"))