"""
Money Flow Index (MFI) - Hacim ağırlıklı RSI
MFI, fiyat ve hacim verilerini birleştirerek para akışını ölçer.
Altın piyasasında likidite ve momentum analizi için kritik.
"""

import pandas as pd
import numpy as np
from typing import Tuple, Optional
from decimal import Decimal
import logging

logger = logging.getLogger(__name__)


class MFI:
    """
    Money Flow Index hesaplama sınıfı
    Hacim verisi olmadığında simüle edilmiş hacim kullanır
    """
    
    def __init__(self, period: int = 14):
        """
        MFI göstergesi için başlangıç parametreleri
        
        Args:
            period: MFI hesaplama periyodu (varsayılan: 14)
        """
        self.period = period
        # Altın için optimize edilmiş seviyeler
        self.overbought_level = 80   # Aşırı alım
        self.oversold_level = 20     # Aşırı satım
        self.strong_overbought = 90  # Güçlü aşırı alım
        self.strong_oversold = 10    # Güçlü aşırı satım
        
    def _simulate_volume(self, df: pd.DataFrame) -> pd.Series:
        """
        Hacim verisi yoksa simüle et
        Fiyat değişimi ve range'e göre hacim tahmini
        
        Args:
            df: OHLC verilerini içeren DataFrame
            
        Returns:
            Simüle edilmiş hacim Series
        """
        try:
            # Fiyat değişim yüzdesi
            price_change = df['close'].pct_change().abs()
            
            # High-Low range (volatilite göstergesi)
            price_range = (df['high'] - df['low']) / df['close']
            
            # Ortalama fiyat
            avg_price = (df['high'] + df['low'] + df['close']) / 3
            
            # Simüle edilmiş hacim = fiyat değişimi × range × ortalama fiyat
            simulated_volume = price_change * price_range * avg_price * 1000000
            
            # İlk değeri ortalama ile doldur
            simulated_volume.fillna(simulated_volume.mean(), inplace=True)
            
            return simulated_volume
            
        except Exception as e:
            logger.error(f"Hacim simülasyon hatası: {str(e)}")
            return pd.Series(index=df.index, dtype=float).fillna(1000000)
    
    def calculate(self, df: pd.DataFrame) -> pd.Series:
        """
        MFI değerlerini hesapla
        
        Args:
            df: high, low, close ve opsiyonel volume kolonlarını içeren DataFrame
            
        Returns:
            MFI değerlerini içeren Series
        """
        try:
            # Hacim kontrolü
            if 'volume' in df.columns and df['volume'].sum() > 0:
                volume = df['volume']
            else:
                logger.info("Hacim verisi bulunamadı, simüle ediliyor...")
                volume = self._simulate_volume(df)
            
            # Typical Price
            typical_price = (df['high'] + df['low'] + df['close']) / 3
            
            # Raw Money Flow
            raw_money_flow = typical_price * volume
            
            # Positive ve Negative Money Flow
            money_flow_positive = pd.Series(0, index=df.index, dtype=float)
            money_flow_negative = pd.Series(0, index=df.index, dtype=float)
            
            # İlk değerden sonraki değerler için
            for i in range(1, len(df)):
                if typical_price.iloc[i] > typical_price.iloc[i-1]:
                    money_flow_positive.iloc[i] = raw_money_flow.iloc[i]
                elif typical_price.iloc[i] < typical_price.iloc[i-1]:
                    money_flow_negative.iloc[i] = raw_money_flow.iloc[i]
            
            # Money Flow Ratio
            positive_flow = money_flow_positive.rolling(self.period).sum()
            negative_flow = money_flow_negative.rolling(self.period).sum()
            
            # Sıfıra bölme koruması
            money_flow_ratio = positive_flow / negative_flow.replace(0, 0.0001)
            
            # MFI hesapla
            mfi = 100 - (100 / (1 + money_flow_ratio))
            
            return mfi
            
        except Exception as e:
            logger.error(f"MFI hesaplama hatası: {str(e)}")
            return pd.Series(dtype=float)
    
    def get_signal(self, mfi_value: float, price_trend: str = "NEUTRAL") -> Tuple[str, float]:
        """
        MFI değerine göre sinyal üret
        
        Args:
            mfi_value: Güncel MFI değeri
            price_trend: Fiyat trendi (opsiyonel divergence kontrolü için)
            
        Returns:
            (sinyal, güven_skoru) tuple'ı
        """
        if pd.isna(mfi_value):
            return "NEUTRAL", 0.0
        
        # Güçlü aşırı alım/satım
        if mfi_value >= self.strong_overbought:
            return "STRONG_SELL", 0.85
        elif mfi_value <= self.strong_oversold:
            return "STRONG_BUY", 0.85
        
        # Normal aşırı alım/satım
        elif mfi_value >= self.overbought_level:
            confidence = 0.6 + (mfi_value - 80) / 40  # 80-90 arası güven artışı
            return "SELL", min(confidence, 0.8)
        elif mfi_value <= self.oversold_level:
            confidence = 0.6 + (20 - mfi_value) / 40  # 10-20 arası güven artışı
            return "BUY", min(confidence, 0.8)
        
        # Orta bölge trendleri
        elif 50 < mfi_value < 70:
            return "BULLISH", 0.5
        elif 30 < mfi_value < 50:
            return "BEARISH", 0.5
        else:
            return "NEUTRAL", 0.3
    
    def get_divergence(self, df: pd.DataFrame, lookback: int = 14) -> Optional[str]:
        """
        MFI ve fiyat arasındaki uyumsuzlukları tespit et
        
        Args:
            df: Fiyat ve MFI verilerini içeren DataFrame
            lookback: Geriye bakış periyodu
            
        Returns:
            "BULLISH_DIVERGENCE", "BEARISH_DIVERGENCE" veya None
        """
        try:
            if len(df) < lookback + self.period:
                return None
            
            mfi = self.calculate(df)
            prices = df['close']
            
            # Son lookback periyodunu al
            recent_mfi = mfi.iloc[-lookback:]
            recent_prices = prices.iloc[-lookback:]
            
            # Son değerler
            current_price = recent_prices.iloc[-1]
            current_mfi = recent_mfi.iloc[-1]
            
            # Önceki ekstremler
            price_min_idx = recent_prices.idxmin()
            price_max_idx = recent_prices.idxmax()
            
            # Bullish Divergence: Fiyat düşük dip, MFI yüksek dip
            if current_price <= recent_prices.loc[price_min_idx] * 1.001:
                prev_mfi_at_price_min = recent_mfi.loc[price_min_idx]
                if current_mfi > prev_mfi_at_price_min * 1.05:
                    return "BULLISH_DIVERGENCE"
            
            # Bearish Divergence: Fiyat yüksek zirve, MFI düşük zirve
            if current_price >= recent_prices.loc[price_max_idx] * 0.999:
                prev_mfi_at_price_max = recent_mfi.loc[price_max_idx]
                if current_mfi < prev_mfi_at_price_max * 0.95:
                    return "BEARISH_DIVERGENCE"
            
            return None
            
        except Exception as e:
            logger.error(f"MFI divergence hesaplama hatası: {str(e)}")
            return None
    
    def get_volume_analysis(self, df: pd.DataFrame) -> dict:
        """
        Hacim bazlı analiz yap
        
        Args:
            df: Fiyat ve hacim verilerini içeren DataFrame
            
        Returns:
            Hacim analizi sonuçları
        """
        try:
            mfi = self.calculate(df)
            current_mfi = mfi.iloc[-1] if len(mfi) > 0 else 50
            
            # Son 5 günlük MFI ortalaması
            recent_avg = mfi.iloc[-5:].mean() if len(mfi) >= 5 else current_mfi
            
            # MFI trendi
            if current_mfi > recent_avg * 1.05:
                volume_trend = "INCREASING"
                strength = min((current_mfi - recent_avg) / recent_avg, 1.0)
            elif current_mfi < recent_avg * 0.95:
                volume_trend = "DECREASING"
                strength = min((recent_avg - current_mfi) / recent_avg, 1.0)
            else:
                volume_trend = "STABLE"
                strength = 0.3
            
            # Para akışı yönü
            if current_mfi > 50:
                money_flow = "POSITIVE"
                flow_strength = (current_mfi - 50) / 50
            else:
                money_flow = "NEGATIVE"
                flow_strength = (50 - current_mfi) / 50
            
            return {
                'volume_trend': volume_trend,
                'trend_strength': round(strength, 2),
                'money_flow': money_flow,
                'flow_strength': round(flow_strength, 2),
                'accumulation': current_mfi > 60,  # Birikim
                'distribution': current_mfi < 40    # Dağıtım
            }
            
        except Exception as e:
            logger.error(f"Hacim analizi hatası: {str(e)}")
            return {
                'volume_trend': 'UNKNOWN',
                'trend_strength': 0.0,
                'money_flow': 'NEUTRAL',
                'flow_strength': 0.0,
                'accumulation': False,
                'distribution': False
            }
    
    def get_analysis(self, df: pd.DataFrame) -> dict:
        """
        Kapsamlı MFI analizi yap
        
        Args:
            df: Fiyat verilerini içeren DataFrame
            
        Returns:
            Analiz sonuçlarını içeren dictionary
        """
        try:
            mfi_series = self.calculate(df)
            current_mfi = mfi_series.iloc[-1] if len(mfi_series) > 0 else None
            
            if current_mfi is None:
                return {
                    'value': None,
                    'signal': 'NEUTRAL',
                    'confidence': 0.0,
                    'divergence': None,
                    'volume_analysis': {}
                }
            
            # Fiyat trendi belirle (basit)
            price_trend = "BULLISH" if df['close'].iloc[-1] > df['close'].iloc[-10] else "BEARISH"
            
            signal, confidence = self.get_signal(current_mfi, price_trend)
            divergence = self.get_divergence(df)
            volume_analysis = self.get_volume_analysis(df)
            
            # Divergence varsa güven skorunu artır
            if divergence:
                if (divergence == "BULLISH_DIVERGENCE" and signal in ["BUY", "STRONG_BUY"]):
                    confidence = min(confidence * 1.2, 0.95)
                elif (divergence == "BEARISH_DIVERGENCE" and signal in ["SELL", "STRONG_SELL"]):
                    confidence = min(confidence * 1.2, 0.95)
            
            return {
                'value': round(current_mfi, 2),
                'signal': signal,
                'confidence': round(confidence, 3),
                'divergence': divergence,
                'overbought': current_mfi >= self.overbought_level,
                'oversold': current_mfi <= self.oversold_level,
                'extreme': current_mfi >= 90 or current_mfi <= 10,
                'volume_analysis': volume_analysis
            }
            
        except Exception as e:
            logger.error(f"MFI analiz hatası: {str(e)}")
            return {
                'value': None,
                'signal': 'NEUTRAL',
                'confidence': 0.0,
                'divergence': None,
                'volume_analysis': {}
            }