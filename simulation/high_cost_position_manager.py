"""
Yüksek İşlem Maliyeti için Özelleştirilmiş Pozisyon Yöneticisi
%0.45 toplam işlem maliyeti ile kar etmek için optimize edilmiş
"""
import logging
from typing import Dict, Optional, Tuple
from decimal import Decimal
from datetime import datetime

from models.simulation import SimulationPosition, ExitReason
from utils.timezone import now

logger = logging.getLogger(__name__)


class HighCostPositionManager:
    """Yüksek işlem maliyeti için özelleştirilmiş pozisyon yöneticisi"""
    
    def __init__(self):
        # Yüksek maliyet için çok sıkı parametreler
        self.min_profit_threshold = 0.008  # %0.8 minimum kar (maliyet üstü)
        self.breakeven_buffer = 0.006      # %0.6 breakeven buffer
        self.high_confidence_threshold = 0.85  # %85 güven için işlem
        
    def should_enter_position(self, 
                            signal_data: Dict,
                            market_conditions: Dict,
                            timeframe_capital: Dict) -> Tuple[bool, str]:
        """
        Yüksek maliyet koşullarında pozisyon açılmalı mı?
        
        Returns:
            (should_enter, reason)
        """
        try:
            confidence = signal_data.get('confidence', 0)
            signal_type = signal_data.get('signal', 'HOLD')
            volatility = market_conditions.get('volatility', 0)
            
            # 1. Temel kontroller
            if signal_type == 'HOLD':
                return False, "Signal is HOLD"
            
            if not timeframe_capital.get('available_capital', 0) > 0:
                return False, "No available capital"
            
            # 2. Güven skoru kontrolü - Çok sıkı
            min_confidence = self._get_min_confidence_for_conditions(
                market_conditions, signal_data
            )
            
            if confidence < min_confidence:
                return False, f"Confidence {confidence:.2%} < required {min_confidence:.2%}"
            
            # 3. Volatilite kontrolü - Yeterli hareket var mı?
            min_volatility = self._get_min_volatility_for_profit()
            if volatility < min_volatility:
                return False, f"Volatility {volatility:.3f} too low for high costs"
            
            # 4. Risk/Reward oranı kontrolü
            expected_rr = signal_data.get('expected_risk_reward', 2.0)
            min_rr = self._get_min_risk_reward_ratio(confidence)
            
            if expected_rr < min_rr:
                return False, f"Risk/Reward {expected_rr:.1f} < required {min_rr:.1f}"
            
            # 5. Trend uyumu kontrolü
            if not self._check_strong_trend_alignment(signal_data, market_conditions):
                return False, "Weak trend alignment for high-cost trading"
            
            return True, f"High-cost entry approved (conf={confidence:.2%}, vol={volatility:.3f})"
            
        except Exception as e:
            logger.error(f"Position entry check error: {str(e)}")
            return False, f"Error: {str(e)}"
    
    def calculate_position_size(self,
                              available_capital: Decimal,
                              entry_price: Decimal,
                              stop_loss: Decimal,
                              confidence: float,
                              strategy_type: str) -> Dict:
        """Yüksek maliyet için optimize edilmiş pozisyon boyutu"""
        try:
            # Risk per trade - konservatif
            base_risk = 0.012  # %1.2 base
            
            # Strateji tipine göre ayarlama
            strategy_multipliers = {
                "HIGH_COST_CONSERVATIVE": 0.8,  # %80 çarpanı
                "HIGH_COST_TREND": 1.0,         # Normal
                "HIGH_COST_DIP_BUYER": 1.2      # %120 çarpanı
            }
            
            risk_multiplier = strategy_multipliers.get(strategy_type, 0.8)
            adjusted_risk = base_risk * risk_multiplier
            
            # Güven skoruna göre ayarlama - Çok sıkı
            confidence_factor = min(confidence ** 2, 0.8)  # Maksimum %80
            final_risk = adjusted_risk * confidence_factor
            
            # Stop loss mesafesine göre pozisyon boyutu
            price_risk = abs(float(entry_price) - float(stop_loss)) / float(entry_price)
            max_loss_amount = float(available_capital) * final_risk
            
            # Pozisyon boyutu (gram)
            position_size = max_loss_amount / price_risk
            
            # Minimum pozisyon kontrolü (işlem maliyetini karşılamak için)
            min_position_value = 500.0  # 500 TL minimum
            if position_size * float(entry_price) < min_position_value:
                return {
                    'position_size': 0,
                    'risk_amount': 0,
                    'reason': f'Position too small (< {min_position_value} TL) for high costs'
                }
            
            return {
                'position_size': round(position_size, 3),
                'risk_amount': round(max_loss_amount, 2),
                'risk_percentage': round(final_risk * 100, 2),
                'confidence_factor': round(confidence_factor, 3),
                'price_risk': round(price_risk * 100, 2)
            }
            
        except Exception as e:
            logger.error(f"Position size calculation error: {str(e)}")
            return {'position_size': 0, 'error': str(e)}
    
    def should_exit_position(self,
                           position: SimulationPosition,
                           current_price: Decimal,
                           market_data: Dict) -> Tuple[bool, ExitReason, str]:
        """
        Yüksek maliyet koşullarında pozisyon kapatılmalı mı?
        """
        try:
            # Mevcut P&L hesapla
            net_pnl, pnl_pct = position.calculate_current_pnl(current_price)
            
            # 1. Stop Loss kontrolü
            if self._check_stop_loss(position, current_price):
                return True, ExitReason.STOP_LOSS, f"Stop loss hit at {current_price}"
            
            # 2. Take Profit kontrolü  
            if self._check_take_profit(position, current_price):
                return True, ExitReason.TAKE_PROFIT, f"Take profit hit at {current_price}"
            
            # 3. Trailing Stop kontrolü
            if position.trailing_stop and self._check_trailing_stop(position, current_price):
                return True, ExitReason.TRAILING_STOP, f"Trailing stop hit at {current_price}"
            
            # 4. Yüksek maliyet için özel çıkış koşulları
            
            # Minimum kar eşiğine ulaştıysa ve momentum kaybediyorsa
            if (pnl_pct >= self.min_profit_threshold and 
                self._is_momentum_weakening(market_data)):
                return True, ExitReason.CONFIDENCE_DROP, "Momentum weakening after reaching min profit"
            
            # Breakeven yakınında ve güven düşüyorsa
            if (abs(pnl_pct) < self.breakeven_buffer and
                market_data.get('signal_confidence', 1.0) < 0.6):
                return True, ExitReason.CONFIDENCE_DROP, "Low confidence near breakeven"
            
            # Volatilite spike - kar koruma
            if (pnl_pct > 0.005 and  # %0.5 kârda
                market_data.get('volatility_spike', False)):
                return True, ExitReason.VOLATILITY_SPIKE, "Protecting profit from volatility spike"
            
            # Zaman limiti kontrolü
            holding_time = (now() - position.entry_time).total_seconds() / 3600  # saat
            max_holding_time = self._get_max_holding_time(position.timeframe)
            
            if holding_time > max_holding_time:
                return True, ExitReason.TIME_LIMIT, f"Max holding time exceeded ({holding_time:.1f}h)"
            
            return False, None, "Position holding"
            
        except Exception as e:
            logger.error(f"Exit check error: {str(e)}")
            return True, ExitReason.MANUAL, f"Error in exit check: {str(e)}"
    
    def _get_min_confidence_for_conditions(self, market_conditions: Dict, signal_data: Dict) -> float:
        """Market koşullarına göre minimum güven eşiği"""
        base_confidence = 0.75  # %75 base
        
        # Risk seviyesine göre artır
        risk_level = market_conditions.get('risk_level', 'MEDIUM')
        if risk_level in ['HIGH', 'EXTREME']:
            base_confidence = 0.85
        
        # Global trend uyumsuzluğunda artır
        global_trend = market_conditions.get('global_trend', 'NEUTRAL')
        signal_type = signal_data.get('signal', 'HOLD')
        
        if ((signal_type == 'BUY' and global_trend == 'BEARISH') or
            (signal_type == 'SELL' and global_trend == 'BULLISH')):
            base_confidence = 0.90  # %90 gerekir
        
        return base_confidence
    
    def _get_min_volatility_for_profit(self) -> float:
        """Kar için minimum volatilite"""
        # %0.45 maliyeti karşılamak için minimum %0.8 hareket gerekli
        return 0.008  # %0.8 günlük volatilite
    
    def _get_min_risk_reward_ratio(self, confidence: float) -> float:
        """Güven skoruna göre minimum RR oranı"""
        if confidence >= 0.85:
            return 3.5  # Çok güçlü sinyal için 3.5:1
        elif confidence >= 0.80:
            return 4.0  # Güçlü sinyal için 4:1
        else:
            return 5.0  # Zayıf sinyal için 5:1
    
    def _check_strong_trend_alignment(self, signal_data: Dict, market_conditions: Dict) -> bool:
        """Güçlü trend uyumu var mı?"""
        signal_type = signal_data.get('signal')
        global_trend = market_conditions.get('global_trend', 'NEUTRAL')
        confidence = signal_data.get('confidence', 0)
        
        # Perfect alignment
        if ((signal_type == 'BUY' and global_trend == 'BULLISH') or
            (signal_type == 'SELL' and global_trend == 'BEARISH')):
            return True
        
        # Counter-trend sadece çok güçlü sinyallerle
        if confidence >= 0.90:
            return True
        
        return False
    
    def _check_stop_loss(self, position: SimulationPosition, current_price: Decimal) -> bool:
        """Stop loss kontrolü"""
        if position.position_type == "LONG":
            return current_price <= position.stop_loss
        else:
            return current_price >= position.stop_loss
    
    def _check_take_profit(self, position: SimulationPosition, current_price: Decimal) -> bool:
        """Take profit kontrolü"""
        if position.position_type == "LONG":
            return current_price >= position.take_profit
        else:
            return current_price <= position.take_profit
    
    def _check_trailing_stop(self, position: SimulationPosition, current_price: Decimal) -> bool:
        """Trailing stop kontrolü"""
        if not position.trailing_stop:
            return False
            
        if position.position_type == "LONG":
            return current_price <= position.trailing_stop
        else:
            return current_price >= position.trailing_stop
    
    def _is_momentum_weakening(self, market_data: Dict) -> bool:
        """Momentum zayıflıyor mu?"""
        # RSI overbought/oversold
        rsi = market_data.get('rsi', 50)
        if rsi > 70 or rsi < 30:
            return True
        
        # MACD divergence
        macd_signal = market_data.get('macd_signal', 'NEUTRAL')
        if macd_signal == 'BEARISH_DIVERGENCE':
            return True
        
        # Sinyal güven düşüşü
        if market_data.get('signal_confidence', 1.0) < 0.7:
            return True
        
        return False
    
    def _get_max_holding_time(self, timeframe: str) -> float:
        """Timeframe'e göre maksimum tutma süresi (saat)"""
        # Yüksek maliyet için daha kısa süreler
        timeframe_limits = {
            "15m": 2,    # 2 saat
            "1h": 8,     # 8 saat  
            "4h": 48,    # 2 gün
            "1d": 120    # 5 gün
        }
        return timeframe_limits.get(timeframe, 24)