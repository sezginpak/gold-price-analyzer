"""
Bollinger Bands Göstergesi
"""
from typing import List, Dict, Optional, Tuple
from decimal import Decimal
import logging
import statistics
from models.price_data import PriceCandle

logger = logging.getLogger(__name__)


class BollingerBandsIndicator:
    """Bollinger Bands hesaplaması ve sinyal üretimi"""
    
    def __init__(self, period: int = 20, std_dev_multiplier: float = 2.0):
        """
        Args:
            period: Moving average periyodu (varsayılan 20)
            std_dev_multiplier: Standart sapma çarpanı (varsayılan 2.0)
        """
        self.period = period
        self.std_dev_multiplier = std_dev_multiplier
    
    def _empty_result(self) -> Dict[str, any]:
        """Boş sonuç döndür"""
        return {
            "upper_band": None,
            "middle_band": None,
            "lower_band": None,
            "band_width": None,
            "percent_b": None,
            "squeeze": None,
            "signal": None,
            "volatility": None,
            "trend": None
        }
    
    def calculate(self, candles: List[PriceCandle]) -> Dict[str, any]:
        """Bollinger Bands hesapla"""
        try:
            if not candles:
                logger.warning("No candles provided for Bollinger Bands calculation")
                return self._empty_result()
            
            if len(candles) < self.period:
                logger.warning(f"Not enough data for Bollinger Bands. Need {self.period}, got {len(candles)}")
                return self._empty_result()
        
            # Son period kadar kapanış fiyatı
            closes = []
            try:
                for candle in candles[-self.period:]:
                    closes.append(float(candle.close))
                current_price = float(candles[-1].close)
            except (AttributeError, ValueError) as e:
                logger.error(f"Error extracting close prices: {e}")
                return self._empty_result()
            
            if len(closes) < 2:
                logger.warning("Not enough close prices for standard deviation")
                return self._empty_result()
            
            # Orta bant (SMA)
            middle_band = sum(closes) / self.period
            
            # Standart sapma
            try:
                std_dev = statistics.stdev(closes)
            except statistics.StatisticsError as e:
                logger.error(f"Error calculating standard deviation: {e}")
                return self._empty_result()
            
            # Üst ve alt bantlar
            upper_band = middle_band + (std_dev * self.std_dev_multiplier)
            lower_band = middle_band - (std_dev * self.std_dev_multiplier)
            
            # Band genişliği
            band_width = upper_band - lower_band
            
            # %B hesaplama (fiyatın bantlar içindeki pozisyonu)
            # %B = (Fiyat - Alt Bant) / (Üst Bant - Alt Bant)
            if band_width > 0:
                percent_b = (current_price - lower_band) / band_width
            else:
                logger.warning("Band width is zero, using default percent_b")
                percent_b = 0.5
            
            # Bollinger Squeeze tespiti (düşük volatilite)
            historical_widths = self._calculate_historical_widths(candles)
            squeeze = self._detect_squeeze(band_width, historical_widths)
            
            # Pozisyon belirleme (altın için daha hassas)
            # %B değerini kullanarak daha detaylı pozisyon
            if percent_b < 0.2:  # Alt bandın altında veya çok yakın
                position = "below_lower"
            elif percent_b > 0.8:  # Üst bandın üstünde veya çok yakın
                position = "above_upper"
            elif percent_b < 0.35:  # Alt banda yakın
                position = "near_lower"
            elif percent_b > 0.65:  # Üst banda yakın
                position = "near_upper"
            else:
                position = "middle"
            
            # Sinyal üretimi
            signal = self._generate_signal(current_price, upper_band, lower_band, middle_band, percent_b, candles)
            
            return {
                "upper_band": upper_band,
                "middle_band": middle_band,
                "lower_band": lower_band,
                "band_width": band_width,
                "percent_b": percent_b,
                "position": position,
                "squeeze": squeeze,
                "signal": signal,
                "volatility": self._calculate_volatility_level(band_width, middle_band),
                "trend": self._determine_trend(candles, middle_band)
            }
            
        except Exception as e:
            logger.error(f"Unexpected error in Bollinger Bands calculation: {e}", exc_info=True)
            return self._empty_result()
    
    def _calculate_historical_widths(self, candles: List[PriceCandle]) -> List[float]:
        """Geçmiş band genişliklerini hesapla"""
        try:
            if len(candles) < self.period + 20:
                return []
            
            widths = []
            for i in range(self.period, len(candles)):
                try:
                    period_candles = candles[i-self.period:i]
                    closes = [float(c.close) for c in period_candles]
                    
                    if len(closes) < 2:
                        continue
                    
                    mean = sum(closes) / len(closes)
                    std_dev = statistics.stdev(closes)
                    
                    # Band genişliği hesapla (upper - lower)
                    width = 2 * std_dev * self.std_dev_multiplier
                    widths.append(width)
                    
                except (statistics.StatisticsError, ValueError) as e:
                    logger.debug(f"Error calculating historical width at index {i}: {e}")
                    continue
            
            return widths
            
        except Exception as e:
            logger.error(f"Error calculating historical widths: {e}")
            return []
    
    def _detect_squeeze(self, current_width: float, historical_widths: List[float]) -> bool:
        """Bollinger Squeeze tespiti"""
        try:
            if not historical_widths or len(historical_widths) < 20:
                return False
            
            # Son 20 genişliğin ortalaması
            recent_widths = historical_widths[-20:]
            avg_width = sum(recent_widths) / len(recent_widths)
            
            if avg_width <= 0:
                return False
            
            # Mevcut genişlik ortalamanın %70'inden azsa squeeze var
            is_squeeze = current_width < avg_width * 0.7
            
            # Ek kontrol: Son 5 genişlik de daralıyor mu?
            if is_squeeze and len(recent_widths) >= 5:
                last_5 = recent_widths[-5:]
                try:
                    is_contracting = all(last_5[i] <= last_5[i-1] for i in range(1, len(last_5)))
                    return is_squeeze and is_contracting
                except IndexError:
                    return is_squeeze
            
            return is_squeeze
            
        except Exception as e:
            logger.error(f"Error detecting squeeze: {e}")
            return False
    
    def _generate_signal(self, price: float, upper: float, lower: float, 
                        middle: float, percent_b: float, candles: List[PriceCandle]) -> Optional[Dict[str, any]]:
        """Bollinger Bands sinyali üret"""
        try:
            signal_type = None
            confidence = 0.0
            reason = ""
            additional_info = {}
            
            # Alt banda dokunma ve geri dönüş
            if percent_b <= 0.05:  # Fiyat alt bandın çok yakınında veya altında
                # Son 3 mumda dönüş var mı?
                if len(candles) >= 3:
                    # Momentum kontrolü
                    price_changes = []
                    try:
                        for i in range(-3, -1):
                            if abs(i) <= len(candles) - 1:
                                price_changes.append(float(candles[i].close - candles[i-1].close))
                    except (IndexError, AttributeError) as e:
                        logger.debug(f"Momentum calculation error: {e}")
                        price_changes = []
                    
                    # Son mum yükseliyor ve momentum artıyor
                    if (len(price_changes) >= 2 and len(candles) >= 2 and 
                        candles[-1].close > candles[-2].close and 
                        price_changes[-1] > price_changes[-2]):
                        signal_type = "BUY"
                        confidence = 0.7
                        reason = "Alt banda dokunma ve güçlü dönüş"
                        
                        # %B negatifse (bandın dışında) güven artar
                        if percent_b < 0:
                            confidence = 0.8
                            reason = "Alt bandın dışından dönüş"
                        
                        additional_info["momentum"] = "increasing"
            
            # Üst banda dokunma ve geri dönüş
            elif percent_b >= 0.95:  # Fiyat üst bandın çok yakınında veya üstünde
                if len(candles) >= 3:
                    # Momentum kontrolü
                    price_changes = []
                    try:
                        for i in range(-3, -1):
                            if abs(i) <= len(candles) - 1:
                                price_changes.append(float(candles[i].close - candles[i-1].close))
                    except (IndexError, AttributeError) as e:
                        logger.debug(f"Momentum calculation error: {e}")
                        price_changes = []
                    
                    # Son mum düşüyor ve momentum azalıyor
                    if (len(price_changes) >= 2 and len(candles) >= 2 and 
                        candles[-1].close < candles[-2].close and 
                        price_changes[-1] < price_changes[-2]):
                        signal_type = "SELL"
                        confidence = 0.7
                        reason = "Üst banda dokunma ve güçlü dönüş"
                        
                        # %B 1'den büyükse (bandın dışında) güven artar
                        if percent_b > 1:
                            confidence = 0.8
                            reason = "Üst bandın dışından dönüş"
                        
                        additional_info["momentum"] = "decreasing"
            
            # Band genişlemesi/daralması sinyalleri
            elif len(candles) >= 5:
                prev_close = float(candles[-2].close)
                
                # Volatilite patlaması - Band genişliyor ve fiyat kırılma yapıyor
                recent_closes = [float(c.close) for c in candles[-5:]]
                volatility_expanding = False
                try:
                    if len(recent_closes) >= 3:
                        volatility_expanding = all(
                            i < 2 or abs(recent_closes[i] - recent_closes[i-1]) > abs(recent_closes[i-1] - recent_closes[i-2])
                            for i in range(len(recent_closes))
                        )
                except (IndexError, ValueError) as e:
                    logger.debug(f"Volatility expansion check error: {e}")
                    volatility_expanding = False
                
                if volatility_expanding:
                    # Aşağıdan yukarı kırılma
                    if prev_close < middle and price > middle and price > upper * 0.95:
                        signal_type = "BUY"
                        confidence = 0.6
                        reason = "Volatilite patlaması - Yukarı kırılım"
                        additional_info["volatility"] = "expanding"
                    
                    # Yukarıdan aşağı kırılma
                    elif prev_close > middle and price < middle and price < lower * 1.05:
                        signal_type = "SELL"
                        confidence = 0.6
                        reason = "Volatilite patlaması - Aşağı kırılım"
                        additional_info["volatility"] = "expanding"
                else:
                    # Normal orta bant kırılması
                    if prev_close < middle and price > middle:
                        signal_type = "BUY"
                        confidence = 0.5
                        reason = "Orta bant yukarı kırılması"
                    elif prev_close > middle and price < middle:
                        signal_type = "SELL"
                        confidence = 0.5
                        reason = "Orta bant aşağı kırılması"
            
            if signal_type:
                result = {
                    "type": signal_type,
                    "confidence": confidence,
                    "reason": reason,
                    "percent_b": percent_b
                }
                if additional_info:
                    result["additional_info"] = additional_info
                return result
            
            return None
            
        except Exception as e:
            logger.error(f"Error generating Bollinger signal: {e}")
            return None
    
    def _calculate_volatility_level(self, band_width: float, middle_band: float) -> str:
        """Volatilite seviyesi"""
        try:
            if middle_band <= 0:
                logger.warning("Middle band is zero or negative")
                return "UNKNOWN"
            
            # Band genişliğinin orta banda oranı
            width_ratio = band_width / middle_band
            
            # Altın için özel volatilite seviyeleri
            if width_ratio < 0.01:
                return "VERY_LOW"
            elif width_ratio < 0.02:
                return "LOW"
            elif width_ratio < 0.04:
                return "NORMAL"
            elif width_ratio < 0.06:
                return "HIGH"
            else:
                return "VERY_HIGH"
                
        except Exception as e:
            logger.error(f"Error calculating volatility level: {e}")
            return "UNKNOWN"
    
    def _determine_trend(self, candles: List[PriceCandle], middle_band: float) -> str:
        """Bollinger Bands'e göre trend"""
        try:
            if len(candles) < 5:
                return "NEUTRAL"
            
            # Son 5 mumun kapanışları
            recent_closes = [float(c.close) for c in candles[-5:]]
            
            # Orta bandın üstünde mi altında mı?
            above_middle = sum(1 for c in recent_closes if c > middle_band)
            
            # Ek kontrol: Orta bant (SMA) yönü
            if len(candles) >= self.period + 5:
                # 5 mum önceki orta bandı hesapla
                old_closes = [float(c.close) for c in candles[-self.period-5:-5]]
                old_middle = sum(old_closes) / len(old_closes)
                
                # Orta bant yükseliyor mu?
                middle_trend = "UP" if middle_band > old_middle else "DOWN"
                
                # Kombine değerlendirme
                if above_middle >= 4 and middle_trend == "UP":
                    return "STRONG_BULLISH"
                elif above_middle >= 4:
                    return "BULLISH"
                elif above_middle <= 1 and middle_trend == "DOWN":
                    return "STRONG_BEARISH"
                elif above_middle <= 1:
                    return "BEARISH"
            else:
                # Basit değerlendirme
                if above_middle >= 4:
                    return "BULLISH"
                elif above_middle <= 1:
                    return "BEARISH"
            
            return "NEUTRAL"
            
        except Exception as e:
            logger.error(f"Error determining trend: {e}")
            return "NEUTRAL"
    
    def get_signal_weight(self, result: Dict[str, any]) -> Tuple[Optional[str], float]:
        """
        Bollinger Bands'e göre sinyal ve güven skoru
        
        Returns:
            (signal_type, confidence): ("BUY"/"SELL"/None, 0.0-1.0)
        """
        try:
            if not result or not result.get("upper_band"):
                return None, 0.0
            
            signal = result.get("signal")
            if not signal:
                # Ekstrem %B değerlerinde düşük güvenle sinyal ver
                percent_b = result.get("percent_b", 0.5)
                if percent_b <= -0.1:  # Çok aşırı oversold
                    return "BUY", 0.3
                elif percent_b >= 1.1:  # Çok aşırı overbought
                    return "SELL", 0.3
                return None, 0.0
            
            # Temel güven skoru
            confidence = signal["confidence"]
            
            # Squeeze durumunda sinyal güçlenir
            if result.get("squeeze", False):
                confidence = min(confidence * 1.3, 1.0)
                logger.debug("Bollinger squeeze detected, confidence boosted")
            
            # Volatiliteye göre ayarlama
            volatility = result.get("volatility", "NORMAL")
            if volatility == "VERY_LOW":
                confidence *= 1.2  # Düşük volatilitede bantlara dokunma daha anlamlı
            elif volatility == "VERY_HIGH":
                confidence *= 0.8  # Yüksek volatilitede daha az güvenilir
            elif volatility == "UNKNOWN":
                confidence *= 0.9  # Bilinmeyen durumda temkinli ol
            
            # Trend doğrulaması
            trend = result.get("trend", "NEUTRAL")
            signal_type = signal["type"]
            
            if signal_type == "BUY" and trend in ["BEARISH", "STRONG_BEARISH"]:
                confidence *= 0.7  # Ters trend, güveni azalt
            elif signal_type == "SELL" and trend in ["BULLISH", "STRONG_BULLISH"]:
                confidence *= 0.7  # Ters trend, güveni azalt
            elif signal_type == "BUY" and trend == "STRONG_BULLISH":
                confidence *= 1.1  # Trend doğrulaması
            elif signal_type == "SELL" and trend == "STRONG_BEARISH":
                confidence *= 1.1  # Trend doğrulaması
            
            # Ek bilgi varsa değerlendir
            additional_info = signal.get("additional_info", {})
            if additional_info.get("momentum") == "increasing" and signal_type == "BUY":
                confidence *= 1.05
            elif additional_info.get("momentum") == "decreasing" and signal_type == "SELL":
                confidence *= 1.05
            
            return signal_type, min(confidence, 1.0)
            
        except Exception as e:
            logger.error(f"Error calculating signal weight: {e}")
            return None, 0.0
    
    def _calculate_ma(self, candles: List[PriceCandle], period: int) -> Optional[float]:
        """Moving Average hesapla"""
        try:
            if len(candles) < period:
                return None
            
            closes = [float(c.close) for c in candles[-period:]]
            return sum(closes) / period
        except (AttributeError, ValueError) as e:
            logger.error(f"Error calculating MA: {e}")
            return None
    
    def get_band_position(self, price: float, result: Dict[str, any]) -> str:
        """Fiyatın bantlar içindeki pozisyonunu belirle"""
        try:
            if not result or result.get("upper_band") is None:
                return "UNKNOWN"
            
            upper = result["upper_band"]
            lower = result["lower_band"]
            middle = result["middle_band"]
            
            if price > upper:
                return "ABOVE_UPPER"
            elif price < lower:
                return "BELOW_LOWER"
            elif price > middle:
                return "UPPER_HALF"
            else:
                return "LOWER_HALF"
        except Exception as e:
            logger.error(f"Error determining band position: {e}")
            return "UNKNOWN"