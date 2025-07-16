"""
MACD (Moving Average Convergence Divergence) Göstergesi
"""
from typing import List, Dict, Optional, Tuple
from decimal import Decimal
import logging
from models.price_data import PriceCandle

logger = logging.getLogger(__name__)


class MACDIndicator:
    """MACD hesaplaması ve sinyal üretimi"""
    
    def __init__(self, fast_period: int = 12, slow_period: int = 26, signal_period: int = 9):
        """
        Args:
            fast_period: Hızlı EMA periyodu (varsayılan 12)
            slow_period: Yavaş EMA periyodu (varsayılan 26)
            signal_period: Sinyal hattı EMA periyodu (varsayılan 9)
        """
        self.fast_period = fast_period
        self.slow_period = slow_period
        self.signal_period = signal_period
    
    def calculate_ema(self, values: List[Decimal], period: int) -> List[Decimal]:
        """Exponential Moving Average hesapla"""
        if len(values) < period:
            return []
        
        ema_values = []
        multiplier = Decimal(2) / (period + 1)
        
        # İlk EMA değeri SMA olarak başlar
        sma = sum(values[:period]) / period
        ema_values.append(sma)
        
        # Sonraki EMA değerleri
        for i in range(period, len(values)):
            ema = (values[i] - ema_values[-1]) * multiplier + ema_values[-1]
            ema_values.append(ema)
        
        return ema_values
    
    def calculate(self, candles: List[PriceCandle]) -> Dict[str, any]:
        """MACD hesapla"""
        if len(candles) < self.slow_period + self.signal_period:
            logger.warning(f"Not enough data for MACD. Need {self.slow_period + self.signal_period}, got {len(candles)}")
            return {
                "macd_line": None,
                "signal_line": None,
                "histogram": None,
                "crossover": None,
                "divergence": None
            }
        
        # Kapanış fiyatlarını al
        closes = [candle.close for candle in candles]
        
        # EMA'ları hesapla
        ema_fast = self.calculate_ema(closes, self.fast_period)
        ema_slow = self.calculate_ema(closes, self.slow_period)
        
        # MACD hattını hesapla (fast EMA - slow EMA)
        # EMA'lar farklı uzunlukta olacak, eşitle
        start_idx = self.slow_period - self.fast_period
        macd_line = []
        for i in range(len(ema_slow)):
            macd_line.append(ema_fast[start_idx + i] - ema_slow[i])
        
        # Signal hattını hesapla (MACD'nin 9 günlük EMA'sı)
        signal_line = self.calculate_ema(macd_line, self.signal_period)
        
        # Histogram hesapla (MACD - Signal)
        histogram = []
        for i in range(len(signal_line)):
            hist_idx = len(macd_line) - len(signal_line) + i
            histogram.append(macd_line[hist_idx] - signal_line[i])
        
        # Crossover tespiti
        crossover = self._detect_crossover(histogram)
        
        # Divergence tespiti
        divergence = self._detect_divergence(closes[-50:], macd_line[-50:]) if len(macd_line) >= 50 else None
        
        return {
            "macd_line": float(macd_line[-1]) if macd_line else None,
            "signal_line": float(signal_line[-1]) if signal_line else None,
            "histogram": float(histogram[-1]) if histogram else None,
            "histogram_prev": float(histogram[-2]) if len(histogram) > 1 else None,
            "crossover": crossover,
            "divergence": divergence,
            "trend": self._determine_trend(histogram),
            "strength": self._calculate_strength(histogram)
        }
    
    def _detect_crossover(self, histogram: List[Decimal]) -> Optional[str]:
        """Crossover tespiti"""
        if len(histogram) < 2:
            return None
        
        current = histogram[-1]
        previous = histogram[-2]
        
        # Bullish crossover: histogram negatiften pozitife geçiyor
        if current > 0 and previous <= 0:
            return "BULLISH_CROSSOVER"
        
        # Bearish crossover: histogram pozitiften negatife geçiyor
        elif current < 0 and previous >= 0:
            return "BEARISH_CROSSOVER"
        
        return None
    
    def _detect_divergence(self, prices: List[Decimal], macd_values: List[Decimal]) -> Optional[str]:
        """Divergence (uyumsuzluk) tespiti"""
        if len(prices) < 20 or len(macd_values) < 20:
            return None
        
        # Son 20 mumda fiyat ve MACD zirvelerini bul
        price_highs = []
        macd_highs = []
        price_lows = []
        macd_lows = []
        
        for i in range(1, len(prices) - 1):
            # Fiyat zirveleri
            if prices[i] > prices[i-1] and prices[i] > prices[i+1]:
                price_highs.append((i, prices[i]))
            
            # Fiyat dipleri
            if prices[i] < prices[i-1] and prices[i] < prices[i+1]:
                price_lows.append((i, prices[i]))
        
        for i in range(1, len(macd_values) - 1):
            # MACD zirveleri
            if macd_values[i] > macd_values[i-1] and macd_values[i] > macd_values[i+1]:
                macd_highs.append((i, macd_values[i]))
            
            # MACD dipleri
            if macd_values[i] < macd_values[i-1] and macd_values[i] < macd_values[i+1]:
                macd_lows.append((i, macd_values[i]))
        
        # Bullish divergence: Fiyat düşük dip, MACD yüksek dip
        if len(price_lows) >= 2 and len(macd_lows) >= 2:
            if (price_lows[-1][1] < price_lows[-2][1] and  # Fiyat düşük dip yapıyor
                macd_lows[-1][1] > macd_lows[-2][1]):       # MACD yüksek dip yapıyor
                return "BULLISH_DIVERGENCE"
        
        # Bearish divergence: Fiyat yüksek zirve, MACD düşük zirve
        if len(price_highs) >= 2 and len(macd_highs) >= 2:
            if (price_highs[-1][1] > price_highs[-2][1] and  # Fiyat yüksek zirve yapıyor
                macd_highs[-1][1] < macd_highs[-2][1]):      # MACD düşük zirve yapıyor
                return "BEARISH_DIVERGENCE"
        
        return None
    
    def _determine_trend(self, histogram: List[Decimal]) -> str:
        """MACD trendi belirle"""
        if len(histogram) < 5:
            return "NEUTRAL"
        
        recent = histogram[-5:]
        
        # Tüm değerler pozitif ve artıyorsa
        if all(h > 0 for h in recent) and recent[-1] > recent[0]:
            return "STRONG_BULLISH"
        
        # Histogram pozitif
        elif histogram[-1] > 0:
            return "BULLISH"
        
        # Tüm değerler negatif ve azalıyorsa
        elif all(h < 0 for h in recent) and recent[-1] < recent[0]:
            return "STRONG_BEARISH"
        
        # Histogram negatif
        elif histogram[-1] < 0:
            return "BEARISH"
        
        return "NEUTRAL"
    
    def _calculate_strength(self, histogram: List[Decimal]) -> float:
        """MACD sinyal gücü (0-1 arası)"""
        if not histogram:
            return 0.0
        
        # Histogram değerinin mutlak değeri ne kadar büyükse o kadar güçlü
        current = abs(float(histogram[-1]))
        
        # Son 20 histogram değerinin ortalaması
        recent = histogram[-20:] if len(histogram) >= 20 else histogram
        avg = sum(abs(float(h)) for h in recent) / len(recent)
        
        if avg == 0:
            return 0.0
        
        # Normalize et (ortalamaya göre)
        strength = min(current / (avg * 2), 1.0)
        
        return strength
    
    def get_signal_weight(self, result: Dict[str, any]) -> Tuple[Optional[str], float]:
        """
        MACD'ye göre sinyal ve güven skoru
        
        Returns:
            (signal_type, confidence): ("BUY"/"SELL"/None, 0.0-1.0)
        """
        if not result["macd_line"]:
            return None, 0.0
        
        signal = None
        confidence = 0.0
        
        # Crossover varsa yüksek güven
        if result["crossover"] == "BULLISH_CROSSOVER":
            signal = "BUY"
            confidence = 0.8
        elif result["crossover"] == "BEARISH_CROSSOVER":
            signal = "SELL"
            confidence = 0.8
        
        # Divergence varsa ekstra güven
        if result["divergence"] == "BULLISH_DIVERGENCE":
            if signal == "BUY":
                confidence = min(confidence + 0.2, 1.0)
            else:
                signal = "BUY"
                confidence = 0.6
        elif result["divergence"] == "BEARISH_DIVERGENCE":
            if signal == "SELL":
                confidence = min(confidence + 0.2, 1.0)
            else:
                signal = "SELL"
                confidence = 0.6
        
        # Trend doğrulaması
        if not signal:
            if result["trend"] == "STRONG_BULLISH":
                signal = "BUY"
                confidence = 0.4
            elif result["trend"] == "STRONG_BEARISH":
                signal = "SELL"
                confidence = 0.4
        
        # Güç ile confidence'ı ayarla
        if signal:
            confidence *= result["strength"]
        
        return signal, confidence