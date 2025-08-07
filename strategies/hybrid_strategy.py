"""
Hibrit Strateji - Gram altın, global trend ve kur riskini birleştiren ana strateji
"""
from typing import Dict, Any, List, Tuple, Optional, Union
from decimal import Decimal
import logging
from collections import defaultdict
from utils import timezone

from models.market_data import MarketData, GramAltinCandle
from analyzers.gram_altin_analyzer import GramAltinAnalyzer
from analyzers.global_trend_analyzer import GlobalTrendAnalyzer
from analyzers.currency_risk_analyzer import CurrencyRiskAnalyzer
from indicators.cci import CCI
from indicators.mfi import MFI
from indicators.advanced_patterns import AdvancedPatternRecognition
from analyzers.multi_day_pattern import MultiDayPatternAnalyzer
from utils.risk_management import KellyRiskManager
from utils.constants import (
    SignalType, RiskLevel, StrengthLevel,
    SIGNAL_STRENGTH_MULTIPLIERS, 
    RISK_POSITION_MULTIPLIERS,
    CONFIDENCE_POSITION_MULTIPLIERS,
    MIN_CONFIDENCE_THRESHOLDS,
    MIN_VOLATILITY_THRESHOLD,
    GLOBAL_TREND_MISMATCH_PENALTY
)
from strategies.constants import TRANSACTION_COST_PERCENTAGE

# Yeni modüller
from indicators.fibonacci_retracement import FibonacciRetracement, calculate_fibonacci_analysis
from indicators.smart_money_concepts import SmartMoneyConcepts, calculate_smc_analysis
from indicators.market_regime import MarketRegimeDetector, calculate_market_regime_analysis
from indicators.divergence_detector import AdvancedDivergenceDetector, calculate_divergence_analysis

# Modüler bileşenler
from strategies.signal_combiner import SignalCombiner
# from .hybrid.confluence_manager import ConfluenceManager
# from .hybrid.divergence_manager import DivergenceManager
# from .hybrid.structure_manager import StructureManager
# from .hybrid.momentum_manager import MomentumManager
# from .hybrid.smart_money_manager import SmartMoneyManager

logger = logging.getLogger(__name__)


