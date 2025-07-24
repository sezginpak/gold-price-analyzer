"""
Trading signal models
"""
from datetime import datetime
from decimal import Decimal
from typing import Dict, List, Optional, Any
from enum import Enum
from pydantic import BaseModel, Field
from utils.timezone import utc_now


class SignalType(str, Enum):
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"


class RiskLevel(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class SignalResult(str, Enum):
    SUCCESS = "SUCCESS"
    FAILURE = "FAILURE"
    PENDING = "PENDING"


class TradingSignal(BaseModel):
    """Alım/Satım sinyali modeli"""
    timestamp: datetime = Field(default_factory=utc_now)
    signal_type: SignalType
    price_level: Decimal = Field(..., description="Sinyal fiyat seviyesi")
    current_price: Decimal = Field(..., description="Mevcut fiyat")
    
    # Güven skorları
    confidence_scores: Dict[str, float] = Field(
        default_factory=dict,
        description="Her analiz yöntemi için güven skoru"
    )
    overall_confidence: float = Field(..., ge=0, le=1)
    
    # Sinyal detayları
    reasons: List[str] = Field(default_factory=list)
    risk_level: RiskLevel = RiskLevel.MEDIUM
    
    # Hedefler
    target_price: Optional[Decimal] = None
    stop_loss: Optional[Decimal] = None
    
    # Sonuç takibi
    executed: bool = Field(default=False)
    execution_price: Optional[Decimal] = None
    execution_time: Optional[datetime] = None
    result: Optional[SignalResult] = SignalResult.PENDING
    profit_loss: Optional[Decimal] = None
    
    # Metadata - ek bilgiler için
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    class Config:
        json_encoders = {
            Decimal: str,
            datetime: lambda v: v.isoformat()
        }
    
    def to_dict(self) -> Dict[str, Any]:
        """MongoDB için dict formatına çevir"""
        return {
            "timestamp": self.timestamp,
            "signal_type": self.signal_type.value,
            "price_level": float(self.price_level),
            "current_price": float(self.current_price),
            "confidence_scores": self.confidence_scores,
            "overall_confidence": self.overall_confidence,
            "reasons": self.reasons,
            "risk_level": self.risk_level.value,
            "target_price": float(self.target_price) if self.target_price else None,
            "stop_loss": float(self.stop_loss) if self.stop_loss else None,
            "executed": self.executed,
            "execution_price": float(self.execution_price) if self.execution_price else None,
            "execution_time": self.execution_time,
            "result": self.result.value if self.result else None,
            "profit_loss": float(self.profit_loss) if self.profit_loss else None
        }


class SupportResistance(BaseModel):
    """Destek/Direnç seviyeleri"""
    level: Decimal
    strength: float = Field(..., ge=0, le=1)  # 0-1 arası güç
    level_type: str  # "support" veya "resistance"
    touch_count: int = Field(default=1)
    last_test: datetime
    
    class Config:
        json_encoders = {
            Decimal: str,
            datetime: lambda v: v.isoformat()
        }