"""
Divergence Manager - Tüm göstergelerin divergence analizini yöneten modül
"""
from typing import Dict, List, Any, Optional
import logging
import numpy as np

logger = logging.getLogger(__name__)


class DivergenceManager:
    """Divergence Scoring System - Tüm göstergeleri birleştirir"""
    
    def __init__(self):
        # Divergence skorlama ağırlıkları
        self.divergence_weights = {
            'RSI': 2,
            'MACD': 3,
            'Stochastic': 2,
            'MFI': 2,
            'CCI': 1
        }
        
        # Minimum swing gücü
        self.min_swing_strength = 0.02  # %2
        self.lookback_period = 5
        
    def analyze_divergences(self, 
                           candles: List,
                           indicators: Dict) -> Dict[str, Any]:
        """
        Tüm göstergelerin divergence analizini yap ve skorla
        
        Returns:
            {
                'total_score': float (0-10),
                'divergence_type': str (BULLISH/BEARISH/NONE),
                'divergences_found': Dict[str, Dict],
                'strength': str (STRONG/MODERATE/WEAK),
                'confidence': float (0-1),
                'recommendation': str,
                'details': Dict
            }
        """
        divergences_found = {}
        bullish_score = 0
        bearish_score = 0
        
        # Fiyat verisi hazırla
        if not candles or len(candles) < self.lookback_period * 2:
            return self._empty_divergence_result()
            
        prices = [float(c.close) for c in candles]
        
        # 1. RSI Divergence
        rsi_result = self._check_rsi_divergence(prices, indicators)
        if rsi_result['found']:
            if rsi_result['type'] == 'bullish':
                bullish_score += self.divergence_weights['RSI']
            else:
                bearish_score += self.divergence_weights['RSI']
            divergences_found['RSI'] = rsi_result
        
        # 2. MACD Divergence
        macd_result = self._check_macd_divergence(prices, indicators)
        if macd_result['found']:
            if macd_result['type'] == 'bullish':
                bullish_score += self.divergence_weights['MACD']
            else:
                bearish_score += self.divergence_weights['MACD']
            divergences_found['MACD'] = macd_result
        
        # 3. Stochastic Divergence
        stoch_result = self._check_stochastic_divergence(prices, indicators)
        if stoch_result['found']:
            if stoch_result['type'] == 'bullish':
                bullish_score += self.divergence_weights['Stochastic']
            else:
                bearish_score += self.divergence_weights['Stochastic']
            divergences_found['Stochastic'] = stoch_result
        
        # 4. MFI Divergence (volume simülasyonu ile)
        mfi_result = self._check_mfi_divergence(prices, indicators)
        if mfi_result['found']:
            if mfi_result['type'] == 'bullish':
                bullish_score += self.divergence_weights['MFI']
            else:
                bearish_score += self.divergence_weights['MFI']
            divergences_found['MFI'] = mfi_result
        
        # 5. CCI Divergence
        cci_result = self._check_cci_divergence(prices, indicators)
        if cci_result['found']:
            if cci_result['type'] == 'bullish':
                bullish_score += self.divergence_weights['CCI']
            else:
                bearish_score += self.divergence_weights['CCI']
            divergences_found['CCI'] = cci_result
        
        # Toplam skor ve analiz
        total_score = max(bullish_score, bearish_score)
        divergence_type = self._determine_divergence_type(bullish_score, bearish_score)
        strength = self._calculate_strength(total_score)
        confidence = self._calculate_confidence(total_score)
        recommendation = self._generate_recommendation(divergence_type, strength)
        
        return {
            'total_score': total_score,
            'divergence_type': divergence_type,
            'divergences_found': divergences_found,
            'strength': strength,
            'confidence': confidence,
            'recommendation': recommendation,
            'bullish_score': bullish_score,
            'bearish_score': bearish_score,
            'details': {
                'divergence_count': len(divergences_found),
                'active_indicators': list(divergences_found.keys()),
                'score_breakdown': {
                    'bullish': bullish_score,
                    'bearish': bearish_score,
                    'max_possible': sum(self.divergence_weights.values())
                }
            }
        }
    
    def _check_rsi_divergence(self, prices: List[float], 
                             indicators: Dict) -> Dict:
        """RSI divergence kontrolü"""
        rsi_value = indicators.get('rsi')
        if rsi_value is None:
            return {'found': False}
        
        # Basitleştirilmiş divergence kontrolü
        # Gerçek implementasyonda swing noktaları bulunmalı
        if len(prices) < 10:
            return {'found': False}
        
        # Son 10 mumda trend kontrolü
        price_trend = prices[-1] > prices[-10]
        
        # RSI extremes
        if rsi_value < 30 and price_trend:
            # Possible hidden bullish
            return {
                'found': True,
                'type': 'bullish',
                'strength': 0.7,
                'description': 'RSI oversold divergence'
            }
        elif rsi_value > 70 and not price_trend:
            # Possible hidden bearish
            return {
                'found': True,
                'type': 'bearish',
                'strength': 0.7,
                'description': 'RSI overbought divergence'
            }
        
        return {'found': False}
    
    def _check_macd_divergence(self, prices: List[float], 
                              indicators: Dict) -> Dict:
        """MACD divergence kontrolü"""
        macd_data = indicators.get('macd', {})
        histogram = macd_data.get('histogram')
        
        if histogram is None:
            return {'found': False}
        
        # MACD histogram trend analizi
        # Pozitif histogram ve düşen fiyat = bearish divergence
        # Negatif histogram ve yükselen fiyat = bullish divergence
        
        if histogram > 0 and len(prices) >= 5:
            if prices[-1] < prices[-5]:
                return {
                    'found': True,
                    'type': 'bearish',
                    'strength': 0.8,
                    'description': 'MACD positive but price falling'
                }
        elif histogram < 0 and len(prices) >= 5:
            if prices[-1] > prices[-5]:
                return {
                    'found': True,
                    'type': 'bullish', 
                    'strength': 0.8,
                    'description': 'MACD negative but price rising'
                }
        
        return {'found': False}
    
    def _check_stochastic_divergence(self, prices: List[float], 
                                    indicators: Dict) -> Dict:
        """Stochastic divergence kontrolü"""
        stoch_data = indicators.get('stochastic', {})
        k_value = stoch_data.get('k')
        
        if k_value is None:
            return {'found': False}
        
        # Stochastic extremes
        if k_value < 20 and len(prices) >= 5:
            if prices[-1] < prices[-5]:
                return {
                    'found': True,
                    'type': 'bullish',
                    'strength': 0.7,
                    'description': 'Stochastic oversold divergence'
                }
        elif k_value > 80 and len(prices) >= 5:
            if prices[-1] > prices[-5]:
                return {
                    'found': True,
                    'type': 'bearish',
                    'strength': 0.7,
                    'description': 'Stochastic overbought divergence'
                }
        
        return {'found': False}
    
    def _check_mfi_divergence(self, prices: List[float], 
                             indicators: Dict) -> Dict:
        """MFI divergence kontrolü (volume simülasyonu ile)"""
        # MFI yoksa price action bazlı simülasyon
        if len(prices) < 14:
            return {'found': False}
        
        # Son 14 mumun volatilitesini hesapla (volume proxy)
        price_changes = [abs(prices[i] - prices[i-1]) for i in range(1, len(prices))]
        avg_volatility = np.mean(price_changes[-14:])
        recent_volatility = np.mean(price_changes[-3:])
        
        # Volatilite divergence (volume proxy)
        if recent_volatility < avg_volatility * 0.5 and prices[-1] > prices[-14]:
            # Düşük volatilite ama yükselen fiyat = bearish
            return {
                'found': True,
                'type': 'bearish',
                'strength': 0.6,
                'description': 'Low volatility but rising price'
            }
        elif recent_volatility > avg_volatility * 1.5 and prices[-1] < prices[-14]:
            # Yüksek volatilite ama düşen fiyat = bullish
            return {
                'found': True,
                'type': 'bullish',
                'strength': 0.6,
                'description': 'High volatility but falling price'
            }
        
        return {'found': False}
    
    def _check_cci_divergence(self, prices: List[float], 
                             indicators: Dict) -> Dict:
        """CCI divergence kontrolü"""
        # CCI verisi yoksa basit momentum analizi
        if len(prices) < 20:
            return {'found': False}
        
        # Typical price momentum
        if prices[-20] != 0:
            momentum = (prices[-1] - prices[-20]) / prices[-20]
        else:
            momentum = 0
            
        if prices[-5] != 0:
            recent_momentum = (prices[-1] - prices[-5]) / prices[-5]
        else:
            recent_momentum = 0
        
        # Momentum divergence
        if momentum > 0.02 and recent_momentum < -0.005:
            # Uzun vadeli yükseliş ama kısa vadeli düşüş
            return {
                'found': True,
                'type': 'bearish',
                'strength': 0.5,
                'description': 'Momentum weakening'
            }
        elif momentum < -0.02 and recent_momentum > 0.005:
            # Uzun vadeli düşüş ama kısa vadeli yükseliş
            return {
                'found': True,
                'type': 'bullish',
                'strength': 0.5,
                'description': 'Momentum strengthening'
            }
        
        return {'found': False}
    
    def _determine_divergence_type(self, bullish_score: float, 
                                  bearish_score: float) -> str:
        """Divergence tipini belirle"""
        if bullish_score > bearish_score and bullish_score >= 3:
            return 'BULLISH'
        elif bearish_score > bullish_score and bearish_score >= 3:
            return 'BEARISH'
        else:
            return 'NONE'
    
    def _calculate_strength(self, total_score: float) -> str:
        """Divergence gücünü hesapla"""
        if total_score >= 6:
            return 'STRONG'
        elif total_score >= 4:
            return 'MODERATE'
        elif total_score >= 2:
            return 'WEAK'
        else:
            return 'NONE'
    
    def _calculate_confidence(self, total_score: float) -> float:
        """Güven skorunu hesapla"""
        max_possible_score = sum(self.divergence_weights.values())
        return total_score / max_possible_score if max_possible_score > 0 else 0
    
    def _generate_recommendation(self, divergence_type: str, strength: str) -> str:
        """Divergence analizine göre öneri oluştur"""
        if strength == 'STRONG':
            if divergence_type == 'BULLISH':
                return "GÜÇLÜ ALIŞ - Çoklu bullish divergence"
            elif divergence_type == 'BEARISH':
                return "GÜÇLÜ SATIŞ - Çoklu bearish divergence"
            else:
                return "BEKLE - Karışık sinyaller"
        elif strength == 'MODERATE':
            if divergence_type == 'BULLISH':
                return "DİKKATLİ ALIŞ - Orta güçte divergence"
            elif divergence_type == 'BEARISH':
                return "DİKKATLİ SATIŞ - Orta güçte divergence"
            else:
                return "BEKLE - Yeterli güç yok"
        else:
            return "BEKLE - Divergence sinyali zayıf veya yok"
    
    def _empty_divergence_result(self) -> Dict:
        """Boş divergence sonucu"""
        return {
            'total_score': 0,
            'divergence_type': 'NONE',
            'divergences_found': {},
            'strength': 'NONE',
            'confidence': 0,
            'recommendation': 'BEKLE - Yetersiz veri',
            'bullish_score': 0,
            'bearish_score': 0,
            'details': {
                'divergence_count': 0,
                'active_indicators': [],
                'score_breakdown': {
                    'bullish': 0,
                    'bearish': 0,
                    'max_possible': sum(self.divergence_weights.values())
                }
            }
        }