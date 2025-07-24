"""
Signal Combiner - Tüm sinyalleri birleştirip nihai sinyal üreten modül
"""
from typing import Dict, Any, List, Tuple
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
        # Ağırlıklar - toplam 1.0 olmalı
        self.weights = {
            "gram_analysis": 0.35,      # %35 - Ana sinyal
            "global_trend": 0.20,       # %20 - Trend doğrulama
            "currency_risk": 0.15,      # %15 - Risk ayarlama
            "advanced_indicators": 0.20, # %20 - CCI + MFI
            "pattern_recognition": 0.10  # %10 - Pattern bonus
        }
        
    def combine_signals(self, 
                       gram_signal: Dict,
                       global_trend: Dict,
                       currency_risk: Dict,
                       advanced_indicators: Dict,
                       patterns: Dict,
                       timeframe: str,
                       market_volatility: float) -> Dict[str, Any]:
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
        
        # Sinyal puanları
        signal_scores = defaultdict(float)
        
        # 1. Gram altın sinyali (ana ağırlık)
        signal_scores[gram_signal_type] += self.weights["gram_analysis"] * (
            gram_confidence if gram_signal_type != "HOLD" else 1.0
        )
        logger.debug(f"📈 After gram signal: {dict(signal_scores)}")
        
        # 2. Global trend uyumu
        self._apply_global_trend_score(
            signal_scores, global_direction, gram_signal_type
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
        final_signal = self._determine_final_signal(signal_scores)
        logger.debug(f"🎯 After determine_final_signal: {final_signal}")
        logger.debug(f"📊 Signal scores: {dict(signal_scores)}")
        
        # Güven skoru hesaplama
        confidence = self._calculate_confidence(
            final_signal, signal_scores, gram_confidence, 
            global_trend, currency_risk
        )
        logger.debug(f"🔢 Calculated confidence: {confidence:.3f}")
        
        # Volatilite ve timeframe filtreleri
        original_signal = final_signal
        final_signal, strength = self._apply_filters(
            final_signal, confidence, market_volatility, 
            timeframe, global_direction, risk_level
        )
        
        if original_signal != final_signal:
            logger.debug(f"🔄 Filter changed signal: {original_signal} -> {final_signal}")
        logger.debug(f"⚡ Final signal: {final_signal}, strength: {strength}")
        
        # Global trend uyumsuzluk cezası
        if final_signal != "HOLD":
            confidence = self._apply_trend_mismatch_penalty(
                final_signal, global_direction, confidence
            )
        
        return {
            "signal": final_signal,
            "confidence": confidence,
            "strength": strength,
            "scores": dict(signal_scores),
            "raw_confidence": signal_scores[final_signal],
            "market_volatility": market_volatility
        }
    
    def _apply_global_trend_score(self, scores: defaultdict, 
                                  global_dir: str, gram_signal: str):
        """Global trend skorunu uygula"""
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
        scores[signal_to_add] += trend_weight * multiplier
    
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
                      global_dir: str, risk_level: str) -> Tuple[str, str]:
        """Volatilite ve timeframe filtrelerini uygula"""
        logger.debug(f"🔍 FILTER CHECK: signal={signal}, conf={confidence:.3f}, vol={volatility:.3f}, tf={timeframe}")
        
        # Volatilite filtresi
        if volatility < MIN_VOLATILITY_THRESHOLD and signal != "HOLD":
            logger.debug(f"🔄 FILTER: Low volatility ({volatility:.3f}% < {MIN_VOLATILITY_THRESHOLD}%), converting {signal} to HOLD")
            return "HOLD", "WEAK"
        
        # Timeframe güven eşiği
        if signal != "HOLD":
            min_confidence = MIN_CONFIDENCE_THRESHOLDS.get(timeframe, 0.5)
            logger.debug(f"🔍 FILTER: Checking confidence {confidence:.3f} >= {min_confidence:.3f} for {timeframe}")
            if confidence < min_confidence:
                logger.debug(f"🔄 FILTER: Low confidence for {timeframe}: {confidence:.3f} < {min_confidence}, converting {signal} to HOLD")
                return "HOLD", "WEAK"
        
        # Sinyal gücü belirleme
        strength = self._calculate_signal_strength(confidence, risk_level)
        logger.debug(f"✅ FILTER: Signal {signal} passed all filters, strength={strength}")
        
        return signal, strength
    
    def _apply_trend_mismatch_penalty(self, signal: str, global_dir: str,
                                     confidence: float) -> float:
        """Global trend uyumsuzluk cezası uygula"""
        # BUY sinyal ama global trend BEARISH
        if signal == "BUY" and global_dir == "BEARISH":
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