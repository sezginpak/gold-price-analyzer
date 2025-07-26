"""
Global Trend Analiz Motoru - ONS/USD üzerinden majör trend belirleme
"""
from typing import List, Dict, Any, Tuple
from decimal import Decimal
import logging
import numpy as np
from utils.timezone import utc_now

from models.market_data import MarketData
from indicators.rsi import RSIIndicator
from indicators.macd import MACDIndicator
from indicators.bollinger_bands import BollingerBandsIndicator
from indicators.stochastic import StochasticIndicator

logger = logging.getLogger(__name__)


class GlobalTrendAnalyzer:
    """ONS/USD üzerinden global altın trendini analiz et"""
    
    def __init__(self):
        self.ma_periods = {
            "short": 20,   # 20 günlük
            "medium": 50,  # 50 günlük
            "long": 200    # 200 günlük
        }
        
        # Teknik göstergeler
        self.rsi = RSIIndicator(period=14)
        self.macd = MACDIndicator(fast_period=12, slow_period=26, signal_period=9)
        self.bollinger = BollingerBandsIndicator(period=20, std_dev_multiplier=2)
        self.stochastic = StochasticIndicator(k_period=14, d_period=3)
    
    def analyze(self, market_data: List[MarketData]) -> Dict[str, Any]:
        """
        ONS/USD verilerini analiz ederek global trendi belirle
        
        Args:
            market_data: Son piyasa verileri (en az 200 kayıt önerilir)
            
        Returns:
            Global trend analiz sonuçları
        """
        try:
            if len(market_data) < 50:
                logger.warning(f"Yetersiz veri: {len(market_data)}")
                return self._empty_analysis()
            
            # ONS/USD fiyatlarını çıkar
            ons_prices = [float(d.ons_usd) for d in market_data]
            current_price = ons_prices[-1]
            
            # Hareketli ortalamalar
            ma_values = self._calculate_moving_averages(ons_prices)
            
            # Trend yönü ve gücü
            trend_direction, trend_strength = self._determine_trend(
                current_price, ma_values, ons_prices
            )
            
            # Momentum göstergeleri
            momentum = self._calculate_momentum(ons_prices)
            
            # Volatilite
            volatility = self._calculate_volatility(ons_prices)
            
            # Önemli seviyeler
            key_levels = self._find_key_levels(ons_prices)
            
            # Teknik göstergeler
            technical_indicators = self._calculate_technical_indicators(ons_prices)
            
            # Gösterge bazlı sinyal
            indicator_signal = self._determine_indicator_signal(technical_indicators)
            
            return {
                "timestamp": utc_now(),
                "ons_usd_price": Decimal(str(current_price)),
                "trend_direction": trend_direction,
                "trend_strength": trend_strength,
                "moving_averages": ma_values,
                "momentum": momentum,
                "volatility": volatility,
                "key_levels": key_levels,
                "technical_indicators": technical_indicators,
                "indicator_signal": indicator_signal,
                "analysis": self._create_trend_analysis(
                    trend_direction, trend_strength, ma_values, momentum, technical_indicators
                )
            }
            
        except Exception as e:
            logger.error(f"Global trend analiz hatası: {e}", exc_info=True)
            return self._empty_analysis()
    
    def _calculate_moving_averages(self, prices: List[float]) -> Dict[str, float]:
        """Hareketli ortalamaları hesapla"""
        ma_values = {}
        
        for name, period in self.ma_periods.items():
            if len(prices) >= period:
                ma_values[f"ma{period}"] = np.mean(prices[-period:])
            else:
                ma_values[f"ma{period}"] = None
        
        return ma_values
    
    def _determine_trend(self, current_price: float, ma_values: Dict, 
                        prices: List[float]) -> Tuple[str, str]:
        """Trend yönü ve gücünü belirle"""
        ma50 = ma_values.get("ma50")
        ma200 = ma_values.get("ma200")
        
        # Trend yönü
        if ma50 and ma200:
            if current_price > ma50 > ma200:
                direction = "BULLISH"
            elif current_price < ma50 < ma200:
                direction = "BEARISH"
            else:
                direction = "NEUTRAL"
        elif ma50:
            if current_price > ma50:
                direction = "BULLISH"
            else:
                direction = "BEARISH"
        else:
            # Son 20 günün trendi
            recent_trend = (prices[-1] - prices[-20]) / prices[-20] * 100
            if recent_trend > 2:
                direction = "BULLISH"
            elif recent_trend < -2:
                direction = "BEARISH"
            else:
                direction = "NEUTRAL"
        
        # Trend gücü
        strength = self._calculate_trend_strength(prices, ma_values)
        
        return direction, strength
    
    def _calculate_trend_strength(self, prices: List[float], ma_values: Dict) -> str:
        """Trend gücünü hesapla"""
        # Son 20 günlük değişim
        if len(prices) >= 20:
            change_20d = (prices[-1] - prices[-20]) / prices[-20] * 100
        else:
            change_20d = 0
        
        # MA'lardan uzaklık
        ma50 = ma_values.get("ma50")
        if ma50:
            distance_from_ma = abs((prices[-1] - ma50) / ma50 * 100)
        else:
            distance_from_ma = 0
        
        # Güç belirleme
        if abs(change_20d) > 5 and distance_from_ma > 3:
            return "STRONG"
        elif abs(change_20d) > 2 or distance_from_ma > 1.5:
            return "MODERATE"
        else:
            return "WEAK"
    
    def _calculate_momentum(self, prices: List[float]) -> Dict[str, float]:
        """Momentum göstergelerini hesapla"""
        momentum = {}
        
        # Rate of Change (ROC)
        if len(prices) >= 10:
            momentum["roc_10"] = (prices[-1] - prices[-10]) / prices[-10] * 100
        
        if len(prices) >= 20:
            momentum["roc_20"] = (prices[-1] - prices[-20]) / prices[-20] * 100
        
        # Momentum skorı
        if momentum:
            avg_momentum = np.mean(list(momentum.values()))
            if avg_momentum > 5:
                momentum["signal"] = "STRONG_BULLISH"
            elif avg_momentum > 2:
                momentum["signal"] = "BULLISH"
            elif avg_momentum < -5:
                momentum["signal"] = "STRONG_BEARISH"
            elif avg_momentum < -2:
                momentum["signal"] = "BEARISH"
            else:
                momentum["signal"] = "NEUTRAL"
        
        return momentum
    
    def _calculate_volatility(self, prices: List[float]) -> Dict[str, float]:
        """Volatilite hesapla"""
        if len(prices) < 21:
            return {"daily": 0, "level": "LOW"}
        
        # Günlük getiriler
        recent_prices = prices[-21:]
        returns = np.diff(recent_prices) / recent_prices[:-1]
        daily_vol = np.std(returns) * 100
        
        # Volatilite seviyesi
        if daily_vol > 3:
            level = "HIGH"
        elif daily_vol > 1.5:
            level = "MEDIUM"
        else:
            level = "LOW"
        
        return {
            "daily": daily_vol,
            "level": level,
            "annualized": daily_vol * np.sqrt(252)  # Yıllık volatilite
        }
    
    def _find_key_levels(self, prices: List[float]) -> Dict[str, float]:
        """Önemli fiyat seviyelerini bul"""
        if len(prices) < 50:
            return {}
        
        recent_prices = prices[-50:]
        
        return {
            "resistance": max(recent_prices),
            "support": min(recent_prices),
            "pivot": (max(recent_prices) + min(recent_prices) + recent_prices[-1]) / 3,
            "weekly_high": max(prices[-5:]) if len(prices) >= 5 else None,
            "weekly_low": min(prices[-5:]) if len(prices) >= 5 else None
        }
    
    def _create_trend_analysis(self, direction: str, strength: str, 
                              ma_values: Dict, momentum: Dict,
                              technical_indicators: Dict = None) -> Dict[str, str]:
        """Trend analizi özeti"""
        tech_summary = ""
        if technical_indicators:
            indicator_signal = technical_indicators.get('indicator_signal', {})
            if indicator_signal:
                tech_summary = f", teknik göstergeler {indicator_signal.get('signal', 'NEUTRAL')} sinyali veriyor"
        
        analysis = {
            "summary": f"Global altın trendi {direction} yönde ve {strength} güçte{tech_summary}",
            "ma_analysis": self._ma_analysis_text(ma_values),
            "momentum_analysis": f"Momentum {momentum.get('signal', 'belirsiz')}",
            "recommendation": self._get_recommendation(direction, strength, momentum)
        }
        
        return analysis
    
    def _ma_analysis_text(self, ma_values: Dict) -> str:
        """MA analizi metni"""
        ma50 = ma_values.get("ma50")
        ma200 = ma_values.get("ma200")
        
        if ma50 and ma200:
            if ma50 > ma200:
                return "Golden Cross oluşmuş, uzun vadeli yükseliş sinyali"
            else:
                return "Death Cross oluşmuş, uzun vadeli düşüş sinyali"
        else:
            return "Yeterli veri yok"
    
    def _get_recommendation(self, direction: str, strength: str, momentum: Dict) -> str:
        """Tavsiye üret"""
        momentum_signal = momentum.get("signal", "NEUTRAL")
        
        if direction == "BULLISH" and "BULLISH" in momentum_signal:
            return "Global trend gram altın alımını destekliyor"
        elif direction == "BEARISH" and "BEARISH" in momentum_signal:
            return "Global trend satış yönünde, dikkatli olun"
        elif direction == "NEUTRAL":
            return "Global trend yatay, yerel fiyat hareketlerine odaklanın"
        else:
            return "Karışık sinyaller, pozisyon boyutunu azaltın"
    
    def _calculate_technical_indicators(self, prices: List[float]) -> Dict[str, Any]:
        """ONS/USD için teknik göstergeleri hesapla"""
        indicators = {}
        
        try:
            # RSI
            if len(prices) >= 15:
                rsi_values = self.rsi.calculate(prices)
                if rsi_values:
                    current_rsi = rsi_values[-1]
                    indicators['rsi'] = current_rsi
                    indicators['rsi_signal'] = self._interpret_rsi(current_rsi)
            
            # MACD
            if len(prices) >= 35:
                macd_result = self.macd.calculate(prices)
                if macd_result['macd_line']:
                    indicators['macd'] = {
                        'macd_line': macd_result['macd_line'][-1],
                        'signal_line': macd_result['signal_line'][-1] if macd_result['signal_line'] else None,
                        'histogram': macd_result['histogram'][-1] if macd_result['histogram'] else None,
                        'trend': macd_result['trend'],
                        'divergence': macd_result.get('divergence', False)
                    }
            
            # Bollinger Bands
            if len(prices) >= 20:
                bb_result = self.bollinger.calculate(prices)
                if bb_result['middle_band']:
                    current_price = prices[-1]
                    indicators['bollinger'] = {
                        'upper': bb_result['upper_band'][-1],
                        'middle': bb_result['middle_band'][-1],
                        'lower': bb_result['lower_band'][-1],
                        'width': bb_result['band_width'][-1] if bb_result['band_width'] else None,
                        'position': bb_result['position'],
                        'signal': bb_result['signal']
                    }
            
            # Stochastic
            if len(prices) >= 20:
                # Stochastic için high/low verileri lazım, şimdilik basit bir yaklaşım
                highs = [max(prices[max(0,i-5):i+1]) for i in range(len(prices))]
                lows = [min(prices[max(0,i-5):i+1]) for i in range(len(prices))]
                stoch_result = self.stochastic.calculate(highs, lows, prices)
                if stoch_result['k_values']:
                    indicators['stochastic'] = {
                        'k': stoch_result['k_values'][-1],
                        'd': stoch_result['d_values'][-1] if stoch_result['d_values'] else None,
                        'zone': stoch_result['zone'],
                        'signal': stoch_result['signal']
                    }
                    
        except Exception as e:
            logger.error(f"Teknik gösterge hesaplama hatası: {e}")
            
        return indicators
    
    def _determine_indicator_signal(self, indicators: Dict[str, Any]) -> Dict[str, Any]:
        """Göstergelere dayalı sinyal üret"""
        buy_signals = 0
        sell_signals = 0
        neutral_signals = 0
        
        # RSI sinyali
        rsi_signal = indicators.get('rsi_signal')
        if rsi_signal == 'oversold':
            buy_signals += 1
        elif rsi_signal == 'overbought':
            sell_signals += 1
        else:
            neutral_signals += 1
        
        # MACD sinyali
        macd = indicators.get('macd', {})
        if macd.get('trend') == 'bullish':
            buy_signals += 1
        elif macd.get('trend') == 'bearish':
            sell_signals += 1
        else:
            neutral_signals += 1
        
        # Bollinger sinyali
        bb = indicators.get('bollinger', {})
        if bb.get('signal') == 'oversold':
            buy_signals += 1
        elif bb.get('signal') == 'overbought':
            sell_signals += 1
        else:
            neutral_signals += 1
        
        # Stochastic sinyali
        stoch = indicators.get('stochastic', {})
        if stoch.get('signal') == 'oversold':
            buy_signals += 1
        elif stoch.get('signal') == 'overbought':
            sell_signals += 1
        else:
            neutral_signals += 1
        
        # Toplam sinyal
        total_indicators = buy_signals + sell_signals + neutral_signals
        
        if total_indicators > 0:
            if buy_signals >= 3:
                signal = "STRONG_BUY"
                confidence = buy_signals / total_indicators
            elif buy_signals >= 2:
                signal = "BUY"
                confidence = buy_signals / total_indicators
            elif sell_signals >= 3:
                signal = "STRONG_SELL"
                confidence = sell_signals / total_indicators
            elif sell_signals >= 2:
                signal = "SELL"
                confidence = sell_signals / total_indicators
            else:
                signal = "NEUTRAL"
                confidence = 0.5
        else:
            signal = "NEUTRAL"
            confidence = 0
            
        return {
            "signal": signal,
            "confidence": confidence,
            "buy_count": buy_signals,
            "sell_count": sell_signals,
            "neutral_count": neutral_signals
        }
    
    def _interpret_rsi(self, rsi: float) -> str:
        """RSI değerini yorumla"""
        if rsi < 30:
            return "oversold"
        elif rsi > 70:
            return "overbought"
        else:
            return "neutral"
    
    def _empty_analysis(self) -> Dict[str, Any]:
        """Boş analiz sonucu"""
        return {
            "timestamp": utc_now(),
            "ons_usd_price": None,
            "trend_direction": "UNKNOWN",
            "trend_strength": "WEAK",
            "moving_averages": {},
            "momentum": {},
            "volatility": {"level": "UNKNOWN"},
            "key_levels": {},
            "technical_indicators": {},
            "indicator_signal": {"signal": "NEUTRAL", "confidence": 0},
            "analysis": {"summary": "Yetersiz veri"}
        }