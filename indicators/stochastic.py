"""
Stochastic Oscillator Göstergesi
"""
from typing import List, Dict, Optional, Tuple
from decimal import Decimal
import logging
from models.price_data import PriceCandle

logger = logging.getLogger(__name__)


class StochasticIndicator:
    """Stochastic Oscillator hesaplaması ve sinyal üretimi"""
    
    def __init__(self, k_period: int = 14, d_period: int = 3, smooth_k: int = 3):
        """
        Args:
            k_period: %K hesaplama periyodu (varsayılan 14)
            d_period: %D hesaplama periyodu (varsayılan 3)
            smooth_k: %K yumuşatma periyodu (varsayılan 3)
        """
        self.k_period = k_period
        self.d_period = d_period
        self.smooth_k = smooth_k
    
    def calculate(self, candles: List[PriceCandle]) -> Dict[str, any]:
        """Stochastic hesapla"""
        if len(candles) < self.k_period + self.smooth_k + self.d_period:
            logger.warning(f"Not enough data for Stochastic. Need {self.k_period + self.smooth_k + self.d_period}, got {len(candles)}")
            return {
                "k": None,
                "d": None,
                "k_prev": None,
                "d_prev": None,
                "signal": None,
                "zone": None
            }
        
        # Raw %K değerlerini hesapla
        raw_k_values = []
        
        for i in range(self.k_period - 1, len(candles)):
            period_candles = candles[i - self.k_period + 1:i + 1]
            
            # Period içindeki en yüksek ve en düşük
            highest_high = max(c.high for c in period_candles)
            lowest_low = min(c.low for c in period_candles)
            
            # Raw %K = (Current Close - Lowest Low) / (Highest High - Lowest Low) * 100
            if highest_high != lowest_low:
                raw_k = ((period_candles[-1].close - lowest_low) / (highest_high - lowest_low)) * 100
            else:
                raw_k = 50  # Eğer high ve low eşitse nötr değer
            
            raw_k_values.append(float(raw_k))
        
        # %K değerlerini yumuşat (SMA)
        k_values = []
        for i in range(self.smooth_k - 1, len(raw_k_values)):
            k = sum(raw_k_values[i - self.smooth_k + 1:i + 1]) / self.smooth_k
            k_values.append(k)
        
        # %D değerlerini hesapla (%K'nın SMA'sı)
        d_values = []
        for i in range(self.d_period - 1, len(k_values)):
            d = sum(k_values[i - self.d_period + 1:i + 1]) / self.d_period
            d_values.append(d)
        
        # Mevcut ve önceki değerler
        current_k = k_values[-1] if k_values else None
        current_d = d_values[-1] if d_values else None
        prev_k = k_values[-2] if len(k_values) > 1 else None
        prev_d = d_values[-2] if len(d_values) > 1 else None
        
        # Bölge tespiti
        zone = self._determine_zone(current_k)
        
        # Sinyal üretimi
        signal = self._generate_signal(current_k, current_d, prev_k, prev_d)
        
        # Divergence tespiti
        divergence = self._detect_divergence(candles, k_values)
        
        return {
            "k": current_k,
            "d": current_d,
            "k_prev": prev_k,
            "d_prev": prev_d,
            "signal": signal,
            "zone": zone,
            "divergence": divergence,
            "momentum": self._calculate_momentum(k_values)
        }
    
    def _determine_zone(self, k_value: Optional[float]) -> Optional[str]:
        """Stochastic bölgesini belirle"""
        if k_value is None:
            return None
        
        if k_value >= 80:
            return "OVERBOUGHT"
        elif k_value <= 20:
            return "OVERSOLD"
        else:
            return "NEUTRAL"
    
    def _generate_signal(self, k: Optional[float], d: Optional[float], 
                        k_prev: Optional[float], d_prev: Optional[float]) -> Optional[Dict[str, any]]:
        """Stochastic sinyali üret"""
        if None in [k, d, k_prev, d_prev]:
            return None
        
        signal_type = None
        confidence = 0.0
        reason = ""
        
        # %K ve %D kesişimleri
        # Bullish crossover: %K, %D'yi aşağıdan yukarı keser
        if k_prev <= d_prev and k > d:
            # Oversold bölgesinde kesişim daha güçlü
            if k < 20:
                signal_type = "BUY"
                confidence = 0.9
                reason = "Oversold bölgesinde bullish crossover"
            elif k < 50:
                signal_type = "BUY"
                confidence = 0.6
                reason = "Bullish crossover"
        
        # Bearish crossover: %K, %D'yi yukarıdan aşağı keser
        elif k_prev >= d_prev and k < d:
            # Overbought bölgesinde kesişim daha güçlü
            if k > 80:
                signal_type = "SELL"
                confidence = 0.9
                reason = "Overbought bölgesinde bearish crossover"
            elif k > 50:
                signal_type = "SELL"
                confidence = 0.6
                reason = "Bearish crossover"
        
        # Oversold'dan çıkış
        elif k_prev <= 20 and k > 20:
            signal_type = "BUY"
            confidence = 0.7
            reason = "Oversold bölgesinden çıkış"
        
        # Overbought'tan çıkış
        elif k_prev >= 80 and k < 80:
            signal_type = "SELL"
            confidence = 0.7
            reason = "Overbought bölgesinden çıkış"
        
        if signal_type:
            return {
                "type": signal_type,
                "confidence": confidence,
                "reason": reason,
                "k": k,
                "d": d
            }
        
        return None
    
    def _detect_divergence(self, candles: List[PriceCandle], k_values: List[float]) -> Optional[str]:
        """Stochastic divergence tespiti"""
        if len(candles) < 20 or len(k_values) < 20:
            return None
        
        # Son 20 mum için analiz
        recent_candles = candles[-20:]
        recent_k = k_values[-20:]
        
        # Fiyat ve Stochastic zirvelerini/diplerini bul
        price_highs = []
        price_lows = []
        k_highs = []
        k_lows = []
        
        for i in range(1, len(recent_candles) - 1):
            # Fiyat zirveleri
            if (recent_candles[i].high > recent_candles[i-1].high and 
                recent_candles[i].high > recent_candles[i+1].high):
                price_highs.append((i, float(recent_candles[i].high)))
            
            # Fiyat dipleri
            if (recent_candles[i].low < recent_candles[i-1].low and 
                recent_candles[i].low < recent_candles[i+1].low):
                price_lows.append((i, float(recent_candles[i].low)))
        
        for i in range(1, len(recent_k) - 1):
            # Stochastic zirveleri
            if recent_k[i] > recent_k[i-1] and recent_k[i] > recent_k[i+1]:
                k_highs.append((i, recent_k[i]))
            
            # Stochastic dipleri
            if recent_k[i] < recent_k[i-1] and recent_k[i] < recent_k[i+1]:
                k_lows.append((i, recent_k[i]))
        
        # Bullish divergence
        if len(price_lows) >= 2 and len(k_lows) >= 2:
            if (price_lows[-1][1] < price_lows[-2][1] and  # Fiyat düşük dip
                k_lows[-1][1] > k_lows[-2][1]):            # Stochastic yüksek dip
                return "BULLISH_DIVERGENCE"
        
        # Bearish divergence
        if len(price_highs) >= 2 and len(k_highs) >= 2:
            if (price_highs[-1][1] > price_highs[-2][1] and  # Fiyat yüksek zirve
                k_highs[-1][1] < k_highs[-2][1]):            # Stochastic düşük zirve
                return "BEARISH_DIVERGENCE"
        
        return None
    
    def _calculate_momentum(self, k_values: List[float]) -> str:
        """Stochastic momentum'u hesapla"""
        if len(k_values) < 5:
            return "NEUTRAL"
        
        recent = k_values[-5:]
        
        # Trend yönü
        if all(recent[i] > recent[i-1] for i in range(1, len(recent))):
            return "STRONG_UP"
        elif all(recent[i] < recent[i-1] for i in range(1, len(recent))):
            return "STRONG_DOWN"
        elif recent[-1] > recent[0]:
            return "UP"
        elif recent[-1] < recent[0]:
            return "DOWN"
        else:
            return "NEUTRAL"
    
    def get_signal_weight(self, result: Dict[str, any]) -> Tuple[Optional[str], float]:
        """
        Stochastic'e göre sinyal ve güven skoru
        
        Returns:
            (signal_type, confidence): ("BUY"/"SELL"/None, 0.0-1.0)
        """
        if not result["k"]:
            return None, 0.0
        
        signal = result.get("signal")
        if not signal:
            # Sinyal yoksa ama ekstrem bölgedeyse düşük güvenle sinyal ver
            if result["zone"] == "OVERSOLD" and result["k"] < 10:
                return "BUY", 0.3
            elif result["zone"] == "OVERBOUGHT" and result["k"] > 90:
                return "SELL", 0.3
            return None, 0.0
        
        confidence = signal["confidence"]
        
        # Divergence varsa güveni artır
        if result["divergence"] == "BULLISH_DIVERGENCE" and signal["type"] == "BUY":
            confidence = min(confidence * 1.3, 1.0)
        elif result["divergence"] == "BEARISH_DIVERGENCE" and signal["type"] == "SELL":
            confidence = min(confidence * 1.3, 1.0)
        
        # Momentum doğrulaması
        momentum = result["momentum"]
        if signal["type"] == "BUY" and momentum in ["UP", "STRONG_UP"]:
            confidence = min(confidence * 1.1, 1.0)
        elif signal["type"] == "SELL" and momentum in ["DOWN", "STRONG_DOWN"]:
            confidence = min(confidence * 1.1, 1.0)
        
        return signal["type"], confidence