class HybridStrategy:
    """Tüm analizleri birleştiren hibrit strateji - Orchestrator"""
    
    def __init__(self, storage=None):
        # Ana analizörler
        self.gram_analyzer = GramAltinAnalyzer()
        self.global_analyzer = GlobalTrendAnalyzer()
        self.currency_analyzer = CurrencyRiskAnalyzer()
        
        # Yeni göstergeler
        self.cci = CCI(period=20)
        self.mfi = MFI(period=14)
        self.pattern_recognizer = AdvancedPatternRecognition()
        self.risk_manager = KellyRiskManager()
        
        # Modüler bileşenler
        self.signal_combiner = SignalCombiner()
        
        # Yeni entegre modüller
        self.fibonacci_analyzer = FibonacciRetracement()
        self.smc_analyzer = SmartMoneyConcepts()
        self.market_regime_detector = MarketRegimeDetector()
        self.divergence_detector = AdvancedDivergenceDetector()
        
        # Modül ağırlıkları (toplamı 1.0 olmalı)
        self.module_weights = {
            'gram_analysis': 0.25,
            'market_regime': 0.20,
            'divergence': 0.20,
            'smc': 0.20,
            'fibonacci': 0.15
        }
        
        # Storage referansı
        self.storage = storage
        
        # Cache için değişkenler
        self._last_fibonacci_analysis = None
        self._last_smc_analysis = None
        self._last_market_regime = None
        self._last_divergence_analysis = None
    
    def analyze(self, gram_candles: List[GramAltinCandle], 
                market_data: List[MarketData], timeframe: str = "15m") -> Dict[str, Any]:
        """
        Tüm analizleri birleştirerek nihai sinyal üret
        
        Args:
            gram_candles: Gram altın mum verileri
            market_data: Genel piyasa verileri
            
        Returns:
            Birleşik analiz sonuçları ve sinyal
        """
        try:
            # 1. Gram altın analizi (ana sinyal)
            logger.info(f"Gram analizi başlıyor. Mum sayısı: {len(gram_candles)}")
            gram_analysis = self.gram_analyzer.analyze(gram_candles)
            self._last_gram_analysis = gram_analysis  # RSI için sakla
            logger.info(f"Gram analizi tamamlandı. Fiyat: {gram_analysis.get('price')}")
            
            # Fiyat kontrolü - eğer None veya 0 ise son mum fiyatını kullan
            if not gram_analysis.get('price') or gram_analysis.get('price') == 0:
                if gram_candles and len(gram_candles) > 0:
                    gram_analysis['price'] = gram_candles[-1].close
                    logger.warning(f"Gram price was None/0, using last candle close price: {gram_analysis['price']}")
                else:
                    logger.error("No gram price and no candles available")
                    return self._empty_result()
            
            # 2. Global trend analizi
            global_analysis = self.global_analyzer.analyze(market_data)
            
            # 3. Kur riski analizi
            currency_analysis = self.currency_analyzer.analyze(market_data)
            
            # 4. Gelişmiş göstergeler (CCI ve MFI)
            advanced_indicators = self._analyze_advanced_indicators(gram_candles)
            
            # 5. Pattern tanıma
            pattern_analysis = self._analyze_patterns(gram_candles)
            
            # 6. Yeni modül analizleri
            fibonacci_analysis = self._analyze_fibonacci(gram_candles)
            smc_analysis = self._analyze_smc(gram_candles)
            market_regime_analysis = self._analyze_market_regime(gram_candles)
            divergence_analysis = self._analyze_advanced_divergence(gram_candles)
            
            # 7. Dip/Tepe detection logic
            dip_peak_analysis = self._enhanced_dip_peak_detection(
                gram_candles, gram_analysis, advanced_indicators, pattern_analysis
            )
            
            # 12. Volatilite kontrolü
            current_price = float(gram_analysis.get('price', 0))
            atr_data = gram_analysis.get('indicators', {}).get('atr', {})
            # ATR bir dict ise value'sunu al, değilse direkt kullan
            if isinstance(atr_data, dict):
                atr_value = atr_data.get('value', 1.0)
            else:
                atr_value = atr_data if atr_data else 1.0
            market_volatility = (atr_value / current_price * 100) if current_price > 0 else 0
            
            # 8. Enhanced Signal Combination - Tüm modülleri dahil et
            logger.debug(f"🔄 HYBRID: Calling enhanced signal combiner for {timeframe}")
            logger.debug(f"🔄 HYBRID: Gram signal = {gram_analysis.get('signal')}")
            combined_signal = self._combine_signals_enhanced_v2(
                gram_analysis, global_analysis, currency_analysis,
                advanced_indicators, pattern_analysis, timeframe, market_volatility,
                fibonacci_analysis, smc_analysis, market_regime_analysis, 
                divergence_analysis, dip_peak_analysis
            )
            logger.debug(f"🔄 HYBRID: Enhanced combined signal = {combined_signal.get('signal')}")
            
            # 7. Kelly Criterion ile pozisyon boyutu hesapla
            position_details = self._calculate_kelly_position(
                combined_signal, gram_analysis, currency_analysis
            )
            
            # 8. Stop-loss ve take-profit ayarla
            risk_levels = self._adjust_risk_levels(
                gram_analysis, currency_analysis
            )
            
            return {
                "timestamp": timezone.utc_now(),
                "gram_price": gram_analysis.get("price"),
                
                # Ana sinyal
                "signal": combined_signal["signal"],
                "confidence": combined_signal["confidence"],
                "signal_strength": combined_signal["strength"],
                
                # Risk yönetimi
                "position_size": position_details.get("lots", 0),
                "position_details": position_details,
                "stop_loss": risk_levels["stop_loss"],
                "take_profit": risk_levels["take_profit"],
                "risk_reward_ratio": risk_levels["risk_reward_ratio"],
                
                # Detaylı analizler
                "gram_analysis": gram_analysis,
                "global_trend": global_analysis,
                "currency_risk": currency_analysis,
                "advanced_indicators": advanced_indicators,
                "pattern_analysis": pattern_analysis,
                "fibonacci_analysis": fibonacci_analysis,
                "smc_analysis": smc_analysis,
                "market_regime_analysis": market_regime_analysis,
                "divergence_analysis": divergence_analysis,
                "dip_peak_analysis": dip_peak_analysis,
                
                # Dip Detection bilgileri
                "dip_detection": combined_signal.get("dip_detection", {}),
                
                # Özet ve öneriler
                "summary": self._create_summary(
                    combined_signal, gram_analysis, global_analysis, currency_analysis
                ),
                "recommendations": self._get_recommendations(
                    combined_signal, position_details, currency_analysis
                )
            }
            
        except Exception as e:
            logger.error(f"Hibrit strateji hatası: {e}", exc_info=True)
            return self._empty_result()
    
    def _combine_signals_enhanced(self, gram: Dict, global_trend: Dict, 
                                currency: Dict, advanced: Dict, patterns: Dict, 
                                timeframe: str, market_volatility: float,
                                divergence: Dict = None, dip_peak_analysis: Dict = None) -> Dict[str, Any]:
        """Enhanced sinyal birleştirme - Dip/tepe yakalama odaklı"""
        try:
            # Temel signal combiner kullan
            base_result = self.signal_combiner.combine_signals(
                gram_signal=gram,
                global_trend=global_trend,
                currency_risk=currency,
                advanced_indicators=advanced,
                patterns=patterns,
                timeframe=timeframe,
                market_volatility=market_volatility,
                divergence_data=divergence
            )
            
            # Dip/Peak analysis sonuçlarını entegre et
            if dip_peak_analysis:
                # Dip opportunity varsa BUY yönünde bias
                if dip_peak_analysis.get('is_strong_dip'):
                    if base_result.get('signal') in ['HOLD', 'BUY']:
                        base_result['signal'] = 'BUY'
                        base_result['confidence'] = min(base_result.get('confidence', 0.5) * 1.2, 1.0)
                        base_result['dip_detection'] = dip_peak_analysis
                        logger.info("🎯 STRONG DIP DETECTED - Enhanced BUY signal")
                
                # Peak opportunity varsa SELL yönünde bias
                elif dip_peak_analysis.get('is_strong_peak'):
                    if base_result.get('signal') in ['HOLD', 'SELL']:
                        base_result['signal'] = 'SELL'
                        base_result['confidence'] = min(base_result.get('confidence', 0.5) * 1.2, 1.0)
                        base_result['peak_detection'] = dip_peak_analysis
                        logger.info("🎯 STRONG PEAK DETECTED - Enhanced SELL signal")
            
            # Volatilite ve maliyet optimizasyonu
            base_result = self._optimize_for_transaction_cost(base_result, market_volatility)
            
            return base_result
            
        except Exception as e:
            logger.error(f"Enhanced signal combination error: {str(e)}")
            return {"signal": "HOLD", "confidence": 0.5, "strength": "WEAK"}
    
    def _combine_signals_enhanced_v2(self, gram: Dict, global_trend: Dict, 
                                   currency: Dict, advanced: Dict, patterns: Dict, 
                                   timeframe: str, market_volatility: float,
                                   fibonacci: Dict, smc: Dict, market_regime: Dict,
                                   divergence: Dict, dip_peak_analysis: Dict = None) -> Dict[str, Any]:
        """Enhanced Signal Combination v2 - Tüm modülleri weighted average ile birleştir"""
        try:
            logger.info("🔗 Enhanced Signal Combination v2 başlatıldı")
            
            # 1. Her modülden sinyal ve güç al
            signals = {}
            strengths = {}
            
            # Gram Altın Analizi (ağırlık: 25%)
            gram_signal = gram.get('signal', 'HOLD')
            gram_confidence = gram.get('confidence', 0.5)
            signals['gram_analysis'] = self._normalize_signal(gram_signal)
            strengths['gram_analysis'] = gram_confidence * 100
            
            # Market Regime (ağırlık: 20%)
            regime_signal = self._extract_regime_signal(market_regime)
            regime_strength = self._extract_regime_strength(market_regime)
            signals['market_regime'] = regime_signal
            strengths['market_regime'] = regime_strength
            
            # Divergence (ağırlık: 20%)
            div_signal = divergence.get('overall_signal', 'NEUTRAL')
            div_strength = divergence.get('signal_strength', 0)
            signals['divergence'] = self._normalize_signal(div_signal)
            strengths['divergence'] = div_strength
            
            # SMC (ağırlık: 20%)
            smc_signal = smc.get('signal', 'NEUTRAL')
            smc_strength = smc.get('strength', 0)
            signals['smc'] = self._normalize_signal(smc_signal)
            strengths['smc'] = smc_strength
            
            # Fibonacci (ağırlık: 15%)
            fib_signal = fibonacci.get('signal', 'NEUTRAL')
            fib_strength = fibonacci.get('strength', 0)
            signals['fibonacci'] = self._normalize_signal(fib_signal)
            strengths['fibonacci'] = fib_strength
            
            # 2. Weighted Average hesapla
            weighted_signal_score = 0.0
            weighted_confidence = 0.0
            total_weight = 0.0
            
            for module, weight in self.module_weights.items():
                if module in signals:
                    signal_numeric = signals[module]
                    strength = strengths[module] / 100.0  # 0-1 aralığına normalize et
                    
                    weighted_signal_score += signal_numeric * strength * weight
                    weighted_confidence += strength * weight
                    total_weight += weight
                    
                    logger.debug(f"📊 {module}: signal={signal_numeric:.2f}, strength={strength:.2f}, weight={weight:.2f}")
            
            # Normalize et
            if total_weight > 0:
                final_signal_score = weighted_signal_score / total_weight
                final_confidence = weighted_confidence / total_weight
            else:
                final_signal_score = 0.0
                final_confidence = 0.5
            
            # 3. Final sinyali belirle
            if final_signal_score > 0.3:
                final_signal = 'BUY'
            elif final_signal_score < -0.3:
                final_signal = 'SELL'
            else:
                final_signal = 'HOLD'
            
            # 4. Confluence score hesapla
            confluence_score = self._calculate_confluence_score(signals, strengths)
            
            # 5. Market regime'e göre sinyal filtreleme
            filtered_signal, filtered_confidence = self._apply_regime_filter(
                final_signal, final_confidence, market_regime
            )
            
            # 6. Adaptive parameter management
            adaptive_params = market_regime.get('adaptive_parameters', {})
            adjusted_confidence = self._apply_adaptive_parameters(
                filtered_confidence, adaptive_params, market_volatility
            )
            
            # 7. Signal quality scoring
            quality_score = self._calculate_signal_quality(
                signals, strengths, confluence_score, market_regime, divergence
            )
            
            # 8. Final sonuç
            result = {
                "signal": filtered_signal,
                "confidence": max(0.0, min(1.0, adjusted_confidence)),
                "strength": self._determine_signal_strength(adjusted_confidence),
                "weighted_score": final_signal_score,
                "confluence_score": confluence_score,
                "quality_score": quality_score,
                "module_signals": {k: v for k, v in signals.items()},
                "module_strengths": {k: v for k, v in strengths.items()},
                "adaptive_applied": bool(adaptive_params),
                "regime_filtered": filtered_signal != final_signal
            }
            
            # 9. Dip/Peak enhancement (mevcut logic)
            if dip_peak_analysis:
                result = self._apply_dip_peak_enhancement(result, dip_peak_analysis)
            
            # 10. Transaction cost optimization
            result = self._optimize_for_transaction_cost(result, market_volatility)
            
            logger.info(f"🎯 Final Enhanced Signal: {result['signal']} (confidence: {result['confidence']:.2f}, quality: {result['quality_score']:.2f})")
            
            return result
            
        except Exception as e:
            logger.error(f"Enhanced signal combination v2 error: {str(e)}")
            return {"signal": "HOLD", "confidence": 0.5, "strength": "WEAK"}
    
    def _normalize_signal(self, signal: str) -> float:
        """Sinyali -1 ile 1 arasında normalize et"""
        signal_map = {
            'BUY': 1.0,
            'BULLISH': 1.0,
            'SELL': -1.0,
            'BEARISH': -1.0,
            'HOLD': 0.0,
            'NEUTRAL': 0.0,
            'WAIT': 0.0,
            'WATCH': 0.0
        }
        return signal_map.get(signal.upper(), 0.0)
    
    def _extract_regime_signal(self, market_regime: Dict) -> float:
        """Market regime'den sinyal çıkar"""
        try:
            if market_regime.get('status') != 'success':
                return 0.0
            
            trend_regime = market_regime.get('trend_regime', {})
            momentum_regime = market_regime.get('momentum_regime', {})
            overall_assessment = market_regime.get('overall_assessment', {})
            
            signal_score = 0.0
            
            # Trend yönü
            trend_direction = trend_regime.get('direction', 'neutral')
            if trend_direction == 'bullish':
                signal_score += 0.4
            elif trend_direction == 'bearish':
                signal_score -= 0.4
            
            # Momentum durumu
            momentum_state = momentum_regime.get('state', 'stable')
            if momentum_state == 'accelerating':
                if momentum_regime.get('rsi_momentum') == 'bullish':
                    signal_score += 0.3
                elif momentum_regime.get('rsi_momentum') == 'bearish':
                    signal_score -= 0.3
            elif momentum_state == 'exhausted':
                signal_score *= 0.5  # Zayıflatır
            
            # Overall opportunity
            opportunity_level = overall_assessment.get('opportunity_level', 'medium')
            if opportunity_level == 'high':
                signal_score *= 1.2
            elif opportunity_level == 'low':
                signal_score *= 0.8
                
            return max(-1.0, min(1.0, signal_score))
            
        except Exception as e:
            logger.error(f"Regime signal extraction error: {str(e)}")
            return 0.0
    
    def _extract_regime_strength(self, market_regime: Dict) -> float:
        """Market regime'den güç skorunu çıkar"""
        try:
            if market_regime.get('status') != 'success':
                return 50.0
            
            trend_regime = market_regime.get('trend_regime', {})
            momentum_regime = market_regime.get('momentum_regime', {})
            overall_assessment = market_regime.get('overall_assessment', {})
            
            # Trend gücü (0-100)
            trend_strength = trend_regime.get('trend_strength', 50)
            
            # Momentum alignment
            momentum_alignment = momentum_regime.get('momentum_alignment', False)
            momentum_bonus = 20 if momentum_alignment else 0
            
            # Overall score
            overall_score = overall_assessment.get('overall_score', 50)
            
            # Weighted combination
            final_strength = (trend_strength * 0.4 + 
                            overall_score * 0.4 + 
                            momentum_bonus * 0.2)
            
            return max(0.0, min(100.0, final_strength))
            
        except Exception as e:
            logger.error(f"Regime strength extraction error: {str(e)}")
            return 50.0
    
    def _calculate_confluence_score(self, signals: Dict, strengths: Dict) -> float:
        """Confluence score - aynı yönde sinyal veren modül sayısı"""
        try:
            buy_signals = 0
            sell_signals = 0
            neutral_signals = 0
            
            total_buy_strength = 0.0
            total_sell_strength = 0.0
            
            for module, signal in signals.items():
                strength = strengths.get(module, 0)
                
                if signal > 0.2:  # BUY
                    buy_signals += 1
                    total_buy_strength += strength
                elif signal < -0.2:  # SELL
                    sell_signals += 1
                    total_sell_strength += strength
                else:  # NEUTRAL
                    neutral_signals += 1
            
            # Dominant yön
            if buy_signals > sell_signals:
                confluence = (buy_signals / len(signals)) * (total_buy_strength / (buy_signals * 100))
            elif sell_signals > buy_signals:
                confluence = (sell_signals / len(signals)) * (total_sell_strength / (sell_signals * 100))
            else:
                confluence = 0.3  # Karışık sinyaller
            
            return max(0.0, min(1.0, confluence))
            
        except Exception as e:
            logger.error(f"Confluence score calculation error: {str(e)}")
            return 0.5
    
    def _apply_regime_filter(self, signal: str, confidence: float, market_regime: Dict) -> Tuple[str, float]:
        """Market regime'e göre sinyal filtreleme"""
        try:
            if market_regime.get('status') != 'success':
                return signal, confidence
            
            volatility_regime = market_regime.get('volatility_regime', {})
            overall_assessment = market_regime.get('overall_assessment', {})
            
            # Extreme volatility'de sinyalleri zayıflatır
            vol_level = volatility_regime.get('level', 'medium')
            if vol_level == 'extreme':
                confidence *= 0.7
                logger.debug("Extreme volatility - confidence reduced")
            
            # High risk durumunda HOLD'a çevirir
            risk_level = overall_assessment.get('risk_level', 'medium')
            if risk_level == 'high' and confidence < 0.7:
                signal = 'HOLD'
                confidence *= 0.8
                logger.debug("High risk regime - converted to HOLD")
            
            # Squeeze potential varsa bekletir
            if volatility_regime.get('squeeze_potential', False):
                if signal != 'HOLD' and confidence < 0.8:
                    signal = 'HOLD'
                    logger.debug("Squeeze potential - waiting for breakout")
            
            return signal, confidence
            
        except Exception as e:
            logger.error(f"Regime filter error: {str(e)}")
            return signal, confidence
    
    def _apply_adaptive_parameters(self, confidence: float, adaptive_params: Dict, volatility: float) -> float:
        """Adaptive parameter management"""
        try:
            if not adaptive_params:
                return confidence
            
            # Signal threshold adjustment
            signal_threshold = adaptive_params.get('signal_threshold', 0.6)
            
            # Threshold'a göre confidence ayarlama
            if confidence < signal_threshold:
                confidence *= 0.8  # Zayıflatır
                logger.debug(f"Below adaptive threshold ({signal_threshold}) - confidence reduced")
            
            # Position size adjustment faktörü
            position_adjustment = adaptive_params.get('position_size_adjustment', 1.0)
            
            # Düşük position adjustment confidence'ı etkiler
            if position_adjustment < 0.8:
                confidence *= 0.9
                logger.debug("Low position size adjustment - confidence reduced")
            
            return confidence
            
        except Exception as e:
            logger.error(f"Adaptive parameter application error: {str(e)}")
            return confidence
    
    def _calculate_signal_quality(self, signals: Dict, strengths: Dict, confluence: float, 
                                market_regime: Dict, divergence: Dict) -> float:
        """Signal quality scoring sistemi"""
        try:
            quality_score = 0.0
            
            # 1. Confluence bonus (0-30 puan)
            quality_score += confluence * 30
            
            # 2. Average strength bonus (0-25 puan)
            avg_strength = sum(strengths.values()) / len(strengths) if strengths else 0
            quality_score += (avg_strength / 100) * 25
            
            # 3. Market regime bonus (0-20 puan)
            if market_regime.get('status') == 'success':
                overall_assessment = market_regime.get('overall_assessment', {})
                opportunity_level = overall_assessment.get('opportunity_level', 'medium')
                
                if opportunity_level == 'high':
                    quality_score += 20
                elif opportunity_level == 'medium':
                    quality_score += 10
            
            # 4. Divergence class bonus (0-15 puan)
            if divergence.get('status') == 'success':
                dominant_div = divergence.get('dominant_divergence', {})
                div_class = dominant_div.get('class_rating', 'C')
                
                class_scores = {'A': 15, 'B': 10, 'C': 5}
                quality_score += class_scores.get(div_class, 0)
            
            # 5. Signal consistency bonus (0-10 puan)
            # Tüm sinyaller aynı yöndeyse bonus
            signal_directions = [1 if s > 0.2 else -1 if s < -0.2 else 0 for s in signals.values()]
            if len(set(signal_directions)) == 1 and signal_directions[0] != 0:
                quality_score += 10
            
            return max(0.0, min(100.0, quality_score))
            
        except Exception as e:
            logger.error(f"Signal quality calculation error: {str(e)}")
            return 50.0
    
    def _determine_signal_strength(self, confidence: float) -> str:
        """Confidence'dan signal strength belirle"""
        if confidence >= 0.8:
            return "VERY_STRONG"
        elif confidence >= 0.65:
            return "STRONG"
        elif confidence >= 0.5:
            return "MEDIUM"
        elif confidence >= 0.35:
            return "WEAK"
        else:
            return "VERY_WEAK"
    
    def _apply_dip_peak_enhancement(self, result: Dict, dip_peak_analysis: Dict) -> Dict:
        """Dip/peak enhancement (mevcut logic'i korur)"""
        try:
            # Dip opportunity varsa BUY yönünde bias
            if dip_peak_analysis.get('is_strong_dip'):
                if result.get('signal') in ['HOLD', 'BUY']:
                    result['signal'] = 'BUY'
                    result['confidence'] = min(result.get('confidence', 0.5) * 1.2, 1.0)
                    result['dip_detection'] = dip_peak_analysis
                    logger.info("🎯 STRONG DIP DETECTED - Enhanced BUY signal")
            
            # Peak opportunity varsa SELL yönünde bias
            elif dip_peak_analysis.get('is_strong_peak'):
                if result.get('signal') in ['HOLD', 'SELL']:
                    result['signal'] = 'SELL'
                    result['confidence'] = min(result.get('confidence', 0.5) * 1.2, 1.0)
                    result['peak_detection'] = dip_peak_analysis
                    logger.info("🎯 STRONG PEAK DETECTED - Enhanced SELL signal")
            
            return result
            
        except Exception as e:
            logger.error(f"Dip/peak enhancement error: {str(e)}")
            return result
    
    def _calculate_position_size(self, signal: Dict, currency: Dict) -> Dict[str, Any]:
        """Risk ayarlı pozisyon büyüklüğü hesapla"""
        base_position = 1.0  # %100 temel pozisyon
        
        # Sinyal gücüne göre ayarla - constants'tan al
        position = base_position * SIGNAL_STRENGTH_MULTIPLIERS.get(signal["strength"], 0.5)
        
        # Kur riski çarpanı
        currency_multiplier = currency.get("position_size_multiplier", 0.8)
        position *= currency_multiplier
        
        # Güven skoruna göre dinamik ayarlama (doğrusal ölçekleme)
        confidence = signal.get("confidence", 0.5)
        
        # Güven skoru bazlı çarpan - lookup table kullan
        confidence_multiplier = 0.5  # varsayılan
        for (min_conf, max_conf), mult in CONFIDENCE_POSITION_MULTIPLIERS.items():
            if min_conf <= confidence < max_conf:
                confidence_multiplier = mult
                break
        
        position *= confidence_multiplier
        
        # HOLD sinyali için özel ayarlama
        if signal.get("signal") == "HOLD":
            # HOLD durumunda güven skoruna göre pozisyon
            # Güven ne kadar yüksekse, o kadar az pozisyon (çünkü bekleme sinyali)
            position = 0.2 + (0.7 - confidence) * 0.3  # 0.2-0.5 arası
        
        # Minimum ve maksimum sınırlar
        position = max(0.2, min(1.0, position))
        
        result = {
            "recommended_size": round(position, 2),
            "max_size": 1.0,
            "min_size": 0.2,
            "risk_adjusted": True,
            "confidence_multiplier": round(confidence_multiplier, 2)
        }
        
        logger.info(f"Position calculation: base={base_position}, strength_mult={SIGNAL_STRENGTH_MULTIPLIERS.get(signal['strength'], 0.5)}, currency_mult={currency_multiplier}, confidence_mult={confidence_multiplier:.2f}, final={result['recommended_size']}")
        return result
    
    def _adjust_risk_levels(self, gram: Dict, currency: Dict) -> Dict[str, Any]:
        """Enhanced Risk Management - SMC order blocks ve Fibonacci seviyeleri dahil"""
        try:
            stop_loss = gram.get("stop_loss")
            take_profit = gram.get("take_profit")
            current_price = float(gram.get("price", 0))
            signal = gram.get("signal", "HOLD")
            
            # Temel seviyeler yoksa varsayılan hesapla
            if not stop_loss or not take_profit:
                atr_data = gram.get('indicators', {}).get('atr', {})
                atr_value = atr_data.get('value', 1.0) if isinstance(atr_data, dict) else atr_data
                
                if signal == "BUY":
                    stop_loss = current_price - (atr_value * 2)
                    take_profit = current_price + (atr_value * 3)
                elif signal == "SELL":
                    stop_loss = current_price + (atr_value * 2)
                    take_profit = current_price - (atr_value * 3)
                else:
                    return {
                        "stop_loss": None,
                        "take_profit": None,
                        "risk_reward_ratio": None,
                        "enhanced_levels": False
                    }
            
            # SMC Order Blocks'u stop level olarak kullan
            enhanced_stop_loss = self._get_smc_stop_level(signal, current_price, float(stop_loss))
            
            # Fibonacci seviyeleri take profit olarak kullan
            enhanced_take_profit = self._get_fibonacci_take_profit(signal, current_price, float(take_profit))
            
            # Yüksek kur riski varsa stop-loss'u sıkılaştır
            risk_level = currency.get("risk_level", "MEDIUM")
            if risk_level in ["HIGH", "EXTREME"]:
                if signal == "BUY":
                    distance = abs(current_price - enhanced_stop_loss)
                    enhanced_stop_loss = current_price - (distance * 0.8)
                elif signal == "SELL":
                    distance = abs(enhanced_stop_loss - current_price)
                    enhanced_stop_loss = current_price + (distance * 0.8)
            
            # Market regime'e göre stop/TP adjustment
            if hasattr(self, '_last_market_regime') and self._last_market_regime:
                volatility_regime = self._last_market_regime.get('volatility_regime', {})
                adaptive_params = self._last_market_regime.get('adaptive_parameters', {})
                
                # Volatilite seviyesine göre adjustment
                vol_level = volatility_regime.get('level', 'medium')
                if vol_level == 'high':
                    # Yüksek volatilitede TP'yi artır, SL'yi gevşet
                    tp_multiplier = adaptive_params.get('take_profit_multiplier', 1.0)
                    sl_multiplier = adaptive_params.get('stop_loss_multiplier', 1.0)
                    
                    if signal == "BUY":
                        enhanced_take_profit = current_price + abs(enhanced_take_profit - current_price) * tp_multiplier
                        enhanced_stop_loss = current_price - abs(current_price - enhanced_stop_loss) * sl_multiplier
                    elif signal == "SELL":
                        enhanced_take_profit = current_price - abs(current_price - enhanced_take_profit) * tp_multiplier
                        enhanced_stop_loss = current_price + abs(enhanced_stop_loss - current_price) * sl_multiplier
            
            # Risk/Ödül oranı
            if signal == "BUY":
                risk = abs(current_price - enhanced_stop_loss)
                reward = abs(enhanced_take_profit - current_price)
            elif signal == "SELL":
                risk = abs(enhanced_stop_loss - current_price)
                reward = abs(current_price - enhanced_take_profit)
            else:
                risk = reward = 0
            
            risk_reward_ratio = reward / risk if risk > 0 else 0
            
            return {
                "stop_loss": enhanced_stop_loss,
                "take_profit": enhanced_take_profit,
                "risk_reward_ratio": round(risk_reward_ratio, 2),
                "enhanced_levels": True,
                "smc_stop_used": enhanced_stop_loss != float(stop_loss),
                "fibonacci_tp_used": enhanced_take_profit != float(take_profit),
                "volatility_adjusted": bool(hasattr(self, '_last_market_regime') and self._last_market_regime)
            }
            
        except Exception as e:
            logger.error(f"Enhanced risk levels calculation error: {str(e)}")
            return {
                "stop_loss": stop_loss,
                "take_profit": take_profit,
                "risk_reward_ratio": 0,
                "enhanced_levels": False,
                "error": str(e)
            }
    
    def _get_smc_stop_level(self, signal: str, current_price: float, default_stop: float) -> float:
        """SMC order blocks'u kullanarak stop level belirle"""
        try:
            if not hasattr(self, '_last_smc_analysis') or not self._last_smc_analysis:
                return default_stop
                
            smc_analysis = self._last_smc_analysis
            if smc_analysis.get('status') != 'success':
                return default_stop
                
            order_blocks = smc_analysis.get('order_blocks', [])
            
            # Signal'a göre uygun order block bul
            suitable_blocks = []
            for ob in order_blocks:
                if signal == "BUY" and ob.get('type') == 'bullish':
                    # BUY için bullish order block'un low'u stop olabilir
                    ob_low = ob.get('low', 0)
                    if ob_low < current_price and abs(current_price - ob_low) < abs(current_price - default_stop) * 1.5:
                        suitable_blocks.append((ob_low, ob.get('strength', 0)))
                elif signal == "SELL" and ob.get('type') == 'bearish':
                    # SELL için bearish order block'un high'ı stop olabilir
                    ob_high = ob.get('high', 0)
                    if ob_high > current_price and abs(ob_high - current_price) < abs(default_stop - current_price) * 1.5:
                        suitable_blocks.append((ob_high, ob.get('strength', 0)))
            
            if suitable_blocks:
                # En güçlü order block'u seç
                suitable_blocks.sort(key=lambda x: x[1], reverse=True)
                best_level = suitable_blocks[0][0]
                logger.debug(f"SMC stop level selected: {best_level} (strength: {suitable_blocks[0][1]})")
                return best_level
                
            return default_stop
            
        except Exception as e:
            logger.error(f"SMC stop level calculation error: {str(e)}")
            return default_stop
    
    def _get_fibonacci_take_profit(self, signal: str, current_price: float, default_tp: float) -> float:
        """Fibonacci seviyeleri kullanarak take profit belirle"""
        try:
            if not hasattr(self, '_last_fibonacci_analysis') or not self._last_fibonacci_analysis:
                return default_tp
                
            fib_analysis = self._last_fibonacci_analysis
            if fib_analysis.get('status') != 'success':
                return default_tp
                
            fibonacci_levels = fib_analysis.get('fibonacci_levels', {})
            
            # Signal'a göre uygun fibonacci seviyeleri bul
            suitable_levels = []
            for level_str, level_data in fibonacci_levels.items():
                level_price = level_data.get('price', 0)
                level_strength = level_data.get('strength', 'weak')
                
                # Güçlü seviyeleri tercih et
                strength_score = {'very_strong': 4, 'strong': 3, 'medium': 2, 'weak': 1}.get(level_strength, 1)
                
                if signal == "BUY" and level_price > current_price:
                    # BUY için üstteki fibonacci seviyeleri TP olabilir
                    distance_score = min(abs(level_price - current_price) / current_price * 100, 10)  # Max %10
                    total_score = strength_score + (10 - distance_score)  # Yakın seviyeler daha iyi
                    suitable_levels.append((level_price, total_score))
                elif signal == "SELL" and level_price < current_price:
                    # SELL için alttaki fibonacci seviyeleri TP olabilir
                    distance_score = min(abs(current_price - level_price) / current_price * 100, 10)
                    total_score = strength_score + (10 - distance_score)
                    suitable_levels.append((level_price, total_score))
            
            if suitable_levels:
                # En iyi skoru olan seviyeyi seç
                suitable_levels.sort(key=lambda x: x[1], reverse=True)
                best_level = suitable_levels[0][0]
                
                # Default'tan çok uzak değilse kullan
                if abs(best_level - default_tp) / current_price < 0.05:  # %5'ten fazla fark olmasın
                    logger.debug(f"Fibonacci TP level selected: {best_level} (score: {suitable_levels[0][1]})")
                    return best_level
                    
            return default_tp
            
        except Exception as e:
            logger.error(f"Fibonacci TP level calculation error: {str(e)}")
            return default_tp
    
    def _create_summary(self, signal: Dict, gram: Dict, 
                       global_trend: Dict, currency: Dict) -> str:
        """Analiz özeti oluştur"""
        parts = []
        
        # Sinyal özeti
        if signal["signal"] != "HOLD":
            parts.append(f"{signal['signal']} sinyali ({signal['strength']} güçte)")
        else:
            parts.append("Bekleme pozisyonunda kalın")
        
        # Dip detection varsa ekle
        dip_detection = signal.get("dip_detection", {})
        if dip_detection.get("is_dip_opportunity"):
            parts.append(f"DIP FIRSAT TESPİTİ (skor: {dip_detection.get('score', 0):.2f})")
            
        # Gram altın durumu
        gram_trend = gram.get("trend", "NEUTRAL")
        parts.append(f"Gram altın {gram_trend} trendinde")
        
        # Global durum
        global_dir = global_trend.get("trend_direction", "UNKNOWN")
        if global_dir != "UNKNOWN":
            parts.append(f"Global trend {global_dir}")
        
        # Risk durumu
        risk_level = currency.get("risk_level", "MEDIUM")
        if risk_level in ["HIGH", "EXTREME"]:
            parts.append(f"Yüksek kur riski ({risk_level})")
        
        return ". ".join(parts)
    
    def _get_recommendations(self, signal: Dict, position: Dict, 
                           currency: Dict) -> List[str]:
        """İşlem önerileri"""
        recommendations = []
        
        # Dip detection özel durumu
        dip_detection = signal.get("dip_detection", {})
        if dip_detection.get("is_dip_opportunity") and signal["signal"] == "BUY":
            recommendations.append("🎯 DIP YAKALAMA FIRSATI - Güçlü alım sinyali")
            if signal.get("position_size_recommendation"):
                recommendations.append(f"Önerilen pozisyon: %{signal['position_size_recommendation']*100:.0f}")
            if signal.get("stop_loss_recommendation"):
                recommendations.append(signal["stop_loss_recommendation"])
            # Dip sinyallerini ekle
            for dip_signal in dip_detection.get("signals", []):
                recommendations.append(f"• {dip_signal}")
        # Normal sinyal önerisi
        elif signal["signal"] == "BUY":
            recommendations.append("Gram altın alımı yapabilirsiniz")
        elif signal["signal"] == "SELL":
            recommendations.append("Gram altın satışı düşünebilirsiniz")
        else:
            recommendations.append("Yeni pozisyon açmayın")
        
        # Pozisyon büyüklüğü
        risk_pct = position.get("risk_percentage", 0)
        if risk_pct > 0:
            if risk_pct < 1.0:
                recommendations.append(f"Düşük pozisyon büyüklüğü önerilir (%{risk_pct:.1f} risk)")
            elif risk_pct < 1.5:
                recommendations.append(f"Orta pozisyon büyüklüğü önerilir (%{risk_pct:.1f} risk)")
            else:
                recommendations.append(f"Normal pozisyon büyüklüğü uygun (%{risk_pct:.1f} risk)")
        
        # Risk uyarıları
        if currency.get("intervention_risk", {}).get("has_risk"):
            recommendations.append("Merkez bankası müdahale riski var, dikkatli olun")
        
        if signal["confidence"] < 0.6:
            recommendations.append("Düşük güven skoru, pozisyon açmadan önce bekleyin")
        
        return recommendations
    
    def _empty_result(self) -> Dict[str, Any]:
        """Boş sonuç"""
        return {
            "timestamp": timezone.utc_now(),
            "gram_price": 0,
            "signal": "HOLD",
            "signal_strength": "WEAK",
            "confidence": 0,
            "position_size": 0,
            "position_details": {"lots": 0, "risk_percentage": 0},
            "stop_loss": None,
            "take_profit": None,
            "risk_reward_ratio": None,
            "gram_analysis": {},
            "global_trend": {"trend_direction": "NEUTRAL"},
            "currency_risk": {"risk_level": "UNKNOWN"},
            "summary": "Analiz yapılamadı",
            "recommendations": ["Veri bekleniyor"]
        }
    
    def _analyze_advanced_indicators(self, gram_candles: List[GramAltinCandle]) -> Dict[str, Any]:
        """CCI ve MFI göstergelerini analiz et"""
        try:
            # DataFrame'e çevir
            import pandas as pd
            data = []
            for candle in gram_candles:
                data.append({
                    'high': float(candle.high),
                    'low': float(candle.low),
                    'close': float(candle.close),
                    'open': float(candle.open),
                    'volume': float(candle.volume) if hasattr(candle, 'volume') and candle.volume is not None else 0
                })
            
            df = pd.DataFrame(data)
            
            # CCI analizi
            cci_analysis = self.cci.get_analysis(df)
            
            # MFI analizi
            mfi_analysis = self.mfi.get_analysis(df)
            
            # Birleşik sinyal
            combined_signal = "NEUTRAL"
            combined_confidence = 0.5
            
            # CCI ve MFI sinyallerini birleştir
            if cci_analysis['signal'] == mfi_analysis['signal'] and cci_analysis['signal'] != "NEUTRAL":
                combined_signal = cci_analysis['signal']
                combined_confidence = (cci_analysis['confidence'] + mfi_analysis['confidence']) / 2
            elif cci_analysis['extreme'] or mfi_analysis['extreme']:
                # Ekstrem durumlar
                if cci_analysis['extreme']:
                    combined_signal = cci_analysis['signal']
                    combined_confidence = cci_analysis['confidence']
                else:
                    combined_signal = mfi_analysis['signal']
                    combined_confidence = mfi_analysis['confidence']
            
            # Gram analizinden RSI değerini al
            rsi_value = None
            if hasattr(self, '_last_gram_analysis') and self._last_gram_analysis:
                rsi_value = self._last_gram_analysis.get('indicators', {}).get('rsi')
            
            return {
                'cci': cci_analysis,
                'mfi': mfi_analysis,
                'combined_signal': combined_signal,
                'combined_confidence': combined_confidence,
                'divergence': cci_analysis.get('divergence') or mfi_analysis.get('divergence'),
                'rsi': rsi_value  # RSI değerini ekle
            }
            
        except Exception as e:
            logger.error(f"Advanced indicators analiz hatası: {str(e)}")
            return {
                'cci': {'signal': 'NEUTRAL', 'confidence': 0},
                'mfi': {'signal': 'NEUTRAL', 'confidence': 0},
                'combined_signal': 'NEUTRAL',
                'combined_confidence': 0
            }
    
    def _analyze_patterns(self, gram_candles: List[GramAltinCandle]) -> Dict[str, Any]:
        """Pattern tanıma analizi"""
        try:
            # DataFrame'e çevir
            import pandas as pd
            data = []
            for candle in gram_candles:
                data.append({
                    'high': float(candle.high),
                    'low': float(candle.low),
                    'close': float(candle.close),
                    'open': float(candle.open)
                })
            
            df = pd.DataFrame(data)
            
            # Pattern analizi
            pattern_result = self.pattern_recognizer.analyze_all_patterns(df)
            
            # Son pattern'i sakla (Kelly hesaplaması için)
            self._last_pattern_analysis = pattern_result
            
            return pattern_result
            
        except Exception as e:
            logger.error(f"Pattern analiz hatası: {str(e)}")
            return {
                'pattern_found': False,
                'signal': 'NEUTRAL',
                'confidence': 0
            }
    
    def _calculate_kelly_position(self, signal: Dict, gram: Dict, currency: Dict) -> Dict[str, Any]:
        """Kelly Criterion ile pozisyon boyutu hesapla"""
        try:
            # Varsayılan sermaye (gram altın ticareti için makul miktar)
            capital = 10000  # 10K TL varsayılan (daha makul)
            
            # Fiyat ve stop loss
            current_price = float(gram.get('price', 0))
            
            # Stop loss kontrolü - HOLD durumunda da geçerli bir değer olmalı
            stop_loss_value = gram.get('stop_loss')
            if stop_loss_value is None or stop_loss_value == 0:
                # HOLD veya None durumunda varsayılan %2 risk kullan
                stop_loss = current_price * 0.98  # BUY için
            else:
                stop_loss = float(stop_loss_value)
            
            # Volatilite bazlı güven ayarlaması
            atr_value = gram.get('atr', {}).get('value', 1.0)
            market_volatility = atr_value / current_price * 100  # Yüzde olarak
            
            # Pattern gücü
            pattern_strength = 0.0
            if hasattr(self, '_last_pattern_analysis'):
                if self._last_pattern_analysis.get('pattern_found'):
                    pattern_strength = self._last_pattern_analysis.get('confidence', 0)
            
            # Risk ayarlı güven skoru
            adjusted_confidence = self.risk_manager.get_risk_adjusted_confidence(
                signal.get('confidence', 0.5),
                market_volatility,
                pattern_strength
            )
            
            # HOLD sinyali için özel durum
            if signal.get('signal') == 'HOLD':
                # HOLD durumunda minimal pozisyon boyutu dön
                position = {
                    'lots': 0.01,  # Minimal lot
                    'position_size': capital * 0.0001,  # %0.01 pozisyon
                    'risk_percentage': 0.01,
                    'risk_amount': capital * 0.0001,
                    'kelly_percentage': 0.0,
                    'confidence_adjusted': adjusted_confidence * 100,
                    'price_risk': 2.0,  # %2 varsayılan risk
                    'max_loss': capital * 0.0001
                }
            else:
                # Normal BUY/SELL pozisyon hesapla
                position = self.risk_manager.calculate_position_size(
                    capital,
                    current_price,
                    stop_loss,
                    adjusted_confidence
                )
            
            # Trading istatistikleri
            stats = self.risk_manager.calculate_trading_stats()
            
            return {
                **position,
                'trading_stats': stats,
                'adjusted_confidence': adjusted_confidence,
                'market_volatility': round(market_volatility, 2)
            }
            
        except Exception as e:
            logger.error(f"Kelly position hesaplama hatası: {str(e)}")
            return {
                'lots': 0.01,  # Minimum pozisyon
                'risk_percentage': 0.5,
                'error': str(e)
            }
    
    def _analyze_fibonacci(self, gram_candles: List[GramAltinCandle]) -> Dict[str, Any]:
        """Fibonacci Retracement analizi"""
        try:
            # DataFrame'e çevir
            import pandas as pd
            data = []
            for candle in gram_candles:
                data.append({
                    'open': float(candle.open),
                    'high': float(candle.high),
                    'low': float(candle.low),
                    'close': float(candle.close)
                })
            
            df = pd.DataFrame(data)
            
            if len(df) < 50:
                return {"status": "insufficient_data", "signal": "NEUTRAL", "strength": 0}
            
            # Fibonacci analizi yap
            fib_result = self.fibonacci_analyzer.analyze(df)
            self._last_fibonacci_analysis = fib_result
            
            # Sinyali dönüştür
            if fib_result.get('status') == 'success':
                signals = fib_result.get('signals', {})
                action = signals.get('action', 'WAIT')
                strength = signals.get('strength', 0)
                
                # Hybrid için normalize et
                if action == 'BUY':
                    signal = 'BUY'
                elif action == 'SELL':
                    signal = 'SELL'
                else:
                    signal = 'NEUTRAL'
                
                return {
                    "status": "success",
                    "signal": signal,
                    "strength": strength,
                    "bounce_potential": fib_result.get('bounce_potential', 0),
                    "nearest_level": fib_result.get('nearest_level'),
                    "fibonacci_levels": fib_result.get('fibonacci_levels', {})
                }
            else:
                return {"status": "error", "signal": "NEUTRAL", "strength": 0}
                
        except Exception as e:
            logger.error(f"Fibonacci analiz hatası: {str(e)}")
            return {"status": "error", "signal": "NEUTRAL", "strength": 0}
    
    def _analyze_smc(self, gram_candles: List[GramAltinCandle]) -> Dict[str, Any]:
        """Smart Money Concepts analizi"""
        try:
            # DataFrame'e çevir
            import pandas as pd
            data = []
            for candle in gram_candles:
                data.append({
                    'open': float(candle.open),
                    'high': float(candle.high),
                    'low': float(candle.low),
                    'close': float(candle.close)
                })
            
            df = pd.DataFrame(data)
            
            if len(df) < 50:
                return {"status": "insufficient_data", "signal": "NEUTRAL", "strength": 0}
            
            # SMC analizi yap
            smc_result = self.smc_analyzer.analyze(df)
            self._last_smc_analysis = smc_result
            
            # Sinyali dönüştür
            if smc_result.get('status') == 'success':
                signals = smc_result.get('signals', {})
                action = signals.get('action', 'WAIT')
                strength = signals.get('strength', 0)
                
                # Hybrid için normalize et
                if action == 'BUY':
                    signal = 'BUY'
                elif action == 'SELL':
                    signal = 'SELL'
                else:
                    signal = 'NEUTRAL'
                
                return {
                    "status": "success",
                    "signal": signal,
                    "strength": strength,
                    "market_structure": smc_result.get('market_structure', {}),
                    "order_blocks": smc_result.get('order_blocks', []),
                    "fair_value_gaps": smc_result.get('fair_value_gaps', []),
                    "liquidity_zones": smc_result.get('liquidity_zones', [])
                }
            else:
                return {"status": "error", "signal": "NEUTRAL", "strength": 0}
                
        except Exception as e:
            logger.error(f"SMC analiz hatası: {str(e)}")
            return {"status": "error", "signal": "NEUTRAL", "strength": 0}
    
    def _analyze_market_regime(self, gram_candles: List[GramAltinCandle]) -> Dict[str, Any]:
        """Market Regime Detection analizi"""
        try:
            # DataFrame'e çevir
            import pandas as pd
            data = []
            for candle in gram_candles:
                data.append({
                    'open': float(candle.open),
                    'high': float(candle.high),
                    'low': float(candle.low),
                    'close': float(candle.close)
                })
            
            df = pd.DataFrame(data)
            
            if len(df) < 50:
                return {"status": "insufficient_data", "regime": "unknown", "risk_level": "medium"}
            
            # Market regime analizi yap
            regime_result = self.market_regime_detector.analyze_market_regime(df)
            self._last_market_regime = regime_result
            
            if regime_result.get('status') == 'success':
                return {
                    "status": "success",
                    "volatility_regime": regime_result.get('volatility_regime', {}),
                    "trend_regime": regime_result.get('trend_regime', {}),
                    "momentum_regime": regime_result.get('momentum_regime', {}),
                    "adaptive_parameters": regime_result.get('adaptive_parameters', {}),
                    "overall_assessment": regime_result.get('overall_assessment', {}),
                    "recommendations": regime_result.get('recommendations', {})
                }
            else:
                return {"status": "error", "regime": "unknown", "risk_level": "medium"}
                
        except Exception as e:
            logger.error(f"Market regime analiz hatası: {str(e)}")
            return {"status": "error", "regime": "unknown", "risk_level": "medium"}
    
    def _analyze_advanced_divergence(self, gram_candles: List[GramAltinCandle]) -> Dict[str, Any]:
        """Advanced Divergence Detection analizi"""
        try:
            # DataFrame'e çevir
            import pandas as pd
            data = []
            for candle in gram_candles:
                data.append({
                    'open': float(candle.open),
                    'high': float(candle.high),
                    'low': float(candle.low),
                    'close': float(candle.close)
                })
            
            df = pd.DataFrame(data)
            
            if len(df) < 50:
                return {"status": "insufficient_data", "signal": "NEUTRAL", "strength": 0}
            
            # Advanced divergence analizi yap
            div_analysis = self.divergence_detector.analyze(df)
            self._last_divergence_analysis = div_analysis
            
            # DivergenceAnalysis objesinden dict'e çevir
            if div_analysis:
                return {
                    "status": "success",
                    "overall_signal": div_analysis.overall_signal,
                    "signal_strength": div_analysis.signal_strength,
                    "confluence_score": div_analysis.confluence_score,
                    "regular_divergences_count": len(div_analysis.regular_divergences),
                    "hidden_divergences_count": len(div_analysis.hidden_divergences),
                    "dominant_divergence": {
                        "type": div_analysis.dominant_divergence.type if div_analysis.dominant_divergence else None,
                        "strength": div_analysis.dominant_divergence.strength if div_analysis.dominant_divergence else 0,
                        "class_rating": div_analysis.dominant_divergence.class_rating if div_analysis.dominant_divergence else "C"
                    },
                    "next_targets": div_analysis.next_targets,
                    "invalidation_levels": div_analysis.invalidation_levels
                }
            else:
                return {"status": "error", "signal": "NEUTRAL", "strength": 0}
                
        except Exception as e:
            logger.error(f"Advanced divergence analiz hatası: {str(e)}")
            return {"status": "error", "signal": "NEUTRAL", "strength": 0}
    
    def _analyze_simple_divergence(self, gram_candles, gram_analysis) -> Dict[str, Any]:
        """Basit divergence analizi - RSI tabanlı"""
        try:
            # RSI divergence gram_analyzer'da zaten hesaplanıyor
            rsi_divergence = gram_analysis.get('rsi_divergence', {})
            if rsi_divergence and rsi_divergence.get('detected'):
                return {
                    "type": rsi_divergence.get('type'),
                    "strength": rsi_divergence.get('strength', 0),
                    "detected": True
                }
            return {"detected": False, "type": None, "strength": 0}
        except Exception as e:
            logger.error(f"Simple divergence analysis error: {str(e)}")
            return {"detected": False, "type": None, "strength": 0}
    
    def _enhanced_dip_peak_detection(self, gram_candles, gram_analysis, 
                                   advanced_indicators, pattern_analysis) -> Dict[str, Any]:
        """Gelişmiş dip/tepe tespit sistemi"""
        try:
            current_price = float(gram_analysis.get('price', 0))
            rsi_value = gram_analysis.get('indicators', {}).get('rsi', 50)
            
            # Dip tespiti kriterleri
            dip_signals = []
            dip_score = 0
            
            # 1. RSI oversold (ağırlık: 25)
            if isinstance(rsi_value, (int, float)) and rsi_value <= 35:
                dip_signals.append(f"RSI oversold ({rsi_value:.1f})")
                dip_score += 25
            elif isinstance(rsi_value, (int, float)) and rsi_value <= 40:
                dip_signals.append(f"RSI near oversold ({rsi_value:.1f})")
                dip_score += 15
            
            # 2. Bollinger Bands alt bant (ağırlık: 20)
            bb_data = gram_analysis.get('indicators', {}).get('bollinger', {})
            bb_position = bb_data.get('position', 'middle')
            if bb_position in ['below_lower', 'near_lower']:
                dip_signals.append(f"Bollinger alt bant ({bb_position})")
                dip_score += 20 if bb_position == 'below_lower' else 15
            
            # 3. RSI Divergence (ağırlık: 30)
            rsi_divergence = gram_analysis.get('rsi_divergence', {})
            if rsi_divergence.get('detected') and rsi_divergence.get('type') == 'bullish':
                div_strength = rsi_divergence.get('strength', 0)
                dip_signals.append(f"Bullish RSI divergence ({div_strength:.2f})")
                dip_score += int(div_strength * 30)
            
            # 4. Destek seviyesi yakınlığı (ağırlık: 15)
            support_levels = gram_analysis.get('support_levels', [])
            if support_levels and current_price > 0:
                nearest_support = support_levels[0]
                distance = abs(current_price - float(nearest_support.level)) / current_price
                if distance <= 0.01:  # %1 mesafede
                    dip_signals.append("Güçlü destek seviyesinde")
                    dip_score += 15
                elif distance <= 0.02:
                    dip_signals.append("Destek seviyesine yakın")
                    dip_score += 10
            
            # 5. Volume spike (ağırlık: 10)
            volume_spike = gram_analysis.get('volume_spike', {})
            if volume_spike and volume_spike.get('detected'):
                spike_ratio = volume_spike.get('spike_ratio', 1)
                dip_signals.append(f"Volume artışı ({spike_ratio:.1f}x)")
                dip_score += min(int(spike_ratio * 3), 10)
            
            # Tepe tespiti kriterleri
            peak_signals = []
            peak_score = 0
            
            # 1. RSI overbought
            if isinstance(rsi_value, (int, float)) and rsi_value >= 70:
                peak_signals.append(f"RSI overbought ({rsi_value:.1f})")
                peak_score += 25
            elif isinstance(rsi_value, (int, float)) and rsi_value >= 65:
                peak_signals.append(f"RSI near overbought ({rsi_value:.1f})")
                peak_score += 15
            
            # 2. Bollinger üst bant
            if bb_position in ['above_upper', 'near_upper']:
                peak_signals.append(f"Bollinger üst bant ({bb_position})")
                peak_score += 20 if bb_position == 'above_upper' else 15
            
            # 3. Bearish divergence
            if rsi_divergence.get('detected') and rsi_divergence.get('type') == 'bearish':
                div_strength = rsi_divergence.get('strength', 0)
                peak_signals.append(f"Bearish RSI divergence ({div_strength:.2f})")
                peak_score += int(div_strength * 30)
            
            # 4. Direnç seviyesi yakınlığı
            resistance_levels = gram_analysis.get('resistance_levels', [])
            if resistance_levels and current_price > 0:
                nearest_resistance = resistance_levels[0]
                distance = abs(current_price - float(nearest_resistance.level)) / current_price
                if distance <= 0.01:
                    peak_signals.append("Güçlü direnç seviyesinde")
                    peak_score += 15
                elif distance <= 0.02:
                    peak_signals.append("Direnç seviyesine yakın")
                    peak_score += 10
            
            # Pattern desteği
            if pattern_analysis and pattern_analysis.get('pattern_found'):
                pattern = pattern_analysis.get('best_pattern', {})
                pattern_type = pattern.get('type', '')
                pattern_confidence = pattern.get('confidence', 0)
                
                if pattern_type == 'BULLISH':
                    dip_signals.append(f"Bullish pattern ({pattern.get('pattern', '')})")
                    dip_score += int(pattern_confidence * 20)
                elif pattern_type == 'BEARISH':
                    peak_signals.append(f"Bearish pattern ({pattern.get('pattern', '')})")
                    peak_score += int(pattern_confidence * 20)
            
            # Sonuç değerlendirmesi
            is_strong_dip = dip_score >= 60  # %60+ skor
            is_strong_peak = peak_score >= 60
            is_moderate_dip = dip_score >= 40  # %40+ skor
            is_moderate_peak = peak_score >= 40
            
            result = {
                "is_strong_dip": is_strong_dip,
                "is_moderate_dip": is_moderate_dip,
                "is_strong_peak": is_strong_peak,
                "is_moderate_peak": is_moderate_peak,
                "dip_score": dip_score,
                "peak_score": peak_score,
                "dip_signals": dip_signals,
                "peak_signals": peak_signals,
                "max_possible_score": 100
            }
            
            if is_strong_dip:
                logger.info(f"🎯 STRONG DIP DETECTED - Score: {dip_score}/100")
                for signal in dip_signals:
                    logger.info(f"  • {signal}")
            elif is_strong_peak:
                logger.info(f"🎯 STRONG PEAK DETECTED - Score: {peak_score}/100")
                for signal in peak_signals:
                    logger.info(f"  • {signal}")
            
            return result
            
        except Exception as e:
            logger.error(f"Enhanced dip/peak detection error: {str(e)}")
            return {
                "is_strong_dip": False,
                "is_strong_peak": False,
                "dip_score": 0,
                "peak_score": 0
            }
    
    def _optimize_for_transaction_cost(self, signal_result: Dict, market_volatility: float) -> Dict[str, Any]:
        """İşlem maliyeti için optimizasyon (%0.45)"""
        try:
            signal = signal_result.get('signal', 'HOLD')
            confidence = signal_result.get('confidence', 0.5)
            
            if signal == 'HOLD':
                return signal_result
            
            # Minimum kar hedefi = işlem maliyeti * 2 (giriş + çıkış)
            min_profit_target = TRANSACTION_COST_PERCENTAGE * 2  # %0.9
            
            # Volatilite bazlı beklenen hareket
            expected_move = market_volatility * 0.5  # Konservatif tahmin
            
            # Eğer beklenen hareket minimum hedeften az ise sinyali zayıflatır
            if expected_move < min_profit_target:
                # Confidence'ı düşür
                penalty = (min_profit_target - expected_move) / min_profit_target
                new_confidence = confidence * (1 - penalty * 0.3)  # Max %30 ceza
                
                signal_result['confidence'] = max(new_confidence, 0.3)
                signal_result['cost_optimization'] = {
                    "applied": True,
                    "expected_move": expected_move,
                    "min_profit_target": min_profit_target,
                    "confidence_penalty": penalty * 0.3,
                    "note": f"Low expected move ({expected_move:.2f}%) vs min target ({min_profit_target:.2f}%)"
                }
                
                # Eğer confidence çok düştüyse HOLD'a çevir
                if signal_result['confidence'] < 0.4:
                    signal_result['signal'] = 'HOLD'
                    logger.info(f"Signal converted to HOLD due to transaction cost optimization")
            else:
                signal_result['cost_optimization'] = {
                    "applied": False,
                    "expected_move": expected_move,
                    "min_profit_target": min_profit_target,
                    "note": f"Expected move ({expected_move:.2f}%) exceeds min target"
                }
            
            return signal_result
            
        except Exception as e:
            logger.error(f"Transaction cost optimization error: {str(e)}")
            return signal_result