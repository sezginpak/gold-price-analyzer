"""
Advanced Divergence Detector Module
RSI, MACD, Stochastic ile Regular ve Hidden Divergence tespiti
Volume verisi olmadan çalışacak şekilde optimize edilmiş
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional, Union
from dataclasses import dataclass, field
from scipy.signal import argrelextrema
from utils.logger import logger
import ta


@dataclass
class DivergencePoint:
    """Divergence noktası bilgisi"""
    index: int
    price: float
    indicator_value: float
    timestamp: Optional[str] = None


@dataclass
class Divergence:
    """Divergence bilgisi"""
    type: str  # "regular_bullish", "regular_bearish", "hidden_bullish", "hidden_bearish"
    indicator: str  # "RSI", "MACD", "Stochastic"
    strength: float  # 0-100
    price_points: List[DivergencePoint] = field(default_factory=list)
    indicator_points: List[DivergencePoint] = field(default_factory=list)
    angle_price: float = 0.0  # Fiyat trendinin açısı
    angle_indicator: float = 0.0  # Indicator trendinin açısı
    angle_difference: float = 0.0  # Açı farkı (divergence gücü)
    maturity_score: float = 0.0  # Divergence olgunluğu
    class_rating: str = "C"  # A, B, C sınıflandırması
    invalidated: bool = False
    success_probability: float = 0.0


@dataclass
class DivergenceAnalysis:
    """Kapsamlı divergence analiz sonucu"""
    regular_divergences: List[Divergence] = field(default_factory=list)
    hidden_divergences: List[Divergence] = field(default_factory=list)
    confluence_score: float = 0.0  # Birden fazla indicator'de aynı divergence
    dominant_divergence: Optional[Divergence] = None
    overall_signal: str = "NEUTRAL"  # "BULLISH", "BEARISH", "NEUTRAL"
    signal_strength: float = 0.0
    next_targets: List[float] = field(default_factory=list)
    invalidation_levels: List[float] = field(default_factory=list)


class AdvancedDivergenceDetector:
    """Gelişmiş Divergence Tespit Sistemi"""
    
    # Divergence sınıflandırması için eşikler
    CLASS_A_THRESHOLD = 80  # Çok güçlü
    CLASS_B_THRESHOLD = 60  # Güçlü
    
    # Minimum divergence kriterleri
    MIN_DIVERGENCE_PERIOD = 10  # Minimum mum sayısı
    MIN_ANGLE_DIFFERENCE = 5.0  # Minimum açı farkı (derece)
    
    def __init__(self, 
                 rsi_period: int = 14,
                 macd_fast: int = 12,
                 macd_slow: int = 26,
                 macd_signal: int = 9,
                 stoch_k: int = 14,
                 stoch_d: int = 3):
        """
        Advanced Divergence Detector başlatıcı
        
        Args:
            rsi_period: RSI periyodu
            macd_fast: MACD hızlı EMA periyodu
            macd_slow: MACD yavaş EMA periyodu  
            macd_signal: MACD sinyal periyodu
            stoch_k: Stochastic %K periyodu
            stoch_d: Stochastic %D periyodu
        """
        self.rsi_period = rsi_period
        self.macd_fast = macd_fast
        self.macd_slow = macd_slow
        self.macd_signal = macd_signal
        self.stoch_k = stoch_k
        self.stoch_d = stoch_d
        
        # Historical success rates (gerçek trading verilerine göre ayarlanmalı)
        self.success_rates = {
            "regular_bullish": {"A": 0.75, "B": 0.65, "C": 0.45},
            "regular_bearish": {"A": 0.75, "B": 0.65, "C": 0.45},
            "hidden_bullish": {"A": 0.65, "B": 0.55, "C": 0.35},
            "hidden_bearish": {"A": 0.65, "B": 0.55, "C": 0.35}
        }
        
    def calculate_indicators(self, df: pd.DataFrame) -> Dict:
        """
        Tüm teknik göstergeleri hesapla
        
        Args:
            df: OHLC verisi
            
        Returns:
            Hesaplanmış göstergeler
        """
        try:
            indicators = {}
            
            # RSI hesaplama
            indicators['rsi'] = ta.momentum.RSIIndicator(
                close=df['close'], 
                window=self.rsi_period
            ).rsi()
            
            # MACD hesaplama
            macd = ta.trend.MACD(
                close=df['close'],
                window_slow=self.macd_slow,
                window_fast=self.macd_fast,
                window_sign=self.macd_signal
            )
            indicators['macd'] = macd.macd()
            indicators['macd_histogram'] = macd.macd_diff()
            indicators['macd_signal'] = macd.macd_signal()
            
            # Stochastic hesaplama
            stoch = ta.momentum.StochasticOscillator(
                high=df['high'],
                low=df['low'],
                close=df['close'],
                window=self.stoch_k,
                smooth_window=self.stoch_d
            )
            indicators['stoch_k'] = stoch.stoch()
            indicators['stoch_d'] = stoch.stoch_signal()
            
            return indicators
            
        except Exception as e:
            logger.error(f"Indicator hesaplama hatası: {e}")
            return {}
    
    def find_swing_points(self, 
                         series: pd.Series, 
                         order: int = 5,
                         min_distance: int = 10) -> Tuple[List[Tuple[int, float]], List[Tuple[int, float]]]:
        """
        Swing high ve low noktalarını bul
        
        Args:
            series: Fiyat veya indicator serisi
            order: Extrema bulma için pencere boyutu
            min_distance: Swing noktaları arasındaki minimum mesafe
            
        Returns:
            (swing_highs, swing_lows) tuple'ı
        """
        try:
            values = series.values
            
            # Scipy ile local extrema bul
            high_indices = argrelextrema(values, np.greater, order=order)[0]
            low_indices = argrelextrema(values, np.less, order=order)[0]
            
            # Minimum mesafe filtresi uygula
            def filter_by_distance(indices, values_array):
                if len(indices) <= 1:
                    return indices
                
                filtered = [indices[0]]
                for i in range(1, len(indices)):
                    if indices[i] - filtered[-1] >= min_distance:
                        filtered.append(indices[i])
                
                return np.array(filtered)
            
            high_indices = filter_by_distance(high_indices, values)
            low_indices = filter_by_distance(low_indices, values)
            
            # Tuple formatına çevir
            swing_highs = [(idx, values[idx]) for idx in high_indices 
                          if 0 <= idx < len(values)]
            swing_lows = [(idx, values[idx]) for idx in low_indices 
                         if 0 <= idx < len(values)]
            
            return swing_highs, swing_lows
            
        except Exception as e:
            logger.error(f"Swing point bulma hatası: {e}")
            return [], []
    
    def calculate_angle(self, point1: Tuple[int, float], point2: Tuple[int, float]) -> float:
        """
        İki nokta arasındaki açıyı hesapla (derece cinsinden)
        
        Args:
            point1: (index, value) birinci nokta
            point2: (index, value) ikinci nokta
            
        Returns:
            Açı (derece)
        """
        try:
            x1, y1 = point1
            x2, y2 = point2
            
            if x2 == x1:
                return 90.0 if y2 > y1 else -90.0
            
            # Açıyı radyandan dereceye çevir
            angle_rad = np.arctan((y2 - y1) / (x2 - x1))
            angle_deg = np.degrees(angle_rad)
            
            return angle_deg
            
        except Exception as e:
            logger.error(f"Açı hesaplama hatası: {e}")
            return 0.0
    
    def detect_regular_divergence(self, 
                                price_highs: List[Tuple[int, float]], 
                                price_lows: List[Tuple[int, float]],
                                indicator_highs: List[Tuple[int, float]], 
                                indicator_lows: List[Tuple[int, float]],
                                indicator_name: str) -> List[Divergence]:
        """
        Regular divergence tespiti
        
        Args:
            price_highs: Fiyat yüksek noktaları
            price_lows: Fiyat düşük noktaları
            indicator_highs: Indicator yüksek noktaları
            indicator_lows: Indicator düşük noktaları
            indicator_name: Indicator adı
            
        Returns:
            Tespit edilen regular divergence'lar
        """
        divergences = []
        
        try:
            # Bearish Regular Divergence: Fiyat HH, Indicator LH
            if len(price_highs) >= 2 and len(indicator_highs) >= 2:
                for i in range(len(price_highs) - 1):
                    for j in range(len(indicator_highs) - 1):
                        price_point1 = price_highs[i]
                        price_point2 = price_highs[i + 1]
                        ind_point1 = indicator_highs[j]
                        ind_point2 = indicator_highs[j + 1]
                        
                        # Zaman uyumu kontrolü (yaklaşık aynı indeksler)
                        if (abs(price_point1[0] - ind_point1[0]) <= 3 and 
                            abs(price_point2[0] - ind_point2[0]) <= 3):
                            
                            # Period kontrolü
                            period = abs(price_point2[0] - price_point1[0])
                            if period < self.MIN_DIVERGENCE_PERIOD:
                                continue
                            
                            # Bearish regular divergence: Price HH, Indicator LH
                            if (price_point2[1] > price_point1[1] and  # Higher High
                                ind_point2[1] < ind_point1[1]):  # Lower High
                                
                                # Açıları hesapla
                                price_angle = self.calculate_angle(price_point1, price_point2)
                                ind_angle = self.calculate_angle(ind_point1, ind_point2)
                                angle_diff = abs(price_angle - ind_angle)
                                
                                if angle_diff >= self.MIN_ANGLE_DIFFERENCE:
                                    divergence = Divergence(
                                        type="regular_bearish",
                                        indicator=indicator_name,
                                        strength=0.0,
                                        price_points=[
                                            DivergencePoint(price_point1[0], price_point1[1], 0),
                                            DivergencePoint(price_point2[0], price_point2[1], 0)
                                        ],
                                        indicator_points=[
                                            DivergencePoint(ind_point1[0], 0, ind_point1[1]),
                                            DivergencePoint(ind_point2[0], 0, ind_point2[1])
                                        ],
                                        angle_price=price_angle,
                                        angle_indicator=ind_angle,
                                        angle_difference=angle_diff
                                    )
                                    divergences.append(divergence)
            
            # Bullish Regular Divergence: Fiyat LL, Indicator HL
            if len(price_lows) >= 2 and len(indicator_lows) >= 2:
                for i in range(len(price_lows) - 1):
                    for j in range(len(indicator_lows) - 1):
                        price_point1 = price_lows[i]
                        price_point2 = price_lows[i + 1]
                        ind_point1 = indicator_lows[j]
                        ind_point2 = indicator_lows[j + 1]
                        
                        # Zaman uyumu kontrolü
                        if (abs(price_point1[0] - ind_point1[0]) <= 3 and 
                            abs(price_point2[0] - ind_point2[0]) <= 3):
                            
                            # Period kontrolü
                            period = abs(price_point2[0] - price_point1[0])
                            if period < self.MIN_DIVERGENCE_PERIOD:
                                continue
                            
                            # Bullish regular divergence: Price LL, Indicator HL
                            if (price_point2[1] < price_point1[1] and  # Lower Low
                                ind_point2[1] > ind_point1[1]):  # Higher Low
                                
                                # Açıları hesapla
                                price_angle = self.calculate_angle(price_point1, price_point2)
                                ind_angle = self.calculate_angle(ind_point1, ind_point2)
                                angle_diff = abs(price_angle - ind_angle)
                                
                                if angle_diff >= self.MIN_ANGLE_DIFFERENCE:
                                    divergence = Divergence(
                                        type="regular_bullish",
                                        indicator=indicator_name,
                                        strength=0.0,
                                        price_points=[
                                            DivergencePoint(price_point1[0], price_point1[1], 0),
                                            DivergencePoint(price_point2[0], price_point2[1], 0)
                                        ],
                                        indicator_points=[
                                            DivergencePoint(ind_point1[0], 0, ind_point1[1]),
                                            DivergencePoint(ind_point2[0], 0, ind_point2[1])
                                        ],
                                        angle_price=price_angle,
                                        angle_indicator=ind_angle,
                                        angle_difference=angle_diff
                                    )
                                    divergences.append(divergence)
            
            return divergences
            
        except Exception as e:
            logger.error(f"Regular divergence tespit hatası: {e}")
            return []
    
    def detect_hidden_divergence(self, 
                               price_highs: List[Tuple[int, float]], 
                               price_lows: List[Tuple[int, float]],
                               indicator_highs: List[Tuple[int, float]], 
                               indicator_lows: List[Tuple[int, float]],
                               indicator_name: str) -> List[Divergence]:
        """
        Hidden divergence tespiti (trend devamı sinyali)
        
        Args:
            price_highs: Fiyat yüksek noktaları
            price_lows: Fiyat düşük noktaları
            indicator_highs: Indicator yüksek noktaları
            indicator_lows: Indicator düşük noktaları
            indicator_name: Indicator adı
            
        Returns:
            Tespit edilen hidden divergence'lar
        """
        divergences = []
        
        try:
            # Bullish Hidden Divergence: Fiyat HL, Indicator LL (uptrend devamı)
            if len(price_lows) >= 2 and len(indicator_lows) >= 2:
                for i in range(len(price_lows) - 1):
                    for j in range(len(indicator_lows) - 1):
                        price_point1 = price_lows[i]
                        price_point2 = price_lows[i + 1]
                        ind_point1 = indicator_lows[j]
                        ind_point2 = indicator_lows[j + 1]
                        
                        # Zaman uyumu kontrolü
                        if (abs(price_point1[0] - ind_point1[0]) <= 3 and 
                            abs(price_point2[0] - ind_point2[0]) <= 3):
                            
                            # Period kontrolü
                            period = abs(price_point2[0] - price_point1[0])
                            if period < self.MIN_DIVERGENCE_PERIOD:
                                continue
                            
                            # Bullish hidden: Price HL, Indicator LL
                            if (price_point2[1] > price_point1[1] and  # Higher Low
                                ind_point2[1] < ind_point1[1]):  # Lower Low
                                
                                # Açıları hesapla
                                price_angle = self.calculate_angle(price_point1, price_point2)
                                ind_angle = self.calculate_angle(ind_point1, ind_point2)
                                angle_diff = abs(price_angle - ind_angle)
                                
                                if angle_diff >= self.MIN_ANGLE_DIFFERENCE:
                                    divergence = Divergence(
                                        type="hidden_bullish",
                                        indicator=indicator_name,
                                        strength=0.0,
                                        price_points=[
                                            DivergencePoint(price_point1[0], price_point1[1], 0),
                                            DivergencePoint(price_point2[0], price_point2[1], 0)
                                        ],
                                        indicator_points=[
                                            DivergencePoint(ind_point1[0], 0, ind_point1[1]),
                                            DivergencePoint(ind_point2[0], 0, ind_point2[1])
                                        ],
                                        angle_price=price_angle,
                                        angle_indicator=ind_angle,
                                        angle_difference=angle_diff
                                    )
                                    divergences.append(divergence)
            
            # Bearish Hidden Divergence: Fiyat LH, Indicator HH (downtrend devamı)
            if len(price_highs) >= 2 and len(indicator_highs) >= 2:
                for i in range(len(price_highs) - 1):
                    for j in range(len(indicator_highs) - 1):
                        price_point1 = price_highs[i]
                        price_point2 = price_highs[i + 1]
                        ind_point1 = indicator_highs[j]
                        ind_point2 = indicator_highs[j + 1]
                        
                        # Zaman uyumu kontrolü
                        if (abs(price_point1[0] - ind_point1[0]) <= 3 and 
                            abs(price_point2[0] - ind_point2[0]) <= 3):
                            
                            # Period kontrolü
                            period = abs(price_point2[0] - price_point1[0])
                            if period < self.MIN_DIVERGENCE_PERIOD:
                                continue
                            
                            # Bearish hidden: Price LH, Indicator HH
                            if (price_point2[1] < price_point1[1] and  # Lower High
                                ind_point2[1] > ind_point1[1]):  # Higher High
                                
                                # Açıları hesapla
                                price_angle = self.calculate_angle(price_point1, price_point2)
                                ind_angle = self.calculate_angle(ind_point1, ind_point2)
                                angle_diff = abs(price_angle - ind_angle)
                                
                                if angle_diff >= self.MIN_ANGLE_DIFFERENCE:
                                    divergence = Divergence(
                                        type="hidden_bearish",
                                        indicator=indicator_name,
                                        strength=0.0,
                                        price_points=[
                                            DivergencePoint(price_point1[0], price_point1[1], 0),
                                            DivergencePoint(price_point2[0], price_point2[1], 0)
                                        ],
                                        indicator_points=[
                                            DivergencePoint(ind_point1[0], 0, ind_point1[1]),
                                            DivergencePoint(ind_point2[0], 0, ind_point2[1])
                                        ],
                                        angle_price=price_angle,
                                        angle_indicator=ind_angle,
                                        angle_difference=angle_diff
                                    )
                                    divergences.append(divergence)
            
            return divergences
            
        except Exception as e:
            logger.error(f"Hidden divergence tespit hatası: {e}")
            return []
    
    def calculate_divergence_strength(self, divergence: Divergence, df: pd.DataFrame) -> float:
        """
        Divergence gücünü hesapla (0-100)
        
        Args:
            divergence: Divergence objesi
            df: OHLC verisi
            
        Returns:
            Strength skoru (0-100)
        """
        try:
            strength = 0.0
            
            # Base strength - açı farkına göre
            angle_score = min(divergence.angle_difference / 45.0 * 40, 40)  # Max 40 puan
            strength += angle_score
            
            # Period uzunluğu bonusu
            if len(divergence.price_points) >= 2:
                period = abs(divergence.price_points[1].index - divergence.price_points[0].index)
                period_score = min(period / 50.0 * 20, 20)  # Max 20 puan
                strength += period_score
            
            # Fiyat değişim oranı
            if len(divergence.price_points) >= 2:
                price_change = abs(divergence.price_points[1].price - divergence.price_points[0].price)
                price_change_pct = price_change / divergence.price_points[0].price * 100
                price_score = min(price_change_pct * 2, 20)  # Max 20 puan
                strength += price_score
            
            # Indicator aşırı bölge bonusu
            if divergence.indicator == "RSI":
                for point in divergence.indicator_points:
                    if point.indicator_value <= 30 or point.indicator_value >= 70:
                        strength += 10  # Aşırı bölgede bonus
                        break
            elif divergence.indicator == "Stochastic":
                for point in divergence.indicator_points:
                    if point.indicator_value <= 20 or point.indicator_value >= 80:
                        strength += 10  # Aşırı bölgede bonus
                        break
            
            # Divergence tipi bonusu (regular daha güçlü)
            if "regular" in divergence.type:
                strength += 10
            else:  # hidden
                strength += 5
            
            return min(strength, 100.0)
            
        except Exception as e:
            logger.error(f"Divergence strength hesaplama hatası: {e}")
            return 0.0
    
    def calculate_maturity_score(self, divergence: Divergence, current_index: int) -> float:
        """
        Divergence olgunluk skorunu hesapla
        Divergence ne kadar eskiyse o kadar olgun
        
        Args:
            divergence: Divergence objesi
            current_index: Şu anki mum indeksi
            
        Returns:
            Maturity skoru (0-100)
        """
        try:
            if not divergence.price_points:
                return 0.0
            
            # Son divergence noktasından geçen süre
            last_point_index = max(point.index for point in divergence.price_points)
            time_since = current_index - last_point_index
            
            # Maturity hesapla (0-50 mum arası optimal, sonra azalır)
            if time_since <= 10:
                return time_since * 10  # 0-100 arası doğrusal artış
            elif time_since <= 50:
                return 100 - (time_since - 10) * 2  # Yavaş azalış
            else:
                return max(20 - (time_since - 50) * 0.5, 0)  # Hızlı azalış
                
        except Exception as e:
            logger.error(f"Maturity score hesaplama hatası: {e}")
            return 0.0
    
    def classify_divergence(self, divergence: Divergence) -> str:
        """
        Divergence'ı A, B, C sınıfına ayır
        
        Args:
            divergence: Divergence objesi
            
        Returns:
            Sınıf ("A", "B", "C")
        """
        try:
            total_score = (divergence.strength + divergence.maturity_score) / 2
            
            if total_score >= self.CLASS_A_THRESHOLD:
                return "A"
            elif total_score >= self.CLASS_B_THRESHOLD:
                return "B"
            else:
                return "C"
                
        except Exception as e:
            logger.error(f"Divergence sınıflandırma hatası: {e}")
            return "C"
    
    def calculate_success_probability(self, divergence: Divergence) -> float:
        """
        Historical success rate'e göre başarı olasılığını hesapla
        
        Args:
            divergence: Divergence objesi
            
        Returns:
            Success probability (0-1)
        """
        try:
            base_rate = self.success_rates.get(divergence.type, {}).get(divergence.class_rating, 0.3)
            
            # Maturity adjustment
            if divergence.maturity_score > 80:
                base_rate *= 1.1  # Olgun divergence'lar daha başarılı
            elif divergence.maturity_score < 30:
                base_rate *= 0.9  # Çok yeni divergence'lar daha riskli
            
            return min(base_rate, 1.0)
            
        except Exception as e:
            logger.error(f"Success probability hesaplama hatası: {e}")
            return 0.3
    
    def filter_false_divergences(self, divergences: List[Divergence], df: pd.DataFrame) -> List[Divergence]:
        """
        False divergence'ları filtrele
        
        Args:
            divergences: Divergence listesi
            df: OHLC verisi
            
        Returns:
            Filtrelenmiş divergence listesi
        """
        try:
            valid_divergences = []
            current_price = df['close'].iloc[-1]
            
            for div in divergences:
                is_valid = True
                
                # 1. Çok yakın divergence'ları birleştir
                # (Bu daha karmaşık bir algoritma gerektirir, şimdilik basit keep edelim)
                
                # 2. Çok zayıf divergence'ları çıkar
                if div.strength < 30:
                    is_valid = False
                
                # 3. Invalidation kontrolü
                if div.type in ["regular_bullish", "hidden_bullish"]:
                    # Bullish divergence invalid if price breaks below last low
                    if len(div.price_points) >= 2:
                        lowest_point = min(point.price for point in div.price_points)
                        if current_price < lowest_point * 0.98:  # %2 tolerance
                            div.invalidated = True
                            is_valid = False
                            
                elif div.type in ["regular_bearish", "hidden_bearish"]:
                    # Bearish divergence invalid if price breaks above last high  
                    if len(div.price_points) >= 2:
                        highest_point = max(point.price for point in div.price_points)
                        if current_price > highest_point * 1.02:  # %2 tolerance
                            div.invalidated = True
                            is_valid = False
                
                if is_valid and not div.invalidated:
                    valid_divergences.append(div)
            
            return valid_divergences
            
        except Exception as e:
            logger.error(f"False divergence filtreleme hatası: {e}")
            return divergences
    
    def calculate_confluence_score(self, all_divergences: List[Divergence]) -> float:
        """
        Birden fazla indicator'de aynı yönde divergence varsa confluence skoru hesapla
        
        Args:
            all_divergences: Tüm divergence'lar
            
        Returns:
            Confluence skoru (0-100)
        """
        try:
            if len(all_divergences) < 2:
                return 0.0
            
            # Aynı tip divergence'ları say
            type_counts = {}
            for div in all_divergences:
                div_type = div.type.split('_')[1]  # bullish/bearish kısmını al
                if div_type not in type_counts:
                    type_counts[div_type] = []
                type_counts[div_type].append(div)
            
            max_confluence = 0.0
            for div_type, divs in type_counts.items():
                if len(divs) >= 2:
                    # Farklı indicator'lerden mi geliyor?
                    indicators = set(div.indicator for div in divs)
                    if len(indicators) >= 2:
                        # Confluence strength = average strength * indicator count
                        avg_strength = sum(div.strength for div in divs) / len(divs)
                        confluence = avg_strength * len(indicators) / 3  # Max 3 indicator
                        max_confluence = max(max_confluence, confluence)
            
            return min(max_confluence, 100.0)
            
        except Exception as e:
            logger.error(f"Confluence score hesaplama hatası: {e}")
            return 0.0
    
    def find_dominant_divergence(self, divergences: List[Divergence]) -> Optional[Divergence]:
        """
        En güçlü (dominant) divergence'ı bul
        
        Args:
            divergences: Divergence listesi
            
        Returns:
            Dominant divergence veya None
        """
        try:
            if not divergences:
                return None
            
            # Composite score hesapla: strength + maturity + class bonus
            best_divergence = None
            best_score = 0.0
            
            for div in divergences:
                class_bonus = {"A": 30, "B": 20, "C": 10}.get(div.class_rating, 0)
                composite_score = div.strength + div.maturity_score + class_bonus
                
                if composite_score > best_score:
                    best_score = composite_score
                    best_divergence = div
            
            return best_divergence
            
        except Exception as e:
            logger.error(f"Dominant divergence bulma hatası: {e}")
            return None
    
    def calculate_targets_and_invalidations(self, 
                                          analysis: DivergenceAnalysis, 
                                          df: pd.DataFrame) -> DivergenceAnalysis:
        """
        Hedef seviyeleri ve geçersizleştirici seviyeleri hesapla
        
        Args:
            analysis: Divergence analizi
            df: OHLC verisi
            
        Returns:
            Güncellenmiş analiz
        """
        try:
            if not analysis.dominant_divergence:
                return analysis
            
            current_price = df['close'].iloc[-1]
            dom_div = analysis.dominant_divergence
            
            # Recent highs/lows bul
            recent_df = df.tail(50)  # Son 50 mum
            recent_high = recent_df['high'].max()
            recent_low = recent_df['low'].min()
            
            if "bullish" in dom_div.type:
                # Bullish targets
                price_range = recent_high - recent_low
                analysis.next_targets = [
                    current_price + price_range * 0.382,  # %38.2 projection
                    current_price + price_range * 0.618,  # %61.8 projection
                    recent_high  # Recent high test
                ]
                
                # Invalidation: Son low kırılması
                if dom_div.price_points:
                    lowest_div_point = min(point.price for point in dom_div.price_points)
                    analysis.invalidation_levels = [lowest_div_point * 0.98]
                    
            else:  # bearish
                # Bearish targets  
                price_range = recent_high - recent_low
                analysis.next_targets = [
                    current_price - price_range * 0.382,  # %38.2 projection
                    current_price - price_range * 0.618,  # %61.8 projection
                    recent_low  # Recent low test
                ]
                
                # Invalidation: Son high kırılması
                if dom_div.price_points:
                    highest_div_point = max(point.price for point in dom_div.price_points)
                    analysis.invalidation_levels = [highest_div_point * 1.02]
            
            return analysis
            
        except Exception as e:
            logger.error(f"Target ve invalidation hesaplama hatası: {e}")
            return analysis
    
    def analyze(self, df: pd.DataFrame, lookback: int = 200) -> DivergenceAnalysis:
        """
        Kapsamlı divergence analizi yap
        
        Args:
            df: OHLC verisi
            lookback: Geriye bakma periyodu
            
        Returns:
            Divergence analiz sonuçları
        """
        try:
            if len(df) < max(50, self.rsi_period, self.macd_slow):
                return DivergenceAnalysis()
            
            # Analiz için veri hazırla
            analysis_df = df.tail(lookback) if len(df) > lookback else df
            analysis_df = analysis_df.reset_index(drop=True)
            
            # Teknik göstergeleri hesapla
            indicators = self.calculate_indicators(analysis_df)
            
            if not indicators:
                logger.warning("Indicator hesaplama başarısız")
                return DivergenceAnalysis()
            
            # Fiyat swing noktaları
            price_highs, price_lows = self.find_swing_points(analysis_df['high'])
            price_highs_close, price_lows_close = self.find_swing_points(analysis_df['close'])
            
            all_regular_divergences = []
            all_hidden_divergences = []
            
            # Her indicator için divergence tespiti
            for indicator_name, indicator_series in indicators.items():
                if indicator_name in ['macd_histogram', 'macd_signal']:
                    continue  # Ana MACD'yi kullan
                    
                # Indicator swing noktaları
                ind_highs, ind_lows = self.find_swing_points(indicator_series)
                
                if not ind_highs or not ind_lows:
                    continue
                
                # Regular divergence tespiti
                regular_divs = self.detect_regular_divergence(
                    price_highs_close, price_lows_close,
                    ind_highs, ind_lows,
                    indicator_name.upper()
                )
                
                # Hidden divergence tespiti
                hidden_divs = self.detect_hidden_divergence(
                    price_highs_close, price_lows_close, 
                    ind_highs, ind_lows,
                    indicator_name.upper()
                )
                
                # Her divergence için detayları hesapla
                current_index = len(analysis_df) - 1
                
                for div in regular_divs + hidden_divs:
                    div.strength = self.calculate_divergence_strength(div, analysis_df)
                    div.maturity_score = self.calculate_maturity_score(div, current_index)
                    div.class_rating = self.classify_divergence(div)
                    div.success_probability = self.calculate_success_probability(div)
                
                all_regular_divergences.extend(regular_divs)
                all_hidden_divergences.extend(hidden_divs)
            
            # False divergence'ları filtrele
            all_regular_divergences = self.filter_false_divergences(all_regular_divergences, analysis_df)
            all_hidden_divergences = self.filter_false_divergences(all_hidden_divergences, analysis_df)
            
            # Analiz sonuçlarını oluştur
            analysis = DivergenceAnalysis(
                regular_divergences=all_regular_divergences,
                hidden_divergences=all_hidden_divergences
            )
            
            # Confluence score hesapla
            all_divergences = all_regular_divergences + all_hidden_divergences
            analysis.confluence_score = self.calculate_confluence_score(all_divergences)
            
            # Dominant divergence bul
            analysis.dominant_divergence = self.find_dominant_divergence(all_divergences)
            
            # Overall signal belirle
            if analysis.dominant_divergence:
                if "bullish" in analysis.dominant_divergence.type:
                    analysis.overall_signal = "BULLISH"
                    analysis.signal_strength = analysis.dominant_divergence.strength
                elif "bearish" in analysis.dominant_divergence.type:
                    analysis.overall_signal = "BEARISH"
                    analysis.signal_strength = analysis.dominant_divergence.strength
            
            # Hedef ve invalidation seviyeleri
            analysis = self.calculate_targets_and_invalidations(analysis, analysis_df)
            
            return analysis
            
        except Exception as e:
            logger.error(f"Divergence analiz hatası: {e}")
            return DivergenceAnalysis()


def calculate_divergence_analysis(df: pd.DataFrame, **kwargs) -> Dict:
    """
    Divergence analizi yaparak sonuçları dict formatında döndür
    
    Args:
        df: OHLC verisi
        **kwargs: Ek parametreler
        
    Returns:
        Divergence analiz sonuçları
    """
    try:
        detector = AdvancedDivergenceDetector()
        analysis = detector.analyze(df)
        
        # Dict formatına çevir
        result = {
            'status': 'success',
            'overall_signal': analysis.overall_signal,
            'signal_strength': analysis.signal_strength,
            'confluence_score': analysis.confluence_score,
            'regular_divergences': [
                {
                    'type': div.type,
                    'indicator': div.indicator,
                    'strength': div.strength,
                    'maturity_score': div.maturity_score,
                    'class_rating': div.class_rating,
                    'success_probability': div.success_probability,
                    'angle_difference': div.angle_difference,
                    'invalidated': div.invalidated,
                    'price_points': [
                        {'index': p.index, 'price': p.price} for p in div.price_points
                    ],
                    'indicator_points': [
                        {'index': p.index, 'value': p.indicator_value} for p in div.indicator_points
                    ]
                }
                for div in analysis.regular_divergences
            ],
            'hidden_divergences': [
                {
                    'type': div.type,
                    'indicator': div.indicator,
                    'strength': div.strength,
                    'maturity_score': div.maturity_score,
                    'class_rating': div.class_rating,
                    'success_probability': div.success_probability,
                    'angle_difference': div.angle_difference,
                    'invalidated': div.invalidated,
                    'price_points': [
                        {'index': p.index, 'price': p.price} for p in div.price_points
                    ],
                    'indicator_points': [
                        {'index': p.index, 'value': p.indicator_value} for p in div.indicator_points
                    ]
                }
                for div in analysis.hidden_divergences
            ],
            'dominant_divergence': {
                'type': analysis.dominant_divergence.type,
                'indicator': analysis.dominant_divergence.indicator,
                'strength': analysis.dominant_divergence.strength,
                'class_rating': analysis.dominant_divergence.class_rating,
                'success_probability': analysis.dominant_divergence.success_probability
            } if analysis.dominant_divergence else None,
            'next_targets': analysis.next_targets,
            'invalidation_levels': analysis.invalidation_levels
        }
        
        return result
        
    except Exception as e:
        logger.error(f"Divergence analiz wrapper hatası: {e}")
        return {
            'status': 'error',
            'message': str(e)
        }