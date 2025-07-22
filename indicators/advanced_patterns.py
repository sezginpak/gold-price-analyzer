"""
Gelişmiş Chart Pattern Tanıma
Head & Shoulders, Double Top/Bottom ve diğer önemli pattern'leri tanır
Altın ticareti için %85 başarı oranına sahip Head & Shoulders pattern'i dahil
"""

import pandas as pd
import numpy as np
from typing import List, Dict, Optional, Tuple
from decimal import Decimal
import logging
from scipy.signal import find_peaks
import warnings
warnings.filterwarnings('ignore')

logger = logging.getLogger(__name__)


class AdvancedPatternRecognition:
    """
    Gelişmiş pattern tanıma sınıfı
    Head & Shoulders, Double Top/Bottom, Cup & Handle gibi pattern'leri tanır
    """
    
    def __init__(self):
        """Pattern tanıma için başlangıç parametreleri"""
        # Pattern doğrulama için toleranslar
        self.shoulder_tolerance = 0.02  # Omuzlar arası %2 tolerans
        self.neckline_tolerance = 0.01  # Neckline kırılması için %1
        self.volume_confirmation = 1.2   # Volume artışı çarpanı
        
    def find_local_extremes(self, prices: pd.Series, window: int = 5) -> Tuple[np.ndarray, np.ndarray]:
        """
        Yerel maksimum ve minimum noktaları bul
        
        Args:
            prices: Fiyat serisi
            window: Ekstrem noktalar için pencere boyutu
            
        Returns:
            (peaks_indices, valleys_indices) tuple'ı
        """
        try:
            # Scipy kullanarak peak'leri bul
            peaks, _ = find_peaks(prices.values, distance=window)
            valleys, _ = find_peaks(-prices.values, distance=window)
            
            return peaks, valleys
            
        except Exception as e:
            logger.error(f"Ekstrem nokta bulma hatası: {str(e)}")
            return np.array([]), np.array([])
    
    def detect_head_and_shoulders(self, df: pd.DataFrame, lookback: int = 50) -> Optional[Dict]:
        """
        Head and Shoulders pattern'i tanı
        %85 başarı oranıyla en güvenilir pattern
        
        Args:
            df: OHLC verilerini içeren DataFrame
            lookback: Geriye bakış periyodu
            
        Returns:
            Pattern bulunduysa detay dictionary, bulunamadıysa None
        """
        try:
            if len(df) < lookback:
                return None
            
            # Son lookback periyodunu al
            recent_data = df.iloc[-lookback:].copy()
            prices = recent_data['high'].values
            
            # Yerel maksimumları bul (potansiyel omuzlar ve baş)
            peaks, valleys = self.find_local_extremes(recent_data['high'], window=5)
            
            if len(peaks) < 3:
                return None
            
            # Son 3 peak'i kontrol et (sağ omuz, baş, sol omuz)
            for i in range(len(peaks) - 2):
                left_shoulder_idx = peaks[i]
                head_idx = peaks[i + 1]
                right_shoulder_idx = peaks[i + 2]
                
                left_shoulder = prices[left_shoulder_idx]
                head = prices[head_idx]
                right_shoulder = prices[right_shoulder_idx]
                
                # Head & Shoulders kriterleri
                # 1. Baş her iki omuzdan da yüksek olmalı
                if head <= left_shoulder or head <= right_shoulder:
                    continue
                
                # 2. Omuzlar birbirine yakın seviyede olmalı (tolerans dahilinde)
                shoulder_diff = abs(left_shoulder - right_shoulder) / left_shoulder
                if shoulder_diff > self.shoulder_tolerance:
                    continue
                
                # Neckline hesapla (omuzlar arasındaki en düşük nokta)
                neckline_start = valleys[valleys > left_shoulder_idx][0] if any(valleys > left_shoulder_idx) else left_shoulder_idx + 1
                neckline_end = valleys[valleys > head_idx][0] if any(valleys > head_idx) else head_idx + 1
                
                if neckline_end >= len(prices) - 1:
                    continue
                
                neckline_level = min(prices[neckline_start], prices[neckline_end])
                
                # Pattern yüksekliği (kar hedefi için)
                pattern_height = head - neckline_level
                
                # Mevcut fiyat neckline'ı kırdı mı?
                current_price = recent_data['close'].iloc[-1]
                neckline_break = current_price < neckline_level * (1 - self.neckline_tolerance)
                
                # Volume kontrolü (opsiyonel)
                volume_confirmed = True
                if 'volume' in df.columns and df['volume'].sum() > 0:
                    head_volume = recent_data['volume'].iloc[head_idx]
                    avg_volume = recent_data['volume'].mean()
                    volume_confirmed = head_volume > avg_volume * self.volume_confirmation
                
                # Pattern tamamlanma yüzdesi
                if neckline_break:
                    completion = 100
                else:
                    distance_to_neckline = (current_price - neckline_level) / pattern_height
                    completion = max(0, min(95, (1 - distance_to_neckline) * 100))
                
                return {
                    'pattern': 'HEAD_AND_SHOULDERS',
                    'type': 'BEARISH',
                    'confidence': 0.85 if volume_confirmed else 0.75,
                    'neckline': round(neckline_level, 2),
                    'target': round(neckline_level - pattern_height, 2),  # Kar hedefi
                    'stop_loss': round(head * 1.01, 2),  # Başın %1 üstü
                    'completion': round(completion, 1),
                    'neckline_break': neckline_break,
                    'volume_confirmed': volume_confirmed,
                    'left_shoulder': {
                        'price': round(left_shoulder, 2),
                        'index': int(left_shoulder_idx)
                    },
                    'head': {
                        'price': round(head, 2),
                        'index': int(head_idx)
                    },
                    'right_shoulder': {
                        'price': round(right_shoulder, 2),
                        'index': int(right_shoulder_idx)
                    }
                }
            
            # Inverse Head & Shoulders kontrolü (Bullish pattern)
            valleys_inv, peaks_inv = self.find_local_extremes(recent_data['low'], window=5)
            
            if len(valleys_inv) >= 3:
                for i in range(len(valleys_inv) - 2):
                    left_shoulder_idx = valleys_inv[i]
                    head_idx = valleys_inv[i + 1]
                    right_shoulder_idx = valleys_inv[i + 2]
                    
                    left_shoulder = recent_data['low'].iloc[left_shoulder_idx]
                    head = recent_data['low'].iloc[head_idx]
                    right_shoulder = recent_data['low'].iloc[right_shoulder_idx]
                    
                    # Inverse H&S kriterleri
                    if head >= left_shoulder or head >= right_shoulder:
                        continue
                    
                    shoulder_diff = abs(left_shoulder - right_shoulder) / left_shoulder
                    if shoulder_diff > self.shoulder_tolerance:
                        continue
                    
                    # Neckline (tepeler arası en yüksek nokta)
                    neckline_level = max(
                        recent_data['high'].iloc[left_shoulder_idx:head_idx].max(),
                        recent_data['high'].iloc[head_idx:right_shoulder_idx].max()
                    )
                    
                    pattern_height = neckline_level - head
                    current_price = recent_data['close'].iloc[-1]
                    neckline_break = current_price > neckline_level * (1 + self.neckline_tolerance)
                    
                    if neckline_break:
                        completion = 100
                    else:
                        distance_to_neckline = (neckline_level - current_price) / pattern_height
                        completion = max(0, min(95, (1 - distance_to_neckline) * 100))
                    
                    return {
                        'pattern': 'INVERSE_HEAD_AND_SHOULDERS',
                        'type': 'BULLISH',
                        'confidence': 0.85,
                        'neckline': round(neckline_level, 2),
                        'target': round(neckline_level + pattern_height, 2),
                        'stop_loss': round(head * 0.99, 2),
                        'completion': round(completion, 1),
                        'neckline_break': neckline_break
                    }
            
            return None
            
        except Exception as e:
            logger.error(f"Head & Shoulders tanıma hatası: {str(e)}")
            return None
    
    def detect_double_patterns(self, df: pd.DataFrame, lookback: int = 30) -> Optional[Dict]:
        """
        Double Top ve Double Bottom pattern'lerini tanı
        
        Args:
            df: OHLC verilerini içeren DataFrame
            lookback: Geriye bakış periyodu
            
        Returns:
            Pattern bulunduysa detay dictionary
        """
        try:
            if len(df) < lookback:
                return None
            
            recent_data = df.iloc[-lookback:].copy()
            
            # Double Top kontrolü
            peaks, _ = self.find_local_extremes(recent_data['high'], window=5)
            if len(peaks) >= 2:
                # Son iki peak'i kontrol et
                peak1_idx = peaks[-2]
                peak2_idx = peaks[-1]
                peak1 = recent_data['high'].iloc[peak1_idx]
                peak2 = recent_data['high'].iloc[peak2_idx]
                
                # İki zirve birbirine yakın mı?
                if abs(peak1 - peak2) / peak1 < 0.03:  # %3 tolerans
                    # Aralarındaki dip
                    valley_between = recent_data['low'].iloc[peak1_idx:peak2_idx].min()
                    pattern_height = ((peak1 + peak2) / 2) - valley_between
                    
                    current_price = recent_data['close'].iloc[-1]
                    pattern_break = current_price < valley_between
                    
                    return {
                        'pattern': 'DOUBLE_TOP',
                        'type': 'BEARISH',
                        'confidence': 0.75,
                        'resistance': round((peak1 + peak2) / 2, 2),
                        'support': round(valley_between, 2),
                        'target': round(valley_between - pattern_height, 2),
                        'stop_loss': round(max(peak1, peak2) * 1.01, 2),
                        'pattern_break': pattern_break
                    }
            
            # Double Bottom kontrolü
            _, valleys = self.find_local_extremes(recent_data['low'], window=5)
            if len(valleys) >= 2:
                valley1_idx = valleys[-2]
                valley2_idx = valleys[-1]
                valley1 = recent_data['low'].iloc[valley1_idx]
                valley2 = recent_data['low'].iloc[valley2_idx]
                
                if abs(valley1 - valley2) / valley1 < 0.03:
                    peak_between = recent_data['high'].iloc[valley1_idx:valley2_idx].max()
                    pattern_height = peak_between - ((valley1 + valley2) / 2)
                    
                    current_price = recent_data['close'].iloc[-1]
                    pattern_break = current_price > peak_between
                    
                    return {
                        'pattern': 'DOUBLE_BOTTOM',
                        'type': 'BULLISH',
                        'confidence': 0.75,
                        'support': round((valley1 + valley2) / 2, 2),
                        'resistance': round(peak_between, 2),
                        'target': round(peak_between + pattern_height, 2),
                        'stop_loss': round(min(valley1, valley2) * 0.99, 2),
                        'pattern_break': pattern_break
                    }
            
            return None
            
        except Exception as e:
            logger.error(f"Double pattern tanıma hatası: {str(e)}")
            return None
    
    def analyze_all_patterns(self, df: pd.DataFrame) -> Dict:
        """
        Tüm pattern'leri analiz et ve en güçlüsünü döndür
        
        Args:
            df: OHLC verilerini içeren DataFrame
            
        Returns:
            Bulunan pattern'ler ve analiz sonuçları
        """
        try:
            patterns = []
            
            # Head & Shoulders kontrolü
            hs_pattern = self.detect_head_and_shoulders(df)
            if hs_pattern:
                patterns.append(hs_pattern)
            
            # Double patterns kontrolü
            double_pattern = self.detect_double_patterns(df)
            if double_pattern:
                patterns.append(double_pattern)
            
            # En yüksek confidence'a sahip pattern'i seç
            if patterns:
                best_pattern = max(patterns, key=lambda x: x['confidence'])
                
                return {
                    'pattern_found': True,
                    'best_pattern': best_pattern,
                    'all_patterns': patterns,
                    'signal': best_pattern['type'],
                    'confidence': best_pattern['confidence']
                }
            else:
                return {
                    'pattern_found': False,
                    'best_pattern': None,
                    'all_patterns': [],
                    'signal': 'NEUTRAL',
                    'confidence': 0.0
                }
                
        except Exception as e:
            logger.error(f"Pattern analizi hatası: {str(e)}")
            return {
                'pattern_found': False,
                'best_pattern': None,
                'all_patterns': [],
                'signal': 'NEUTRAL',
                'confidence': 0.0
            }