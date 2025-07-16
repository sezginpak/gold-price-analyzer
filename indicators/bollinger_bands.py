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
    
    def calculate(self, candles: List[PriceCandle]) -> Dict[str, any]:
        """Bollinger Bands hesapla"""
        if len(candles) < self.period:
            logger.warning(f"Not enough data for Bollinger Bands. Need {self.period}, got {len(candles)}")
            return {
                "upper_band": None,
                "middle_band": None,
                "lower_band": None,
                "band_width": None,
                "percent_b": None,
                "squeeze": None,
                "signal": None
            }
        
        # Son period kadar kapanış fiyatı
        closes = [float(candle.close) for candle in candles[-self.period:]]
        current_price = float(candles[-1].close)
        
        # Orta bant (SMA)
        middle_band = sum(closes) / self.period
        
        # Standart sapma
        std_dev = statistics.stdev(closes)
        
        # Üst ve alt bantlar
        upper_band = middle_band + (std_dev * self.std_dev_multiplier)
        lower_band = middle_band - (std_dev * self.std_dev_multiplier)
        
        # Band genişliği
        band_width = upper_band - lower_band
        
        # %B hesaplama (fiyatın bantlar içindeki pozisyonu)
        # %B = (Fiyat - Alt Bant) / (Üst Bant - Alt Bant)
        percent_b = (current_price - lower_band) / band_width if band_width > 0 else 0.5
        
        # Bollinger Squeeze tespiti (düşük volatilite)
        historical_widths = self._calculate_historical_widths(candles)
        squeeze = self._detect_squeeze(band_width, historical_widths)
        
        # Sinyal üretimi
        signal = self._generate_signal(current_price, upper_band, lower_band, middle_band, percent_b, candles)
        
        return {
            "upper_band": upper_band,
            "middle_band": middle_band,
            "lower_band": lower_band,
            "band_width": band_width,
            "percent_b": percent_b,
            "squeeze": squeeze,
            "signal": signal,
            "volatility": self._calculate_volatility_level(band_width, middle_band),
            "trend": self._determine_trend(candles, middle_band)
        }
    
    def _calculate_historical_widths(self, candles: List[PriceCandle]) -> List[float]:
        """Geçmiş band genişliklerini hesapla"""
        if len(candles) < self.period + 20:
            return []
        
        widths = []
        for i in range(self.period, len(candles)):
            period_candles = candles[i-self.period:i]
            closes = [float(c.close) for c in period_candles]
            
            mean = sum(closes) / len(closes)
            std_dev = statistics.stdev(closes) if len(closes) > 1 else 0
            
            width = 2 * std_dev * self.std_dev_multiplier
            widths.append(width)
        
        return widths
    
    def _detect_squeeze(self, current_width: float, historical_widths: List[float]) -> bool:
        """Bollinger Squeeze tespiti"""
        if len(historical_widths) < 20:
            return False
        
        # Son 20 genişliğin ortalaması
        avg_width = sum(historical_widths[-20:]) / 20
        
        # Mevcut genişlik ortalamanın %70'inden azsa squeeze var
        return current_width < avg_width * 0.7
    
    def _generate_signal(self, price: float, upper: float, lower: float, 
                        middle: float, percent_b: float, candles: List[PriceCandle]) -> Optional[Dict[str, any]]:
        """Bollinger Bands sinyali üret"""
        signal_type = None
        confidence = 0.0
        reason = ""
        
        # Alt banda dokunma ve geri dönüş
        if percent_b <= 0.05:  # Fiyat alt bandın çok yakınında veya altında
            # Son 3 mumda dönüş var mı?
            if len(candles) >= 3:
                if candles[-1].close > candles[-2].close:  # Fiyat yükseliyor
                    signal_type = "BUY"
                    confidence = 0.7
                    reason = "Alt banda dokunma ve dönüş"
        
        # Üst banda dokunma ve geri dönüş
        elif percent_b >= 0.95:  # Fiyat üst bandın çok yakınında veya üstünde
            if len(candles) >= 3:
                if candles[-1].close < candles[-2].close:  # Fiyat düşüyor
                    signal_type = "SELL"
                    confidence = 0.7
                    reason = "Üst banda dokunma ve dönüş"
        
        # Orta bant kırılması
        elif len(candles) >= 2:
            prev_close = float(candles[-2].close)
            
            # Aşağıdan yukarı kırılma
            if prev_close < middle and price > middle:
                signal_type = "BUY"
                confidence = 0.5
                reason = "Orta bant yukarı kırılması"
            
            # Yukarıdan aşağı kırılma
            elif prev_close > middle and price < middle:
                signal_type = "SELL"
                confidence = 0.5
                reason = "Orta bant aşağı kırılması"
        
        if signal_type:
            return {
                "type": signal_type,
                "confidence": confidence,
                "reason": reason,
                "percent_b": percent_b
            }
        
        return None
    
    def _calculate_volatility_level(self, band_width: float, middle_band: float) -> str:
        """Volatilite seviyesi"""
        # Band genişliğinin orta banda oranı
        width_ratio = band_width / middle_band if middle_band > 0 else 0
        
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
    
    def _determine_trend(self, candles: List[PriceCandle], middle_band: float) -> str:
        """Bollinger Bands'e göre trend"""
        if len(candles) < 5:
            return "NEUTRAL"
        
        # Son 5 mumun kapanışları
        recent_closes = [float(c.close) for c in candles[-5:]]
        
        # Orta bandın üstünde mi altında mı?
        above_middle = sum(1 for c in recent_closes if c > middle_band)
        
        if above_middle >= 4:
            return "BULLISH"
        elif above_middle <= 1:
            return "BEARISH"
        else:
            return "NEUTRAL"
    
    def get_signal_weight(self, result: Dict[str, any]) -> Tuple[Optional[str], float]:
        """
        Bollinger Bands'e göre sinyal ve güven skoru
        
        Returns:
            (signal_type, confidence): ("BUY"/"SELL"/None, 0.0-1.0)
        """
        if not result["upper_band"]:
            return None, 0.0
        
        signal = result.get("signal")
        if not signal:
            return None, 0.0
        
        # Squeeze durumunda sinyal güçlenir
        confidence = signal["confidence"]
        if result["squeeze"]:
            confidence = min(confidence * 1.3, 1.0)
        
        # Volatiliteye göre ayarlama
        volatility = result["volatility"]
        if volatility == "VERY_LOW":
            confidence *= 1.2  # Düşük volatilitede bantlara dokunma daha anlamlı
        elif volatility == "VERY_HIGH":
            confidence *= 0.8  # Yüksek volatilitede daha az güvenilir
        
        return signal["type"], min(confidence, 1.0)