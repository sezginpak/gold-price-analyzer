"""
Alım/Satım sinyali üretici
"""
from typing import List, Optional, Dict
from decimal import Decimal
from datetime import datetime
import logging
from models.price_data import PriceData, PriceCandle
from models.trading_signal import TradingSignal, SignalType, RiskLevel
from analyzers.support_resistance import SupportResistanceAnalyzer

logger = logging.getLogger(__name__)


class SignalGenerator:
    """Basit sinyal üretici"""
    
    def __init__(self, min_confidence: float = 0.7):
        self.min_confidence = min_confidence
        self.sr_analyzer = SupportResistanceAnalyzer()
        
    def generate_signal(
        self, 
        current_price: PriceData,
        candles: List[PriceCandle],
        risk_tolerance: str = "medium"
    ) -> Optional[TradingSignal]:
        """Alım/Satım sinyali üret"""
        
        if len(candles) < 50:  # Minimum veri gereksinimi
            logger.warning("Not enough data for signal generation")
            return None
        
        # Destek/Direnç analizi
        sr_levels = self.sr_analyzer.analyze(candles)
        nearest_levels = self.sr_analyzer.get_nearest_levels(current_price.ons_try, sr_levels)
        
        signal = None
        reasons = []
        confidence_scores = {}
        
        # ALIM SİNYALİ KONTROLÜ
        if "nearest_support" in nearest_levels:
            support = nearest_levels["nearest_support"]
            
            # Desteğe yaklaşma kontrolü
            if self.sr_analyzer.is_near_support(current_price.ons_try, support.level):
                confidence_scores["support_bounce"] = support.strength
                reasons.append(f"Güçlü destek seviyesine ({support.level}) yaklaşıldı")
                
                # Ek kontroller eklenebilir (momentum, trend vs.)
                overall_confidence = confidence_scores["support_bounce"]
                
                if overall_confidence >= self.min_confidence:
                    # Stop loss desteğin %1 altında
                    stop_loss = support.level * Decimal("0.99")
                    
                    # Hedef en yakın direnç veya %2 kar
                    target = support.level * Decimal("1.02")
                    if "nearest_resistance" in nearest_levels:
                        resistance = nearest_levels["nearest_resistance"]
                        # Hedef olarak direnç seviyesinin %99'unu al (tam dirençte satış)
                        target = min(target, resistance.level * Decimal("0.99"))
                    
                    signal = TradingSignal(
                        signal_type=SignalType.BUY,
                        price_level=current_price.ons_try,
                        current_price=current_price.ons_try,
                        confidence_scores=confidence_scores,
                        overall_confidence=overall_confidence,
                        reasons=reasons,
                        risk_level=self._calculate_risk_level(risk_tolerance, overall_confidence),
                        target_price=target,
                        stop_loss=stop_loss
                    )
        
        # SATIM SİNYALİ KONTROLÜ
        elif "nearest_resistance" in nearest_levels:
            resistance = nearest_levels["nearest_resistance"]
            
            # Dirence yaklaşma kontrolü
            if self.sr_analyzer.is_near_resistance(current_price.ons_try, resistance.level):
                confidence_scores["resistance_reject"] = resistance.strength
                reasons.append(f"Güçlü direnç seviyesine ({resistance.level}) yaklaşıldı")
                
                overall_confidence = confidence_scores["resistance_reject"]
                
                if overall_confidence >= self.min_confidence:
                    # Stop loss direncin %1 üstünde
                    stop_loss = resistance.level * Decimal("1.01")
                    
                    # Hedef en yakın destek veya %2 kar
                    target = resistance.level * Decimal("0.98")
                    if "nearest_support" in nearest_levels:
                        support = nearest_levels["nearest_support"]
                        target = max(target, support.level * Decimal("1.01"))
                    
                    signal = TradingSignal(
                        signal_type=SignalType.SELL,
                        price_level=current_price.ons_try,
                        current_price=current_price.ons_try,
                        confidence_scores=confidence_scores,
                        overall_confidence=overall_confidence,
                        reasons=reasons,
                        risk_level=self._calculate_risk_level(risk_tolerance, overall_confidence),
                        target_price=target,
                        stop_loss=stop_loss
                    )
        
        if signal:
            logger.info(f"Generated {signal.signal_type} signal at {signal.price_level} with confidence {signal.overall_confidence}")
        
        return signal
    
    def _calculate_risk_level(self, risk_tolerance: str, confidence: float) -> RiskLevel:
        """Risk seviyesi hesapla"""
        if risk_tolerance == "low":
            if confidence >= 0.9:
                return RiskLevel.LOW
            elif confidence >= 0.8:
                return RiskLevel.MEDIUM
            else:
                return RiskLevel.HIGH
        elif risk_tolerance == "medium":
            if confidence >= 0.8:
                return RiskLevel.LOW
            elif confidence >= 0.7:
                return RiskLevel.MEDIUM
            else:
                return RiskLevel.HIGH
        else:  # high risk tolerance
            if confidence >= 0.7:
                return RiskLevel.LOW
            elif confidence >= 0.6:
                return RiskLevel.MEDIUM
            else:
                return RiskLevel.HIGH