"""
Multi-Confirmation Signal Analyzer
Tüm göstergeleri birleştirip güçlü sinyaller üreten sistem
"""
from typing import List, Dict, Optional, Tuple
from decimal import Decimal
from datetime import datetime
import logging
from dataclasses import dataclass

from models.price_data import PriceData, PriceCandle
from models.trading_signal import TradingSignal, SignalType, RiskLevel
from models.analysis_result import AnalysisResult, TrendType, TrendStrength

# Indicators
from indicators.macd import MACDIndicator
from indicators.bollinger_bands import BollingerBandsIndicator
from indicators.stochastic import StochasticIndicator
from indicators.atr import ATRIndicator
from indicators.pattern_recognition import PatternRecognition

logger = logging.getLogger(__name__)


@dataclass
class IndicatorSignal:
    """Tek bir göstergeden gelen sinyal"""
    indicator_name: str
    signal_type: Optional[str]  # "BUY", "SELL", None
    confidence: float  # 0.0 - 1.0
    reason: str
    details: Dict[str, any]


class MultiConfirmationAnalyzer:
    """Çoklu onay sinyal analizi"""
    
    def __init__(self, 
                 min_confirmations: int = 3,
                 min_total_confidence: float = 0.7,
                 use_atr_filter: bool = True):
        """
        Args:
            min_confirmations: Minimum onay sayısı
            min_total_confidence: Minimum toplam güven skoru
            use_atr_filter: ATR bazlı volatilite filtresi kullan
        """
        self.min_confirmations = min_confirmations
        self.min_total_confidence = min_total_confidence
        self.use_atr_filter = use_atr_filter
        
        # Göstergeleri başlat
        self.macd = MACDIndicator()
        self.bollinger = BollingerBandsIndicator()
        self.stochastic = StochasticIndicator()
        self.atr = ATRIndicator()
        self.patterns = PatternRecognition()
        
        # Gösterge ağırlıkları (önem sırası)
        self.weights = {
            "support_resistance": 0.25,
            "macd": 0.20,
            "bollinger": 0.15,
            "stochastic": 0.15,
            "patterns": 0.15,
            "trend": 0.10
        }
    
    def analyze(self, 
                current_price: PriceData,
                candles: List[PriceCandle],
                sr_signal: Optional[TradingSignal],
                trend: TrendType,
                trend_strength: TrendStrength,
                rsi_value: Optional[float] = None) -> Optional[TradingSignal]:
        """
        Tüm göstergeleri analiz edip güçlü sinyal üret
        
        Args:
            current_price: Mevcut fiyat
            candles: OHLC mumları
            sr_signal: Destek/Direnç sinyali
            trend: Mevcut trend
            trend_strength: Trend gücü
            rsi_value: RSI değeri
        
        Returns:
            Güçlü sinyal veya None
        """
        try:
            if not current_price or not candles:
                logger.warning("Missing required data for multi-confirmation analysis")
                return None
            
            if len(candles) < 50:
                logger.warning(f"Not enough candles for multi-confirmation: {len(candles)}")
                return None
            
            indicators = []
            
            # 1. Destek/Direnç sinyali
            if sr_signal:
                indicators.append(IndicatorSignal(
                    indicator_name="support_resistance",
                    signal_type=sr_signal.signal_type.value,
                    confidence=sr_signal.overall_confidence,
                    reason=", ".join(sr_signal.reasons),
                    details={"levels": sr_signal.confidence_scores}
                ))
        
            # 2. MACD analizi
            try:
                macd_result = self.macd.calculate(candles)
                macd_signal, macd_confidence = self.macd.get_signal_weight(macd_result)
                if macd_signal:
                    indicators.append(IndicatorSignal(
                        indicator_name="macd",
                        signal_type=macd_signal,
                        confidence=macd_confidence,
                        reason=self._get_macd_reason(macd_result),
                        details=macd_result
                    ))
            except Exception as e:
                logger.error(f"MACD analysis failed: {e}")
        
            # 3. Bollinger Bands analizi
            try:
                bb_result = self.bollinger.calculate(candles)
                bb_signal, bb_confidence = self.bollinger.get_signal_weight(bb_result)
                if bb_signal:
                    indicators.append(IndicatorSignal(
                        indicator_name="bollinger",
                        signal_type=bb_signal,
                        confidence=bb_confidence,
                        reason=bb_result["signal"]["reason"] if bb_result.get("signal") else "Bollinger signal",
                        details=bb_result
                    ))
            except Exception as e:
                logger.error(f"Bollinger Bands analysis failed: {e}")
            
            # 4. Stochastic analizi
            try:
                stoch_result = self.stochastic.calculate(candles)
                stoch_signal, stoch_confidence = self.stochastic.get_signal_weight(stoch_result)
                if stoch_signal:
                    indicators.append(IndicatorSignal(
                        indicator_name="stochastic",
                        signal_type=stoch_signal,
                        confidence=stoch_confidence,
                        reason=self._get_stochastic_reason(stoch_result),
                        details=stoch_result
                    ))
            except Exception as e:
                logger.error(f"Stochastic analysis failed: {e}")
            
            # 5. Pattern Recognition
            try:
                pattern_result = self.patterns.detect_patterns(candles)
                pattern_signal, pattern_confidence = self.patterns.get_signal_weight(pattern_result)
                if pattern_signal:
                    indicators.append(IndicatorSignal(
                        indicator_name="patterns",
                        signal_type=pattern_signal,
                        confidence=pattern_confidence,
                        reason=pattern_result["signal"]["reason"] if pattern_result.get("signal") else "Pattern detected",
                        details=pattern_result
                    ))
            except Exception as e:
                logger.error(f"Pattern recognition failed: {e}")
            
            # 6. Trend doğrulaması
            trend_signal = self._get_trend_signal(trend, trend_strength)
            if trend_signal:
                indicators.append(trend_signal)
            
            # 7. RSI doğrulaması
            if rsi_value:
                rsi_signal = self._get_rsi_signal(rsi_value)
                if rsi_signal:
                    indicators.append(rsi_signal)
            
            # ATR filtresi (volatilite kontrolü)
            atr_result = {}
            volatility_multiplier = 1.0
            try:
                atr_result = self.atr.calculate(candles)
                if self.use_atr_filter and atr_result.get("atr"):
                    _, volatility_multiplier = self.atr.get_signal_weight(atr_result)
            except Exception as e:
                logger.error(f"ATR calculation failed: {e}")
                # ATR başarısız olsa bile devam et
            
            # İndikatör sonuçlarını topla
            indicator_details = {
                'macd': macd_result,
                'bollinger': bb_result,
                'stochastic': stoch_result,
                'patterns': pattern_result,
                'atr': atr_result
            }
            
            # Sinyalleri değerlendir
            final_signal = self._evaluate_signals(indicators, current_price, atr_result, volatility_multiplier, indicator_details)
            
            return final_signal
            
        except Exception as e:
            logger.error(f"Multi-confirmation analysis failed: {e}", exc_info=True)
            return None
    
    def _evaluate_signals(self, 
                         indicators: List[IndicatorSignal], 
                         current_price: PriceData,
                         atr_result: Dict[str, any],
                         volatility_multiplier: float,
                         indicator_details: Dict[str, any]) -> Optional[TradingSignal]:
        """Sinyalleri değerlendir ve final sinyal üret"""
        
        if not indicators:
            return None
        
        # Alım ve satım sinyallerini ayır
        buy_signals = [i for i in indicators if i.signal_type == "BUY"]
        sell_signals = [i for i in indicators if i.signal_type == "SELL"]
        
        # Hangi yön daha güçlü?
        buy_score = self._calculate_weighted_score(buy_signals)
        sell_score = self._calculate_weighted_score(sell_signals)
        
        # Minimum onay kontrolü
        if len(buy_signals) >= self.min_confirmations and buy_score > sell_score:
            signal_type = SignalType.BUY
            confirmations = buy_signals
            total_score = buy_score
        elif len(sell_signals) >= self.min_confirmations and sell_score > buy_score:
            signal_type = SignalType.SELL
            confirmations = sell_signals
            total_score = sell_score
        else:
            return None
        
        # Volatilite çarpanı uygula
        total_score *= volatility_multiplier
        
        # Minimum güven kontrolü
        if total_score < self.min_total_confidence:
            return None
        
        # Stop loss ve take profit hesapla
        if atr_result["atr"]:
            atr_stop = Decimal(str(atr_result["atr"] * 2))
            atr_target = Decimal(str(atr_result["atr"] * 3))
        else:
            # ATR yoksa %2 stop, %3 target
            atr_stop = current_price.ons_try * Decimal("0.02")
            atr_target = current_price.ons_try * Decimal("0.03")
        
        if signal_type == SignalType.BUY:
            stop_loss = current_price.ons_try - atr_stop
            take_profit = current_price.ons_try + atr_target
        else:
            stop_loss = current_price.ons_try + atr_stop
            take_profit = current_price.ons_try - atr_target
        
        # Detaylı sebepler
        reasons = []
        confidence_scores = {}
        
        for conf in confirmations:
            reasons.append(f"{conf.indicator_name}: {conf.reason}")
            confidence_scores[conf.indicator_name] = conf.confidence
        
        # Risk seviyesi
        risk_level = self._calculate_risk_level(total_score, len(confirmations), volatility_multiplier)
        
        # Final sinyal
        signal = TradingSignal(
            timestamp=datetime.now(),
            signal_type=signal_type,
            price_level=current_price.ons_try,
            current_price=current_price.ons_try,
            confidence_scores=confidence_scores,
            overall_confidence=min(total_score, 1.0),
            reasons=reasons[:5],  # En fazla 5 sebep
            risk_level=risk_level,
            target_price=take_profit,
            stop_loss=stop_loss,
            metadata={
                "confirmations": len(confirmations),
                "volatility_adjusted": volatility_multiplier != 1.0,
                "atr": atr_result.get("atr"),
                "indicators_used": [c.indicator_name for c in confirmations],
                "indicator_details": indicator_details
            }
        )
        
        logger.info(
            f"Multi-confirmation signal: {signal_type.value} with {len(confirmations)} confirmations, "
            f"confidence: {total_score:.2f}"
        )
        
        return signal
    
    def _calculate_weighted_score(self, signals: List[IndicatorSignal]) -> float:
        """Ağırlıklı güven skoru hesapla"""
        if not signals:
            return 0.0
        
        total_score = 0.0
        total_weight = 0.0
        
        for signal in signals:
            weight = self.weights.get(signal.indicator_name, 0.1)
            total_score += signal.confidence * weight
            total_weight += weight
        
        # Normalize et
        if total_weight > 0:
            normalized_score = total_score / total_weight
        else:
            normalized_score = sum(s.confidence for s in signals) / len(signals)
        
        # Çoklu onay bonusu
        confirmation_bonus = min(len(signals) * 0.05, 0.2)  # Her onay için %5, max %20
        
        return min(normalized_score + confirmation_bonus, 1.0)
    
    def _calculate_risk_level(self, confidence: float, confirmations: int, volatility: float) -> RiskLevel:
        """Risk seviyesi hesapla"""
        # Temel risk (güvene göre)
        if confidence >= 0.85:
            base_risk = RiskLevel.LOW
        elif confidence >= 0.70:
            base_risk = RiskLevel.MEDIUM
        else:
            base_risk = RiskLevel.HIGH
        
        # Onay sayısına göre ayarla
        if confirmations >= 5 and base_risk == RiskLevel.MEDIUM:
            base_risk = RiskLevel.LOW
        elif confirmations <= 2 and base_risk == RiskLevel.MEDIUM:
            base_risk = RiskLevel.HIGH
        
        # Volatiliteye göre ayarla
        if volatility < 0.8:  # Yüksek volatilite
            if base_risk == RiskLevel.LOW:
                base_risk = RiskLevel.MEDIUM
            elif base_risk == RiskLevel.MEDIUM:
                base_risk = RiskLevel.HIGH
        
        return base_risk
    
    def _get_macd_reason(self, result: Dict[str, any]) -> str:
        """MACD sebebi oluştur"""
        reasons = []
        
        if result.get("crossover") == "BULLISH_CROSSOVER":
            reasons.append("MACD bullish crossover")
        elif result.get("crossover") == "BEARISH_CROSSOVER":
            reasons.append("MACD bearish crossover")
        
        if result.get("divergence") == "BULLISH_DIVERGENCE":
            reasons.append("MACD bullish divergence")
        elif result.get("divergence") == "BEARISH_DIVERGENCE":
            reasons.append("MACD bearish divergence")
        
        if result.get("trend") == "STRONG_BULLISH":
            reasons.append("MACD güçlü yükseliş")
        elif result.get("trend") == "STRONG_BEARISH":
            reasons.append("MACD güçlü düşüş")
        
        return " + ".join(reasons) if reasons else "MACD sinyali"
    
    def _get_stochastic_reason(self, result: Dict[str, any]) -> str:
        """Stochastic sebebi oluştur"""
        signal = result.get("signal", {})
        if signal:
            return signal.get("reason", "Stochastic sinyali")
        
        zone = result.get("zone", "")
        if zone == "OVERSOLD":
            return "Stochastic oversold bölgesi"
        elif zone == "OVERBOUGHT":
            return "Stochastic overbought bölgesi"
        
        return "Stochastic sinyali"
    
    def _get_trend_signal(self, trend: TrendType, strength: TrendStrength) -> Optional[IndicatorSignal]:
        """Trend bazlı sinyal"""
        if trend == TrendType.NEUTRAL:
            return None
        
        # Güçlü trendlerde sinyal ver
        if strength in [TrendStrength.STRONG, TrendStrength.MODERATE]:
            confidence = 0.4 if strength == TrendStrength.STRONG else 0.2
            
            return IndicatorSignal(
                indicator_name="trend",
                signal_type="BUY" if trend == TrendType.BULLISH else "SELL",
                confidence=confidence,
                reason=f"{strength.value} {trend.value} trend",
                details={"trend": trend.value, "strength": strength.value}
            )
        
        return None
    
    def _get_rsi_signal(self, rsi: float) -> Optional[IndicatorSignal]:
        """RSI bazlı sinyal"""
        if rsi < 30:
            return IndicatorSignal(
                indicator_name="rsi",
                signal_type="BUY",
                confidence=0.3 if rsi < 25 else 0.2,
                reason=f"RSI oversold ({rsi:.0f})",
                details={"rsi": rsi}
            )
        elif rsi > 70:
            return IndicatorSignal(
                indicator_name="rsi",
                signal_type="SELL",
                confidence=0.3 if rsi > 75 else 0.2,
                reason=f"RSI overbought ({rsi:.0f})",
                details={"rsi": rsi}
            )
        
        return None