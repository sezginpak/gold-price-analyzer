"""
Multi-day pattern analyzer - 2-3 günlük dip/tepe yakalama
"""
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
import logging
from decimal import Decimal
import numpy as np

from models.market_data import GramAltinCandle
from utils.timezone import now

logger = logging.getLogger(__name__)


class MultiDayPatternAnalyzer:
    """2-3 günlük dip/tepe pattern analizi"""
    
    def __init__(self, lookback_days: int = 3):
        self.lookback_days = lookback_days
        self.min_price_change_pct = 1.5  # %1.5 minimum değişim
        
    def analyze(self, candles: List[GramAltinCandle]) -> Dict[str, Any]:
        """
        Son 2-3 günün dip/tepe noktalarını analiz et
        
        Returns:
            {
                "is_near_bottom": bool,
                "is_near_top": bool,
                "bottom_distance_pct": float,
                "top_distance_pct": float,
                "multi_day_trend": str,
                "confidence": float,
                "support_level": float,
                "resistance_level": float
            }
        """
        if len(candles) < 24 * self.lookback_days:  # Yeterli veri yok (saatlik mum)
            return self._empty_result()
            
        try:
            # Son 3 günlük veriyi al
            recent_candles = candles[-(24 * self.lookback_days):]
            
            # Fiyat dizisi oluştur
            prices = [float(c.close) for c in recent_candles]
            highs = [float(c.high) for c in recent_candles]
            lows = [float(c.low) for c in recent_candles]
            
            # 3 günlük min/max
            three_day_high = max(highs)
            three_day_low = min(lows)
            current_price = prices[-1]
            
            # Orta nokta
            mid_point = (three_day_high + three_day_low) / 2
            price_range = three_day_high - three_day_low
            
            # Dip/Tepe uzaklık hesaplama
            bottom_distance_pct = ((current_price - three_day_low) / three_day_low) * 100
            top_distance_pct = ((three_day_high - current_price) / current_price) * 100
            
            # Trend analizi - son 24 saat vs önceki 48 saat
            last_24h_avg = np.mean(prices[-24:])
            prev_48h_avg = np.mean(prices[-72:-24]) if len(prices) > 72 else np.mean(prices[:-24])
            
            trend_change_pct = ((last_24h_avg - prev_48h_avg) / prev_48h_avg) * 100
            
            # Multi-day trend belirleme
            if trend_change_pct > 1.0:
                multi_day_trend = "BULLISH"
            elif trend_change_pct < -1.0:
                multi_day_trend = "BEARISH"
            else:
                multi_day_trend = "SIDEWAYS"
            
            # Dip/Tepe yakınlık kontrolü
            is_near_bottom = bottom_distance_pct <= 1.0  # Dip'e %1 yakınlık
            is_near_top = top_distance_pct <= 1.0  # Tepe'ye %1 yakınlık
            
            # Destek/Direnç seviyeleri (basit yaklaşım)
            support_level = three_day_low * 0.995  # %0.5 altı
            resistance_level = three_day_high * 1.005  # %0.5 üstü
            
            # Güven skoru hesaplama
            confidence = self._calculate_confidence(
                bottom_distance_pct, top_distance_pct, 
                price_range, three_day_low, multi_day_trend
            )
            
            # Momentum kontrolü - son 6 saatlik hareket
            recent_momentum = ((prices[-1] - prices[-6]) / prices[-6]) * 100 if len(prices) > 6 else 0
            
            result = {
                "is_near_bottom": is_near_bottom,
                "is_near_top": is_near_top,
                "bottom_distance_pct": round(bottom_distance_pct, 2),
                "top_distance_pct": round(top_distance_pct, 2),
                "multi_day_trend": multi_day_trend,
                "confidence": round(confidence, 3),
                "support_level": round(support_level, 2),
                "resistance_level": round(resistance_level, 2),
                "three_day_high": round(three_day_high, 2),
                "three_day_low": round(three_day_low, 2),
                "price_range_pct": round((price_range / mid_point) * 100, 2),
                "recent_momentum": round(recent_momentum, 2)
            }
            
            # Log önemli durumlar
            if is_near_bottom:
                logger.info(f"📉 MULTI-DAY BOTTOM DETECTED: {current_price:.2f} near {three_day_low:.2f}")
            elif is_near_top:
                logger.info(f"📈 MULTI-DAY TOP DETECTED: {current_price:.2f} near {three_day_high:.2f}")
                
            return result
            
        except Exception as e:
            logger.error(f"Multi-day pattern analysis error: {e}")
            return self._empty_result()
    
    def _calculate_confidence(self, bottom_dist: float, top_dist: float, 
                            price_range: float, low_price: float, trend: str) -> float:
        """Güven skoru hesaplama"""
        confidence = 0.5  # Base confidence
        
        # Dip/Tepe yakınlığı
        if bottom_dist <= 0.5:
            confidence += 0.3  # Çok yakın dip
        elif bottom_dist <= 1.0:
            confidence += 0.2  # Yakın dip
        elif top_dist <= 0.5:
            confidence += 0.3  # Çok yakın tepe
        elif top_dist <= 1.0:
            confidence += 0.2  # Yakın tepe
            
        # Price range - volatilite göstergesi
        range_pct = (price_range / low_price) * 100
        if range_pct > 3.0:  # %3+ range = yüksek volatilite
            confidence += 0.1
        elif range_pct < 1.0:  # Düşük volatilite
            confidence -= 0.1
            
        # Trend uyumu
        if trend == "BEARISH" and bottom_dist <= 1.0:
            confidence += 0.1  # BEARISH'te dip = fırsat
        elif trend == "BULLISH" and top_dist <= 1.0:
            confidence += 0.1  # BULLISH'te tepe = dikkat
            
        return max(0.1, min(1.0, confidence))
    
    def _empty_result(self) -> Dict[str, Any]:
        """Boş sonuç"""
        return {
            "is_near_bottom": False,
            "is_near_top": False,
            "bottom_distance_pct": 0,
            "top_distance_pct": 0,
            "multi_day_trend": "UNKNOWN",
            "confidence": 0,
            "support_level": 0,
            "resistance_level": 0,
            "three_day_high": 0,
            "three_day_low": 0,
            "price_range_pct": 0,
            "recent_momentum": 0
        }