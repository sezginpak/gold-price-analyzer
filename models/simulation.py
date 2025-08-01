"""
Simülasyon sistemi modelleri
"""
from datetime import datetime
from decimal import Decimal
from typing import Dict, List, Optional, Any, Tuple
from enum import Enum
from dataclasses import dataclass, field
from pydantic import BaseModel, Field
import json


class SimulationStatus(str, Enum):
    """Simülasyon durumları"""
    ACTIVE = "ACTIVE"
    PAUSED = "PAUSED"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class StrategyType(str, Enum):
    """Strateji tipleri"""
    MAIN = "MAIN"
    CONSERVATIVE = "CONSERVATIVE"
    MOMENTUM = "MOMENTUM"
    MEAN_REVERSION = "MEAN_REVERSION"
    CONSENSUS = "CONSENSUS"
    RISK_ADJUSTED = "RISK_ADJUSTED"
    TIME_BASED = "TIME_BASED"


class PositionStatus(str, Enum):
    """Pozisyon durumları"""
    OPEN = "OPEN"
    CLOSED = "CLOSED"
    CANCELLED = "CANCELLED"


class ExitReason(str, Enum):
    """Pozisyon çıkış nedenleri"""
    STOP_LOSS = "STOP_LOSS"
    TAKE_PROFIT = "TAKE_PROFIT"
    TRAILING_STOP = "TRAILING_STOP"
    REVERSE_SIGNAL = "REVERSE_SIGNAL"
    TIME_LIMIT = "TIME_LIMIT"
    CONFIDENCE_DROP = "CONFIDENCE_DROP"
    VOLATILITY_SPIKE = "VOLATILITY_SPIKE"
    DAILY_LIMIT = "DAILY_LIMIT"
    END_OF_DAY = "END_OF_DAY"
    MANUAL = "MANUAL"


@dataclass
class SimulationConfig:
    """Simülasyon konfigürasyonu"""
    name: str
    strategy_type: StrategyType
    initial_capital: Decimal = Decimal("1000.0")  # gram
    min_confidence: float = 0.35  # Daha düşük eşik - geçici test için
    max_risk: float = 0.02
    max_daily_risk: float = 0.02
    spread: Decimal = Decimal("2.0")  # TL - gerçekçi spread değeri (~%0.05)
    commission_rate: float = 0.0003  # %0.03 komisyon
    
    # Timeframe sermaye dağılımı
    capital_distribution: Dict[str, Decimal] = field(default_factory=lambda: {
        "15m": Decimal("250.0"),
        "1h": Decimal("250.0"),
        "4h": Decimal("250.0"),
        "1d": Decimal("250.0")
    })
    
    # İşlem saatleri
    trading_hours: Tuple[int, int] = (9, 17)  # 09:00-17:00
    
    # Çıkış stratejisi parametreleri
    atr_multiplier_sl: float = 1.5  # Stop loss için ATR çarpanı
    risk_reward_ratio: float = 2.0  # Take profit için RR oranı
    trailing_stop_activation: float = 0.5  # TP'nin %50'sine gelince aktif
    trailing_stop_distance: float = 0.3  # Mevcut kârın %30'unu bırak
    
    # Zaman limitleri (saat cinsinden)
    time_limits: Dict[str, int] = field(default_factory=lambda: {
        "15m": 4,    # 4 saat
        "1h": 24,    # 1 gün
        "4h": 72,    # 3 gün
        "1d": 168    # 7 gün
    })
    
    # Strateji özel parametreleri
    strategy_params: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Dictionary'ye çevir"""
        return {
            "name": self.name,
            "strategy_type": self.strategy_type.value,
            "initial_capital": float(self.initial_capital),
            "min_confidence": self.min_confidence,
            "max_risk": self.max_risk,
            "max_daily_risk": self.max_daily_risk,
            "spread": float(self.spread),
            "commission_rate": self.commission_rate,
            "capital_distribution": {k: float(v) for k, v in self.capital_distribution.items()},
            "trading_hours": self.trading_hours,
            "atr_multiplier_sl": self.atr_multiplier_sl,
            "risk_reward_ratio": self.risk_reward_ratio,
            "trailing_stop_activation": self.trailing_stop_activation,
            "trailing_stop_distance": self.trailing_stop_distance,
            "time_limits": self.time_limits,
            "strategy_params": self.strategy_params
        }


