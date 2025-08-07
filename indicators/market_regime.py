"""
Market Regime Detection Module
Volatilite rejimi, trend vs range market ayrımı ve adaptive parametre sistemi
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from scipy.stats import percentileofscore
from utils.logger import logger


@dataclass
class VolatilityRegime:
    """Volatilite rejim bilgisi"""
    level: str  # "very_low", "low", "medium", "high", "extreme"
    atr_value: float
    atr_percentile: float
    expanding: bool
    contracting: bool
    squeeze_potential: bool


@dataclass
class TrendRegime:
    """Trend rejim bilgisi"""
    type: str  # "trending", "ranging", "transitioning"
    direction: str  # "bullish", "bearish", "neutral"
    adx_value: float
    trend_strength: float
    breakout_potential: bool


@dataclass
class MomentumRegime:
    """Momentum rejim bilgisi"""
    state: str  # "accelerating", "decelerating", "stable", "exhausted"
    rsi_momentum: str  # "bullish", "bearish", "neutral"
    macd_momentum: str  # "bullish", "bearish", "neutral"
    momentum_alignment: bool
    reversal_potential: float


@dataclass
class AdaptiveParameters:
    """Rejime göre uyarlanmış parametreler"""
    rsi_overbought: float
    rsi_oversold: float
    signal_threshold: float
    stop_loss_multiplier: float
    take_profit_multiplier: float
    position_size_adjustment: float


@dataclass
class RegimeTransition:
    """Rejim geçiş bilgisi"""
    current_regime: str
    transition_probability: float
    next_regime: str
    early_warning: bool
    confidence: float


class MarketRegimeDetector:
    """Market Regime Detection ana sınıfı"""
    
    def __init__(self):
        """Market Regime Detector başlatıcı"""
        self.volatility_history = []
        self.trend_history = []
        self.momentum_history = []
        self.current_regime = "neutral"
        
    def calculate_atr(self, df: pd.DataFrame, period: int = 14) -> List[float]:
        """
        Average True Range hesapla
        
        Args:
            df: OHLC verisi
            period: ATR periyodu
            
        Returns:
            ATR değerleri listesi
        """
        try:
            if len(df) < period + 1:
                return []
            
            # True Range hesaplama
            df = df.copy()
            df['prev_close'] = df['close'].shift(1)
            df['tr1'] = df['high'] - df['low']
            df['tr2'] = (df['high'] - df['prev_close']).abs()
            df['tr3'] = (df['low'] - df['prev_close']).abs()
            df['true_range'] = df[['tr1', 'tr2', 'tr3']].max(axis=1)
            
            # ATR hesaplama (Wilder's smoothing)
            atr_values = []
            true_ranges = df['true_range'].dropna().values
            
            if len(true_ranges) < period:
                return []
            
            # İlk ATR değeri
            first_atr = np.mean(true_ranges[:period])
            atr_values.append(first_atr)
            
            # Sonraki ATR değerleri
            for i in range(period, len(true_ranges)):
                atr = (atr_values[-1] * (period - 1) + true_ranges[i]) / period
                atr_values.append(atr)
                
            return atr_values
            
        except Exception as e:
            logger.error(f"ATR hesaplama hatası: {e}")
            return []
    
    def calculate_adx(self, df: pd.DataFrame, period: int = 14) -> Dict[str, List[float]]:
        """
        Average Directional Index (ADX) hesapla
        
        Args:
            df: OHLC verisi
            period: ADX periyodu
            
        Returns:
            ADX, +DI, -DI değerleri
        """
        try:
            if len(df) < period * 2:
                return {'adx': [], 'plus_di': [], 'minus_di': []}
            
            df = df.copy()
            
            # Directional Movement hesaplama
            df['high_diff'] = df['high'].diff()
            df['low_diff'] = df['low'].diff()
            
            df['plus_dm'] = np.where(
                (df['high_diff'] > df['low_diff']) & (df['high_diff'] > 0),
                df['high_diff'], 0
            )
            df['minus_dm'] = np.where(
                (df['low_diff'] > df['high_diff']) & (df['low_diff'] > 0),
                df['low_diff'], 0
            )
            
            # True Range
            df['prev_close'] = df['close'].shift(1)
            df['tr1'] = df['high'] - df['low']
            df['tr2'] = (df['high'] - df['prev_close']).abs()
            df['tr3'] = (df['low'] - df['prev_close']).abs()
            df['true_range'] = df[['tr1', 'tr2', 'tr3']].max(axis=1)
            
            # Smoothed values
            df['plus_dm_smooth'] = df['plus_dm'].rolling(window=period).mean()
            df['minus_dm_smooth'] = df['minus_dm'].rolling(window=period).mean()
            df['tr_smooth'] = df['true_range'].rolling(window=period).mean()
            
            # DI hesaplama
            df['plus_di'] = (df['plus_dm_smooth'] / df['tr_smooth']) * 100
            df['minus_di'] = (df['minus_dm_smooth'] / df['tr_smooth']) * 100
            
            # ADX hesaplama
            df['di_diff'] = (df['plus_di'] - df['minus_di']).abs()
            df['di_sum'] = df['plus_di'] + df['minus_di']
            df['dx'] = (df['di_diff'] / df['di_sum']) * 100
            
            # ADX smoothing
            adx_values = []
            dx_values = df['dx'].dropna().values
            
            if len(dx_values) < period:
                return {'adx': [], 'plus_di': [], 'minus_di': []}
            
            # İlk ADX
            first_adx = np.mean(dx_values[:period])
            adx_values.append(first_adx)
            
            # Sonraki ADX değerleri
            for i in range(period, len(dx_values)):
                adx = (adx_values[-1] * (period - 1) + dx_values[i]) / period
                adx_values.append(adx)
            
            return {
                'adx': adx_values,
                'plus_di': df['plus_di'].dropna().tolist()[-len(adx_values):],
                'minus_di': df['minus_di'].dropna().tolist()[-len(adx_values):]
            }
            
        except Exception as e:
            logger.error(f"ADX hesaplama hatası: {e}")
            return {'adx': [], 'plus_di': [], 'minus_di': []}
    
    def detect_volatility_regime(
        self,
        df: pd.DataFrame,
        atr_period: int = 14,
        lookback_period: int = 100
    ) -> VolatilityRegime:
        """
        Volatilite rejimini tespit et
        
        Args:
            df: OHLC verisi
            atr_period: ATR hesaplama periyodu
            lookback_period: Historical analiz periyodu
            
        Returns:
            VolatilityRegime objesi
        """
        try:
            # ATR hesapla
            atr_values = self.calculate_atr(df, atr_period)
            
            if not atr_values:
                return VolatilityRegime(
                    level="unknown",
                    atr_value=0.0,
                    atr_percentile=50.0,
                    expanding=False,
                    contracting=False,
                    squeeze_potential=False
                )
            
            current_atr = atr_values[-1]
            current_price = df['close'].iloc[-1]
            atr_percent = (current_atr / current_price) * 100
            
            # Historical ATR için percentile hesapla
            historical_atr = atr_values[-min(lookback_period, len(atr_values)):]
            atr_percentile = percentileofscore(historical_atr, current_atr)
            
            # Volatilite seviyesi belirleme
            if atr_percent < 0.5:
                level = "very_low"
            elif atr_percent < 1.0:
                level = "low"
            elif atr_percent < 2.0:
                level = "medium"
            elif atr_percent < 3.5:
                level = "high"
            else:
                level = "extreme"
            
            # Expanding/Contracting analizi
            expanding = False
            contracting = False
            squeeze_potential = False
            
            if len(atr_values) >= 20:
                recent_atr = np.mean(atr_values[-10:])
                older_atr = np.mean(atr_values[-20:-10])
                
                if older_atr > 0:
                    atr_change = (recent_atr - older_atr) / older_atr
                    expanding = bool(atr_change > 0.15)  # %15'ten fazla artış
                    contracting = bool(atr_change < -0.15)  # %15'ten fazla azalış
                
                # Squeeze potential: düşük volatilite + contracting
                squeeze_potential = bool(level in ["very_low", "low"] and 
                                       contracting and atr_percentile < 20)
            
            return VolatilityRegime(
                level=level,
                atr_value=current_atr,
                atr_percentile=atr_percentile,
                expanding=expanding,
                contracting=contracting,
                squeeze_potential=squeeze_potential
            )
            
        except Exception as e:
            logger.error(f"Volatilite rejim tespiti hatası: {e}")
            return VolatilityRegime(
                level="unknown",
                atr_value=0.0,
                atr_percentile=50.0,
                expanding=False,
                contracting=False,
                squeeze_potential=False
            )
    
    def detect_trend_regime(
        self,
        df: pd.DataFrame,
        adx_period: int = 14,
        trend_threshold: float = 25.0
    ) -> TrendRegime:
        """
        Trend rejimini tespit et (Trending vs Ranging)
        
        Args:
            df: OHLC verisi
            adx_period: ADX hesaplama periyodu
            trend_threshold: Trend/range ayrımı için ADX eşiği
            
        Returns:
            TrendRegime objesi
        """
        try:
            # ADX hesapla
            adx_data = self.calculate_adx(df, adx_period)
            
            if not adx_data['adx']:
                return TrendRegime(
                    type="unknown",
                    direction="neutral",
                    adx_value=0.0,
                    trend_strength=0.0,
                    breakout_potential=False
                )
            
            current_adx = adx_data['adx'][-1]
            plus_di = adx_data['plus_di'][-1]
            minus_di = adx_data['minus_di'][-1]
            
            # Trend tipi belirleme
            if current_adx > trend_threshold:
                trend_type = "trending"
            elif current_adx < trend_threshold * 0.6:  # 15 için <15
                trend_type = "ranging"
            else:
                trend_type = "transitioning"
            
            # Trend yönü belirleme
            if plus_di > minus_di * 1.1:  # %10 üstünde
                direction = "bullish"
            elif minus_di > plus_di * 1.1:
                direction = "bearish"
            else:
                direction = "neutral"
            
            # Trend gücü (0-100 normalize)
            trend_strength = min(current_adx / 50.0 * 100, 100)
            
            # Breakout potansiyeli
            breakout_potential = False
            if len(adx_data['adx']) >= 10:
                recent_adx_trend = np.mean(adx_data['adx'][-5:]) - np.mean(adx_data['adx'][-10:-5])
                breakout_potential = bool(trend_type == "ranging" and 
                                        recent_adx_trend > 2.0 and 
                                        current_adx > 15)
            
            return TrendRegime(
                type=trend_type,
                direction=direction,
                adx_value=current_adx,
                trend_strength=trend_strength,
                breakout_potential=breakout_potential
            )
            
        except Exception as e:
            logger.error(f"Trend rejim tespiti hatası: {e}")
            return TrendRegime(
                type="unknown",
                direction="neutral",
                adx_value=0.0,
                trend_strength=0.0,
                breakout_potential=False
            )
    
    def detect_momentum_regime(
        self,
        df: pd.DataFrame,
        rsi_period: int = 14,
        macd_fast: int = 12,
        macd_slow: int = 26,
        macd_signal: int = 9
    ) -> MomentumRegime:
        """
        Momentum rejimini tespit et
        
        Args:
            df: OHLC verisi
            rsi_period: RSI periyodu
            macd_fast: MACD hızlı EMA
            macd_slow: MACD yavaş EMA
            macd_signal: MACD sinyal EMA
            
        Returns:
            MomentumRegime objesi
        """
        try:
            if len(df) < max(rsi_period, macd_slow) + 10:
                return MomentumRegime(
                    state="unknown",
                    rsi_momentum="neutral",
                    macd_momentum="neutral",
                    momentum_alignment=False,
                    reversal_potential=0.0
                )
            
            # RSI hesaplama
            closes = df['close'].values
            deltas = np.diff(closes)
            gains = np.where(deltas > 0, deltas, 0)
            losses = np.where(deltas < 0, -deltas, 0)
            
            avg_gain = np.mean(gains[:rsi_period])
            avg_loss = np.mean(losses[:rsi_period])
            
            for i in range(rsi_period, len(gains)):
                avg_gain = (avg_gain * (rsi_period - 1) + gains[i]) / rsi_period
                avg_loss = (avg_loss * (rsi_period - 1) + losses[i]) / rsi_period
            
            rs = avg_gain / avg_loss if avg_loss != 0 else 100
            current_rsi = 100 - (100 / (1 + rs))
            
            # MACD hesaplama
            exp1 = closes.copy().astype(float)
            exp2 = closes.copy().astype(float)
            
            # EMA hesaplama
            alpha_fast = 2.0 / (macd_fast + 1)
            alpha_slow = 2.0 / (macd_slow + 1)
            
            for i in range(1, len(exp1)):
                exp1[i] = alpha_fast * closes[i] + (1 - alpha_fast) * exp1[i-1]
                exp2[i] = alpha_slow * closes[i] + (1 - alpha_slow) * exp2[i-1]
            
            macd_line = exp1 - exp2
            
            # Signal line
            signal_line = macd_line.copy()
            alpha_signal = 2.0 / (macd_signal + 1)
            
            for i in range(1, len(signal_line)):
                signal_line[i] = alpha_signal * macd_line[i] + (1 - alpha_signal) * signal_line[i-1]
            
            histogram = macd_line - signal_line
            
            # RSI momentum durumu
            if current_rsi > 60:
                rsi_momentum = "bullish" if current_rsi < 80 else "exhausted_bullish"
            elif current_rsi < 40:
                rsi_momentum = "bearish" if current_rsi > 20 else "exhausted_bearish"
            else:
                rsi_momentum = "neutral"
            
            # MACD momentum durumu
            current_histogram = histogram[-1]
            prev_histogram = histogram[-2] if len(histogram) > 1 else current_histogram
            
            if current_histogram > 0:
                if current_histogram > prev_histogram:
                    macd_momentum = "bullish"
                else:
                    macd_momentum = "weakening_bullish"
            elif current_histogram < 0:
                if current_histogram < prev_histogram:
                    macd_momentum = "bearish"
                else:
                    macd_momentum = "weakening_bearish"
            else:
                macd_momentum = "neutral"
            
            # Momentum alignment
            bullish_signals = sum([
                rsi_momentum in ["bullish"],
                macd_momentum in ["bullish"]
            ])
            bearish_signals = sum([
                rsi_momentum in ["bearish"],
                macd_momentum in ["bearish"]
            ])
            
            momentum_alignment = bool(bullish_signals >= 2 or bearish_signals >= 2)
            
            # State belirleme
            if len(histogram) >= 10:
                recent_change = histogram[-1] - histogram[-5]
                if abs(recent_change) > np.std(histogram[-20:]) * 1.5:
                    if recent_change > 0:
                        state = "accelerating"
                    else:
                        state = "decelerating"
                else:
                    state = "stable"
            else:
                state = "stable"
            
            # Exhaustion kontrolü
            if ((current_rsi > 80 and rsi_momentum == "bullish") or
                (current_rsi < 20 and rsi_momentum == "bearish")):
                state = "exhausted"
            
            # Reversal potential
            reversal_potential = 0.0
            if current_rsi > 75 or current_rsi < 25:
                reversal_potential += 30
            
            if len(histogram) >= 5:
                histogram_divergence = self._check_momentum_divergence(
                    closes[-20:], histogram[-20:]
                )
                if histogram_divergence:
                    reversal_potential += 40
            
            reversal_potential = min(reversal_potential, 100)
            
            return MomentumRegime(
                state=state,
                rsi_momentum=rsi_momentum,
                macd_momentum=macd_momentum,
                momentum_alignment=momentum_alignment,
                reversal_potential=reversal_potential
            )
            
        except Exception as e:
            logger.error(f"Momentum rejim tespiti hatası: {e}")
            return MomentumRegime(
                state="unknown",
                rsi_momentum="neutral",
                macd_momentum="neutral",
                momentum_alignment=False,
                reversal_potential=0.0
            )
    
    def _check_momentum_divergence(
        self,
        prices: np.ndarray,
        momentum: np.ndarray
    ) -> bool:
        """Momentum divergence kontrolü"""
        try:
            if len(prices) < 10 or len(momentum) < 10:
                return False
            
            # Son 10 periyotta price ve momentum peaks bul
            price_peaks = []
            momentum_peaks = []
            
            for i in range(1, len(prices) - 1):
                if prices[i] > prices[i-1] and prices[i] > prices[i+1]:
                    price_peaks.append((i, prices[i]))
                if momentum[i] > momentum[i-1] and momentum[i] > momentum[i+1]:
                    momentum_peaks.append((i, momentum[i]))
            
            # Divergence kontrolü
            if len(price_peaks) >= 2 and len(momentum_peaks) >= 2:
                # Bearish divergence: price yüksek peak, momentum düşük peak
                if (price_peaks[-1][1] > price_peaks[-2][1] and
                    momentum_peaks[-1][1] < momentum_peaks[-2][1]):
                    return True
                
                # Bullish divergence: price düşük peak, momentum yüksek peak
                if (price_peaks[-1][1] < price_peaks[-2][1] and
                    momentum_peaks[-1][1] > momentum_peaks[-2][1]):
                    return True
            
            return False
            
        except Exception as e:
            logger.error(f"Momentum divergence kontrolü hatası: {e}")
            return False
    
    def get_adaptive_parameters(
        self,
        volatility_regime: VolatilityRegime,
        trend_regime: TrendRegime,
        momentum_regime: MomentumRegime
    ) -> AdaptiveParameters:
        """
        Rejime göre adaptive parametreleri hesapla
        
        Args:
            volatility_regime: Volatilite rejimi
            trend_regime: Trend rejimi
            momentum_regime: Momentum rejimi
            
        Returns:
            AdaptiveParameters objesi
        """
        try:
            # Base parametreler
            base_rsi_overbought = 70
            base_rsi_oversold = 30
            base_signal_threshold = 0.6
            base_stop_multiplier = 2.0
            base_tp_multiplier = 3.0
            base_position_size = 1.0
            
            # Volatilite adjustments
            if volatility_regime.level == "very_low":
                rsi_overbought = base_rsi_overbought - 10  # 60
                rsi_oversold = base_rsi_oversold + 10     # 40
                signal_threshold = base_signal_threshold + 0.2  # 0.8
                stop_multiplier = base_stop_multiplier * 1.5   # 3.0
                position_size = base_position_size * 1.3       # 1.3
            elif volatility_regime.level == "low":
                rsi_overbought = base_rsi_overbought - 5   # 65
                rsi_oversold = base_rsi_oversold + 5       # 35
                signal_threshold = base_signal_threshold + 0.1  # 0.7
                stop_multiplier = base_stop_multiplier * 1.2   # 2.4
                position_size = base_position_size * 1.1       # 1.1
            elif volatility_regime.level == "high":
                rsi_overbought = base_rsi_overbought + 5   # 75
                rsi_oversold = base_rsi_oversold - 5       # 25
                signal_threshold = base_signal_threshold - 0.1  # 0.5
                stop_multiplier = base_stop_multiplier * 0.8   # 1.6
                position_size = base_position_size * 0.8       # 0.8
            elif volatility_regime.level == "extreme":
                rsi_overbought = base_rsi_overbought + 10  # 80
                rsi_oversold = base_rsi_oversold - 10      # 20
                signal_threshold = base_signal_threshold - 0.2  # 0.4
                stop_multiplier = base_stop_multiplier * 0.6   # 1.2
                position_size = base_position_size * 0.5       # 0.5
            else:  # medium
                rsi_overbought = base_rsi_overbought
                rsi_oversold = base_rsi_oversold
                signal_threshold = base_signal_threshold
                stop_multiplier = base_stop_multiplier
                position_size = base_position_size
            
            # Trend adjustments
            if trend_regime.type == "trending":
                if trend_regime.direction == "bullish":
                    rsi_overbought += 5  # Trend yönünde daha toleranslı
                    signal_threshold -= 0.1
                elif trend_regime.direction == "bearish":
                    rsi_oversold -= 5
                    signal_threshold -= 0.1
                position_size *= 1.2  # Güçlü trend'de position artır
            elif trend_regime.type == "ranging":
                signal_threshold += 0.1  # Range'de daha seçici ol
                position_size *= 0.8     # Daha küçük pozisyon
            
            # Momentum adjustments
            if momentum_regime.state == "exhausted":
                signal_threshold += 0.2  # Çok seçici ol
                position_size *= 0.7     # Küçük pozisyon
            elif momentum_regime.reversal_potential > 60:
                if momentum_regime.rsi_momentum in ["bullish", "exhausted_bullish"]:
                    rsi_overbought -= 10  # Erken reversal sinyali
                elif momentum_regime.rsi_momentum in ["bearish", "exhausted_bearish"]:
                    rsi_oversold += 10
            
            # Take profit multiplier adjustments
            tp_multiplier = base_tp_multiplier
            if volatility_regime.level in ["high", "extreme"]:
                tp_multiplier *= 1.5  # Yüksek volatilitede TP'yi artır
            elif volatility_regime.level == "very_low":
                tp_multiplier *= 0.8  # Düşük volatilitede TP'yi azalt
            
            return AdaptiveParameters(
                rsi_overbought=max(60, min(85, rsi_overbought)),  # 60-85 aralığı
                rsi_oversold=max(15, min(40, rsi_oversold)),      # 15-40 aralığı
                signal_threshold=max(0.2, min(1.0, signal_threshold)),  # 0.2-1.0
                stop_loss_multiplier=max(1.0, min(4.0, stop_multiplier)),  # 1.0-4.0
                take_profit_multiplier=max(1.5, min(5.0, tp_multiplier)),  # 1.5-5.0
                position_size_adjustment=max(0.3, min(1.5, position_size)) # 0.3-1.5
            )
            
        except Exception as e:
            logger.error(f"Adaptive parametre hesaplama hatası: {e}")
            return AdaptiveParameters(
                rsi_overbought=70,
                rsi_oversold=30,
                signal_threshold=0.6,
                stop_loss_multiplier=2.0,
                take_profit_multiplier=3.0,
                position_size_adjustment=1.0
            )
    
    def detect_regime_transition(
        self,
        current_vol_regime: VolatilityRegime,
        current_trend_regime: TrendRegime,
        current_momentum_regime: MomentumRegime,
        historical_data: Dict
    ) -> RegimeTransition:
        """
        Rejim geçiş potansiyelini tespit et
        
        Args:
            current_vol_regime: Mevcut volatilite rejimi
            current_trend_regime: Mevcut trend rejimi
            current_momentum_regime: Mevcut momentum rejimi
            historical_data: Geçmiş rejim verileri
            
        Returns:
            RegimeTransition objesi
        """
        try:
            # Mevcut rejimi belirle
            current_regime = f"{current_vol_regime.level}_{current_trend_regime.type}"
            
            transition_probability = 0.0
            next_regime = current_regime
            early_warning = False
            confidence = 0.5
            
            # Volatilite geçiş sinyalleri
            if current_vol_regime.squeeze_potential:
                transition_probability += 40
                next_regime = f"expanding_{current_trend_regime.type}"
                early_warning = True
                confidence += 0.2
            
            if current_vol_regime.expanding and current_vol_regime.level == "extreme":
                transition_probability += 30
                next_regime = f"contracting_{current_trend_regime.type}"
                early_warning = True
                confidence += 0.15
            
            # Trend geçiş sinyalleri
            if current_trend_regime.breakout_potential:
                transition_probability += 35
                next_regime = f"{current_vol_regime.level}_trending"
                early_warning = True
                confidence += 0.2
            
            # Momentum exhaustion sinyalleri
            if current_momentum_regime.state == "exhausted":
                transition_probability += 25
                confidence += 0.1
                early_warning = True
            
            if current_momentum_regime.reversal_potential > 70:
                transition_probability += 30
                confidence += 0.15
                early_warning = True
            
            # Momentum alignment değişimi
            if not current_momentum_regime.momentum_alignment:
                transition_probability += 15
            
            # Historical pattern matching
            if historical_data and len(historical_data.get('regimes', [])) > 0:
                recent_regimes = historical_data['regimes'][-10:]
                similar_patterns = sum(1 for r in recent_regimes 
                                     if r.get('pattern_similarity', 0) > 0.7)
                if similar_patterns > 3:
                    transition_probability += 20
                    confidence += 0.1
            
            # Final adjustments
            transition_probability = min(transition_probability, 100)
            confidence = min(confidence, 1.0)
            
            # Early warning threshold
            early_warning = early_warning or transition_probability > 60
            
            return RegimeTransition(
                current_regime=current_regime,
                transition_probability=transition_probability,
                next_regime=next_regime,
                early_warning=early_warning,
                confidence=confidence
            )
            
        except Exception as e:
            logger.error(f"Rejim geçiş tespiti hatası: {e}")
            return RegimeTransition(
                current_regime="unknown",
                transition_probability=0.0,
                next_regime="unknown",
                early_warning=False,
                confidence=0.0
            )
    
    def analyze_market_regime(self, df: pd.DataFrame) -> Dict:
        """
        Komple market regime analizi
        
        Args:
            df: OHLC verisi
            
        Returns:
            Market regime analiz sonuçları
        """
        try:
            if len(df) < 50:
                return {
                    'status': 'insufficient_data',
                    'message': 'Market regime analizi için yetersiz veri'
                }
            
            # Regime detection
            volatility_regime = self.detect_volatility_regime(df)
            trend_regime = self.detect_trend_regime(df)
            momentum_regime = self.detect_momentum_regime(df)
            
            # Adaptive parameters
            adaptive_params = self.get_adaptive_parameters(
                volatility_regime, trend_regime, momentum_regime
            )
            
            # Regime transition
            historical_data = getattr(self, 'historical_regime_data', {})
            transition = self.detect_regime_transition(
                volatility_regime, trend_regime, momentum_regime, historical_data
            )
            
            # Overall regime assessment
            overall_regime = self._assess_overall_regime(
                volatility_regime, trend_regime, momentum_regime
            )
            
            # Trading recommendations
            recommendations = self._generate_regime_recommendations(
                volatility_regime, trend_regime, momentum_regime, adaptive_params
            )
            
            result = {
                'status': 'success',
                'timestamp': pd.Timestamp.now().isoformat(),
                'current_price': float(df['close'].iloc[-1]),
                'volatility_regime': {
                    'level': str(volatility_regime.level),
                    'atr_value': float(volatility_regime.atr_value),
                    'atr_percentile': float(volatility_regime.atr_percentile),
                    'expanding': bool(volatility_regime.expanding),
                    'contracting': bool(volatility_regime.contracting),
                    'squeeze_potential': bool(volatility_regime.squeeze_potential)
                },
                'trend_regime': {
                    'type': str(trend_regime.type),
                    'direction': str(trend_regime.direction),
                    'adx_value': float(trend_regime.adx_value),
                    'trend_strength': float(trend_regime.trend_strength),
                    'breakout_potential': bool(trend_regime.breakout_potential)
                },
                'momentum_regime': {
                    'state': str(momentum_regime.state),
                    'rsi_momentum': str(momentum_regime.rsi_momentum),
                    'macd_momentum': str(momentum_regime.macd_momentum),
                    'momentum_alignment': bool(momentum_regime.momentum_alignment),
                    'reversal_potential': float(momentum_regime.reversal_potential)
                },
                'adaptive_parameters': {
                    'rsi_overbought': float(adaptive_params.rsi_overbought),
                    'rsi_oversold': float(adaptive_params.rsi_oversold),
                    'signal_threshold': float(adaptive_params.signal_threshold),
                    'stop_loss_multiplier': float(adaptive_params.stop_loss_multiplier),
                    'take_profit_multiplier': float(adaptive_params.take_profit_multiplier),
                    'position_size_adjustment': float(adaptive_params.position_size_adjustment)
                },
                'regime_transition': {
                    'current_regime': str(transition.current_regime),
                    'transition_probability': float(transition.transition_probability),
                    'next_regime': str(transition.next_regime),
                    'early_warning': bool(transition.early_warning),
                    'confidence': float(transition.confidence)
                },
                'overall_assessment': overall_regime,
                'recommendations': recommendations
            }
            
            # Save to history
            self._update_regime_history(result)
            
            return result
            
        except Exception as e:
            logger.error(f"Market regime analiz hatası: {e}")
            return {
                'status': 'error',
                'message': str(e)
            }
    
    def _assess_overall_regime(
        self,
        vol_regime: VolatilityRegime,
        trend_regime: TrendRegime,
        momentum_regime: MomentumRegime
    ) -> Dict:
        """Overall regime assessment"""
        try:
            # Risk level assessment
            risk_score = 0
            if vol_regime.level in ["high", "extreme"]:
                risk_score += 40
            elif vol_regime.level == "very_low":
                risk_score += 20  # Squeeze riski
            
            if trend_regime.type == "ranging":
                risk_score += 20
            
            if momentum_regime.state == "exhausted":
                risk_score += 30
            
            if momentum_regime.reversal_potential > 60:
                risk_score += 25
            
            risk_level = "low" if risk_score < 30 else "medium" if risk_score < 60 else "high"
            
            # Opportunity assessment
            opportunity_score = 0
            if vol_regime.squeeze_potential:
                opportunity_score += 40
            
            if trend_regime.breakout_potential:
                opportunity_score += 35
            
            if trend_regime.type == "trending" and trend_regime.trend_strength > 60:
                opportunity_score += 30
            
            if momentum_regime.momentum_alignment:
                opportunity_score += 25
            
            opportunity_level = "low" if opportunity_score < 30 else "medium" if opportunity_score < 60 else "high"
            
            # Market phase
            if vol_regime.level == "very_low" and trend_regime.type == "ranging":
                phase = "consolidation"
            elif vol_regime.expanding and trend_regime.breakout_potential:
                phase = "breakout_forming"
            elif trend_regime.type == "trending" and vol_regime.level in ["medium", "high"]:
                phase = "trending"
            elif momentum_regime.state == "exhausted":
                phase = "exhaustion"
            else:
                phase = "transition"
            
            return {
                'risk_level': str(risk_level),
                'risk_score': int(min(risk_score, 100)),
                'opportunity_level': str(opportunity_level),
                'opportunity_score': int(min(opportunity_score, 100)),
                'market_phase': str(phase),
                'overall_score': int(min(opportunity_score - risk_score + 50, 100))
            }
            
        except Exception as e:
            logger.error(f"Overall regime assessment hatası: {e}")
            return {
                'risk_level': 'unknown',
                'risk_score': 50,
                'opportunity_level': 'unknown',
                'opportunity_score': 50,
                'market_phase': 'unknown',
                'overall_score': 50
            }
    
    def _generate_regime_recommendations(
        self,
        vol_regime: VolatilityRegime,
        trend_regime: TrendRegime,
        momentum_regime: MomentumRegime,
        adaptive_params: AdaptiveParameters
    ) -> Dict:
        """Rejime göre trading tavsiyeleri"""
        try:
            recommendations = {
                'strategy': 'wait',
                'position_sizing': 'normal',
                'time_horizon': 'medium',
                'key_levels': [],
                'warnings': [],
                'opportunities': []
            }
            
            # Volatilite bazlı tavsiyeler
            if vol_regime.squeeze_potential:
                recommendations['strategy'] = 'breakout_watch'
                recommendations['position_sizing'] = 'reduced_pre_breakout'
                recommendations['opportunities'].append(
                    "Volatilite sıkışması - breakout potansiyeli yüksek"
                )
            elif vol_regime.level == "extreme":
                recommendations['strategy'] = 'defensive'
                recommendations['position_sizing'] = 'minimal'
                recommendations['warnings'].append(
                    "Ekstrem volatilite - risk yönetimi kritik"
                )
            
            # Trend bazlı tavsiyeler
            if trend_regime.type == "trending":
                if trend_regime.direction == "bullish":
                    recommendations['strategy'] = 'trend_following_long'
                    recommendations['time_horizon'] = 'long'
                elif trend_regime.direction == "bearish":
                    recommendations['strategy'] = 'trend_following_short'
                    recommendations['time_horizon'] = 'long'
                
                recommendations['opportunities'].append(
                    f"Güçlü {trend_regime.direction} trend - trend takip stratejisi"
                )
            elif trend_regime.type == "ranging":
                recommendations['strategy'] = 'range_trading'
                recommendations['time_horizon'] = 'short'
                recommendations['opportunities'].append(
                    "Range market - destek/direnç trading"
                )
            
            # Momentum bazlı tavsiyeler
            if momentum_regime.state == "exhausted":
                recommendations['warnings'].append(
                    "Momentum tükenmesi - reversal riski yüksek"
                )
                recommendations['strategy'] = 'reversal_watch'
                recommendations['position_sizing'] = 'reduced'
            
            if momentum_regime.reversal_potential > 70:
                recommendations['opportunities'].append(
                    "Yüksek reversal potansiyeli - counter-trend fırsatı"
                )
            
            # Position sizing adjustments
            size_multiplier = adaptive_params.position_size_adjustment
            if size_multiplier < 0.7:
                recommendations['position_sizing'] = 'minimal'
            elif size_multiplier < 1.0:
                recommendations['position_sizing'] = 'reduced'
            elif size_multiplier > 1.2:
                recommendations['position_sizing'] = 'increased'
            
            return recommendations
            
        except Exception as e:
            logger.error(f"Rejim tavsiye üretimi hatası: {e}")
            return {
                'strategy': 'wait',
                'position_sizing': 'normal',
                'time_horizon': 'medium',
                'key_levels': [],
                'warnings': ['Analiz hatası - varsayılan ayarlar kullanılıyor'],
                'opportunities': []
            }
    
    def _update_regime_history(self, analysis_result: Dict):
        """Rejim geçmişini güncelle"""
        try:
            if not hasattr(self, 'historical_regime_data'):
                self.historical_regime_data = {'regimes': []}
            
            # Son analiz sonucunu kaydet
            regime_entry = {
                'timestamp': analysis_result.get('timestamp'),
                'volatility_level': analysis_result['volatility_regime']['level'],
                'trend_type': analysis_result['trend_regime']['type'],
                'momentum_state': analysis_result['momentum_regime']['state'],
                'overall_score': analysis_result['overall_assessment']['overall_score'],
                'transition_probability': analysis_result['regime_transition']['transition_probability']
            }
            
            self.historical_regime_data['regimes'].append(regime_entry)
            
            # Son 100 kayıt tut
            if len(self.historical_regime_data['regimes']) > 100:
                self.historical_regime_data['regimes'] = self.historical_regime_data['regimes'][-100:]
            
        except Exception as e:
            logger.error(f"Rejim geçmişi güncelleme hatası: {e}")


def calculate_market_regime_analysis(df: pd.DataFrame) -> Dict:
    """
    Market Regime Detection analizi yap
    
    Args:
        df: OHLC verisi
        
    Returns:
        Market regime analiz sonuçları
    """
    try:
        detector = MarketRegimeDetector()
        return detector.analyze_market_regime(df)
    except Exception as e:
        logger.error(f"Market regime analiz hatası: {e}")
        return {
            'status': 'error',
            'message': str(e)
        }