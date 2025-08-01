"""
Signal Combiner - Tüm sinyalleri birleştirip nihai sinyal üreten modül
"""
from typing import Dict, Any, List, Tuple, Optional
from decimal import Decimal
import logging
from collections import defaultdict

from utils.constants import (
    MIN_CONFIDENCE_THRESHOLDS,
    MIN_VOLATILITY_THRESHOLD,
    GLOBAL_TREND_MISMATCH_PENALTY
)

logger = logging.getLogger(__name__)


class SignalCombiner:
    """Farklı kaynaklardan gelen sinyalleri birleştirir"""
    
    def __init__(self):
        # Ağırlıklar - USD/TRY sabit olduğu için global trend ağırlığı artırıldı
        self.weights = {
            "gram_analysis": 0.30,      # %30 - Gram sinyal (azaltıldı)
            "global_trend": 0.40,       # %40 - Global trend (büyük artış)
            "currency_risk": 0.05,      # %5 - Kur riski (minimize edildi)
            "advanced_indicators": 0.15, # %15 - CCI + MFI
            "pattern_recognition": 0.10  # %10 - Pattern bonus
        }
        
        # Dip yakalama parametreleri
        self.dip_detection_weights = {
            "divergence": 0.35,          # %35 - Divergence en güçlü sinyal
            "oversold_rsi": 0.25,        # %25 - RSI < 30
            "momentum_exhaustion": 0.20, # %20 - Momentum tükenmesi
            "smart_money": 0.20          # %20 - Kurumsal alım
        }
        
    def combine_signals(self, 
                       gram_signal: Dict,
                       global_trend: Dict,
                       currency_risk: Dict,
                       advanced_indicators: Dict,
                       patterns: Dict,
                       timeframe: str,
                       market_volatility: float,
                       divergence_data: Dict = None,
                       momentum_data: Dict = None,
                       smart_money_data: Dict = None,
                       multi_day_pattern: Dict = None) -> Dict[str, Any]:
        """
        Tüm sinyalleri birleştir ve nihai sinyal üret
        
        Args:
            gram_signal: Gram altın analiz sinyali
            global_trend: Global trend analizi
            currency_risk: Kur riski analizi
            advanced_indicators: CCI + MFI analizi
            patterns: Pattern tanıma sonuçları
            timeframe: Zaman dilimi
            market_volatility: Piyasa volatilitesi
            
        Returns:
            Birleştirilmiş sinyal ve güven skoru
        """
        # Temel sinyaller
        gram_signal_type = gram_signal.get("signal", "HOLD")
        gram_confidence = gram_signal.get("confidence", 0)
        global_direction = global_trend.get("trend_direction", "NEUTRAL")
        risk_level = currency_risk.get("risk_level", "MEDIUM")
        
        # Debug: Ana parametreler
        logger.debug(f"🔍 SIGNAL COMBINER INPUT:")
        logger.debug(f"   Gram signal: {gram_signal_type} (conf: {gram_confidence:.2%})")
        logger.debug(f"   Global trend: {global_trend.get('trend')} (dir: {global_direction})")
        logger.debug(f"   Currency risk: {risk_level}")
        logger.debug(f"   Market volatility: {market_volatility:.3f}")
        
        # Dip detection analizi
        dip_score, dip_signals = self._analyze_dip_opportunity(
            global_direction, divergence_data, momentum_data, 
            smart_money_data, advanced_indicators
        )
        logger.debug(f"📊 Dip Detection Score: {dip_score:.2f}, Signals: {dip_signals}")
        
        # Sinyal puanları
        signal_scores = defaultdict(float)
        
        # 1. Gram altın sinyali (ana ağırlık)
        signal_scores[gram_signal_type] += self.weights["gram_analysis"] * (
            gram_confidence if gram_signal_type != "HOLD" else 1.0
        )
        logger.debug(f"📈 After gram signal: {dict(signal_scores)}")
        
        # 2. Global trend uyumu - Artık teknik göstergeler de dahil
        self._apply_global_trend_score(
            signal_scores, global_direction, gram_signal_type, global_trend
        )
        
        # 3. Kur riski etkisi
        self._apply_currency_risk_score(
            signal_scores, risk_level, gram_signal_type
        )
        
        # 4. Gelişmiş göstergeler
        self._apply_advanced_indicators_score(
            signal_scores, advanced_indicators
        )
        
        # 5. Pattern tanıma bonusu
        self._apply_pattern_recognition_score(
            signal_scores, patterns
        )
        
        # Nihai sinyal belirleme
        logger.debug(f"📊 Before determine_final_signal - Scores: {dict(signal_scores)}")
        
        # Multi-day pattern kontrolü
        multi_day_override = False
        if multi_day_pattern:
            # 3 günlük dip yakınındaysak ve gram BUY diyorsa
            if (multi_day_pattern.get("is_near_bottom") and 
                gram_signal_type == "BUY" and 
                gram_confidence >= 0.45):
                logger.info(f"📉 MULTI-DAY DIP OVERRIDE: Near 3-day bottom, using BUY signal")
                multi_day_override = True
            # 3 günlük tepe yakınındaysak ve gram SELL diyorsa
            elif (multi_day_pattern.get("is_near_top") and 
                  gram_signal_type == "SELL" and 
                  gram_confidence >= 0.45):
                logger.info(f"📈 MULTI-DAY TOP OVERRIDE: Near 3-day top, using SELL signal")
                multi_day_override = True
        
        # Gram override - eğer gram güçlü sinyal veriyorsa direkt kullan
        gram_override_applied = False
        logger.info(f"🔍 GRAM OVERRIDE CHECK: signal={gram_signal_type}, conf={gram_confidence:.3f}, threshold=0.45")
        
        if (gram_signal_type in ["BUY", "SELL"] and gram_confidence >= 0.45) or multi_day_override:
            logger.info(f"🎯 GRAM OVERRIDE ACTIVATED: Using gram signal {gram_signal_type} (conf={gram_confidence:.2%})")
            final_signal = gram_signal_type
            gram_override_applied = True
        else:
            logger.info(f"❌ GRAM OVERRIDE NOT ACTIVATED: Conditions not met")
            final_signal = self._determine_final_signal(signal_scores)
            
        logger.debug(f"🎯 After determine_final_signal: {final_signal}")
        logger.debug(f"📊 Signal scores: {dict(signal_scores)}")
        
        # Güven skoru hesaplama
        if gram_override_applied:
            # Override durumunda gram confidence'ı direkt kullan
            confidence = gram_confidence
            logger.info(f"📊 GRAM OVERRIDE: Using gram confidence directly: {confidence:.2%}")
        else:
            confidence = self._calculate_confidence(
                final_signal, signal_scores, gram_confidence, 
                global_trend, currency_risk
            )
        logger.debug(f"🔢 Calculated confidence: {confidence:.3f}")
        
        # Dip yakalama override - BEARISH trend'de güçlü dip sinyali varsa
        if global_direction == "BEARISH" and dip_score >= 0.4:
            logger.info(f"🎯 DIP DETECTION OVERRIDE: Score={dip_score:.2f}, Original signal={final_signal}")
            final_signal = "BUY"
            confidence = max(confidence, dip_score * 1.2)  # Dip skorunu %20 boost ile güven olarak kullan
            
            # Pozisyon boyutu önerisi ekle
            position_size = self._calculate_dip_position_size(dip_score, risk_level)
            logger.info(f"💰 Recommended position size: {position_size:.0%}")
        
        # Volatilite ve timeframe filtreleri - Override durumunda atlama
        original_signal = final_signal
        logger.debug(f"🔍 BEFORE FILTERS: signal={final_signal}, conf={confidence:.3f}, volatility={market_volatility:.3f}")
        logger.debug(f"   Timeframe: {timeframe}, Min threshold: {MIN_CONFIDENCE_THRESHOLDS.get(timeframe, 0.5):.3f}")
        
        if gram_override_applied:
            logger.info(f"🎯 GRAM OVERRIDE: Skipping filters for {final_signal}")
            strength = self._calculate_signal_strength(confidence, risk_level)
        else:
            final_signal, strength = self._apply_filters(
                final_signal, confidence, market_volatility, 
                timeframe, global_direction, risk_level, dip_score
            )
        
        if original_signal != final_signal:
            logger.info(f"🔄 FILTER CHANGED SIGNAL: {original_signal} -> {final_signal} (conf={confidence:.3f})")
        logger.debug(f"⚡ Final signal: {final_signal}, strength: {strength}, confidence: {confidence:.3f}")
        
        # Global trend uyumsuzluk cezası - Override durumunda uygulama
        if final_signal != "HOLD" and not gram_override_applied:
            confidence = self._apply_trend_mismatch_penalty(
                final_signal, global_direction, confidence, dip_score
            )
        
        # Dip detection bilgileri ekle
        result = {
            "signal": final_signal,
            "confidence": confidence,
            "strength": strength,
            "scores": dict(signal_scores),
            "raw_confidence": signal_scores[final_signal],
            "market_volatility": market_volatility,
            "dip_detection": {
                "score": dip_score,
                "signals": dip_signals,
                "is_dip_opportunity": dip_score >= 0.6
            }
        }
        
        # BEARISH trend'de dip yakaladıysak pozisyon boyutu önerisi ekle
        if global_direction == "BEARISH" and dip_score >= 0.6 and final_signal == "BUY":
            result["position_size_recommendation"] = self._calculate_dip_position_size(dip_score, risk_level)
            result["stop_loss_recommendation"] = "Tight stop-loss: %1-2 below entry"
            
        return result
    
    def _apply_global_trend_score(self, scores: defaultdict, 
                                  global_dir: str, gram_signal: str,
                                  global_trend: Dict = None):
        """Global trend skorunu uygula - Artık teknik göstergeler de var"""
        trend_weight = self.weights["global_trend"]
        
        # Trend uyum tablosu
        trend_signal_map = {
            ("BULLISH", "BUY"): ("BUY", 1.0),
            ("BEARISH", "SELL"): ("SELL", 1.0),
            ("BULLISH", "SELL"): ("HOLD", 0.5),
            ("BEARISH", "BUY"): ("HOLD", 0.5),
        }
        
        signal_to_add, multiplier = trend_signal_map.get(
            (global_dir, gram_signal), 
            ("HOLD", 0.3)
        )
        
        # Temel trend skoru
        scores[signal_to_add] += trend_weight * multiplier * 0.6  # %60 trend direction
        
        # ONS/USD teknik göstergelerinden gelen sinyal
        if global_trend and 'indicator_signal' in global_trend:
            indicator_signal = global_trend['indicator_signal']
            signal_type = indicator_signal.get('signal', 'NEUTRAL')
            confidence = indicator_signal.get('confidence', 0)
            
            # Teknik gösterge sinyalini ekle (%40 ağırlık)
            if 'BUY' in signal_type:
                scores['BUY'] += trend_weight * confidence * 0.4
            elif 'SELL' in signal_type:
                scores['SELL'] += trend_weight * confidence * 0.4
            else:
                scores['HOLD'] += trend_weight * 0.4 * 0.5
    
    def _apply_currency_risk_score(self, scores: defaultdict, 
                                   risk_level: str, gram_signal: str):
        """Kur riski skorunu uygula"""
        risk_weight = self.weights["currency_risk"]
        is_high_risk = risk_level in ["HIGH", "EXTREME"]
        
        if is_high_risk:
            scores["HOLD"] += risk_weight * 0.7
            # Mevcut sinyalleri zayıflat
            for sig in ["BUY", "SELL"]:
                scores[sig] *= 0.7
        elif gram_signal in ["BUY", "SELL"]:
            scores[gram_signal] += risk_weight * 0.5
    
    def _apply_advanced_indicators_score(self, scores: defaultdict, 
                                        advanced: Dict):
        """Gelişmiş gösterge skorlarını uygula"""
        advanced_weight = self.weights["advanced_indicators"]
        advanced_signal = advanced.get("combined_signal", "NEUTRAL")
        advanced_confidence = advanced.get("combined_confidence", 0)
        
        if advanced_signal != "NEUTRAL":
            scores[advanced_signal] += advanced_weight * advanced_confidence
            
            # Divergence varsa ekstra güç
            if advanced.get("divergence"):
                scores[advanced_signal] += advanced_weight * 0.3
    
    def _apply_pattern_recognition_score(self, scores: defaultdict, 
                                        patterns: Dict):
        """Pattern tanıma skorlarını uygula"""
        pattern_weight = self.weights["pattern_recognition"]
        
        if patterns.get("pattern_found"):
            pattern_signal = patterns.get("signal", "NEUTRAL")
            pattern_confidence = patterns.get("confidence", 0)
            
            if pattern_signal != "NEUTRAL":
                scores[pattern_signal] += pattern_weight * pattern_confidence
                
                # Güçlü pattern'ler için ekstra bonus
                best_pattern = patterns.get("best_pattern", {})
                strong_patterns = ["HEAD_AND_SHOULDERS", "INVERSE_HEAD_AND_SHOULDERS"]
                if best_pattern.get("pattern") in strong_patterns:
                    scores[pattern_signal] += pattern_weight * 0.5
    
    def _determine_final_signal(self, scores: defaultdict) -> str:
        """Skorlara göre nihai sinyali belirle"""
        if not scores:
            return "HOLD"
            
        return max(scores.items(), key=lambda x: x[1])[0]
    
    def _calculate_confidence(self, final_signal: str, scores: defaultdict,
                            gram_confidence: float, global_trend: Dict,
                            currency_risk: Dict) -> float:
        """Nihai güven skorunu hesapla"""
        # Destekleyen analizörlerin ağırlığını hesapla
        supporting_weight = 0
        
        # Gram analizi desteği
        if scores.get(final_signal, 0) > 0:
            supporting_weight += self.weights["gram_analysis"]
        
        # Global trend desteği
        if self._check_trend_support(final_signal, global_trend):
            supporting_weight += self.weights["global_trend"]
        
        # Currency risk desteği
        if self._check_risk_support(final_signal, currency_risk):
            supporting_weight += self.weights["currency_risk"]
        
        # Skor bazlı güven
        if supporting_weight > 0:
            score_confidence = min(scores[final_signal] / supporting_weight, 1.0)
        else:
            score_confidence = 0.3
        
        # Final güven hesaplama
        if final_signal == "HOLD":
            # HOLD için gram güveni daha önemli
            normalized_confidence = (gram_confidence * 0.7) + (score_confidence * 0.3)
        else:
            # BUY/SELL için dengeli
            normalized_confidence = (gram_confidence * 0.6) + (score_confidence * 0.4)
            # Minimum güven
            normalized_confidence = max(normalized_confidence, 0.4)
        
        logger.debug(f"Confidence: gram={gram_confidence:.3f}, score={score_confidence:.3f}, final={normalized_confidence:.3f}")
        
        return normalized_confidence
    
    def _apply_filters(self, signal: str, confidence: float, 
                      volatility: float, timeframe: str,
                      global_dir: str, risk_level: str,
                      dip_score: float = 0) -> Tuple[str, str]:
        """Yüksek işlem maliyeti için sıkı filtreler - Sadece en güçlü sinyaller geçer"""
        logger.debug(f"🔍 HIGH-COST FILTER CHECK: signal={signal}, conf={confidence:.3f}, vol={volatility:.3f}, tf={timeframe}")
        
        # 1. Volatilite filtresi - Artık daha sıkı
        if volatility < MIN_VOLATILITY_THRESHOLD and signal != "HOLD":
            logger.debug(f"🔄 FILTER: Low volatility ({volatility:.3f}% < {MIN_VOLATILITY_THRESHOLD}%), converting {signal} to HOLD")
            return "HOLD", "WEAK"
        
        # 2. Timeframe güven eşiği - Artık çok daha sıkı
        if signal != "HOLD":
            min_confidence = MIN_CONFIDENCE_THRESHOLDS.get(timeframe, 0.5)
            
            # 3. Yüksek işlem maliyeti için ek güven kontrolü
            high_cost_confidence_multiplier = 1.1  # %10 daha yüksek eşik
            adjusted_min_confidence = min_confidence * high_cost_confidence_multiplier
            
            # Dip detection durumunda bile eşiği çok düşürme
            if dip_score > 0.4 or (global_dir == "BEARISH" and signal == "BUY"):
                adjusted_min_confidence *= 0.95  # Sadece %5 azalt
                logger.debug(f"🎯 FILTER: Minor threshold reduction for strong dip: {adjusted_min_confidence:.3f}")
            
            logger.debug(f"🔍 HIGH-COST FILTER: Checking confidence {confidence:.3f} >= {adjusted_min_confidence:.3f} for {timeframe}")
            if confidence < adjusted_min_confidence:
                logger.debug(f"🔄 HIGH-COST FILTER: Insufficient confidence for {timeframe}: {confidence:.3f} < {adjusted_min_confidence:.3f}, converting {signal} to HOLD")
                return "HOLD", "WEAK"
        
        # 4. Risk seviyesi filtresi - Yüksek riskde daha sıkı
        if signal != "HOLD" and risk_level in ["HIGH", "EXTREME"]:
            risk_confidence_threshold = 0.85  # %85 güven gerekli
            if confidence < risk_confidence_threshold:
                logger.debug(f"🔄 RISK FILTER: High risk requires higher confidence: {confidence:.3f} < {risk_confidence_threshold:.3f}")
                return "HOLD", "WEAK"
        
        # 5. Momentum ve trend uyum kontrolü - Sadece güçlü trend uyumları geçsin
        if signal != "HOLD":
            if not self._check_strong_trend_alignment(signal, global_dir, confidence):
                logger.debug(f"🔄 TREND FILTER: Weak trend alignment, converting {signal} to HOLD")
                return "HOLD", "WEAK"
        
        # Sinyal gücü belirleme - Daha sıkı kriterler
        strength = self._calculate_signal_strength_high_cost(confidence, risk_level)
        logger.debug(f"✅ HIGH-COST FILTER: Signal {signal} passed all strict filters, strength={strength}")
        
        return signal, strength
    
    def _check_strong_trend_alignment(self, signal: str, global_dir: str, confidence: float) -> bool:
        """Güçlü trend uyumu kontrolü - Yüksek işlem maliyeti için"""
        # BUY sinyali için BULLISH trend gerekli (dip yakalama hariç)
        if signal == "BUY":
            if global_dir == "BULLISH":
                return True
            elif global_dir == "BEARISH" and confidence >= 0.85:  # Çok güçlü dip sinyali
                return True
            else:
                return False
        
        # SELL sinyali için BEARISH trend gerekli
        if signal == "SELL":
            if global_dir == "BEARISH":
                return True
            elif global_dir == "BULLISH" and confidence >= 0.85:  # Çok güçlü tepe sinyali
                return True
            else:
                return False
        
        return True  # HOLD için her zaman true
    
    def _calculate_signal_strength_high_cost(self, confidence: float, risk: str) -> str:
        """Yüksek işlem maliyeti için sinyal gücü hesaplama - Daha sıkı kriterler"""
        # Güven skoruna göre temel güç - Daha yüksek eşikler
        if confidence >= 0.85:
            base_strength = "STRONG"
        elif confidence >= 0.75:
            base_strength = "MODERATE"
        else:
            base_strength = "WEAK"
        
        # Risk seviyesine göre ayarlama - Daha sıkı
        if risk in ["HIGH", "EXTREME"]:
            # Yüksek risk durumunda güç seviyesini düşür
            if base_strength == "STRONG":
                return "MODERATE"
            else:
                return "WEAK"
        elif risk == "MEDIUM" and base_strength == "WEAK":
            return "WEAK"  # Orta risk durumunda weak sinyalleri kabul etme
        
        return base_strength
    
    def _apply_trend_mismatch_penalty(self, signal: str, global_dir: str,
                                     confidence: float, dip_score: float = 0) -> float:
        """Global trend uyumsuzluk cezası uygula"""
        # BUY sinyal ama global trend BEARISH - Dip detection yoksa ceza uygula
        if signal == "BUY" and global_dir == "BEARISH" and dip_score < 0.6:
            confidence *= GLOBAL_TREND_MISMATCH_PENALTY
            logger.info(f"Trend mismatch penalty: confidence reduced to {confidence:.3f}")
        # SELL sinyal ama global trend BULLISH
        elif signal == "SELL" and global_dir == "BULLISH":
            confidence *= GLOBAL_TREND_MISMATCH_PENALTY
            logger.info(f"Trend mismatch penalty: confidence reduced to {confidence:.3f}")
        
        return confidence
    
    def _calculate_signal_strength(self, confidence: float, risk: str) -> str:
        """Sinyal gücünü hesapla"""
        # Güven skoruna göre temel güç
        if confidence >= 0.75:
            base_strength = "STRONG"
        elif confidence >= 0.55:
            base_strength = "MODERATE"
        else:
            base_strength = "WEAK"
        
        # Risk seviyesine göre ayarlama
        if risk in ["HIGH", "EXTREME"]:
            # Yüksek risk durumunda güç seviyesini düşür
            if base_strength == "STRONG":
                return "MODERATE"
            elif base_strength == "MODERATE":
                return "WEAK"
        
        return base_strength
    
    def _check_trend_support(self, signal: str, global_trend: Dict) -> bool:
        """Global trend'in sinyali destekleyip desteklemediğini kontrol et"""
        trend_dir = global_trend.get("trend_direction", "NEUTRAL")
        
        if signal == "BUY" and trend_dir == "BULLISH":
            return True
        elif signal == "SELL" and trend_dir == "BEARISH":
            return True
        elif signal == "HOLD" and trend_dir == "NEUTRAL":
            return True
        
        return False
    
    def _check_risk_support(self, signal: str, currency_risk: Dict) -> bool:
        """Kur riskinin sinyali destekleyip desteklemediğini kontrol et"""
        risk_level = currency_risk.get("risk_level", "MEDIUM")
        
        if signal == "HOLD" and risk_level in ["HIGH", "EXTREME"]:
            return True
        elif signal in ["BUY", "SELL"] and risk_level in ["LOW", "MEDIUM"]:
            return True
        
        return False
    
    def _analyze_dip_opportunity(self, global_direction: str, 
                                divergence_data: Dict, momentum_data: Dict,
                                smart_money_data: Dict, advanced_indicators: Dict) -> Tuple[float, List[str]]:
        """BEARISH trend'de dip yakalama fırsatı analizi"""
        dip_score = 0.0
        dip_signals = []
        
        # Sadece BEARISH trend'de dip ara
        if global_direction != "BEARISH":
            return 0.0, []
        
        # 1. Bullish Divergence kontrolü
        if divergence_data and divergence_data.get('divergence_type') == 'BULLISH':
            div_strength = divergence_data.get('strength', 'WEAK')
            if div_strength == 'STRONG':
                dip_score += self.dip_detection_weights['divergence'] * 1.0
                dip_signals.append("Strong bullish divergence detected")
            elif div_strength == 'MODERATE':
                dip_score += self.dip_detection_weights['divergence'] * 0.7
                dip_signals.append("Moderate bullish divergence")
            else:
                dip_score += self.dip_detection_weights['divergence'] * 0.4
                dip_signals.append("Weak bullish divergence")
        
        # 2. RSI Oversold kontrolü
        rsi_value = advanced_indicators.get('rsi')
        if rsi_value and rsi_value < 30:
            oversold_severity = (30 - rsi_value) / 30  # 0'a ne kadar yakın
            dip_score += self.dip_detection_weights['oversold_rsi'] * (0.7 + oversold_severity * 0.3)
            dip_signals.append(f"RSI oversold at {rsi_value:.1f}")
        elif rsi_value and rsi_value < 35:
            dip_score += self.dip_detection_weights['oversold_rsi'] * 0.5
            dip_signals.append(f"RSI approaching oversold at {rsi_value:.1f}")
        
        # 3. Momentum Exhaustion kontrolü
        if momentum_data and momentum_data.get('exhaustion_detected'):
            if momentum_data.get('exhaustion_type') == 'BULLISH':  # Bearish exhaustion = Bullish reversal
                exhaustion_score = momentum_data.get('exhaustion_score', 0)
                dip_score += self.dip_detection_weights['momentum_exhaustion'] * exhaustion_score
                dip_signals.append(f"Momentum exhaustion detected (score: {exhaustion_score:.2f})")
                
                # Volume spike bonus
                vol_analysis = momentum_data.get('volatility_analysis', {})
                if vol_analysis.get('volatility_spike'):
                    dip_score += 0.1  # Bonus
                    dip_signals.append("Volume spike confirms exhaustion")
        
        # 4. Smart Money Accumulation kontrolü
        if smart_money_data:
            sm_direction = smart_money_data.get('smart_money_direction')
            if sm_direction == 'BULLISH':
                manipulation_score = smart_money_data.get('manipulation_score', 0)
                dip_score += self.dip_detection_weights['smart_money'] * manipulation_score
                dip_signals.append(f"Smart money accumulation detected (score: {manipulation_score:.2f})")
                
                # Stop hunt bonus
                if smart_money_data.get('stop_hunt_detected'):
                    stop_hunt_type = smart_money_data.get('stop_hunt_details', {}).get('type')
                    if 'BULLISH' in stop_hunt_type:
                        dip_score += 0.15  # Bonus
                        dip_signals.append("Bullish stop hunt confirmed")
        
        # Support bounce bonus (pattern_recognition'dan gelirse)
        # Bu kısım patterns verisiyle genişletilebilir
        
        # Normalize score (0-1 arası)
        dip_score = min(dip_score, 1.0)
        
        # Eğer hiç sinyal yoksa ama RSI düşükse minimal skor ver
        if dip_score == 0 and rsi_value and rsi_value < 40:
            dip_score = 0.2
            dip_signals.append("Potential oversold bounce setup")
        
        return round(dip_score, 3), dip_signals
    
    def _calculate_dip_position_size(self, dip_score: float, risk_level: str) -> float:
        """Dip yakalama için pozisyon boyutu önerisi"""
        # Base position size dip skoruna göre
        if dip_score >= 0.8:
            base_size = 0.7  # %70
        elif dip_score >= 0.6:
            base_size = 0.5  # %50
        else:
            base_size = 0.3  # %30
        
        # Risk seviyesine göre ayarla
        risk_multipliers = {
            "LOW": 1.2,
            "MEDIUM": 1.0,
            "HIGH": 0.7,
            "EXTREME": 0.5
        }
        
        risk_multiplier = risk_multipliers.get(risk_level, 1.0)
        final_size = base_size * risk_multiplier
        
        # Min-max limits
        return max(0.2, min(0.8, final_size))