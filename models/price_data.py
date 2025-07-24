"""
Price data models
"""
from datetime import datetime
from decimal import Decimal
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field
from utils.timezone import utc_now


class PriceData(BaseModel):
    """Fiyat verisi modeli"""
    timestamp: datetime = Field(default_factory=utc_now)
    ons_usd: Decimal = Field(..., description="Ons altın USD fiyatı")
    usd_try: Decimal = Field(..., description="USD/TRY kuru")
    ons_try: Decimal = Field(..., description="Ons altın TRY fiyatı")
    gram_altin: Optional[Decimal] = Field(None, description="Gram altın TRY fiyatı")
    source: str = Field(default="api", description="Veri kaynağı")
    interval: str = Field(default="5s", description="Veri aralığı")
    
    class Config:
        json_encoders = {
            Decimal: str,
            datetime: lambda v: v.isoformat()
        }
    
    def to_dict(self) -> Dict[str, Any]:
        """MongoDB için dict formatına çevir"""
        return {
            "timestamp": self.timestamp,
            "ons_usd": float(self.ons_usd),
            "usd_try": float(self.usd_try),
            "ons_try": float(self.ons_try),
            "gram_altin": float(self.gram_altin) if self.gram_altin else None,
            "source": self.source,
            "interval": self.interval
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PriceData":
        """MongoDB'den gelen veriyi model'e çevir"""
        return cls(
            timestamp=data["timestamp"],
            ons_usd=Decimal(str(data["ons_usd"])),
            usd_try=Decimal(str(data["usd_try"])),
            ons_try=Decimal(str(data["ons_try"])),
            source=data.get("source", "api"),
            interval=data.get("interval", "5s")
        )


class PriceCandle(BaseModel):
    """OHLC mum verisi"""
    timestamp: datetime
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: Optional[Decimal] = None
    interval: str  # "15m", "1h", "4h", "1d"
    
    class Config:
        json_encoders = {
            Decimal: str,
            datetime: lambda v: v.isoformat()
        }
    
    def to_dict(self) -> Dict[str, Any]:
        """MongoDB için dict formatına çevir"""
        return {
            "timestamp": self.timestamp,
            "open": float(self.open),
            "high": float(self.high),
            "low": float(self.low),
            "close": float(self.close),
            "volume": float(self.volume) if self.volume else None,
            "interval": self.interval
        }