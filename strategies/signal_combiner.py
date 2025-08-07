"""
Signal Combiner - Multi-timeframe ve pattern priority sistemi
Dip/tepe yakalama için optimize edilmiş sinyal birleştirme
"""

import logging
from typing import Dict, Any, List, Tuple, Optional
from decimal import Decimal
import numpy as np
from strategies.constants import (
    MIN_CONFIDENCE_THRESHOLDS, RSI_OVERSOLD, RSI_OVERBOUGHT,
    PATTERN_RELIABILITY_SCORES, DIP_DETECTION_CRITERIA, PEAK_DETECTION_CRITERIA,
    TIMEFRAME_WEIGHTS, TRANSACTION_COST_PERCENTAGE
)

logger = logging.getLogger(__name__)


class SignalCombiner:
    """Gelişmiş sinyal birleştirme sistemi"""
    
    def __init__(self):
        self.pattern_priority = {
            # En güvenilir pattern'ler (dip/tepe yakalama için)
            "head_and_shoulders": 0.90,
            "inverse_head_and_shoulders": 0.90,
            "double_bottom": 0.85,
            "double_top": 0.85,
            "triple_bottom": 0.80,
            "triple_top": 0.80,
            "falling_wedge": 0.75,  # Bullish breakout
            "rising_wedge": 0.75,   # Bearish breakout
            "cup_and_handle": 0.70,
            "flag": 0.65,
            "pennant": 0.65
        }
    
    def combine_signals(self, gram_signal: Dict, global_trend: Dict, currency_risk: Dict,
                       advanced_indicators: Dict, patterns: Dict, timeframe: str,
                       market_volatility: float, divergence_data: Dict = None,
                       momentum_data: Dict = None, smart_money_data: Dict = None,
                       multi_day_pattern: Dict = None) -> Dict[str, Any]:
        """
        Tüm sinyalleri birleştirerek nihai karar ver
        
        Args:
            gram_signal: Gram altın temel analizi
            global_trend: Global trend analizi
            currency_risk: Kur riski analizi
            advanced_indicators: CCI, MFI vb. göstergeler
            patterns: Pattern tanıma sonuçları
            timeframe: Analiz edilen zaman dilimi
            market_volatility: Piyasa volatilitesi
            
        Returns:
            Birleşik sinyal analizi
        """
        try:
            logger.info(f"🔄 SIGNAL_COMBINER: Starting signal combination for {timeframe}")
            
            # Dip/tepe fırsat analizi
            dip_opportunity = self._analyze_dip_opportunity(
                gram_signal, advanced_indicators, patterns, divergence_data
            )
            
            peak_opportunity = self._analyze_peak_opportunity(
                gram_signal, advanced_indicators, patterns, divergence_data
            )
            
            # Multi-timeframe doğrulama
            mtf_confirmation = self._multi_timeframe_confirmation(
                gram_signal, timeframe, market_volatility
            )
            
            # Pattern öncelik analizi
            pattern_analysis = self._analyze_pattern_priority(patterns)
            
            # False signal filtresi
            false_signal_risk = self._assess_false_signal_risk(
                gram_signal, global_trend, currency_risk, market_volatility
            )
            
            # Ana sinyal kararı
            final_signal = self._determine_final_signal(
                gram_signal, dip_opportunity, peak_opportunity,
                mtf_confirmation, pattern_analysis, false_signal_risk
            )
            
            # Güven skoru hesapla
            confidence = self._calculate_combined_confidence(
                gram_signal, mtf_confirmation, pattern_analysis,
                false_signal_risk, timeframe, dip_opportunity, peak_opportunity
            )
            
            # Sinyal gücünü belirle
            signal_strength = self._determine_signal_strength(
                confidence, dip_opportunity, peak_opportunity, pattern_analysis
            )
            
            result = {
                "signal": final_signal,
                "confidence": confidence,
                "strength": signal_strength,
                "dip_detection": dip_opportunity,
                "peak_detection": peak_opportunity,
                "mtf_confirmation": mtf_confirmation,
                "pattern_analysis": pattern_analysis,
                "false_signal_risk": false_signal_risk,
                "market_conditions": {
                    "volatility": market_volatility,
                    "timeframe": timeframe,
                    "risk_level": currency_risk.get("risk_level", "MEDIUM")
                }
            }
            
            logger.info(f"🎯 SIGNAL_COMBINER: Final signal = {final_signal}, confidence = {confidence:.3f}")
            return result
            
        except Exception as e:
            logger.error(f"Signal combination error: {str(e)}", exc_info=True)
            return {
                "signal": "HOLD",
                "confidence": 0.5,
                "strength": "WEAK",
                "error": str(e)
            }
    
    def _analyze_dip_opportunity(self, gram_signal: Dict, advanced_indicators: Dict,
                               patterns: Dict, divergence_data: Dict = None) -> Dict[str, Any]:
        """Dip yakalama fırsatı analizi"""
        try:
            dip_score = 0
            max_score = 0
            signals = []
            
            # RSI Oversold kontrolü (kritik)
            rsi_value = gram_signal.get('indicators', {}).get('rsi')
            if isinstance(rsi_value, (int, float)):
                max_score += 20
                if rsi_value <= RSI_OVERSOLD:
                    dip_score += 20
                    signals.append(f"RSI oversold ({rsi_value:.1f} ≤ {RSI_OVERSOLD})")
                elif rsi_value <= RSI_OVERSOLD + 5:  # Yakın oversold
                    dip_score += 15
                    signals.append(f"RSI near oversold ({rsi_value:.1f})")
            
            # Bollinger Bands alt banda yakınlık
            bb_data = gram_signal.get('indicators', {}).get('bollinger', {})
            bb_position = bb_data.get('position', 'middle')
            max_score += 15
            if bb_position == 'below_lower':
                dip_score += 15
                signals.append("Fiyat Bollinger alt bandının altında")
            elif bb_position == 'near_lower':
                dip_score += 10
                signals.append("Fiyat Bollinger alt bandına yakın")
            
            # RSI Divergence (bullish)
            if divergence_data and divergence_data.get('detected') and divergence_data.get('type') == 'bullish':
                max_score += 25
                div_strength = divergence_data.get('strength', 0)
                dip_score += div_strength * 25
                signals.append(f"Bullish RSI divergence (güç: {div_strength:.2f})")
            else:
                max_score += 25
            
            # Destek seviyesi yakınlığı
            support_levels = gram_signal.get('support_levels', [])
            current_price = gram_signal.get('price', 0)
            if support_levels and current_price:
                max_score += 15
                nearest_support = support_levels[0]
                support_distance = abs(float(current_price) - float(nearest_support.level)) / float(current_price)
                
                if support_distance <= 0.01:  # %1 mesafede
                    dip_score += 15
                    signals.append(f"Güçlü destek seviyesinde ({nearest_support.level})")
                elif support_distance <= 0.02:  # %2 mesafede
                    dip_score += 10
                    signals.append("Destek seviyesine yakın")
            
            # Volume spike (onaylayıcı)
            volume_data = gram_signal.get('volume_spike', {})
            if volume_data and volume_data.get('detected'):
                max_score += 10
                spike_ratio = volume_data.get('spike_ratio', 1)
                volume_bonus = min(spike_ratio / 2, 1.0) * 10
                dip_score += volume_bonus
                signals.append(f"Volume artışı ({spike_ratio:.1f}x)")
            else:
                max_score += 10
            
            # MACD pozitif momentum (erken işaret)
            macd_data = gram_signal.get('indicators', {}).get('macd', {})
            if macd_data.get('histogram', 0) > 0 and macd_data.get('macd', 0) < 0:
                max_score += 10
                dip_score += 10
                signals.append("MACD pozitif momentum")
            else:
                max_score += 10
            
            # Stochastic oversold
            stoch_data = gram_signal.get('indicators', {}).get('stochastic', {})
            if stoch_data.get('signal') == 'oversold':
                max_score += 5
                dip_score += 5
                signals.append("Stochastic oversold")
            else:
                max_score += 5
            
            # Pattern desteği
            if patterns and patterns.get('pattern_found'):
                pattern = patterns.get('best_pattern', {})
                pattern_type = pattern.get('type', '')
                pattern_name = pattern.get('pattern', '').lower()
                
                if pattern_type == 'BULLISH':
                    max_score += 15
                    pattern_confidence = pattern.get('confidence', 0)
                    pattern_priority = self.pattern_priority.get(pattern_name, 0.5)
                    pattern_bonus = pattern_confidence * pattern_priority * 15
                    dip_score += pattern_bonus
                    signals.append(f"Bullish pattern: {pattern_name} (güven: {pattern_confidence:.2f})")
                else:
                    max_score += 15
            
            # Final score hesaplama
            final_score = dip_score / max_score if max_score > 0 else 0
            
            # Minimum eşik kontrolü
            is_dip_opportunity = final_score >= DIP_DETECTION_CRITERIA['min_combined_score']
            
            return {
                "is_dip_opportunity": is_dip_opportunity,
                "score": final_score,
                "raw_score": dip_score,
                "max_possible_score": max_score,
                "signals": signals,
                "confidence_boost": 0.15 if is_dip_opportunity else 0
            }
            
        except Exception as e:
            logger.error(f"Dip opportunity analysis error: {str(e)}")
            return {"is_dip_opportunity": False, "score": 0, "signals": []}
    
    def _analyze_peak_opportunity(self, gram_signal: Dict, advanced_indicators: Dict,
                                patterns: Dict, divergence_data: Dict = None) -> Dict[str, Any]:
        """Tepe yakalama fırsatı analizi"""
        try:
            peak_score = 0
            max_score = 0
            signals = []
            
            # RSI Overbought kontrolü
            rsi_value = gram_signal.get('indicators', {}).get('rsi')
            if isinstance(rsi_value, (int, float)):
                max_score += 20
                if rsi_value >= RSI_OVERBOUGHT:
                    peak_score += 20
                    signals.append(f"RSI overbought ({rsi_value:.1f} ≥ {RSI_OVERBOUGHT})")
                elif rsi_value >= RSI_OVERBOUGHT - 5:
                    peak_score += 15
                    signals.append(f"RSI near overbought ({rsi_value:.1f})")
            
            # Bollinger Bands üst banda yakınlık
            bb_data = gram_signal.get('indicators', {}).get('bollinger', {})
            bb_position = bb_data.get('position', 'middle')
            max_score += 15
            if bb_position == 'above_upper':
                peak_score += 15
                signals.append("Fiyat Bollinger üst bandının üstünde")
            elif bb_position == 'near_upper':
                peak_score += 10
                signals.append("Fiyat Bollinger üst bandına yakın")
            
            # RSI Divergence (bearish)
            if divergence_data and divergence_data.get('detected') and divergence_data.get('type') == 'bearish':
                max_score += 25
                div_strength = divergence_data.get('strength', 0)
                peak_score += div_strength * 25
                signals.append(f"Bearish RSI divergence (güç: {div_strength:.2f})")
            else:
                max_score += 25
            
            # Direnç seviyesi yakınlığı
            resistance_levels = gram_signal.get('resistance_levels', [])
            current_price = gram_signal.get('price', 0)
            if resistance_levels and current_price:
                max_score += 15
                nearest_resistance = resistance_levels[0]
                resistance_distance = abs(float(current_price) - float(nearest_resistance.level)) / float(current_price)
                
                if resistance_distance <= 0.01:
                    peak_score += 15
                    signals.append(f"Güçlü direnç seviyesinde ({nearest_resistance.level})")
                elif resistance_distance <= 0.02:
                    peak_score += 10
                    signals.append("Direnç seviyesine yakın")
            
            # MACD negatif momentum
            macd_data = gram_signal.get('indicators', {}).get('macd', {})
            if macd_data.get('histogram', 0) < 0 and macd_data.get('macd', 0) > 0:
                max_score += 10
                peak_score += 10
                signals.append("MACD negatif momentum")
            else:
                max_score += 10
            
            # Pattern desteği
            if patterns and patterns.get('pattern_found'):
                pattern = patterns.get('best_pattern', {})
                pattern_type = pattern.get('type', '')
                pattern_name = pattern.get('pattern', '').lower()
                
                if pattern_type == 'BEARISH':
                    max_score += 15
                    pattern_confidence = pattern.get('confidence', 0)
                    pattern_priority = self.pattern_priority.get(pattern_name, 0.5)
                    pattern_bonus = pattern_confidence * pattern_priority * 15
                    peak_score += pattern_bonus
                    signals.append(f"Bearish pattern: {pattern_name}")
                else:
                    max_score += 15
            
            final_score = peak_score / max_score if max_score > 0 else 0
            is_peak_opportunity = final_score >= PEAK_DETECTION_CRITERIA['min_combined_score']
            
            return {
                "is_peak_opportunity": is_peak_opportunity,
                "score": final_score,
                "raw_score": peak_score,
                "max_possible_score": max_score,
                "signals": signals,
                "confidence_boost": 0.15 if is_peak_opportunity else 0
            }
            
        except Exception as e:
            logger.error(f"Peak opportunity analysis error: {str(e)}")
            return {"is_peak_opportunity": False, "score": 0, "signals": []}
    
    def _multi_timeframe_confirmation(self, gram_signal: Dict, timeframe: str,
                                    market_volatility: float) -> Dict[str, Any]:
        """Multi-timeframe doğrulama sistemi"""
        try:
            # Şimdilik tek timeframe analizi - gelecekte genişletilebilir
            current_signal = gram_signal.get('signal', 'HOLD')
            current_confidence = gram_signal.get('confidence', 0.5)
            
            # Timeframe ağırlığı
            tf_weight = TIMEFRAME_WEIGHTS.get(timeframe, 0.25)
            
            # Volatilite ayarlaması
            volatility_adjustment = 1.0
            if market_volatility > 1.5:  # Yüksek volatilite
                volatility_adjustment = 0.8
            elif market_volatility < 0.5:  # Düşük volatilite
                volatility_adjustment = 1.1
            
            adjusted_confidence = current_confidence * tf_weight * volatility_adjustment
            
            return {
                "confirmed": adjusted_confidence > MIN_CONFIDENCE_THRESHOLDS.get(timeframe, 0.6),
                "confidence": min(adjusted_confidence, 1.0),
                "timeframe_weight": tf_weight,
                "volatility_adjustment": volatility_adjustment,
                "supporting_timeframes": [timeframe]  # Şimdilik tek
            }
            
        except Exception as e:
            logger.error(f"Multi-timeframe confirmation error: {str(e)}")
            return {"confirmed": False, "confidence": 0.5}
    
    def _analyze_pattern_priority(self, patterns: Dict) -> Dict[str, Any]:
        """Pattern öncelik sistemi"""
        try:
            if not patterns or not patterns.get('pattern_found'):
                return {
                    "has_pattern": False,
                    "priority_score": 0,
                    "pattern_type": "NONE"
                }
            
            best_pattern = patterns.get('best_pattern', {})
            pattern_name = best_pattern.get('pattern', '').lower()
            pattern_confidence = best_pattern.get('confidence', 0)
            pattern_type = best_pattern.get('type', 'NEUTRAL')
            
            # Pattern prioritesi (reliability score)
            priority_score = self.pattern_priority.get(pattern_name, 0.5)
            
            # Weighted score
            weighted_score = pattern_confidence * priority_score
            
            return {
                "has_pattern": True,
                "pattern_name": pattern_name,
                "pattern_type": pattern_type,
                "base_confidence": pattern_confidence,
                "priority_score": priority_score,
                "weighted_score": weighted_score,
                "is_high_priority": priority_score >= 0.80  # Head & Shoulders, Double patterns
            }
            
        except Exception as e:
            logger.error(f"Pattern priority analysis error: {str(e)}")
            return {"has_pattern": False, "priority_score": 0}
    
    def _assess_false_signal_risk(self, gram_signal: Dict, global_trend: Dict,
                                 currency_risk: Dict, market_volatility: float) -> Dict[str, Any]:
        """False signal riski değerlendirmesi"""
        try:
            risk_factors = []
            risk_score = 0
            
            # Yüksek volatilite riski
            if market_volatility > 1.5:
                risk_score += 0.2
                risk_factors.append(f"Yüksek volatilite ({market_volatility:.1f}%)")
            
            # Trend uyumsuzluğu
            gram_trend = gram_signal.get('trend', 'NEUTRAL')
            gram_signal_dir = gram_signal.get('signal', 'HOLD')
            
            if (gram_trend == 'BEARISH' and gram_signal_dir == 'BUY') or \
               (gram_trend == 'BULLISH' and gram_signal_dir == 'SELL'):
                risk_score += 0.15
                risk_factors.append("Trend-sinyal uyumsuzluğu")
            
            # Kur riski
            currency_risk_level = currency_risk.get('risk_level', 'MEDIUM')
            if currency_risk_level in ['HIGH', 'EXTREME']:
                risk_score += 0.1
                risk_factors.append(f"Yüksek kur riski ({currency_risk_level})")
            
            # Düşük güven skoru
            confidence = gram_signal.get('confidence', 0.5)
            if confidence < 0.6:
                risk_score += 0.1
                risk_factors.append(f"Düşük güven ({confidence:.2f})")
            
            # Global trend uyumsuzluğu
            global_direction = global_trend.get('trend_direction', 'UNKNOWN')
            if global_direction != 'UNKNOWN':
                if (global_direction == 'BEARISH' and gram_signal_dir == 'BUY') or \
                   (global_direction == 'BULLISH' and gram_signal_dir == 'SELL'):
                    risk_score += 0.1
                    risk_factors.append("Global trend uyumsuzluğu")
            
            risk_level = "LOW"
            if risk_score > 0.3:
                risk_level = "HIGH"
            elif risk_score > 0.15:
                risk_level = "MEDIUM"
            
            return {
                "risk_level": risk_level,
                "risk_score": min(risk_score, 1.0),
                "risk_factors": risk_factors,
                "confidence_penalty": risk_score * 0.3  # Güven skorundan düşülecek
            }
            
        except Exception as e:
            logger.error(f"False signal risk assessment error: {str(e)}")
            return {"risk_level": "MEDIUM", "risk_score": 0.2}
    
    def _determine_final_signal(self, gram_signal: Dict, dip_opportunity: Dict,
                              peak_opportunity: Dict, mtf_confirmation: Dict,
                              pattern_analysis: Dict, false_signal_risk: Dict) -> str:
        """Final sinyal kararı"""
        try:
            base_signal = gram_signal.get('signal', 'HOLD')
            
            # Dip fırsat kontrolü (en yüksek öncelik)
            if dip_opportunity.get('is_dip_opportunity'):
                if base_signal == 'BUY' or base_signal == 'HOLD':
                    return 'BUY'
            
            # Peak fırsat kontrolü
            if peak_opportunity.get('is_peak_opportunity'):
                if base_signal == 'SELL' or base_signal == 'HOLD':
                    return 'SELL'
            
            # Yüksek false signal riski - HOLD'a çevir
            if false_signal_risk.get('risk_level') == 'HIGH':
                return 'HOLD'
            
            # Multi-timeframe doğrulaması
            if not mtf_confirmation.get('confirmed') and base_signal != 'HOLD':
                return 'HOLD'
            
            # Pattern desteği
            if pattern_analysis.get('has_pattern') and pattern_analysis.get('is_high_priority'):
                pattern_type = pattern_analysis.get('pattern_type')
                if pattern_type == 'BULLISH' and base_signal != 'SELL':
                    return 'BUY'
                elif pattern_type == 'BEARISH' and base_signal != 'BUY':
                    return 'SELL'
            
            return base_signal
            
        except Exception as e:
            logger.error(f"Final signal determination error: {str(e)}")
            return 'HOLD'
    
    def _calculate_combined_confidence(self, gram_signal: Dict, mtf_confirmation: Dict,
                                     pattern_analysis: Dict, false_signal_risk: Dict,
                                     timeframe: str, dip_opportunity: Dict,
                                     peak_opportunity: Dict) -> float:
        """Birleşik güven skoru hesaplama"""
        try:
            base_confidence = gram_signal.get('confidence', 0.5)
            
            # Dip/Peak bonus
            dip_boost = dip_opportunity.get('confidence_boost', 0)
            peak_boost = peak_opportunity.get('confidence_boost', 0)
            opportunity_boost = max(dip_boost, peak_boost)
            
            # MTF confirmation
            mtf_boost = mtf_confirmation.get('confidence', base_confidence) - base_confidence
            
            # Pattern boost
            pattern_boost = 0
            if pattern_analysis.get('has_pattern'):
                pattern_weighted = pattern_analysis.get('weighted_score', 0)
                if pattern_analysis.get('is_high_priority'):
                    pattern_boost = pattern_weighted * 0.2
                else:
                    pattern_boost = pattern_weighted * 0.1
            
            # Risk penalty
            risk_penalty = false_signal_risk.get('confidence_penalty', 0)
            
            # Final calculation
            final_confidence = base_confidence + opportunity_boost + mtf_boost + pattern_boost - risk_penalty
            
            # Timeframe minimum eşiği
            min_threshold = MIN_CONFIDENCE_THRESHOLDS.get(timeframe, 0.6)
            
            return max(min_threshold * 0.8, min(final_confidence, 1.0))
            
        except Exception as e:
            logger.error(f"Combined confidence calculation error: {str(e)}")
            return 0.5
    
    def _determine_signal_strength(self, confidence: float, dip_opportunity: Dict,
                                 peak_opportunity: Dict, pattern_analysis: Dict) -> str:
        """Sinyal gücünü belirle"""
        try:
            # Base strength from confidence
            if confidence >= 0.8:
                strength = "STRONG"
            elif confidence >= 0.65:
                strength = "MODERATE"
            else:
                strength = "WEAK"
            
            # Opportunity boost
            if dip_opportunity.get('is_dip_opportunity') or peak_opportunity.get('is_peak_opportunity'):
                if strength == "WEAK":
                    strength = "MODERATE"
                elif strength == "MODERATE":
                    strength = "STRONG"
            
            # High priority pattern boost
            if pattern_analysis.get('is_high_priority') and pattern_analysis.get('weighted_score', 0) > 0.7:
                if strength == "WEAK":
                    strength = "MODERATE"
            
            return strength
            
        except Exception as e:
            logger.error(f"Signal strength determination error: {str(e)}")
            return "WEAK"