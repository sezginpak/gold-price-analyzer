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
    
    def _empty_result(self) -> Dict[str, any]:
        """Boş sonuç döndür"""
        return {
            "macd_line": None,
            "signal_line": None,
            "histogram": None,
            "histogram_prev": None,
            "crossover": None,
            "divergence": None,
            "trend": "NEUTRAL",
            "strength": 0.0
        }
    
    def calculate_ema(self, values: List[Decimal], period: int) -> List[Decimal]:
        """Exponential Moving Average hesapla"""
        try:
            if not values:
                logger.warning("Empty values list for EMA calculation")
                return []
            
            if len(values) < period:
                logger.debug(f"Insufficient data for EMA: need {period}, got {len(values)}")
                return []
            
            if period <= 0:
                logger.error(f"Invalid EMA period: {period}")
                return []
            
            ema_values = []
            multiplier = Decimal(2) / (period + 1)
            
            # İlk EMA değeri SMA olarak başlar
            sma = sum(values[:period]) / period
            ema_values.append(sma)
            
            # Sonraki EMA değerleri
            for i in range(period, len(values)):
                try:
                    ema = (values[i] - ema_values[-1]) * multiplier + ema_values[-1]
                    ema_values.append(ema)
                except (IndexError, TypeError) as e:
                    logger.error(f"Error calculating EMA at index {i}: {e}")
                    break
            
            return ema_values
            
        except Exception as e:
            logger.error(f"Unexpected error in EMA calculation: {e}")
            return []
    
    def calculate(self, candles: List[PriceCandle]) -> Dict[str, any]:
        """MACD hesapla"""
        try:
            if not candles:
                logger.warning("No candles provided for MACD calculation")
                return self._empty_result()
            
            if len(candles) < self.slow_period + self.signal_period:
                logger.warning(f"Not enough data for MACD. Need {self.slow_period + self.signal_period}, got {len(candles)}")
                return self._empty_result()
        
            # Kapanış fiyatlarını al
            closes = []
            for candle in candles:
                try:
                    closes.append(candle.close)
                except AttributeError as e:
                    logger.error(f"Invalid candle data: {e}")
                    return self._empty_result()
            
            # EMA'ları hesapla
            ema_fast = self.calculate_ema(closes, self.fast_period)
            ema_slow = self.calculate_ema(closes, self.slow_period)
            
            if not ema_fast or not ema_slow:
                logger.warning("Failed to calculate EMAs")
                return self._empty_result()
            
            # MACD hattını hesapla (fast EMA - slow EMA)
            # EMA'lar farklı uzunlukta olacak, eşitle
            start_idx = self.slow_period - self.fast_period
            macd_line = []
            
            try:
                for i in range(len(ema_slow)):
                    if start_idx + i < len(ema_fast):
                        macd_line.append(ema_fast[start_idx + i] - ema_slow[i])
            except IndexError as e:
                logger.error(f"Index error calculating MACD line: {e}")
                return self._empty_result()
            
            if not macd_line:
                logger.warning("Failed to calculate MACD line")
                return self._empty_result()
            
            # Signal hattını hesapla (MACD'nin 9 günlük EMA'sı)
            signal_line = self.calculate_ema(macd_line, self.signal_period)
            
            if not signal_line:
                logger.warning("Failed to calculate signal line")
                return self._empty_result()
            
            # Histogram hesapla (MACD - Signal)
            histogram = []
            try:
                for i in range(len(signal_line)):
                    hist_idx = len(macd_line) - len(signal_line) + i
                    if 0 <= hist_idx < len(macd_line):
                        histogram.append(macd_line[hist_idx] - signal_line[i])
            except IndexError as e:
                logger.error(f"Index error calculating histogram: {e}")
                return self._empty_result()
            
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
            
        except Exception as e:
            logger.error(f"Unexpected error in MACD calculation: {e}", exc_info=True)
            return self._empty_result()
    
    def _detect_crossover(self, histogram: List[Decimal]) -> Optional[str]:
        """Crossover tespiti"""
        try:
            if not histogram or len(histogram) < 2:
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
            
        except (IndexError, TypeError) as e:
            logger.error(f"Error detecting crossover: {e}")
            return None
    
    def _detect_divergence(self, prices: List[Decimal], macd_values: List[Decimal]) -> Optional[str]:
        """Divergence (uyumsuzluk) tespiti"""
        try:
            if not prices or not macd_values:
                return None
            
            if len(prices) < 20 or len(macd_values) < 20:
                return None
            
            # Listelerin uzunluklarını eşitle
            min_len = min(len(prices), len(macd_values))
            prices = prices[-min_len:]
            macd_values = macd_values[-min_len:]
            
            # Son 20 mumda fiyat ve MACD zirvelerini bul
            price_highs = []
            macd_highs = []
            price_lows = []
            macd_lows = []
            
            for i in range(1, len(prices) - 1):
                try:
                    # Fiyat zirveleri
                    if prices[i] > prices[i-1] and prices[i] > prices[i+1]:
                        price_highs.append((i, prices[i]))
                    
                    # Fiyat dipleri
                    if prices[i] < prices[i-1] and prices[i] < prices[i+1]:
                        price_lows.append((i, prices[i]))
                except (IndexError, TypeError) as e:
                    logger.debug(f"Error finding price peaks at index {i}: {e}")
                    continue
            
            for i in range(1, len(macd_values) - 1):
                try:
                    # MACD zirveleri
                    if macd_values[i] > macd_values[i-1] and macd_values[i] > macd_values[i+1]:
                        macd_highs.append((i, macd_values[i]))
                    
                    # MACD dipleri
                    if macd_values[i] < macd_values[i-1] and macd_values[i] < macd_values[i+1]:
                        macd_lows.append((i, macd_values[i]))
                except (IndexError, TypeError) as e:
                    logger.debug(f"Error finding MACD peaks at index {i}: {e}")
                    continue
        
            # Bullish divergence: Fiyat düşük dip, MACD yüksek dip
            if len(price_lows) >= 2 and len(macd_lows) >= 2:
                # Zaman yakınlığı kontrolü (maksimum 5 bar fark)
                if abs(price_lows[-1][0] - macd_lows[-1][0]) <= 5:
                    if (price_lows[-1][1] < price_lows[-2][1] and  # Fiyat düşük dip yapıyor
                        macd_lows[-1][1] > macd_lows[-2][1]):       # MACD yüksek dip yapıyor
                        return "BULLISH_DIVERGENCE"
            
            # Bearish divergence: Fiyat yüksek zirve, MACD düşük zirve
            if len(price_highs) >= 2 and len(macd_highs) >= 2:
                # Zaman yakınlığı kontrolü
                if abs(price_highs[-1][0] - macd_highs[-1][0]) <= 5:
                    if (price_highs[-1][1] > price_highs[-2][1] and  # Fiyat yüksek zirve yapıyor
                        macd_highs[-1][1] < macd_highs[-2][1]):      # MACD düşük zirve yapıyor
                        return "BEARISH_DIVERGENCE"
            
            return None
            
        except Exception as e:
            logger.error(f"Error detecting divergence: {e}")
            return None
    
    def _determine_trend(self, histogram: List[Decimal]) -> str:
        """MACD trendi belirle"""
        try:
            if not histogram or len(histogram) < 5:
                return "NEUTRAL"
            
            recent = histogram[-5:]
            current = histogram[-1]
            
            # Histogram değişim hızını kontrol et
            if len(histogram) >= 10:
                older = histogram[-10:-5]
                recent_avg = sum(recent) / len(recent)
                older_avg = sum(older) / len(older)
                momentum = recent_avg - older_avg
            else:
                momentum = 0
            
            # Tüm değerler pozitif ve güçlü momentum
            if all(h > 0 for h in recent) and recent[-1] > recent[0] and momentum > 0:
                return "STRONG_BULLISH"
            
            # Histogram pozitif
            elif current > 0:
                return "BULLISH"
            
            # Tüm değerler negatif ve güçlü momentum
            elif all(h < 0 for h in recent) and recent[-1] < recent[0] and momentum < 0:
                return "STRONG_BEARISH"
            
            # Histogram negatif
            elif current < 0:
                return "BEARISH"
            
            return "NEUTRAL"
            
        except Exception as e:
            logger.error(f"Error determining MACD trend: {e}")
            return "NEUTRAL"
    
    def _calculate_strength(self, histogram: List[Decimal]) -> float:
        """MACD sinyal gücü (0-1 arası)"""
        try:
            if not histogram:
                return 0.0
            
            # Histogram değerinin mutlak değeri ne kadar büyükse o kadar güçlü
            current = abs(float(histogram[-1]))
            
            # Son 20 histogram değerinin ortalaması
            recent = histogram[-20:] if len(histogram) >= 20 else histogram
            abs_values = [abs(float(h)) for h in recent]
            
            if not abs_values:
                return 0.0
            
            avg = sum(abs_values) / len(abs_values)
            
            if avg == 0:
                return 0.0
            
            # Standart sapma hesapla
            std_dev = (sum((x - avg) ** 2 for x in abs_values) / len(abs_values)) ** 0.5
            
            # Z-score bazlı güç hesaplama
            if std_dev > 0:
                z_score = (current - avg) / std_dev
                # Z-score'u 0-1 aralığına normalize et
                strength = min(max((z_score + 2) / 4, 0), 1.0)
            else:
                # Standart sapma 0 ise basit normalizasyon
                strength = min(current / (avg * 2), 1.0)
            
            return strength
            
        except Exception as e:
            logger.error(f"Error calculating MACD strength: {e}")
            return 0.0
    
    def get_histogram_trend(self, result: Dict[str, any]) -> str:
        """Histogram trendini döndür"""
        try:
            if not result:
                return "NEUTRAL"
            
            trend = result.get("trend", "NEUTRAL")
            histogram = result.get("histogram")
            histogram_prev = result.get("histogram_prev")
            
            if histogram is not None and histogram_prev is not None:
                # Histogram artıyorsa
                if histogram > histogram_prev:
                    if histogram > 0:
                        return "STRENGTHENING_BULLISH"
                    else:
                        return "WEAKENING_BEARISH"
                # Histogram azalıyorsa
                elif histogram < histogram_prev:
                    if histogram > 0:
                        return "WEAKENING_BULLISH"
                    else:
                        return "STRENGTHENING_BEARISH"
            
            return trend
            
        except Exception as e:
            logger.error(f"Error getting histogram trend: {e}")
            return "NEUTRAL"
    
    def is_histogram_extreme(self, result: Dict[str, any]) -> bool:
        """Histogram ekstrem değerde mi?"""
        try:
            if not result or not result.get("histogram"):
                return False
            
            strength = result.get("strength", 0)
            return strength > 0.8  # %80'den yüksek güç ekstrem
            
        except Exception as e:
            logger.error(f"Error checking histogram extreme: {e}")
            return False
    
    def get_signal_weight(self, result: Dict[str, any]) -> Tuple[Optional[str], float]:
        """
        MACD'ye göre sinyal ve güven skoru
        
        Returns:
            (signal_type, confidence): ("BUY"/"SELL"/None, 0.0-1.0)
        """
        try:
            if not result or not result.get("macd_line"):
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
                confidence *= result.get("strength", 1.0)
                confidence = min(confidence, 1.0)  # Max 1.0
            
            return signal, confidence
            
        except Exception as e:
            logger.error(f"Error calculating MACD signal weight: {e}")
            return None, 0.0