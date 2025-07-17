"""
Alım/Satım sinyali üretici
"""
from typing import List, Optional, Dict
from decimal import Decimal
from datetime import datetime
import logging
from models.price_data import PriceData, PriceCandle
from models.trading_signal import TradingSignal, SignalType, RiskLevel
from models.analysis_result import (
    AnalysisResult, TrendType, TrendStrength, 
    SupportResistanceLevel, TechnicalIndicators
)
from analyzers.support_resistance import SupportResistanceAnalyzer
from analyzers.multi_confirmation_analyzer import MultiConfirmationAnalyzer
from storage.sqlite_storage import SQLiteStorage
from performance_tracker import PerformanceTracker

logger = logging.getLogger(__name__)


class SignalGenerator:
    """Basit sinyal üretici"""
    
    def __init__(self, min_confidence: float = 0.7, storage: Optional[SQLiteStorage] = None, 
                 use_multi_confirmation: bool = True):
        self.min_confidence = min_confidence
        self.sr_analyzer = SupportResistanceAnalyzer()
        self.storage = storage or SQLiteStorage()
        self.use_multi_confirmation = use_multi_confirmation
        
        if use_multi_confirmation:
            self.multi_analyzer = MultiConfirmationAnalyzer()
            self.performance_tracker = PerformanceTracker()
        
    def generate_signal(
        self, 
        current_price: PriceData,
        candles: List[PriceCandle],
        risk_tolerance: str = "medium",
        trend: Optional[TrendType] = None,
        trend_strength: Optional[TrendStrength] = None,
        rsi_value: Optional[float] = None
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
        
        # Multi-confirmation kullan
        if self.use_multi_confirmation and (signal or trend):
            try:
                # Multi-confirmation analizi
                multi_signal = self.multi_analyzer.analyze(
                    current_price=current_price,
                    candles=candles,
                    sr_signal=signal,
                    trend=trend or TrendType.NEUTRAL,
                    trend_strength=trend_strength or TrendStrength.WEAK,
                    rsi_value=rsi_value
                )
                
                if multi_signal:
                    # Performans takibi
                    try:
                        signal_id = self.performance_tracker.track_signal(multi_signal)
                        if signal_id:
                            multi_signal.metadata["signal_id"] = signal_id
                    except Exception as e:
                        logger.error(f"Failed to track signal performance: {e}")
                        # Performans takibi başarısız olsa bile sinyal ver
                    
                    logger.info(f"Multi-confirmation signal generated: {multi_signal.signal_type} at {multi_signal.price_level} with {len(multi_signal.metadata.get('indicators_used', []))} confirmations")
                    return multi_signal
                elif signal:
                    # Multi-confirmation başarısız, sadece S/R sinyali varsa düşük güvenle ver
                    signal.overall_confidence *= 0.7
                    signal.reasons.append("(Tek gösterge)")
                    
            except Exception as e:
                logger.error(f"Multi-confirmation analysis failed: {e}")
                # Multi-confirmation başarısız olsa bile basit sinyali dene
        
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
    
    def analyze_and_save(
        self, 
        current_price: PriceData,
        candles: List[PriceCandle],
        risk_tolerance: str = "medium",
        timeframe: str = "15m"
    ) -> AnalysisResult:
        """Detaylı analiz yap ve kaydet"""
        
        # Trend analizi
        trend, trend_strength = self._analyze_trend(candles)
        
        # Teknik göstergeler
        rsi = self._calculate_simple_rsi(candles)
        
        # Sinyal üret (multi-confirmation ile)
        signal = self.generate_signal(
            current_price, 
            candles, 
            risk_tolerance,
            trend=trend,
            trend_strength=trend_strength,
            rsi_value=rsi
        )
        
        # Destek/Direnç analizi (zaten generate_signal'da yapıldı ama analiz için tekrar lazım)
        sr_levels = self.sr_analyzer.analyze(candles)
        nearest_levels = self.sr_analyzer.get_nearest_levels(current_price.ons_try, sr_levels)
        
        # Fiyat değişimi hesapla - önceki analiz sonucundan al
        price_change = Decimal('0')
        price_change_pct = 0.0
        
        # Önceki analiz sonucunu al
        previous_analyses = self.storage.get_analysis_history(limit=1)
        if previous_analyses and len(previous_analyses) > 0:
            prev_price = previous_analyses[0].price
            price_change = current_price.ons_try - prev_price
            if prev_price > 0:
                price_change_pct = float((price_change / prev_price) * 100)
        elif len(candles) > 1:
            # Eğer önceki analiz yoksa, bir önceki muma bak
            prev_close = candles[-2].close
            price_change = current_price.ons_try - prev_close
            price_change_pct = float((price_change / prev_close) * 100)
        
        # RSI sinyali
        rsi_signal = "Overbought" if rsi > 70 else "Oversold" if rsi < 30 else "Neutral"
        
        # MA hesaplamaları
        ma_20 = self._calculate_ma(candles, 20)
        ma_50 = self._calculate_ma(candles, 50)
        ma_cross = None
        if ma_20 and ma_50:
            if ma_20 > ma_50 and candles[-2] and self._calculate_ma(candles[:-1], 20) <= self._calculate_ma(candles[:-1], 50):
                ma_cross = "Golden Cross"
            elif ma_20 < ma_50 and candles[-2] and self._calculate_ma(candles[:-1], 20) >= self._calculate_ma(candles[:-1], 50):
                ma_cross = "Death Cross"
        
        # Multi-confirmation'dan gelen indikatör değerleri
        indicator_values = {}
        if signal and hasattr(signal, 'metadata') and 'indicator_details' in signal.metadata:
            details = signal.metadata['indicator_details']
            
            # MACD
            if 'macd' in details and details['macd']:
                macd_data = details['macd']
                indicator_values['macd_line'] = macd_data.get('macd_line')
                indicator_values['macd_signal'] = macd_data.get('signal_line')
                indicator_values['macd_histogram'] = macd_data.get('histogram')
                indicator_values['macd_crossover'] = macd_data.get('crossover')
                indicator_values['macd_trend'] = macd_data.get('trend')
            
            # Bollinger Bands
            if 'bollinger' in details and details['bollinger']:
                bb_data = details['bollinger']
                indicator_values['bb_upper'] = bb_data.get('upper_band')
                indicator_values['bb_middle'] = bb_data.get('middle_band')
                indicator_values['bb_lower'] = bb_data.get('lower_band')
                indicator_values['bb_percent_b'] = bb_data.get('percent_b')
                indicator_values['bb_squeeze'] = bb_data.get('squeeze')
                indicator_values['bb_signal'] = bb_data['signal'].get('type') if bb_data.get('signal') else None
            
            # Stochastic
            if 'stochastic' in details and details['stochastic']:
                stoch_data = details['stochastic']
                indicator_values['stoch_k'] = stoch_data.get('k')
                indicator_values['stoch_d'] = stoch_data.get('d')
                indicator_values['stoch_zone'] = stoch_data.get('zone')
                indicator_values['stoch_signal'] = stoch_data['signal'].get('type') if stoch_data.get('signal') else None
            
            # ATR
            if 'atr' in details and details['atr']:
                atr_data = details['atr']
                indicator_values['atr'] = atr_data.get('atr')
                indicator_values['atr_percent'] = atr_data.get('atr_percent')
                indicator_values['volatility_level'] = atr_data.get('volatility_level')
            
            # Pattern Recognition
            if 'patterns' in details and details['patterns']:
                pattern_data = details['patterns']
                indicator_values['patterns'] = pattern_data.get('patterns', [])
                if pattern_data.get('strongest_pattern'):
                    indicator_values['strongest_pattern'] = pattern_data['strongest_pattern'].get('name')
                if pattern_data.get('signal'):
                    indicator_values['pattern_signal'] = pattern_data['signal'].get('type')
        
        indicators = TechnicalIndicators(
            rsi=rsi,
            rsi_signal=rsi_signal,
            ma_short=ma_20,
            ma_long=ma_50,
            ma_cross=ma_cross,
            **indicator_values
        )
        
        # Support/Resistance levels
        support_levels = []
        resistance_levels = []
        
        for level in sr_levels.get("support_levels", []):
            support_levels.append(SupportResistanceLevel(
                level=level.level,
                strength="Güçlü" if level.strength > 0.8 else "Orta" if level.strength > 0.5 else "Zayıf",
                touches=level.touches
            ))
        
        for level in sr_levels.get("resistance_levels", []):
            resistance_levels.append(SupportResistanceLevel(
                level=level.level,
                strength="Güçlü" if level.strength > 0.8 else "Orta" if level.strength > 0.5 else "Zayıf",
                touches=level.touches
            ))
        
        # AnalysisResult oluştur
        analysis = AnalysisResult(
            timestamp=datetime.now(),
            timeframe=timeframe,  # Timeframe bilgisini ekle
            price=current_price.ons_try,
            price_change=price_change,
            price_change_pct=price_change_pct,
            trend=trend,
            trend_strength=trend_strength,
            support_levels=support_levels[:3],  # En önemli 3 seviye
            resistance_levels=resistance_levels[:3],  # En önemli 3 seviye
            nearest_support=nearest_levels.get("nearest_support", {}).get("level") if "nearest_support" in nearest_levels else None,
            nearest_resistance=nearest_levels.get("nearest_resistance", {}).get("level") if "nearest_resistance" in nearest_levels else None,
            signal=signal.signal_type.value if signal else None,
            signal_strength=signal.confidence if signal else None,
            confidence=signal.confidence if signal else 0.0,
            indicators=indicators,
            risk_level=signal.risk_level.value if signal else None,
            stop_loss=signal.stop_loss if signal else None,
            take_profit=signal.target_price if signal else None,
            analysis_details={
                "candle_count": len(candles),
                "signal_reasons": signal.reasons if signal else [],
                "support_count": len(support_levels),
                "resistance_count": len(resistance_levels)
            }
        )
        
        # Veritabanına kaydet
        try:
            self.storage.save_analysis_result(analysis)
            logger.info(f"Analysis saved: {trend.value} trend, Signal: {analysis.signal}")
        except Exception as e:
            logger.error(f"Failed to save analysis: {e}")
        
        return analysis
    
    def _analyze_trend(self, candles: List[PriceCandle]) -> tuple[TrendType, TrendStrength]:
        """Trend analizi yap"""
        if len(candles) < 10:
            return TrendType.NEUTRAL, TrendStrength.WEAK
        
        # Son 10 mumun ortalaması ile önceki 10 mumun ortalamasını karşılaştır
        recent_avg = sum([c.close for c in candles[-10:]]) / 10
        older_avg = sum([c.close for c in candles[-20:-10]]) / 10 if len(candles) >= 20 else recent_avg
        
        change_pct = float((recent_avg - older_avg) / older_avg * 100)
        
        # Trend tipi
        if change_pct > 1:
            trend = TrendType.BULLISH
        elif change_pct < -1:
            trend = TrendType.BEARISH
        else:
            trend = TrendType.NEUTRAL
        
        # Trend gücü
        if abs(change_pct) > 3:
            strength = TrendStrength.STRONG
        elif abs(change_pct) > 1.5:
            strength = TrendStrength.MODERATE
        else:
            strength = TrendStrength.WEAK
        
        return trend, strength
    
    def _calculate_simple_rsi(self, candles: List[PriceCandle], period: int = 14) -> float:
        """Basit RSI hesaplaması"""
        if len(candles) < period + 1:
            return 50.0  # Nötr değer
        
        gains = []
        losses = []
        
        for i in range(1, period + 1):
            change = float(candles[-i].close - candles[-i-1].close)
            if change > 0:
                gains.append(change)
                losses.append(0)
            else:
                gains.append(0)
                losses.append(abs(change))
        
        avg_gain = sum(gains) / period
        avg_loss = sum(losses) / period
        
        if avg_loss == 0:
            return 100.0
        
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        
        return rsi
    
    def _calculate_ma(self, candles: List[PriceCandle], period: int) -> Optional[Decimal]:
        """Moving Average hesapla"""
        if len(candles) < period:
            return None
        
        return sum([c.close for c in candles[-period:]]) / period