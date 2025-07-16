"""
Destek ve Direnç seviyesi tespit algoritması
"""
from typing import List, Tuple, Dict
from decimal import Decimal
from datetime import datetime, timedelta
import numpy as np
from models.price_data import PriceCandle
from models.trading_signal import SupportResistance
import logging

logger = logging.getLogger(__name__)


class SupportResistanceAnalyzer:
    """Destek/Direnç analizi"""
    
    def __init__(self, lookback_periods: int = 100, min_touches: int = 2, tolerance: float = 0.002):
        """
        Args:
            lookback_periods: Geriye dönük bakılacak mum sayısı
            min_touches: Minimum dokunma sayısı
            tolerance: Fiyat toleransı (0.002 = %0.2)
        """
        self.lookback_periods = lookback_periods
        self.min_touches = min_touches
        self.tolerance = tolerance
    
    def find_pivot_points(self, candles: List[PriceCandle]) -> Tuple[List[float], List[float]]:
        """Pivot noktalarını bul (yerel min/max)"""
        if len(candles) < 3:
            return [], []
        
        highs = []
        lows = []
        
        for i in range(1, len(candles) - 1):
            prev_candle = candles[i - 1]
            curr_candle = candles[i]
            next_candle = candles[i + 1]
            
            # Yerel maksimum
            if curr_candle.high > prev_candle.high and curr_candle.high > next_candle.high:
                highs.append(float(curr_candle.high))
            
            # Yerel minimum
            if curr_candle.low < prev_candle.low and curr_candle.low < next_candle.low:
                lows.append(float(curr_candle.low))
        
        return highs, lows
    
    def cluster_levels(self, levels: List[float], tolerance: float) -> List[Tuple[float, int]]:
        """Yakın seviyeleri grupla"""
        if not levels:
            return []
        
        sorted_levels = sorted(levels)
        clusters = []
        current_cluster = [sorted_levels[0]]
        
        for level in sorted_levels[1:]:
            if (level - current_cluster[-1]) / current_cluster[-1] <= tolerance:
                current_cluster.append(level)
            else:
                # Cluster'ı kaydet
                avg_level = sum(current_cluster) / len(current_cluster)
                clusters.append((avg_level, len(current_cluster)))
                current_cluster = [level]
        
        # Son cluster'ı ekle
        if current_cluster:
            avg_level = sum(current_cluster) / len(current_cluster)
            clusters.append((avg_level, len(current_cluster)))
        
        return clusters
    
    def analyze(self, candles: List[PriceCandle]) -> Dict[str, List[SupportResistance]]:
        """Destek ve direnç seviyelerini analiz et"""
        if len(candles) < self.lookback_periods:
            logger.warning(f"Not enough candles for analysis. Need {self.lookback_periods}, got {len(candles)}")
            return {"support": [], "resistance": []}
        
        # Son lookback_periods kadar mumu al
        recent_candles = candles[-self.lookback_periods:]
        
        # Pivot noktalarını bul
        highs, lows = self.find_pivot_points(recent_candles)
        
        # Seviyeleri grupla
        resistance_clusters = self.cluster_levels(highs, self.tolerance)
        support_clusters = self.cluster_levels(lows, self.tolerance)
        
        # Filtreleme - minimum dokunma sayısı
        strong_resistances = [
            SupportResistance(
                level=Decimal(str(level)),
                strength=min(1.0, count / 5),  # 5 dokunmada maksimum güç
                level_type="resistance",
                touch_count=count,
                last_test=datetime.utcnow()
            )
            for level, count in resistance_clusters
            if count >= self.min_touches
        ]
        
        strong_supports = [
            SupportResistance(
                level=Decimal(str(level)),
                strength=min(1.0, count / 5),
                level_type="support",
                touch_count=count,
                last_test=datetime.utcnow()
            )
            for level, count in support_clusters
            if count >= self.min_touches
        ]
        
        # Güce göre sırala
        strong_resistances.sort(key=lambda x: x.strength, reverse=True)
        strong_supports.sort(key=lambda x: x.strength, reverse=True)
        
        logger.info(f"Found {len(strong_supports)} support and {len(strong_resistances)} resistance levels")
        
        return {
            "support": strong_supports,
            "resistance": strong_resistances
        }
    
    def get_nearest_levels(self, current_price: Decimal, levels: Dict[str, List[SupportResistance]]) -> Dict[str, SupportResistance]:
        """Mevcut fiyata en yakın destek/direnç seviyelerini bul"""
        result = {}
        
        # En yakın destek
        supports = [s for s in levels.get("support", []) if s.level < current_price]
        if supports:
            result["nearest_support"] = max(supports, key=lambda x: x.level)
        
        # En yakın direnç
        resistances = [r for r in levels.get("resistance", []) if r.level > current_price]
        if resistances:
            result["nearest_resistance"] = min(resistances, key=lambda x: x.level)
        
        return result
    
    def is_near_support(self, current_price: Decimal, support_level: Decimal, threshold: float = 0.005) -> bool:
        """Fiyat desteğe yakın mı? (threshold: %0.5)"""
        distance = abs(current_price - support_level) / support_level
        return distance <= threshold
    
    def is_near_resistance(self, current_price: Decimal, resistance_level: Decimal, threshold: float = 0.005) -> bool:
        """Fiyat dirence yakın mı?"""
        distance = abs(current_price - resistance_level) / resistance_level
        return distance <= threshold