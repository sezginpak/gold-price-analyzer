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
import warnings
warnings.filterwarnings('ignore')

# Scipy opsiyonel - yoksa basit implementasyon kullan
try:
    from scipy.signal import find_peaks
    HAS_SCIPY = True
except ImportError:
    HAS_SCIPY = False
    # Basit peak bulma fonksiyonu
    def find_peaks(data, **kwargs):
        """Scipy olmadan basit peak bulma"""
        peaks = []
        distance = kwargs.get('distance', 5)
        
        for i in range(1, len(data) - 1):
            if i < distance or i >= len(data) - distance:
                continue
                
            # Local maximum kontrolü
            is_peak = True
            for j in range(max(0, i - distance), min(len(data), i + distance)):
                if j != i and data[j] >= data[i]:
                    is_peak = False
                    break
            
            if is_peak:
                peaks.append(i)
        
        return (peaks,)

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
    
    def detect_bollinger_squeeze(self, df: pd.DataFrame, period: int = 20) -> Dict:
        """
        Bollinger Band Squeeze detector - büyük hareket öncesi sıkışma
        
        Args:
            df: OHLC verilerini içeren DataFrame
            period: Bollinger Bands periyodu
            
        Returns:
            Squeeze analizi
        """
        try:
            if len(df) < period + 5:
                return {"detected": False, "strength": 0}
            
            # Bollinger Bands hesapla
            close_prices = df['close'].rolling(window=period).mean()
            std_dev = df['close'].rolling(window=period).std()
            
            upper_band = close_prices + (std_dev * 2)
            lower_band = close_prices - (std_dev * 2)
            band_width = (upper_band - lower_band) / close_prices
            
            # Mevcut band genişliği
            current_width = band_width.iloc[-1] if not pd.isna(band_width.iloc[-1]) else 0
            
            # Son 50 periyodun ortalama band genişliği
            lookback = min(50, len(band_width) - period)
            if lookback > 0:
                avg_width = band_width.iloc[-lookback:-1].mean()
                
                # Squeeze tespiti: Mevcut genişlik ortalamadan %20 daha dar
                squeeze_detected = current_width < (avg_width * 0.8)
                squeeze_strength = (avg_width - current_width) / avg_width if avg_width > 0 else 0
                
                # Fiyat orta banda ne kadar yakın?
                current_price = df['close'].iloc[-1]
                middle_band = close_prices.iloc[-1]
                price_distance = abs(current_price - middle_band) / middle_band if middle_band > 0 else 0
                
                return {
                    "detected": squeeze_detected,
                    "strength": min(squeeze_strength, 1.0),
                    "current_width": current_width,
                    "average_width": avg_width,
                    "price_to_middle": price_distance,
                    "ready_for_breakout": squeeze_detected and price_distance < 0.005  # %0.5'ten yakın
                }
            else:
                return {"detected": False, "strength": 0}
                
        except Exception as e:
            logger.error(f"Bollinger squeeze tespiti hatası: {str(e)}")
            return {"detected": False, "strength": 0}
    
    def analyze_macd_histogram_momentum(self, df: pd.DataFrame) -> Dict:
        """
        MACD Histogram momentum analizi - erken trend değişimi tespiti
        
        Args:
            df: OHLC verilerini içeren DataFrame
            
        Returns:
            MACD histogram momentum analizi
        """
        try:
            if len(df) < 26:
                return {"momentum": "NEUTRAL", "strength": 0, "divergence": False}
            
            # MACD hesapla
            close_prices = df['close']
            exp1 = close_prices.ewm(span=12).mean()
            exp2 = close_prices.ewm(span=26).mean()
            macd_line = exp1 - exp2
            signal_line = macd_line.ewm(span=9).mean()
            histogram = macd_line - signal_line
            
            if len(histogram) < 5:
                return {"momentum": "NEUTRAL", "strength": 0, "divergence": False}
            
            # Son 5 histogram değeri
            recent_hist = histogram.iloc[-5:].values
            
            # Momentum yönü
            momentum_change = recent_hist[-1] - recent_hist[0]
            momentum_strength = abs(momentum_change)
            
            # Histogram trend
            if momentum_change > 0.1:
                momentum = "BULLISH"
            elif momentum_change < -0.1:
                momentum = "BEARISH"
            else:
                momentum = "NEUTRAL"
            
            # Divergence kontrolü (basit)
            price_trend = df['close'].iloc[-5:].diff().sum()
            histogram_trend = histogram.iloc[-5:].diff().sum()
            
            # Fiyat ve histogram zıt yönde mi?
            divergence_detected = (price_trend > 0 and histogram_trend < 0) or \
                                (price_trend < 0 and histogram_trend > 0)
            
            # Zero line cross kontrolü
            zero_cross = None
            if len(recent_hist) >= 2:
                if recent_hist[-2] <= 0 and recent_hist[-1] > 0:
                    zero_cross = "BULLISH"
                elif recent_hist[-2] >= 0 and recent_hist[-1] < 0:
                    zero_cross = "BEARISH"
            
            return {
                "momentum": momentum,
                "strength": min(momentum_strength * 10, 1.0),  # 0-1 arası normalize
                "divergence": divergence_detected,
                "zero_cross": zero_cross,
                "current_histogram": recent_hist[-1],
                "histogram_trend": histogram_trend
            }
            
        except Exception as e:
            logger.error(f"MACD histogram analizi hatası: {str(e)}")
            return {"momentum": "NEUTRAL", "strength": 0, "divergence": False}
    
    def analyze_volume_price_action(self, df: pd.DataFrame) -> Dict:
        """
        Volume Price Analysis (VPA) - Volume ve fiyat ilişkisi
        
        Args:
            df: OHLC ve volume verilerini içeren DataFrame
            
        Returns:
            VPA analizi
        """
        try:
            if 'volume' not in df.columns or len(df) < 10:
                return {"analysis": "NO_DATA", "signal": "NEUTRAL", "strength": 0}
            
            # Son 10 mumun analizi
            recent_data = df.iloc[-10:].copy()
            
            if recent_data['volume'].sum() == 0:
                return {"analysis": "NO_VOLUME_DATA", "signal": "NEUTRAL", "strength": 0}
            
            # Volume ve fiyat değişimi
            price_changes = recent_data['close'].pct_change().iloc[-5:]
            volume_changes = recent_data['volume'].pct_change().iloc[-5:]
            
            # VPA kuralları
            vpa_signals = []
            
            for i in range(len(price_changes)):
                if pd.isna(price_changes.iloc[i]) or pd.isna(volume_changes.iloc[i]):
                    continue
                    
                price_change = price_changes.iloc[i]
                volume_change = volume_changes.iloc[i]
                
                # Yüksek volume + yüksek fiyat artışı = güçlü alım
                if price_change > 0.01 and volume_change > 0.2:
                    vpa_signals.append("STRONG_BUYING")
                # Düşük volume + fiyat artışı = zayıf alım (dikkat)
                elif price_change > 0.01 and volume_change < -0.2:
                    vpa_signals.append("WEAK_BUYING")
                # Yüksek volume + fiyat düşüşü = güçlü satım
                elif price_change < -0.01 and volume_change > 0.2:
                    vpa_signals.append("STRONG_SELLING")
                # Düşük volume + fiyat düşüşü = zayıf satım (dip sinyali?)
                elif price_change < -0.01 and volume_change < -0.2:
                    vpa_signals.append("WEAK_SELLING")
            
            # Genel sinyal
            if vpa_signals.count("STRONG_BUYING") > 2:
                signal = "BULLISH"
                strength = 0.8
            elif vpa_signals.count("WEAK_SELLING") > 2:
                signal = "BULLISH"  # Zayıf satış = dip fırsatı
                strength = 0.6
            elif vpa_signals.count("STRONG_SELLING") > 2:
                signal = "BEARISH"
                strength = 0.8
            elif vpa_signals.count("WEAK_BUYING") > 2:
                signal = "BEARISH"  # Zayıf alım = tepe sinyali
                strength = 0.6
            else:
                signal = "NEUTRAL"
                strength = 0.3
            
            return {
                "analysis": "COMPLETED",
                "signal": signal,
                "strength": strength,
                "vpa_signals": vpa_signals,
                "dominant_pattern": max(set(vpa_signals), key=vpa_signals.count) if vpa_signals else "NEUTRAL"
            }
            
        except Exception as e:
            logger.error(f"VPA analizi hatası: {str(e)}")
            return {"analysis": "ERROR", "signal": "NEUTRAL", "strength": 0}
    
    def comprehensive_pattern_analysis(self, df: pd.DataFrame) -> Dict:
        """
        Kapsamlı pattern analizi - tüm teknikleri birleştir
        
        Args:
            df: OHLC verilerini içeren DataFrame
            
        Returns:
            Birleşik pattern analizi
        """
        try:
            # Tüm analizleri yap
            traditional_patterns = self.analyze_all_patterns(df)
            bollinger_squeeze = self.detect_bollinger_squeeze(df)
            macd_momentum = self.analyze_macd_histogram_momentum(df)
            vpa_analysis = self.analyze_volume_price_action(df)
            
            # Birleşik skor hesapla
            total_score = 0
            signal_count = {"BULLISH": 0, "BEARISH": 0, "NEUTRAL": 0}
            
            # Geleneksel pattern'ler (en yüksek ağırlık)
            if traditional_patterns['pattern_found']:
                pattern_signal = traditional_patterns['signal']
                pattern_confidence = traditional_patterns['confidence']
                signal_count[pattern_signal] += pattern_confidence * 0.4
                total_score += 0.4
            
            # Bollinger Squeeze (patlama sinyali)
            if bollinger_squeeze.get('ready_for_breakout'):
                squeeze_strength = bollinger_squeeze.get('strength', 0)
                signal_count["NEUTRAL"] += squeeze_strength * 0.2  # Nötral ama hazır
                total_score += 0.2
            
            # MACD Momentum
            macd_signal = macd_momentum.get('momentum', 'NEUTRAL')
            macd_strength = macd_momentum.get('strength', 0)
            signal_count[macd_signal] += macd_strength * 0.25
            total_score += 0.25
            
            # VPA Analysis
            vpa_signal = vpa_analysis.get('signal', 'NEUTRAL')
            vpa_strength = vpa_analysis.get('strength', 0)
            signal_count[vpa_signal] += vpa_strength * 0.15
            total_score += 0.15
            
            # En güçlü sinyali belirle
            if total_score > 0:
                dominant_signal = max(signal_count.keys(), key=lambda k: signal_count[k])
                final_confidence = signal_count[dominant_signal] / total_score
            else:
                dominant_signal = "NEUTRAL"
                final_confidence = 0
            
            return {
                "final_signal": dominant_signal,
                "final_confidence": min(final_confidence, 1.0),
                "components": {
                    "traditional_patterns": traditional_patterns,
                    "bollinger_squeeze": bollinger_squeeze,
                    "macd_momentum": macd_momentum,
                    "vpa_analysis": vpa_analysis
                },
                "signal_breakdown": signal_count,
                "total_analysis_score": total_score
            }
            
        except Exception as e:
            logger.error(f"Kapsamlı pattern analizi hatası: {str(e)}")
            return {
                "final_signal": "NEUTRAL",
                "final_confidence": 0,
                "components": {},
                "error": str(e)
            }