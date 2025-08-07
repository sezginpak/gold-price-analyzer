"""
Fibonacci Retracement Module
Otomatik swing high/low tespiti ve Fibonacci seviyeleri hesaplama
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from scipy.signal import argrelextrema
from utils.logger import logger


@dataclass
class FibonacciLevel:
    """Fibonacci seviye bilgisi"""
    level: float  # 0.236, 0.382, 0.5, 0.618, 0.786
    price: float
    strength: str  # "weak", "medium", "strong", "very_strong"
    description: str


class FibonacciRetracement:
    """Fibonacci Retracement analizi"""
    
    # Fibonacci seviyeleri ve güç dereceleri
    FIBONACCI_LEVELS = {
        0.0: ("very_strong", "Başlangıç Seviyesi"),
        0.236: ("medium", "%23.6 Retracement"),
        0.382: ("strong", "%38.2 Retracement - Altın Oran"),
        0.5: ("strong", "%50 Retracement - Psikolojik Seviye"),
        0.618: ("very_strong", "%61.8 Retracement - Altın Oran"),
        0.786: ("medium", "%78.6 Retracement"),
        1.0: ("very_strong", "%100 Seviyesi"),
        1.272: ("medium", "%127.2 Extension"),
        1.618: ("strong", "%161.8 Extension - Altın Oran"),
        2.0: ("medium", "%200 Extension"),
        2.618: ("medium", "%261.8 Extension")
    }
    
    def __init__(self):
        """Fibonacci Retracement başlatıcı"""
        self.last_swing_high = None
        self.last_swing_low = None
        self.current_trend = None
        self.fib_levels = {}
        
    def find_swing_points(
        self, 
        df: pd.DataFrame, 
        window: int = 10,
        min_swing_strength: float = 0.001
    ) -> Dict[str, List[Tuple[int, float]]]:
        """
        Swing high ve low noktalarını bul
        
        Args:
            df: OHLC verisi
            window: Swing point pencere boyutu
            min_swing_strength: Minimum swing güç eşiği
            
        Returns:
            Swing points dictionary
        """
        try:
            if len(df) < window * 2:
                return {'highs': [], 'lows': []}
                
            highs = df['high'].values
            lows = df['low'].values
            
            # Local extrema bulma
            high_indices = argrelextrema(highs, np.greater, order=window)[0]
            low_indices = argrelextrema(lows, np.less, order=window)[0]
            
            # Güç filtreleme
            swing_highs = []
            for idx in high_indices:
                if idx < window or idx >= len(highs) - window:
                    continue
                    
                # Swing strength hesapla (daha basit yaklaşım)
                left_max = np.max(highs[idx-window:idx])
                right_max = np.max(highs[idx+1:idx+window+1])
                current_high = highs[idx]
                
                # Current high, çevre değerlerden yüksekse swing high
                if current_high > left_max and current_high > right_max:
                    # Strength hesapla
                    strength = min(
                        (current_high - left_max) / current_high,
                        (current_high - right_max) / current_high
                    )
                    
                    if strength >= min_swing_strength:
                        swing_highs.append((idx, current_high))
            
            swing_lows = []
            for idx in low_indices:
                if idx < window or idx >= len(lows) - window:
                    continue
                    
                # Swing strength hesapla (daha basit yaklaşım)
                left_min = np.min(lows[idx-window:idx])
                right_min = np.min(lows[idx+1:idx+window+1])
                current_low = lows[idx]
                
                # Current low, çevre değerlerden düşükse swing low
                if current_low < left_min and current_low < right_min:
                    # Strength hesapla
                    strength = min(
                        (left_min - current_low) / current_low,
                        (right_min - current_low) / current_low
                    )
                    
                    if strength >= min_swing_strength:
                        swing_lows.append((idx, current_low))
            
            return {
                'highs': swing_highs,
                'lows': swing_lows
            }
            
        except Exception as e:
            logger.error(f"Swing point bulma hatası: {e}")
            return {'highs': [], 'lows': []}
    
    def calculate_fibonacci_levels(
        self, 
        high: float, 
        low: float,
        trend: str = "up"
    ) -> Dict[float, FibonacciLevel]:
        """
        Fibonacci seviyelerini hesapla
        
        Args:
            high: Swing high değeri
            low: Swing low değeri
            trend: Trend yönü ("up" veya "down")
            
        Returns:
            Fibonacci seviyeleri
        """
        try:
            range_size = high - low
            levels = {}
            
            for ratio, (strength, desc) in self.FIBONACCI_LEVELS.items():
                if trend == "up":
                    # Uptrend'de retracement seviyeleri
                    if ratio <= 1.0:
                        price = high - (range_size * ratio)
                    else:
                        # Extension seviyeleri
                        price = high + (range_size * (ratio - 1.0))
                else:
                    # Downtrend'de retracement seviyeleri
                    if ratio <= 1.0:
                        price = low + (range_size * ratio)
                    else:
                        # Extension seviyeleri
                        price = low - (range_size * (ratio - 1.0))
                
                levels[ratio] = FibonacciLevel(
                    level=ratio,
                    price=price,
                    strength=strength,
                    description=desc
                )
            
            return levels
            
        except Exception as e:
            logger.error(f"Fibonacci seviye hesaplama hatası: {e}")
            return {}
    
    def identify_trend(self, df: pd.DataFrame) -> str:
        """
        Mevcut trendi belirle
        
        Args:
            df: OHLC verisi
            
        Returns:
            Trend yönü ("up", "down", "sideways")
        """
        try:
            if len(df) < 20:
                return "sideways"
            
            # Son mumlar için trend analizi
            recent_df = df.tail(min(50, len(df)))
            
            # Moving average bazlı trend
            ma_short = recent_df['close'].rolling(window=min(10, len(recent_df))).mean()
            ma_long = recent_df['close'].rolling(window=min(20, len(recent_df))).mean()
            
            current_price = recent_df['close'].iloc[-1]
            
            # MA'lar hesaplanabilirse
            if len(ma_short.dropna()) > 0 and len(ma_long.dropna()) > 0:
                ma_short_current = ma_short.iloc[-1]
                ma_long_current = ma_long.iloc[-1]
                
                # Trend kriteri (tolerance ile)
                trend_threshold = 0.002  # %0.2 threshold
                
                if (current_price > ma_short_current * (1 + trend_threshold) and 
                    ma_short_current > ma_long_current * (1 + trend_threshold)):
                    return "up"
                elif (current_price < ma_short_current * (1 - trend_threshold) and 
                      ma_short_current < ma_long_current * (1 - trend_threshold)):
                    return "down"
                else:
                    return "sideways"
            else:
                # Basit slope analizi
                first_price = recent_df['close'].iloc[0]
                last_price = recent_df['close'].iloc[-1]
                price_change = (last_price - first_price) / first_price
                
                if price_change > 0.01:  # %1'den fazla yükselmiş
                    return "up"
                elif price_change < -0.01:  # %1'den fazla düşmüş
                    return "down"
                else:
                    return "sideways"
                
        except Exception as e:
            logger.error(f"Trend belirleme hatası: {e}")
            return "sideways"
    
    def get_nearest_fibonacci_level(
        self, 
        current_price: float,
        tolerance: float = 0.002
    ) -> Optional[FibonacciLevel]:
        """
        Mevcut fiyata en yakın Fibonacci seviyesini bul
        
        Args:
            current_price: Mevcut fiyat
            tolerance: Yakınlık toleransı (%)
            
        Returns:
            En yakın Fibonacci seviyesi
        """
        try:
            if not self.fib_levels:
                return None
            
            nearest_level = None
            min_distance = float('inf')
            
            for level in self.fib_levels.values():
                distance = abs(current_price - level.price) / current_price
                
                if distance < tolerance and distance < min_distance:
                    min_distance = distance
                    nearest_level = level
            
            return nearest_level
            
        except Exception as e:
            logger.error(f"En yakın Fibonacci seviye bulma hatası: {e}")
            return None
    
    def analyze(self, df: pd.DataFrame) -> Dict:
        """
        Fibonacci analizi yap
        
        Args:
            df: OHLC verisi
            
        Returns:
            Analiz sonuçları
        """
        try:
            if len(df) < 50:
                return {
                    'status': 'insufficient_data',
                    'message': 'Fibonacci analizi için yetersiz veri'
                }
            
            # Swing points bul
            swings = self.find_swing_points(df)
            
            if not swings['highs'] or not swings['lows']:
                return {
                    'status': 'no_swings',
                    'message': 'Swing point bulunamadı'
                }
            
            # Son swing high ve low
            last_high_idx, last_high_price = swings['highs'][-1]
            last_low_idx, last_low_price = swings['lows'][-1]
            
            # Trend belirle
            self.current_trend = self.identify_trend(df)
            
            # Hangi swing daha yeni?
            if last_high_idx > last_low_idx:
                # Son hareket yukarı, retracement down bekle
                self.last_swing_high = last_high_price
                self.last_swing_low = last_low_price
                fib_trend = "down"  # Retracement için
            else:
                # Son hareket aşağı, retracement up bekle
                self.last_swing_high = last_high_price
                self.last_swing_low = last_low_price
                fib_trend = "up"  # Retracement için
            
            # Fibonacci seviyelerini hesapla
            self.fib_levels = self.calculate_fibonacci_levels(
                self.last_swing_high,
                self.last_swing_low,
                fib_trend
            )
            
            # Mevcut fiyat analizi
            current_price = df['close'].iloc[-1]
            nearest_level = self.get_nearest_fibonacci_level(current_price)
            
            # Fibonacci bounce potansiyeli
            bounce_potential = self._calculate_bounce_potential(
                current_price,
                nearest_level,
                self.current_trend
            )
            
            # Sonuçları hazırla - tüm numpy değerleri Python tiplerini çevir
            result = {
                'status': 'success',
                'trend': str(self.current_trend),
                'swing_high': float(self.last_swing_high),
                'swing_low': float(self.last_swing_low),
                'range': float(self.last_swing_high - self.last_swing_low),
                'current_price': float(current_price),
                'fibonacci_levels': {
                    f"{k:.3f}": {
                        'price': float(v.price),
                        'strength': str(v.strength),  # strength bir string olarak tanımlanmış
                        'description': str(v.description),
                        'distance_pct': float(abs(current_price - v.price) / current_price * 100)
                    }
                    for k, v in self.fib_levels.items()
                },
                'nearest_level': {
                    'level': float(nearest_level.level) if nearest_level else None,
                    'price': float(nearest_level.price) if nearest_level else None,
                    'strength': str(nearest_level.strength) if nearest_level else None,  # strength bir string
                    'description': str(nearest_level.description) if nearest_level else None
                } if nearest_level else None,
                'bounce_potential': float(bounce_potential),
                'signals': {
                    k: float(v) if isinstance(v, (int, float, np.number)) and not isinstance(v, bool)
                    else bool(v) if isinstance(v, (bool, np.bool_))
                    else [float(x) if isinstance(x, (int, float, np.number)) and not isinstance(x, bool) else str(x) for x in v] if isinstance(v, list)
                    else str(v) for k, v in self._generate_fibonacci_signals(
                        current_price,
                        nearest_level,
                        bounce_potential,
                        self.current_trend
                    ).items()
                }
            }
            
            return result
            
        except Exception as e:
            logger.error(f"Fibonacci analiz hatası: {e}")
            return {
                'status': 'error',
                'message': str(e)
            }
    
    def _calculate_bounce_potential(
        self,
        current_price: float,
        nearest_level: Optional[FibonacciLevel],
        trend: str
    ) -> float:
        """
        Fibonacci seviyesinden dönüş potansiyelini hesapla
        
        Returns:
            Bounce potansiyeli (0-100)
        """
        try:
            if not nearest_level:
                return 0.0
            
            potential = 0.0
            
            # Seviye gücüne göre base potential
            strength_scores = {
                "very_strong": 40,
                "strong": 30,
                "medium": 20,
                "weak": 10
            }
            potential += strength_scores.get(nearest_level.strength, 0)
            
            # Altın oran seviyeleri bonus
            golden_ratios = [0.382, 0.618, 1.618]
            if any(abs(nearest_level.level - gr) < 0.01 for gr in golden_ratios):
                potential += 20
            
            # %50 psikolojik seviye bonus
            if abs(nearest_level.level - 0.5) < 0.01:
                potential += 15
            
            # Trend uyumu
            if trend == "up" and nearest_level.level <= 0.618:
                potential += 15  # Uptrend'de derin retracement = güçlü alım fırsatı
            elif trend == "down" and nearest_level.level >= 0.382:
                potential += 15  # Downtrend'de shallow retracement = güçlü satım fırsatı
            
            # Fiyat yakınlığı (ne kadar yakınsa o kadar güçlü)
            distance_pct = abs(current_price - nearest_level.price) / current_price
            if distance_pct < 0.001:  # %0.1'den yakın
                potential += 10
            elif distance_pct < 0.003:  # %0.3'ten yakın
                potential += 5
            
            return min(potential, 100.0)
            
        except Exception as e:
            logger.error(f"Bounce potential hesaplama hatası: {e}")
            return 0.0
    
    def _generate_fibonacci_signals(
        self,
        current_price: float,
        nearest_level: Optional[FibonacciLevel],
        bounce_potential: float,
        trend: str
    ) -> Dict:
        """
        Fibonacci bazlı trading sinyalleri üret
        
        Returns:
            Trading sinyalleri
        """
        try:
            signals = {
                'action': 'WAIT',
                'strength': 0,
                'reason': [],
                'target_levels': [],
                'stop_level': None
            }
            
            if not nearest_level:
                return signals
            
            # Güçlü seviyeye yaklaşma
            if bounce_potential >= 60:
                if trend == "up" and nearest_level.level <= 0.618:
                    signals['action'] = 'BUY'
                    signals['strength'] = bounce_potential
                    signals['reason'].append(f"{nearest_level.description} seviyesinde güçlü destek")
                    
                    # Target seviyeleri
                    if nearest_level.level <= 0.382:
                        signals['target_levels'] = [
                            self.fib_levels[0.0].price,  # %100 seviyesi
                            self.fib_levels[1.272].price if 1.272 in self.fib_levels else None
                        ]
                    else:
                        signals['target_levels'] = [self.fib_levels[0.236].price]
                    
                    # Stop seviyesi
                    signals['stop_level'] = self.fib_levels[0.786].price if 0.786 in self.fib_levels else self.last_swing_low
                    
                elif trend == "down" and nearest_level.level >= 0.382:
                    signals['action'] = 'SELL'
                    signals['strength'] = bounce_potential
                    signals['reason'].append(f"{nearest_level.description} seviyesinde güçlü direnç")
                    
                    # Target seviyeleri
                    if nearest_level.level >= 0.618:
                        signals['target_levels'] = [
                            self.fib_levels[1.0].price,  # %0 seviyesi
                            self.fib_levels[1.272].price if 1.272 in self.fib_levels else None
                        ]
                    else:
                        signals['target_levels'] = [self.fib_levels[0.786].price]
                    
                    # Stop seviyesi
                    signals['stop_level'] = self.fib_levels[0.236].price if 0.236 in self.fib_levels else self.last_swing_high
            
            # Orta güçte sinyal
            elif bounce_potential >= 40:
                signals['action'] = 'WATCH'
                signals['strength'] = bounce_potential
                signals['reason'].append(f"{nearest_level.description} seviyesi test ediliyor")
            
            return signals
            
        except Exception as e:
            logger.error(f"Fibonacci sinyal üretme hatası: {e}")
            return {
                'action': 'WAIT',
                'strength': 0,
                'reason': ['Sinyal üretme hatası'],
                'target_levels': [],
                'stop_level': None
            }


def calculate_fibonacci_analysis(df: pd.DataFrame) -> Dict:
    """
    Fibonacci retracement analizi yap
    
    Args:
        df: OHLC verisi
        
    Returns:
        Fibonacci analiz sonuçları
    """
    try:
        analyzer = FibonacciRetracement()
        return analyzer.analyze(df)
    except Exception as e:
        logger.error(f"Fibonacci analiz hatası: {e}")
        return {
            'status': 'error',
            'message': str(e)
        }