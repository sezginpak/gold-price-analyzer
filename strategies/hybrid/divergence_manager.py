"""
Divergence Manager - Advanced Divergence Detection entegrasyonu ile
"""
from typing import Dict, List, Any, Optional
import logging
import pandas as pd
from indicators.divergence_detector import AdvancedDivergenceDetector

logger = logging.getLogger(__name__)


class DivergenceManager:
    """Advanced Divergence Detection entegrasyonu ile gelişmiş divergence analizi"""
    
    def __init__(self):
        # Advanced Divergence Detector
        self.divergence_detector = AdvancedDivergenceDetector()
        
        # Legacy skorlama ağırlıkları (backward compatibility)
        self.divergence_weights = {
            'RSI': 2,
            'MACD': 3,
            'Stochastic': 2,
            'MFI': 2,
            'CCI': 1
        }
        
        # Advanced modül ağırlıkları
        self.advanced_weights = {
            'regular_bullish': 4.0,
            'regular_bearish': 4.0,
            'hidden_bullish': 2.5,
            'hidden_bearish': 2.5
        }
        
        # Sınıf ağırlıkları
        self.class_weights = {
            'A': 1.0,
            'B': 0.8,
            'C': 0.6
        }
        
        self.lookback_period = 150  # Advanced analiz için daha fazla veri
        
    def analyze_divergences(self, 
                           candles: List,
                           indicators: Dict) -> Dict[str, Any]:
        """
        Advanced Divergence Detection ile kapsamlı divergence analizi
        
        Returns:
            {
                'total_score': float (0-10),
                'divergence_type': str (BULLISH/BEARISH/NONE),
                'divergences_found': Dict[str, Dict],
                'strength': str (STRONG/MODERATE/WEAK),
                'confidence': float (0-1),
                'recommendation': str,
                'details': Dict,
                'advanced_analysis': Dict  # Yeni gelişmiş analiz
            }
        """
        try:
            # Minimum veri kontrolü
            if not candles or len(candles) < 50:
                return self._empty_divergence_result()
            
            # DataFrame oluştur
            df = self._create_dataframe_from_candles(candles)
            
            # Advanced divergence analizi
            advanced_analysis = self.divergence_detector.analyze(df, lookback=self.lookback_period)
            
            # Legacy analizi de yap (backward compatibility)
            legacy_analysis = self._legacy_divergence_analysis(candles, indicators)
            
            # İki analizi birleştir
            combined_analysis = self._combine_analyses(advanced_analysis, legacy_analysis)
            
            return combined_analysis
            
        except Exception as e:
            logger.error(f"Divergence analiz hatası: {e}")
            return self._empty_divergence_result()
    
    def _create_dataframe_from_candles(self, candles: List) -> pd.DataFrame:
        """Candle listesinden pandas DataFrame oluştur"""
        try:
            data = []
            for candle in candles:
                data.append({
                    'open': float(candle.open),
                    'high': float(candle.high),
                    'low': float(candle.low),
                    'close': float(candle.close),
                })
            
            return pd.DataFrame(data)
            
        except Exception as e:
            logger.error(f"DataFrame oluşturma hatası: {e}")
            return pd.DataFrame()
    
    def _legacy_divergence_analysis(self, candles: List, indicators: Dict) -> Dict:
        """Eski divergence analiz sistemi (backward compatibility)"""
        try:
            divergences_found = {}
            bullish_score = 0
            bearish_score = 0
            
            prices = [float(c.close) for c in candles]
            
            # Legacy analizler
            rsi_result = self._check_rsi_divergence(prices, indicators)
            if rsi_result['found']:
                if rsi_result['type'] == 'bullish':
                    bullish_score += self.divergence_weights['RSI']
                else:
                    bearish_score += self.divergence_weights['RSI']
                divergences_found['RSI'] = rsi_result
            
            macd_result = self._check_macd_divergence(prices, indicators)
            if macd_result['found']:
                if macd_result['type'] == 'bullish':
                    bullish_score += self.divergence_weights['MACD']
                else:
                    bearish_score += self.divergence_weights['MACD']
                divergences_found['MACD'] = macd_result
            
            return {
                'legacy_divergences': divergences_found,
                'legacy_bullish_score': bullish_score,
                'legacy_bearish_score': bearish_score
            }
            
        except Exception as e:
            logger.error(f"Legacy analiz hatası: {e}")
            return {
                'legacy_divergences': {},
                'legacy_bullish_score': 0,
                'legacy_bearish_score': 0
            }
    
    def _combine_analyses(self, advanced_analysis, legacy_analysis: Dict) -> Dict:
        """Advanced ve legacy analizleri birleştir"""
        try:
            # Advanced scoring
            advanced_score = 0
            bullish_score = 0 
            bearish_score = 0
            
            # Regular divergences scoring
            for div in advanced_analysis.regular_divergences:
                weight = self.advanced_weights.get(div.type, 0)
                class_weight = self.class_weights.get(div.class_rating, 0.5)
                score = (div.strength / 100) * weight * class_weight
                
                advanced_score += score
                if 'bullish' in div.type:
                    bullish_score += score
                else:
                    bearish_score += score
            
            # Hidden divergences scoring 
            for div in advanced_analysis.hidden_divergences:
                weight = self.advanced_weights.get(div.type, 0)
                class_weight = self.class_weights.get(div.class_rating, 0.5)
                score = (div.strength / 100) * weight * class_weight
                
                advanced_score += score
                if 'bullish' in div.type:
                    bullish_score += score
                else:
                    bearish_score += score
            
            # Confluence bonus
            if advanced_analysis.confluence_score > 50:
                confluence_bonus = advanced_analysis.confluence_score / 100 * 2
                advanced_score += confluence_bonus
                if bullish_score > bearish_score:
                    bullish_score += confluence_bonus
                else:
                    bearish_score += confluence_bonus
            
            # Legacy scores ekle (düşük ağırlıkla)
            legacy_bullish = legacy_analysis.get('legacy_bullish_score', 0) * 0.3
            legacy_bearish = legacy_analysis.get('legacy_bearish_score', 0) * 0.3
            
            bullish_score += legacy_bullish
            bearish_score += legacy_bearish
            total_score = max(bullish_score, bearish_score)
            
            # Final analysis
            divergence_type = self._determine_advanced_type(
                bullish_score, 
                bearish_score,
                advanced_analysis.overall_signal
            )
            
            strength = self._calculate_advanced_strength(
                total_score, 
                advanced_analysis.signal_strength
            )
            
            confidence = self._calculate_advanced_confidence(
                total_score,
                advanced_analysis.confluence_score,
                len(advanced_analysis.regular_divergences) + len(advanced_analysis.hidden_divergences)
            )
            
            recommendation = self._generate_advanced_recommendation(
                divergence_type, 
                strength,
                advanced_analysis.dominant_divergence
            )
            
            # Combined divergences
            all_divergences = {}
            
            # Advanced divergences
            for div in advanced_analysis.regular_divergences + advanced_analysis.hidden_divergences:
                all_divergences[f"{div.indicator}_{div.type}"] = {
                    'found': True,
                    'type': 'bullish' if 'bullish' in div.type else 'bearish',
                    'strength': div.strength / 100,
                    'class': div.class_rating,
                    'success_probability': div.success_probability,
                    'description': f"{div.type} {div.indicator} (Sınıf {div.class_rating})"
                }
            
            # Legacy divergences ekle
            for key, div in legacy_analysis.get('legacy_divergences', {}).items():
                if key not in all_divergences:
                    all_divergences[f"legacy_{key}"] = div
            
            return {
                'total_score': min(total_score, 10.0),  # Max 10
                'divergence_type': divergence_type,
                'divergences_found': all_divergences,
                'strength': strength,
                'confidence': confidence,
                'recommendation': recommendation,
                'bullish_score': bullish_score,
                'bearish_score': bearish_score,
                'advanced_analysis': {
                    'overall_signal': advanced_analysis.overall_signal,
                    'signal_strength': advanced_analysis.signal_strength,
                    'confluence_score': advanced_analysis.confluence_score,
                    'regular_count': len(advanced_analysis.regular_divergences),
                    'hidden_count': len(advanced_analysis.hidden_divergences),
                    'dominant_divergence': {
                        'type': advanced_analysis.dominant_divergence.type,
                        'indicator': advanced_analysis.dominant_divergence.indicator,
                        'strength': advanced_analysis.dominant_divergence.strength,
                        'class': advanced_analysis.dominant_divergence.class_rating,
                        'success_rate': advanced_analysis.dominant_divergence.success_probability
                    } if advanced_analysis.dominant_divergence else None,
                    'next_targets': advanced_analysis.next_targets,
                    'invalidation_levels': advanced_analysis.invalidation_levels
                },
                'details': {
                    'divergence_count': len(all_divergences),
                    'active_indicators': list(all_divergences.keys()),
                    'advanced_score': advanced_score,
                    'legacy_contribution': legacy_bullish + legacy_bearish,
                    'score_breakdown': {
                        'bullish': bullish_score,
                        'bearish': bearish_score,
                        'advanced_contribution': advanced_score,
                        'legacy_contribution': legacy_bullish + legacy_bearish
                    }
                }
            }
            
        except Exception as e:
            logger.error(f"Analiz birleştirme hatası: {e}")
            return self._empty_divergence_result()
    
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
        if rsi_value < 30 and not price_trend:
            # Fiyat düşüyor ama RSI oversold - bullish divergence
            return {
                'found': True,
                'type': 'bullish',
                'strength': 0.7,
                'description': 'RSI oversold divergence'
            }
        elif rsi_value > 70 and price_trend:
            # Fiyat yükseliyor ama RSI overbought - bearish divergence
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
    
    def _determine_advanced_type(self, 
                               bullish_score: float, 
                               bearish_score: float,
                               advanced_signal: str) -> str:
        """Advanced analiz ile divergence tipini belirle"""
        # Advanced signal'ı önceliklendir
        if advanced_signal in ['BULLISH', 'BEARISH'] and abs(bullish_score - bearish_score) > 1:
            return advanced_signal
        
        # Klasik skorlama
        if bullish_score > bearish_score and bullish_score >= 2:
            return 'BULLISH'
        elif bearish_score > bullish_score and bearish_score >= 2:
            return 'BEARISH'
        else:
            return 'NONE'
    
    def _calculate_advanced_strength(self, 
                                   total_score: float, 
                                   advanced_strength: float) -> str:
        """Advanced analiz ile strength hesapla"""
        # Advanced strength'i de dikkate al
        composite_strength = (total_score * 10 + advanced_strength) / 2
        
        if composite_strength >= 70:
            return 'STRONG'
        elif composite_strength >= 50:
            return 'MODERATE' 
        elif composite_strength >= 30:
            return 'WEAK'
        else:
            return 'NONE'
    
    def _calculate_advanced_confidence(self, 
                                     total_score: float,
                                     confluence_score: float, 
                                     divergence_count: int) -> float:
        """Advanced confidence hesaplama"""
        # Base confidence
        base_confidence = min(total_score / 10, 1.0)
        
        # Confluence bonus
        confluence_bonus = confluence_score / 100 * 0.3
        
        # Divergence count bonus
        count_bonus = min(divergence_count / 5, 0.2)
        
        total_confidence = base_confidence + confluence_bonus + count_bonus
        return min(total_confidence, 1.0)
    
    def _generate_advanced_recommendation(self, 
                                        divergence_type: str, 
                                        strength: str,
                                        dominant_div) -> str:
        """Advanced recommendation üretme"""
        base_rec = self._generate_recommendation(divergence_type, strength)
        
        if dominant_div:
            success_rate = dominant_div.success_probability
            class_rating = dominant_div.class_rating
            
            if class_rating == 'A' and success_rate > 0.7:
                if divergence_type == 'BULLISH':
                    return f"GÜÇLÜ ALIŞ - Sınıf A divergence (Başarı: {success_rate:.0%})"
                elif divergence_type == 'BEARISH':
                    return f"GÜÇLÜ SATIŞ - Sınıf A divergence (Başarı: {success_rate:.0%})"
            elif class_rating == 'B' and success_rate > 0.6:
                if divergence_type == 'BULLISH':
                    return f"ALIŞ - Sınıf B divergence (Başarı: {success_rate:.0%})"
                elif divergence_type == 'BEARISH':
                    return f"SATIŞ - Sınıf B divergence (Başarı: {success_rate:.0%})"
        
        return base_rec
    
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
            'advanced_analysis': {
                'overall_signal': 'NEUTRAL',
                'signal_strength': 0,
                'confluence_score': 0,
                'regular_count': 0,
                'hidden_count': 0,
                'dominant_divergence': None,
                'next_targets': [],
                'invalidation_levels': []
            },
            'details': {
                'divergence_count': 0,
                'active_indicators': [],
                'advanced_score': 0,
                'legacy_contribution': 0,
                'score_breakdown': {
                    'bullish': 0,
                    'bearish': 0,
                    'advanced_contribution': 0,
                    'legacy_contribution': 0
                }
            }
        }