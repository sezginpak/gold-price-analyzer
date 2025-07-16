"""
ATR (Average True Range) Göstergesi - Volatilite ölçümü
"""
from typing import List, Dict, Optional, Tuple
from decimal import Decimal
import logging
from models.price_data import PriceCandle

logger = logging.getLogger(__name__)


class ATRIndicator:
    """ATR hesaplaması ve volatilite analizi"""
    
    def __init__(self, period: int = 14):
        """
        Args:
            period: ATR hesaplama periyodu (varsayılan 14)
        """
        self.period = period
    
    def calculate(self, candles: List[PriceCandle]) -> Dict[str, any]:
        """ATR hesapla"""
        if len(candles) < self.period + 1:
            logger.warning(f"Not enough data for ATR. Need {self.period + 1}, got {len(candles)}")
            return {
                "atr": None,
                "atr_percent": None,
                "volatility_level": None,
                "volatility_trend": None,
                "risk_level": None
            }
        
        # True Range değerlerini hesapla
        true_ranges = []
        
        for i in range(1, len(candles)):
            current = candles[i]
            previous = candles[i-1]
            
            # True Range = max(
            #   High - Low,
            #   abs(High - Previous Close),
            #   abs(Low - Previous Close)
            # )
            tr1 = float(current.high - current.low)
            tr2 = abs(float(current.high - previous.close))
            tr3 = abs(float(current.low - previous.close))
            
            true_range = max(tr1, tr2, tr3)
            true_ranges.append(true_range)
        
        # İlk ATR değeri: ilk N true range'in ortalaması
        if len(true_ranges) < self.period:
            return {
                "atr": None,
                "atr_percent": None,
                "volatility_level": None,
                "volatility_trend": None,
                "risk_level": None
            }
        
        # ATR hesaplama (Wilder's smoothing)
        atr_values = []
        
        # İlk ATR
        first_atr = sum(true_ranges[:self.period]) / self.period
        atr_values.append(first_atr)
        
        # Sonraki ATR değerleri
        for i in range(self.period, len(true_ranges)):
            atr = (atr_values[-1] * (self.period - 1) + true_ranges[i]) / self.period
            atr_values.append(atr)
        
        current_atr = atr_values[-1]
        current_price = float(candles[-1].close)
        
        # ATR'nin fiyata oranı (yüzde olarak)
        atr_percent = (current_atr / current_price) * 100 if current_price > 0 else 0
        
        # Volatilite seviyesi
        volatility_level = self._determine_volatility_level(atr_percent)
        
        # Volatilite trendi
        volatility_trend = self._analyze_volatility_trend(atr_values)
        
        # Risk seviyesi
        risk_level = self._calculate_risk_level(atr_percent, volatility_trend)
        
        # Historical ATR analizi
        historical_analysis = self._analyze_historical_atr(atr_values)
        
        return {
            "atr": current_atr,
            "atr_percent": atr_percent,
            "volatility_level": volatility_level,
            "volatility_trend": volatility_trend,
            "risk_level": risk_level,
            "historical_percentile": historical_analysis["percentile"],
            "expanding_volatility": historical_analysis["expanding"],
            "contracting_volatility": historical_analysis["contracting"],
            "suggested_stop_distance": current_atr * 2  # 2x ATR stop loss önerisi
        }
    
    def _determine_volatility_level(self, atr_percent: float) -> str:
        """Volatilite seviyesini belirle"""
        if atr_percent < 0.5:
            return "VERY_LOW"
        elif atr_percent < 1.0:
            return "LOW"
        elif atr_percent < 2.0:
            return "NORMAL"
        elif atr_percent < 3.0:
            return "HIGH"
        else:
            return "EXTREME"
    
    def _analyze_volatility_trend(self, atr_values: List[float]) -> str:
        """Volatilite trendini analiz et"""
        if len(atr_values) < 10:
            return "STABLE"
        
        recent = atr_values[-10:]
        older = atr_values[-20:-10] if len(atr_values) >= 20 else atr_values[:10]
        
        recent_avg = sum(recent) / len(recent)
        older_avg = sum(older) / len(older)
        
        change_percent = ((recent_avg - older_avg) / older_avg) * 100
        
        if change_percent > 20:
            return "EXPANDING_FAST"
        elif change_percent > 10:
            return "EXPANDING"
        elif change_percent < -20:
            return "CONTRACTING_FAST"
        elif change_percent < -10:
            return "CONTRACTING"
        else:
            return "STABLE"
    
    def _calculate_risk_level(self, atr_percent: float, volatility_trend: str) -> str:
        """Risk seviyesini hesapla"""
        # Temel risk volatiliteye göre
        if atr_percent < 1.0:
            base_risk = "LOW"
        elif atr_percent < 2.0:
            base_risk = "MEDIUM"
        else:
            base_risk = "HIGH"
        
        # Trend'e göre ayarlama
        if volatility_trend in ["EXPANDING_FAST", "EXPANDING"]:
            # Artan volatilite riski artırır
            if base_risk == "LOW":
                return "MEDIUM"
            elif base_risk == "MEDIUM":
                return "HIGH"
            else:
                return "EXTREME"
        elif volatility_trend in ["CONTRACTING_FAST", "CONTRACTING"]:
            # Azalan volatilite breakout riski oluşturabilir
            return base_risk  # Değiştirme
        
        return base_risk
    
    def _analyze_historical_atr(self, atr_values: List[float]) -> Dict[str, any]:
        """Tarihi ATR analizi"""
        if len(atr_values) < 20:
            return {
                "percentile": 50,
                "expanding": False,
                "contracting": False
            }
        
        current = atr_values[-1]
        historical = sorted(atr_values[-100:] if len(atr_values) >= 100 else atr_values)
        
        # Percentile hesapla
        position = 0
        for val in historical:
            if val < current:
                position += 1
        
        percentile = (position / len(historical)) * 100
        
        # Genişleme/daralma tespiti
        recent_5 = atr_values[-5:]
        recent_20 = atr_values[-20:]
        
        expanding = all(recent_5[i] > recent_5[i-1] for i in range(1, len(recent_5)))
        contracting = all(recent_5[i] < recent_5[i-1] for i in range(1, len(recent_5)))
        
        return {
            "percentile": percentile,
            "expanding": expanding,
            "contracting": contracting
        }
    
    def calculate_dynamic_stop_loss(self, entry_price: Decimal, atr: float, 
                                   risk_multiplier: float = 2.0, is_long: bool = True) -> Decimal:
        """
        ATR bazlı dinamik stop loss hesapla
        
        Args:
            entry_price: Giriş fiyatı
            atr: Mevcut ATR değeri
            risk_multiplier: ATR çarpanı (varsayılan 2.0)
            is_long: Long pozisyon mu?
        
        Returns:
            Stop loss seviyesi
        """
        stop_distance = Decimal(str(atr * risk_multiplier))
        
        if is_long:
            stop_loss = entry_price - stop_distance
        else:
            stop_loss = entry_price + stop_distance
        
        return stop_loss
    
    def calculate_position_size(self, capital: float, risk_percent: float, 
                               entry_price: float, stop_loss: float) -> float:
        """
        ATR bazlı pozisyon boyutu hesapla
        
        Args:
            capital: Toplam sermaye
            risk_percent: Risk yüzdesi (örn: 2.0 için %2)
            entry_price: Giriş fiyatı
            stop_loss: Stop loss seviyesi
        
        Returns:
            Pozisyon boyutu
        """
        risk_amount = capital * (risk_percent / 100)
        stop_distance = abs(entry_price - stop_loss)
        
        if stop_distance == 0:
            return 0
        
        position_size = risk_amount / stop_distance
        
        return position_size
    
    def get_signal_weight(self, result: Dict[str, any]) -> Tuple[Optional[str], float]:
        """
        ATR sinyal ağırlığı (doğrudan sinyal vermez, diğer sinyalleri filtreler)
        
        Returns:
            (signal_type, confidence_modifier): (None, 0.0-1.0)
        """
        if not result["atr"]:
            return None, 1.0  # ATR yoksa değiştirme
        
        # Ekstrem volatilitede güveni azalt
        if result["volatility_level"] == "EXTREME":
            return None, 0.5
        elif result["volatility_level"] == "HIGH":
            return None, 0.8
        
        # Hızla genişleyen volatilitede dikkatli ol
        if result["volatility_trend"] == "EXPANDING_FAST":
            return None, 0.7
        
        # Düşük volatilite breakout potansiyeli
        if result["volatility_level"] == "VERY_LOW" and result["contracting_volatility"]:
            # Breakout beklentisi, sinyalleri güçlendir
            return None, 1.2
        
        return None, 1.0