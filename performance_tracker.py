"""
Performance Tracker - Sinyal performansı takip sistemi
"""
from typing import List, Dict, Optional, Tuple
from decimal import Decimal
from datetime import datetime, timedelta
from dataclasses import dataclass, field
import json
import logging
from models.trading_signal import TradingSignal, SignalType

logger = logging.getLogger(__name__)


@dataclass
class SignalResult:
    """Sinyal sonuç verisi"""
    signal_id: str
    timestamp: datetime
    signal_type: SignalType
    entry_price: Decimal
    stop_loss: Decimal
    take_profit: Decimal
    confidence: float
    exit_price: Optional[Decimal] = None
    exit_time: Optional[datetime] = None
    exit_reason: Optional[str] = None  # "TP", "SL", "MANUAL", "TIMEOUT"
    pnl: Optional[float] = None  # Profit/Loss percentage
    pnl_amount: Optional[Decimal] = None
    duration: Optional[timedelta] = None
    max_profit: Optional[float] = None  # Maximum profit during trade
    max_loss: Optional[float] = None    # Maximum loss during trade
    result: Optional[str] = None  # "WIN", "LOSS", "BREAKEVEN"


class PerformanceTracker:
    """Sinyal performansı takip ve analiz"""
    
    def __init__(self, db_path: str = "performance.db"):
        self.db_path = db_path
        self.active_signals: Dict[str, SignalResult] = {}
        self.completed_signals: List[SignalResult] = []
        self._load_history()
    
    def track_signal(self, signal: TradingSignal) -> str:
        """Yeni sinyali takibe al"""
        try:
            if not signal:
                logger.warning("Cannot track None signal")
                return ""
            
            signal_id = f"{signal.timestamp.isoformat()}_{signal.signal_type.value}"
            
            result = SignalResult(
                signal_id=signal_id,
                timestamp=signal.timestamp,
                signal_type=signal.signal_type,
                entry_price=signal.price_level,
                stop_loss=signal.stop_loss,
                take_profit=signal.target_price,
                confidence=signal.overall_confidence
            )
            
            self.active_signals[signal_id] = result
            logger.info(f"Tracking new signal: {signal_id}")
            
            return signal_id
            
        except Exception as e:
            logger.error(f"Failed to track signal: {e}", exc_info=True)
            return ""
    
    def update_signal(self, signal_id: str, current_price: Decimal):
        """Aktif sinyali güncelle"""
        try:
            if not signal_id or signal_id not in self.active_signals:
                return
            
            if not current_price or current_price <= 0:
                logger.warning(f"Invalid price for signal update: {current_price}")
                return
            
            signal = self.active_signals[signal_id]
        
            # Max profit/loss güncelle
            if signal.signal_type == SignalType.BUY:
                profit_pct = float((current_price - signal.entry_price) / signal.entry_price * 100)
                
                if signal.max_profit is None or profit_pct > signal.max_profit:
                    signal.max_profit = profit_pct
                if signal.max_loss is None or profit_pct < signal.max_loss:
                    signal.max_loss = profit_pct
                
                # TP/SL kontrolü
                if current_price >= signal.take_profit:
                    self.close_signal(signal_id, current_price, "TP")
                elif current_price <= signal.stop_loss:
                    self.close_signal(signal_id, current_price, "SL")
            
            else:  # SELL signal
                profit_pct = float((signal.entry_price - current_price) / signal.entry_price * 100)
                
                if signal.max_profit is None or profit_pct > signal.max_profit:
                    signal.max_profit = profit_pct
                if signal.max_loss is None or profit_pct < signal.max_loss:
                    signal.max_loss = profit_pct
                
                # TP/SL kontrolü
                if current_price <= signal.take_profit:
                    self.close_signal(signal_id, current_price, "TP")
                elif current_price >= signal.stop_loss:
                    self.close_signal(signal_id, current_price, "SL")
                    
        except Exception as e:
            logger.error(f"Failed to update signal {signal_id}: {e}")
    
    def close_signal(self, signal_id: str, exit_price: Decimal, exit_reason: str):
        """Sinyali kapat"""
        if signal_id not in self.active_signals:
            return
        
        signal = self.active_signals[signal_id]
        signal.exit_price = exit_price
        signal.exit_time = datetime.now()
        signal.exit_reason = exit_reason
        signal.duration = signal.exit_time - signal.timestamp
        
        # PnL hesapla
        if signal.signal_type == SignalType.BUY:
            signal.pnl = float((exit_price - signal.entry_price) / signal.entry_price * 100)
            signal.pnl_amount = exit_price - signal.entry_price
        else:  # SELL
            signal.pnl = float((signal.entry_price - exit_price) / signal.entry_price * 100)
            signal.pnl_amount = signal.entry_price - exit_price
        
        # Sonucu belirle
        if signal.pnl > 0.1:  # %0.1'den fazla kar
            signal.result = "WIN"
        elif signal.pnl < -0.1:  # %0.1'den fazla zarar
            signal.result = "LOSS"
        else:
            signal.result = "BREAKEVEN"
        
        # Tamamlananlar listesine ekle
        self.completed_signals.append(signal)
        del self.active_signals[signal_id]
        
        # Kaydet
        self._save_signal(signal)
        
        logger.info(f"Signal closed: {signal_id}, Result: {signal.result}, PnL: {signal.pnl:.2f}%")
    
    def check_timeouts(self, timeout_hours: int = 24):
        """Zaman aşımına uğrayan sinyalleri kapat"""
        current_time = datetime.now()
        timeout_delta = timedelta(hours=timeout_hours)
        
        for signal_id, signal in list(self.active_signals.items()):
            if current_time - signal.timestamp > timeout_delta:
                # Mevcut fiyat bilgisi olmadığı için entry price'da kapat
                self.close_signal(signal_id, signal.entry_price, "TIMEOUT")
    
    def get_statistics(self) -> Dict[str, any]:
        """Performans istatistikleri"""
        if not self.completed_signals:
            return {
                "total_signals": 0,
                "win_rate": 0,
                "profit_factor": 0,
                "avg_win": 0,
                "avg_loss": 0,
                "max_win": 0,
                "max_loss": 0,
                "avg_duration": 0,
                "total_pnl": 0
            }
        
        wins = [s for s in self.completed_signals if s.result == "WIN"]
        losses = [s for s in self.completed_signals if s.result == "LOSS"]
        
        total_wins = sum(s.pnl for s in wins) if wins else 0
        total_losses = abs(sum(s.pnl for s in losses)) if losses else 0
        
        avg_duration = sum(
            s.duration.total_seconds() for s in self.completed_signals if s.duration
        ) / len(self.completed_signals)
        
        return {
            "total_signals": len(self.completed_signals),
            "active_signals": len(self.active_signals),
            "win_count": len(wins),
            "loss_count": len(losses),
            "win_rate": len(wins) / len(self.completed_signals) * 100 if self.completed_signals else 0,
            "profit_factor": total_wins / total_losses if total_losses > 0 else float('inf'),
            "avg_win": sum(s.pnl for s in wins) / len(wins) if wins else 0,
            "avg_loss": sum(s.pnl for s in losses) / len(losses) if losses else 0,
            "max_win": max((s.pnl for s in wins), default=0),
            "max_loss": min((s.pnl for s in losses), default=0),
            "avg_duration_hours": avg_duration / 3600 if avg_duration else 0,
            "total_pnl": sum(s.pnl for s in self.completed_signals),
            "sharpe_ratio": self._calculate_sharpe_ratio(),
            "max_drawdown": self._calculate_max_drawdown()
        }
    
    def get_signal_history(self, limit: int = 50) -> List[Dict[str, any]]:
        """Son sinyal geçmişi"""
        signals = sorted(
            self.completed_signals, 
            key=lambda x: x.exit_time or x.timestamp, 
            reverse=True
        )[:limit]
        
        return [
            {
                "id": s.signal_id,
                "timestamp": s.timestamp.isoformat(),
                "type": s.signal_type.value,
                "entry_price": float(s.entry_price),
                "exit_price": float(s.exit_price) if s.exit_price else None,
                "exit_time": s.exit_time.isoformat() if s.exit_time else None,
                "exit_reason": s.exit_reason,
                "pnl": s.pnl,
                "result": s.result,
                "confidence": s.confidence,
                "duration_hours": s.duration.total_seconds() / 3600 if s.duration else None,
                "max_profit": s.max_profit,
                "max_loss": s.max_loss
            }
            for s in signals
        ]
    
    def get_performance_by_confidence(self) -> Dict[str, any]:
        """Güven skoruna göre performans analizi"""
        confidence_buckets = {
            "high": {"min": 0.8, "signals": []},
            "medium": {"min": 0.6, "signals": []},
            "low": {"min": 0.0, "signals": []}
        }
        
        for signal in self.completed_signals:
            if signal.confidence >= 0.8:
                confidence_buckets["high"]["signals"].append(signal)
            elif signal.confidence >= 0.6:
                confidence_buckets["medium"]["signals"].append(signal)
            else:
                confidence_buckets["low"]["signals"].append(signal)
        
        results = {}
        for bucket_name, bucket_data in confidence_buckets.items():
            signals = bucket_data["signals"]
            if signals:
                wins = [s for s in signals if s.result == "WIN"]
                results[bucket_name] = {
                    "count": len(signals),
                    "win_rate": len(wins) / len(signals) * 100,
                    "avg_pnl": sum(s.pnl for s in signals) / len(signals)
                }
            else:
                results[bucket_name] = {
                    "count": 0,
                    "win_rate": 0,
                    "avg_pnl": 0
                }
        
        return results
    
    def get_best_worst_trades(self, count: int = 5) -> Dict[str, List[Dict]]:
        """En iyi ve en kötü işlemler"""
        sorted_by_pnl = sorted(self.completed_signals, key=lambda x: x.pnl or 0)
        
        worst = sorted_by_pnl[:count]
        best = sorted_by_pnl[-count:][::-1]
        
        return {
            "best_trades": [
                {
                    "timestamp": s.timestamp.isoformat(),
                    "type": s.signal_type.value,
                    "pnl": s.pnl,
                    "entry": float(s.entry_price),
                    "exit": float(s.exit_price) if s.exit_price else None,
                    "confidence": s.confidence
                }
                for s in best
            ],
            "worst_trades": [
                {
                    "timestamp": s.timestamp.isoformat(),
                    "type": s.signal_type.value,
                    "pnl": s.pnl,
                    "entry": float(s.entry_price),
                    "exit": float(s.exit_price) if s.exit_price else None,
                    "confidence": s.confidence
                }
                for s in worst
            ]
        }
    
    def _calculate_sharpe_ratio(self) -> float:
        """Sharpe oranı hesapla"""
        if len(self.completed_signals) < 2:
            return 0.0
        
        returns = [s.pnl for s in self.completed_signals if s.pnl is not None]
        if not returns:
            return 0.0
        
        avg_return = sum(returns) / len(returns)
        
        if len(returns) < 2:
            return 0.0
        
        # Standart sapma
        variance = sum((r - avg_return) ** 2 for r in returns) / (len(returns) - 1)
        std_dev = variance ** 0.5
        
        if std_dev == 0:
            return 0.0
        
        # Basitleştirilmiş Sharpe (risksiz getiri = 0)
        sharpe = avg_return / std_dev
        
        return sharpe
    
    def _calculate_max_drawdown(self) -> float:
        """Maksimum düşüş hesapla"""
        if not self.completed_signals:
            return 0.0
        
        # Kümülatif PnL
        cumulative_pnl = []
        total = 0
        
        for signal in sorted(self.completed_signals, key=lambda x: x.exit_time or x.timestamp):
            if signal.pnl:
                total += signal.pnl
                cumulative_pnl.append(total)
        
        if not cumulative_pnl:
            return 0.0
        
        # Max drawdown
        peak = cumulative_pnl[0]
        max_dd = 0
        
        for value in cumulative_pnl:
            if value > peak:
                peak = value
            
            drawdown = (peak - value) / peak * 100 if peak > 0 else 0
            if drawdown > max_dd:
                max_dd = drawdown
        
        return max_dd
    
    def _save_signal(self, signal: SignalResult):
        """Sinyali dosyaya kaydet"""
        try:
            # JSON formatına dönüştür
            data = {
                "signal_id": signal.signal_id,
                "timestamp": signal.timestamp.isoformat(),
                "signal_type": signal.signal_type.value,
                "entry_price": str(signal.entry_price),
                "stop_loss": str(signal.stop_loss),
                "take_profit": str(signal.take_profit),
                "confidence": signal.confidence,
                "exit_price": str(signal.exit_price) if signal.exit_price else None,
                "exit_time": signal.exit_time.isoformat() if signal.exit_time else None,
                "exit_reason": signal.exit_reason,
                "pnl": signal.pnl,
                "pnl_amount": str(signal.pnl_amount) if signal.pnl_amount else None,
                "duration": signal.duration.total_seconds() if signal.duration else None,
                "max_profit": signal.max_profit,
                "max_loss": signal.max_loss,
                "result": signal.result
            }
            
            # Dosyaya ekle
            with open(self.db_path, 'a') as f:
                f.write(json.dumps(data) + '\n')
                
        except Exception as e:
            logger.error(f"Failed to save signal: {e}")
    
    def _load_history(self):
        """Geçmiş sinyalleri yükle"""
        try:
            import os
            if not os.path.exists(self.db_path):
                return
            
            with open(self.db_path, 'r') as f:
                for line in f:
                    try:
                        data = json.loads(line.strip())
                        
                        signal = SignalResult(
                            signal_id=data["signal_id"],
                            timestamp=datetime.fromisoformat(data["timestamp"]),
                            signal_type=SignalType(data["signal_type"]),
                            entry_price=Decimal(data["entry_price"]),
                            stop_loss=Decimal(data["stop_loss"]),
                            take_profit=Decimal(data["take_profit"]),
                            confidence=data["confidence"],
                            exit_price=Decimal(data["exit_price"]) if data["exit_price"] else None,
                            exit_time=datetime.fromisoformat(data["exit_time"]) if data["exit_time"] else None,
                            exit_reason=data["exit_reason"],
                            pnl=data["pnl"],
                            pnl_amount=Decimal(data["pnl_amount"]) if data["pnl_amount"] else None,
                            duration=timedelta(seconds=data["duration"]) if data["duration"] else None,
                            max_profit=data["max_profit"],
                            max_loss=data["max_loss"],
                            result=data["result"]
                        )
                        
                        if signal.exit_time:
                            self.completed_signals.append(signal)
                        else:
                            self.active_signals[signal.signal_id] = signal
                            
                    except Exception as e:
                        logger.error(f"Failed to load signal: {e}")
                        
        except FileNotFoundError:
            pass
        except Exception as e:
            logger.error(f"Failed to load history: {e}")