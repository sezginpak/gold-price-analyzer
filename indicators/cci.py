"""
Commodity Channel Index (CCI) - Altın fiyat analizi için özel olarak optimize edilmiş
CCI, fiyatın ortalamadan ne kadar saptığını ölçer ve aşırı alım/satım bölgelerini belirler.
"""

import pandas as pd
import numpy as np
from typing import Tuple, Optional
from decimal import Decimal
import logging

logger = logging.getLogger(__name__)


class CCI:
    """
    Commodity Channel Index hesaplama sınıfı
    Altın ticareti için optimize edilmiş parametreler
    """
    
    def __init__(self, period: int = 20):
        """
        CCI göstergesi için başlangıç parametreleri
        
        Args:
            period: CCI hesaplama periyodu (varsayılan: 20)
        """
        self.period = period
        # Altın için optimize edilmiş seviyeler
        self.overbought_level = 100  # Aşırı alım
        self.oversold_level = -100   # Aşırı satım
        self.extreme_overbought = 200  # Ekstrem aşırı alım
        self.extreme_oversold = -200   # Ekstrem aşırı satım
        
    def calculate(self, df: pd.DataFrame) -> pd.Series:
        """
        CCI değerlerini hesapla
        
        Args:
            df: high, low, close kolonlarını içeren DataFrame
            
        Returns:
            CCI değerlerini içeren Series
        """
        try:
            # Typical Price hesapla
            typical_price = (df['high'] + df['low'] + df['close']) / 3
            
            # Simple Moving Average
            sma = typical_price.rolling(window=self.period).mean()
            
            # Mean Absolute Deviation
            mad = typical_price.rolling(window=self.period).apply(
                lambda x: np.abs(x - x.mean()).mean()
            )
            
            # CCI hesapla
            # Sabit 0.015, CCI'nin %70-80'inin +100 ile -100 arasında kalmasını sağlar
            cci = (typical_price - sma) / (0.015 * mad)
            
            return cci
            
        except Exception as e:
            logger.error(f"CCI hesaplama hatası: {str(e)}")
            return pd.Series(dtype=float)
    
    def get_signal(self, cci_value: float) -> Tuple[str, float]:
        """
        CCI değerine göre sinyal üret
        
        Args:
            cci_value: Güncel CCI değeri
            
        Returns:
            (sinyal, güven_skoru) tuple'ı
        """
        if pd.isna(cci_value):
            return "NEUTRAL", 0.0
            
        # Ekstrem durumlar - yüksek güven
        if cci_value >= self.extreme_overbought:
            return "STRONG_SELL", 0.9
        elif cci_value <= self.extreme_oversold:
            return "STRONG_BUY", 0.9
            
        # Normal aşırı alım/satım
        elif cci_value >= self.overbought_level:
            confidence = min(0.7 + (cci_value - 100) / 200, 0.85)
            return "SELL", confidence
        elif cci_value <= self.oversold_level:
            confidence = min(0.7 + abs(cci_value + 100) / 200, 0.85)
            return "BUY", confidence
            
        # Nötr bölge
        else:
            return "NEUTRAL", 0.3
    
    def get_divergence(self, df: pd.DataFrame, lookback: int = 14) -> Optional[str]:
        """
        CCI ve fiyat arasındaki uyumsuzlukları tespit et
        
        Args:
            df: Fiyat ve CCI verilerini içeren DataFrame
            lookback: Geriye bakış periyodu
            
        Returns:
            "BULLISH_DIVERGENCE", "BEARISH_DIVERGENCE" veya None
        """
        try:
            if len(df) < lookback + self.period:
                return None
                
            cci = self.calculate(df)
            prices = df['close']
            
            # Son lookback periyodunu al
            recent_cci = cci.iloc[-lookback:]
            recent_prices = prices.iloc[-lookback:]
            
            # Fiyat yeni dip yaparken CCI yükselen dip = Bullish divergence
            if (recent_prices.iloc[-1] < recent_prices.min() * 1.001 and 
                recent_cci.iloc[-1] > recent_cci.min() * 1.05):
                return "BULLISH_DIVERGENCE"
                
            # Fiyat yeni zirve yaparken CCI düşen zirve = Bearish divergence
            elif (recent_prices.iloc[-1] > recent_prices.max() * 0.999 and
                  recent_cci.iloc[-1] < recent_cci.max() * 0.95):
                return "BEARISH_DIVERGENCE"
                
            return None
            
        except Exception as e:
            logger.error(f"CCI divergence hesaplama hatası: {str(e)}")
            return None
    
    def get_trend_strength(self, cci_value: float) -> Tuple[str, float]:
        """
        CCI değerine göre trend gücünü belirle
        
        Args:
            cci_value: Güncel CCI değeri
            
        Returns:
            (trend_yönü, güç) tuple'ı
        """
        if pd.isna(cci_value):
            return "NEUTRAL", 0.0
            
        abs_cci = abs(cci_value)
        
        # Trend yönü
        trend = "BULLISH" if cci_value > 0 else "BEARISH"
        
        # Trend gücü (0-1 arası normalize edilmiş)
        if abs_cci < 50:
            strength = 0.2  # Zayıf trend
        elif abs_cci < 100:
            strength = 0.5  # Orta trend
        elif abs_cci < 150:
            strength = 0.7  # Güçlü trend
        else:
            strength = 0.9  # Çok güçlü trend
            
        return trend, strength
    
    def get_analysis(self, df: pd.DataFrame) -> dict:
        """
        Kapsamlı CCI analizi yap
        
        Args:
            df: Fiyat verilerini içeren DataFrame
            
        Returns:
            Analiz sonuçlarını içeren dictionary
        """
        try:
            cci_series = self.calculate(df)
            current_cci = cci_series.iloc[-1] if len(cci_series) > 0 else None
            
            if current_cci is None:
                return {
                    'value': None,
                    'signal': 'NEUTRAL',
                    'confidence': 0.0,
                    'trend': 'NEUTRAL',
                    'trend_strength': 0.0,
                    'divergence': None
                }
            
            signal, confidence = self.get_signal(current_cci)
            trend, trend_strength = self.get_trend_strength(current_cci)
            divergence = self.get_divergence(df)
            
            # Divergence varsa güven skorunu artır
            if divergence:
                if (divergence == "BULLISH_DIVERGENCE" and signal in ["BUY", "STRONG_BUY"]):
                    confidence = min(confidence * 1.2, 0.95)
                elif (divergence == "BEARISH_DIVERGENCE" and signal in ["SELL", "STRONG_SELL"]):
                    confidence = min(confidence * 1.2, 0.95)
            
            return {
                'value': round(current_cci, 2),
                'signal': signal,
                'confidence': round(confidence, 3),
                'trend': trend,
                'trend_strength': round(trend_strength, 2),
                'divergence': divergence,
                'overbought': current_cci >= self.overbought_level,
                'oversold': current_cci <= self.oversold_level,
                'extreme': abs(current_cci) >= 200
            }
            
        except Exception as e:
            logger.error(f"CCI analiz hatası: {str(e)}")
            return {
                'value': None,
                'signal': 'NEUTRAL',
                'confidence': 0.0,
                'trend': 'NEUTRAL',
                'trend_strength': 0.0,
                'divergence': None
            }