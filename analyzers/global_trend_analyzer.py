"""
Global Trend Analiz Motoru - ONS/USD üzerinden majör trend belirleme
"""
from typing import List, Dict, Any, Tuple
from decimal import Decimal
from datetime import datetime
import logging
import numpy as np

from models.market_data import MarketData

logger = logging.getLogger(__name__)


class GlobalTrendAnalyzer:
    """ONS/USD üzerinden global altın trendini analiz et"""
    
    def __init__(self):
        self.ma_periods = {
            "short": 20,   # 20 günlük
            "medium": 50,  # 50 günlük
            "long": 200    # 200 günlük
        }
    
    def analyze(self, market_data: List[MarketData]) -> Dict[str, Any]:
        """
        ONS/USD verilerini analiz ederek global trendi belirle
        
        Args:
            market_data: Son piyasa verileri (en az 200 kayıt önerilir)
            
        Returns:
            Global trend analiz sonuçları
        """
        try:
            if len(market_data) < 50:
                logger.warning(f"Yetersiz veri: {len(market_data)}")
                return self._empty_analysis()
            
            # ONS/USD fiyatlarını çıkar
            ons_prices = [float(d.ons_usd) for d in market_data]
            current_price = ons_prices[-1]
            
            # Hareketli ortalamalar
            ma_values = self._calculate_moving_averages(ons_prices)
            
            # Trend yönü ve gücü
            trend_direction, trend_strength = self._determine_trend(
                current_price, ma_values, ons_prices
            )
            
            # Momentum göstergeleri
            momentum = self._calculate_momentum(ons_prices)
            
            # Volatilite
            volatility = self._calculate_volatility(ons_prices)
            
            # Önemli seviyeler
            key_levels = self._find_key_levels(ons_prices)
            
            return {
                "timestamp": datetime.utcnow(),
                "ons_usd_price": Decimal(str(current_price)),
                "trend_direction": trend_direction,
                "trend_strength": trend_strength,
                "moving_averages": ma_values,
                "momentum": momentum,
                "volatility": volatility,
                "key_levels": key_levels,
                "analysis": self._create_trend_analysis(
                    trend_direction, trend_strength, ma_values, momentum
                )
            }
            
        except Exception as e:
            logger.error(f"Global trend analiz hatası: {e}", exc_info=True)
            return self._empty_analysis()
    
    def _calculate_moving_averages(self, prices: List[float]) -> Dict[str, float]:
        """Hareketli ortalamaları hesapla"""
        ma_values = {}
        
        for name, period in self.ma_periods.items():
            if len(prices) >= period:
                ma_values[f"ma{period}"] = np.mean(prices[-period:])
            else:
                ma_values[f"ma{period}"] = None
        
        return ma_values
    
    def _determine_trend(self, current_price: float, ma_values: Dict, 
                        prices: List[float]) -> Tuple[str, str]:
        """Trend yönü ve gücünü belirle"""
        ma50 = ma_values.get("ma50")
        ma200 = ma_values.get("ma200")
        
        # Trend yönü
        if ma50 and ma200:
            if current_price > ma50 > ma200:
                direction = "BULLISH"
            elif current_price < ma50 < ma200:
                direction = "BEARISH"
            else:
                direction = "SIDEWAYS"
        elif ma50:
            if current_price > ma50:
                direction = "BULLISH"
            else:
                direction = "BEARISH"
        else:
            # Son 20 günün trendi
            recent_trend = (prices[-1] - prices[-20]) / prices[-20] * 100
            if recent_trend > 2:
                direction = "BULLISH"
            elif recent_trend < -2:
                direction = "BEARISH"
            else:
                direction = "SIDEWAYS"
        
        # Trend gücü
        strength = self._calculate_trend_strength(prices, ma_values)
        
        return direction, strength
    
    def _calculate_trend_strength(self, prices: List[float], ma_values: Dict) -> str:
        """Trend gücünü hesapla"""
        # Son 20 günlük değişim
        if len(prices) >= 20:
            change_20d = (prices[-1] - prices[-20]) / prices[-20] * 100
        else:
            change_20d = 0
        
        # MA'lardan uzaklık
        ma50 = ma_values.get("ma50")
        if ma50:
            distance_from_ma = abs((prices[-1] - ma50) / ma50 * 100)
        else:
            distance_from_ma = 0
        
        # Güç belirleme
        if abs(change_20d) > 5 and distance_from_ma > 3:
            return "STRONG"
        elif abs(change_20d) > 2 or distance_from_ma > 1.5:
            return "MODERATE"
        else:
            return "WEAK"
    
    def _calculate_momentum(self, prices: List[float]) -> Dict[str, float]:
        """Momentum göstergelerini hesapla"""
        momentum = {}
        
        # Rate of Change (ROC)
        if len(prices) >= 10:
            momentum["roc_10"] = (prices[-1] - prices[-10]) / prices[-10] * 100
        
        if len(prices) >= 20:
            momentum["roc_20"] = (prices[-1] - prices[-20]) / prices[-20] * 100
        
        # Momentum skorı
        if momentum:
            avg_momentum = np.mean(list(momentum.values()))
            if avg_momentum > 5:
                momentum["signal"] = "STRONG_BULLISH"
            elif avg_momentum > 2:
                momentum["signal"] = "BULLISH"
            elif avg_momentum < -5:
                momentum["signal"] = "STRONG_BEARISH"
            elif avg_momentum < -2:
                momentum["signal"] = "BEARISH"
            else:
                momentum["signal"] = "NEUTRAL"
        
        return momentum
    
    def _calculate_volatility(self, prices: List[float]) -> Dict[str, float]:
        """Volatilite hesapla"""
        if len(prices) < 20:
            return {"daily": 0, "level": "LOW"}
        
        # Günlük getiriler
        returns = np.diff(prices[-20:]) / prices[-21:-1]
        daily_vol = np.std(returns) * 100
        
        # Volatilite seviyesi
        if daily_vol > 3:
            level = "HIGH"
        elif daily_vol > 1.5:
            level = "MEDIUM"
        else:
            level = "LOW"
        
        return {
            "daily": daily_vol,
            "level": level,
            "annualized": daily_vol * np.sqrt(252)  # Yıllık volatilite
        }
    
    def _find_key_levels(self, prices: List[float]) -> Dict[str, float]:
        """Önemli fiyat seviyelerini bul"""
        if len(prices) < 50:
            return {}
        
        recent_prices = prices[-50:]
        
        return {
            "resistance": max(recent_prices),
            "support": min(recent_prices),
            "pivot": (max(recent_prices) + min(recent_prices) + recent_prices[-1]) / 3,
            "weekly_high": max(prices[-5:]) if len(prices) >= 5 else None,
            "weekly_low": min(prices[-5:]) if len(prices) >= 5 else None
        }
    
    def _create_trend_analysis(self, direction: str, strength: str, 
                              ma_values: Dict, momentum: Dict) -> Dict[str, str]:
        """Trend analizi özeti"""
        analysis = {
            "summary": f"Global altın trendi {direction} yönde ve {strength} güçte",
            "ma_analysis": self._ma_analysis_text(ma_values),
            "momentum_analysis": f"Momentum {momentum.get('signal', 'belirsiz')}",
            "recommendation": self._get_recommendation(direction, strength, momentum)
        }
        
        return analysis
    
    def _ma_analysis_text(self, ma_values: Dict) -> str:
        """MA analizi metni"""
        ma50 = ma_values.get("ma50")
        ma200 = ma_values.get("ma200")
        
        if ma50 and ma200:
            if ma50 > ma200:
                return "Golden Cross oluşmuş, uzun vadeli yükseliş sinyali"
            else:
                return "Death Cross oluşmuş, uzun vadeli düşüş sinyali"
        else:
            return "Yeterli veri yok"
    
    def _get_recommendation(self, direction: str, strength: str, momentum: Dict) -> str:
        """Tavsiye üret"""
        momentum_signal = momentum.get("signal", "NEUTRAL")
        
        if direction == "BULLISH" and "BULLISH" in momentum_signal:
            return "Global trend gram altın alımını destekliyor"
        elif direction == "BEARISH" and "BEARISH" in momentum_signal:
            return "Global trend satış yönünde, dikkatli olun"
        elif direction == "SIDEWAYS":
            return "Global trend yatay, yerel fiyat hareketlerine odaklanın"
        else:
            return "Karışık sinyaller, pozisyon boyutunu azaltın"
    
    def _empty_analysis(self) -> Dict[str, Any]:
        """Boş analiz sonucu"""
        return {
            "timestamp": datetime.utcnow(),
            "ons_usd_price": None,
            "trend_direction": "UNKNOWN",
            "trend_strength": "WEAK",
            "moving_averages": {},
            "momentum": {},
            "volatility": {"level": "UNKNOWN"},
            "key_levels": {},
            "analysis": {"summary": "Yetersiz veri"}
        }