class SimulationPosition(BaseModel):
    """Simülasyon pozisyonu"""
    id: Optional[int] = None
    simulation_id: int
    timeframe: str
    
    # Pozisyon bilgileri
    position_type: str = "LONG"
    status: PositionStatus = PositionStatus.OPEN
    
    # Giriş
    entry_signal_id: Optional[int] = None
    entry_time: datetime
    entry_price: Decimal
    entry_spread: Decimal
    entry_commission: Decimal
    
    # Boyut ve risk
    position_size: Decimal  # gram
    allocated_capital: Decimal
    risk_amount: Decimal
    
    # Risk yönetimi
    stop_loss: Decimal
    take_profit: Decimal
    trailing_stop: Optional[Decimal] = None
    max_profit: Decimal = Decimal("0.0")
    
    # Çıkış
    exit_time: Optional[datetime] = None
    exit_price: Optional[Decimal] = None
    exit_spread: Optional[Decimal] = None
    exit_commission: Optional[Decimal] = None
    exit_reason: Optional[ExitReason] = None
    
    # Sonuç
    gross_profit_loss: Optional[Decimal] = None
    net_profit_loss: Optional[Decimal] = None
    profit_loss_pct: Optional[float] = None
    holding_period_minutes: Optional[int] = None
    
    # Analiz
    entry_confidence: float
    entry_indicators: Optional[Dict[str, Any]] = None
    exit_indicators: Optional[Dict[str, Any]] = None
    
    class Config:
        json_encoders = {
            Decimal: lambda v: float(v),
            datetime: lambda v: v.isoformat(),
            Enum: lambda v: v.value
        }
    
    def calculate_current_pnl(self, current_price: Decimal) -> Tuple[Decimal, float]:
        """Mevcut kar/zarar hesapla"""
        if self.position_type == "LONG":
            gross_pnl = (current_price - self.entry_price) * self.position_size
        else:
            gross_pnl = (self.entry_price - current_price) * self.position_size
        
        # Spread ve komisyon dahil
        exit_spread = self.entry_spread  # Çıkışta da aynı spread
        exit_commission = current_price * self.position_size * self.entry_commission / self.entry_price
        
        net_pnl = gross_pnl - exit_spread - exit_commission
        pnl_pct = (net_pnl / self.allocated_capital) * 100
        
        return net_pnl, pnl_pct
    
    def should_activate_trailing_stop(self, current_price: Decimal, activation_pct: float = 0.5) -> bool:
        """Trailing stop aktif edilmeli mi?"""
        if self.position_type == "LONG":
            price_diff = current_price - self.entry_price
            target_diff = self.take_profit - self.entry_price
        else:
            price_diff = self.entry_price - current_price
            target_diff = self.entry_price - self.take_profit
        
        if target_diff > 0:
            progress = price_diff / target_diff
            return progress >= activation_pct
        
        return False
    
    def calculate_trailing_stop(self, current_price: Decimal, trail_distance: float = 0.3) -> Decimal:
        """Yeni trailing stop seviyesi hesapla"""
        net_pnl, _ = self.calculate_current_pnl(current_price)
        
        if net_pnl > self.max_profit:
            self.max_profit = net_pnl
        
        # Maksimum kârın %70'ini koru (trail_distance = 0.3)
        protected_profit = self.max_profit * (1 - trail_distance)
        
        if self.position_type == "LONG":
            # Korunacak kâr seviyesine göre stop fiyatı
            new_stop = self.entry_price + (protected_profit / self.position_size)
        else:
            new_stop = self.entry_price - (protected_profit / self.position_size)
        
        return new_stop


@dataclass
class TimeframeCapital:
    """Timeframe bazlı sermaye durumu"""
    timeframe: str
    allocated_capital: Decimal
    current_capital: Decimal
    in_position: bool = False
    open_position_id: Optional[int] = None
    last_trade_time: Optional[datetime] = None
    
    def available_capital(self) -> Decimal:
        """Kullanılabilir sermaye"""
        return self.current_capital if not self.in_position else Decimal("0")
    
    def update_capital(self, pnl: Decimal):
        """Sermayeyi güncelle"""
        self.current_capital += pnl
        self.in_position = False
        self.open_position_id = None


class SimulationSummary(BaseModel):
    """Simülasyon özet bilgileri"""
    simulation_id: int
    name: str
    strategy_type: str
    status: SimulationStatus
    
    # Sermaye durumu
    initial_capital: Decimal
    current_capital: Decimal
    total_pnl: Decimal
    total_pnl_pct: float
    
    # Timeframe detayları
    timeframe_capitals: Dict[str, Dict[str, float]]
    
    # İşlem istatistikleri
    total_trades: int
    open_positions: int
    winning_trades: int
    losing_trades: int
    win_rate: float
    
    # Performans metrikleri
    profit_factor: float
    sharpe_ratio: float
    max_drawdown: float
    max_drawdown_pct: float
    avg_win: float
    avg_loss: float
    avg_win_loss_ratio: float
    
    # Zaman bilgileri
    start_date: datetime
    last_update: datetime
    running_days: int
    
    # Günlük durum
    daily_pnl: Decimal
    daily_pnl_pct: float
    daily_trades: int
    daily_risk_used: float
    
    class Config:
        json_encoders = {
            Decimal: lambda v: float(v),
            datetime: lambda v: v.isoformat(),
            Enum: lambda v: v.value
        }