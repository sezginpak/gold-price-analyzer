"""
RSI (Relative Strength Index) göstergesi
"""
from typing import List, Tuple, Optional
import numpy as np
import logging

logger = logging.getLogger(__name__)


class RSIIndicator:
    """RSI hesaplama ve analizi"""
    
    def __init__(self, period: int = 14):
        """
        Args:
            period: RSI periyodu (varsayılan 14)
        """
        self.period = period
        # Altın için daha hassas RSI eşikleri
        self.oversold_level = 40  # Normalde 30
        self.overbought_level = 60  # Normalde 70
        
    def calculate(self, prices: List[float]) -> Tuple[Optional[float], Optional[str]]:
        """
        RSI hesapla
        
        Args:
            prices: Fiyat listesi
            
        Returns:
            (RSI değeri, Sinyal)
        """
        try:
            if len(prices) < self.period + 1:
                return None, None
            
            # Fiyat değişimleri
            price_array = np.array(prices)
            deltas = np.diff(price_array)
            
            # Kazanç ve kayıpları ayır
            gains = deltas.copy()
            losses = deltas.copy()
            gains[gains < 0] = 0
            losses[losses > 0] = 0
            losses = np.abs(losses)
            
            # İlk ortalamalar
            avg_gain = np.mean(gains[:self.period])
            avg_loss = np.mean(losses[:self.period])
            
            # Wilder's smoothing
            for i in range(self.period, len(gains)):
                avg_gain = (avg_gain * (self.period - 1) + gains[i]) / self.period
                avg_loss = (avg_loss * (self.period - 1) + losses[i]) / self.period
            
            # RSI hesapla
            if avg_loss == 0:
                rsi = 100
            else:
                rs = avg_gain / avg_loss
                rsi = 100 - (100 / (1 + rs))
            
            # Sinyal üret
            if rsi < self.oversold_level:
                signal = "oversold"
            elif rsi > self.overbought_level:
                signal = "overbought"
            else:
                signal = "neutral"
            
            return round(rsi, 2), signal
            
        except Exception as e:
            logger.error(f"RSI calculation error: {e}")
            return None, None
    
    def get_divergence(self, prices: List[float], rsi_values: List[float]) -> Optional[str]:
        """
        RSI divergence tespiti
        
        Args:
            prices: Fiyat listesi
            rsi_values: RSI değerleri
            
        Returns:
            Divergence tipi (bullish/bearish/None)
        """
        if len(prices) < 4 or len(rsi_values) < 4:
            return None
        
        # Son iki dip/tepe noktasını bul
        price_lows = []
        price_highs = []
        rsi_lows = []
        rsi_highs = []
        
        for i in range(1, len(prices) - 1):
            # Dip noktaları
            if prices[i] < prices[i-1] and prices[i] < prices[i+1]:
                price_lows.append((i, prices[i]))
                rsi_lows.append((i, rsi_values[i]))
            # Tepe noktaları
            elif prices[i] > prices[i-1] and prices[i] > prices[i+1]:
                price_highs.append((i, prices[i]))
                rsi_highs.append((i, rsi_values[i]))
        
        # Bullish divergence kontrolü
        if len(price_lows) >= 2 and len(rsi_lows) >= 2:
            if (price_lows[-1][1] < price_lows[-2][1] and 
                rsi_lows[-1][1] > rsi_lows[-2][1]):
                return "bullish_divergence"
        
        # Bearish divergence kontrolü
        if len(price_highs) >= 2 and len(rsi_highs) >= 2:
            if (price_highs[-1][1] > price_highs[-2][1] and 
                rsi_highs[-1][1] < rsi_highs[-2][1]):
                return "bearish_divergence"
        
        return None