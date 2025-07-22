"""
Gram Altın Analiz Motoru - Ana analiz sistemi
"""
from typing import List, Dict, Any, Optional, Tuple
from decimal import Decimal
from datetime import datetime, timedelta
import logging
import numpy as np

from models.market_data import MarketData, GramAltinCandle
from indicators.rsi import RSIIndicator
from indicators.macd import MACDIndicator
from indicators.bollinger_bands import BollingerBandsIndicator
from indicators.stochastic import StochasticIndicator
from indicators.atr import ATRIndicator
from indicators.pattern_recognition import PatternRecognition
from models.analysis_result import TrendType, TrendStrength, SupportResistanceLevel

logger = logging.getLogger(__name__)


class GramAltinAnalyzer:
    """Gram altın fiyatı üzerinden teknik analiz"""
    
    def __init__(self):
        self.rsi = RSIIndicator()
        self.macd = MACDIndicator()
        self.bollinger = BollingerBandsIndicator()
        self.stochastic = StochasticIndicator()
        self.atr = ATRIndicator()
        self.pattern_recognition = PatternRecognition()
        
    def analyze(self, candles: List[GramAltinCandle]) -> Dict[str, Any]:
        """
        Gram altın mumlarını analiz et
        
        Returns:
            Analiz sonuçları (göstergeler, destek/direnç, sinyal)
        """
        try:
            logger.info(f"Gram altın analizi başladı. Mum sayısı: {len(candles) if candles else 0}")
            
            if not candles:
                logger.error("Candles listesi boş!")
                return self._empty_analysis()
                
            if len(candles) < 10:
                logger.warning(f"Yetersiz mum verisi: {len(candles)}, minimum 10 gerekli")
                return self._empty_analysis()
            
            # Fiyat dizisi hazırla
            prices = [float(c.close) for c in candles]
            high_prices = [float(c.high) for c in candles]
            low_prices = [float(c.low) for c in candles]
            
            current_price = Decimal(str(prices[-1]))
            logger.info(f"Mevcut gram altın fiyatı: {current_price}")
            
            # Teknik göstergeler
            rsi_value, rsi_signal = self.rsi.calculate(prices)
            macd_result = self.macd.calculate(candles)
            bb_result = self.bollinger.calculate(candles)
            stoch_result = self.stochastic.calculate(candles)
            atr_value = self.atr.calculate(candles)
            pattern_result = self.pattern_recognition.detect_patterns(candles)
            patterns = pattern_result.get("patterns", []) if isinstance(pattern_result, dict) else []
            
            # Trend analizi
            trend, trend_strength = self._analyze_trend(prices, macd_result)
            
            # Destek/Direnç seviyeleri
            support_levels, resistance_levels = self._find_support_resistance(candles)
            
            # Sinyal üretimi
            signal, confidence = self._generate_signal(
                current_price=current_price,
                prices=prices,
                rsi=(rsi_value, rsi_signal),
                macd=macd_result,
                bollinger=bb_result,
                stochastic=stoch_result,
                trend=trend,
                trend_strength=trend_strength,
                patterns=patterns
            )
            
            # Risk hesaplama
            stop_loss, take_profit = self._calculate_risk_levels(
                current_price, signal, atr_value, support_levels, resistance_levels
            )
            
            result = {
                "timestamp": datetime.utcnow(),
                "price": current_price,
                "trend": trend,
                "trend_strength": trend_strength,
                "indicators": {
                    "rsi": rsi_value,
                    "rsi_signal": rsi_signal,
                    "macd": macd_result,
                    "bollinger": bb_result,
                    "stochastic": stoch_result,
                    "atr": atr_value
                },
                "patterns": patterns,
                "support_levels": support_levels,
                "resistance_levels": resistance_levels,
                "signal": signal,
                "confidence": confidence,
                "stop_loss": stop_loss,
                "take_profit": take_profit,
                "analysis_details": self._create_analysis_details(
                    rsi_signal, macd_result, bb_result, stoch_result, patterns
                )
            }
            
            logger.info(f"Gram altın analizi tamamlandı. Sinyal: {signal}, Güven: {confidence:.2%}, Fiyat: {current_price}")
            return result
            
        except Exception as e:
            logger.error(f"Gram altın analiz hatası: {e}", exc_info=True)
            return self._empty_analysis()
    
    def _analyze_trend(self, prices: List[float], macd: Dict) -> Tuple[TrendType, TrendStrength]:
        """Trend yönü ve gücünü belirle"""
        current_price = prices[-1]
        
        # Yeterli veri varsa MA20 kullan, yoksa daha kısa MA kullan
        if len(prices) >= 20:
            ma_period = 20
        elif len(prices) >= 10:
            ma_period = 10
        else:
            ma_period = len(prices) // 2 if len(prices) > 2 else 2
        
        ma = np.mean(prices[-ma_period:])
        
        # MACD durumu
        macd_histogram = macd.get("histogram")
        macd_bullish = macd_histogram is not None and macd_histogram > 0
        
        # Fiyat MA'nin üstünde ve MACD pozitif
        if current_price > ma and macd_bullish:
            trend = TrendType.BULLISH
        elif current_price < ma and not macd_bullish:
            trend = TrendType.BEARISH
        else:
            trend = TrendType.NEUTRAL
        
        # Trend gücü
        if ma > 0:  # Sıfıra bölme kontrolü
            price_distance = abs((current_price - ma) / ma * 100)
            if price_distance > 3:
                strength = TrendStrength.STRONG
            elif price_distance > 1:
                strength = TrendStrength.MODERATE
            else:
                strength = TrendStrength.WEAK
        else:
            strength = TrendStrength.WEAK
            
        return trend, strength
    
    def _find_support_resistance(self, candles: List[GramAltinCandle]) -> Tuple[List[SupportResistanceLevel], List[SupportResistanceLevel]]:
        """Destek ve direnç seviyelerini bul"""
        # Basit pivot noktaları
        highs = [float(c.high) for c in candles]
        lows = [float(c.low) for c in candles]
        
        # Son 50 mumun en yüksek ve en düşük noktaları
        recent_highs = sorted(highs[-50:], reverse=True)[:5]
        recent_lows = sorted(lows[-50:])[:5]
        
        # Destek seviyeleri
        support_levels = []
        for i, low in enumerate(recent_lows):
            support_levels.append(SupportResistanceLevel(
                level=Decimal(str(low)),
                strength="strong" if i == 0 else "moderate" if i < 3 else "weak",
                touches=highs.count(low) + lows.count(low)
            ))
        
        # Direnç seviyeleri
        resistance_levels = []
        for i, high in enumerate(recent_highs):
            resistance_levels.append(SupportResistanceLevel(
                level=Decimal(str(high)),
                strength="strong" if i == 0 else "moderate" if i < 3 else "weak",
                touches=highs.count(high) + lows.count(high)
            ))
        
        return support_levels[:3], resistance_levels[:3]
    
    def _generate_signal(self, **kwargs) -> Tuple[str, float]:
        """Tüm göstergeleri birleştirerek sinyal üret"""
        buy_signals = 0
        sell_signals = 0
        total_weight = 0
        
        # RSI sinyali
        rsi_value, rsi_signal = kwargs["rsi"]
        if rsi_signal == "oversold":
            buy_signals += 2
            total_weight += 2
        elif rsi_signal == "overbought":
            sell_signals += 2
            total_weight += 2
        else:
            total_weight += 1
        
        # MACD sinyali
        macd = kwargs["macd"]
        if macd.get("signal") == "BUY":
            buy_signals += 3
        elif macd.get("signal") == "SELL":
            sell_signals += 3
        total_weight += 3
        
        # Bollinger Bands
        bb = kwargs["bollinger"]
        if bb.get("position") == "below_lower":
            buy_signals += 2
        elif bb.get("position") == "above_upper":
            sell_signals += 2
        total_weight += 2
        
        # Stochastic
        stoch = kwargs["stochastic"]
        if stoch.get("signal") == "oversold":
            buy_signals += 1
        elif stoch.get("signal") == "overbought":
            sell_signals += 1
        total_weight += 1
        
        # Pattern recognition
        patterns = kwargs["patterns"]
        for pattern in patterns:
            # Pattern bir string veya dict olabilir
            pattern_name = pattern if isinstance(pattern, str) else pattern.get("name", "")
            if "bullish" in pattern_name.lower():
                buy_signals += 2
            elif "bearish" in pattern_name.lower():
                sell_signals += 2
            total_weight += 2
        
        # Trend uyumu
        trend = kwargs["trend"]
        if trend == TrendType.BULLISH and buy_signals > sell_signals:
            buy_signals += 1
        elif trend == TrendType.BEARISH and sell_signals > buy_signals:
            sell_signals += 1
        
        # Sinyal kararı
        if buy_signals > sell_signals and buy_signals >= total_weight * 0.4:
            signal = "BUY"
            confidence = buy_signals / total_weight
        elif sell_signals > buy_signals and sell_signals >= total_weight * 0.4:
            signal = "SELL"
            confidence = sell_signals / total_weight
        else:
            signal = "HOLD"
            # HOLD durumunda daha hassas confidence hesapla
            total_signals = buy_signals + sell_signals
            
            # Temel güven bileşenleri
            components = []
            
            # 1. Sinyal dengesi (0-1 arası, dengeli olduğunda yüksek)
            if total_signals > 0:
                balance_ratio = 1 - abs(buy_signals - sell_signals) / total_weight
                components.append(("balance", balance_ratio, 0.15))
            
            # 2. RSI değeri (30-70 arası normalize)
            if rsi_value is not None:
                rsi_normalized = 1 - abs(rsi_value - 50) / 50
                components.append(("rsi", rsi_normalized, 0.15))
            
            # 3. Bollinger Band pozisyonu
            bb_position = bb.get("position", "middle")
            bb_width = bb.get("band_width", 0)
            if bb_width > 0:
                # Band genişliği volatiliteyi gösterir
                volatility_factor = min(bb_width / 100, 1.0)  # Normalize et
                components.append(("volatility", volatility_factor, 0.1))
            
            # 4. MACD momentum
            macd_hist = macd.get("histogram", 0)
            if macd_hist is not None:
                # Histogram değerini normalize et (-1 ile 1 arası)
                macd_normalized = 1 - min(abs(macd_hist) / 10, 1.0)
                components.append(("momentum", macd_normalized, 0.15))
            
            # 4.5 Fiyat değişim hızı ve volatilite
            prices = kwargs.get("prices", [])
            if prices and len(prices) >= 5:
                recent_prices = prices[-5:]
                price_change = (recent_prices[-1] - recent_prices[0]) / recent_prices[0]
                # Altın için %0.5'lik değişim bile önemli
                volatility_score = min(abs(price_change) * 200, 1.0)  # %0.5 = 1.0 skor
                components.append(("price_change", 1 - volatility_score, 0.1))
                
                # Son 10 mumun standart sapması (volatilite)
                if len(prices) >= 10:
                    last_10_prices = prices[-10:]
                    std_dev = np.std(last_10_prices)
                    avg_price = np.mean(last_10_prices)
                    volatility_ratio = std_dev / avg_price if avg_price > 0 else 0
                    # Düşük volatilite = yüksek güven
                    volatility_conf = 1 - min(volatility_ratio * 100, 1.0)  # %1 volatilite = 0 güven
                    components.append(("std_dev", volatility_conf, 0.1))
            
            # 5. Stochastic değeri
            stoch_k = stoch.get("k", 50)
            if stoch_k is not None:
                stoch_normalized = 1 - abs(stoch_k - 50) / 50
                components.append(("stochastic", stoch_normalized, 0.1))
            
            # 6. Trend gücü
            trend_strength = kwargs.get("trend_strength", TrendStrength.WEAK)
            strength_scores = {
                TrendStrength.STRONG: 0.3,
                TrendStrength.MODERATE: 0.6,
                TrendStrength.WEAK: 0.9
            }
            components.append(("trend", strength_scores.get(trend_strength, 0.5), 0.15))
            
            # 7. Aktif gösterge oranı
            active_count = sum([
                1 if rsi_value is not None else 0,
                1 if macd.get("signal") else 0,
                1 if bb.get("position") else 0,
                1 if stoch.get("signal") else 0,
                1 if len(patterns) > 0 else 0
            ])
            indicator_ratio = active_count / 5
            components.append(("indicators", indicator_ratio, 0.1))
            
            # 8. Veri yeterliliği (mum sayısı)
            prices = kwargs.get("prices", [])
            if prices:
                data_sufficiency = min(len(prices) / 50, 1.0)  # 50 mum = %100 yeterlilik
                components.append(("data_sufficiency", data_sufficiency, 0.1))
            
            # Ağırlıklı ortalama hesapla
            if components:
                total_weight_sum = sum(weight for _, _, weight in components)
                confidence = sum(value * weight for _, value, weight in components) / total_weight_sum
                
                # Debug için bileşenleri logla
                comp_details = ", ".join([f"{name}={value:.3f}*{weight}" for name, value, weight in components])
                logger.info(f"HOLD confidence components: {comp_details}, final={confidence:.3f}")
            else:
                confidence = 0.5
            
            # 0.3 - 0.7 aralığına sınırla (HOLD için daha dar aralık)
            confidence = max(0.3, min(0.7, confidence))
        
        logger.info(f"Signal generation: buy={buy_signals}, sell={sell_signals}, total_weight={total_weight}, signal={signal}, confidence={confidence:.3f}")
        return signal, confidence
    
    def _calculate_risk_levels(self, current_price: Decimal, signal: str, 
                              atr: float, support_levels: List, resistance_levels: List) -> Tuple[Optional[Decimal], Optional[Decimal]]:
        """Stop-loss ve take-profit hesapla"""
        if signal == "HOLD":
            return None, None
        
        atr_decimal = Decimal(str(atr))
        
        if signal == "BUY":
            # En yakın desteğin biraz altı veya ATR bazlı
            if support_levels:
                stop_loss = support_levels[0].level * Decimal("0.995")
            else:
                stop_loss = current_price - (atr_decimal * 2)
            
            # En yakın direncin biraz altı veya ATR bazlı
            if resistance_levels:
                take_profit = resistance_levels[0].level * Decimal("0.995")
            else:
                take_profit = current_price + (atr_decimal * 3)
                
        else:  # SELL
            # En yakın direncin biraz üstü veya ATR bazlı
            if resistance_levels:
                stop_loss = resistance_levels[0].level * Decimal("1.005")
            else:
                stop_loss = current_price + (atr_decimal * 2)
            
            # En yakın desteğin biraz üstü veya ATR bazlı
            if support_levels:
                take_profit = support_levels[0].level * Decimal("1.005")
            else:
                take_profit = current_price - (atr_decimal * 3)
        
        return stop_loss, take_profit
    
    def _create_analysis_details(self, rsi_signal: str, macd: Dict, 
                                bollinger: Dict, stochastic: Dict, patterns: List) -> Dict:
        """Detaylı analiz açıklaması"""
        details = {
            "rsi_analysis": f"RSI {rsi_signal} bölgesinde",
            "macd_analysis": f"MACD {macd.get('signal', 'nötr')} sinyali veriyor",
            "bollinger_analysis": f"Fiyat Bollinger bandının {bollinger.get('position', 'ortasında')}",
            "stochastic_analysis": f"Stochastic {stochastic.get('signal', 'nötr')} seviyede",
            "patterns_found": [p["name"] for p in patterns] if patterns else ["Belirgin formasyon yok"]
        }
        return details
    
    def _empty_analysis(self) -> Dict[str, Any]:
        """Boş analiz sonucu"""
        return {
            "timestamp": datetime.utcnow(),
            "price": Decimal("0"),
            "trend": TrendType.NEUTRAL,
            "trend_strength": TrendStrength.WEAK,
            "indicators": {},
            "patterns": [],
            "support_levels": [],
            "resistance_levels": [],
            "signal": "HOLD",
            "confidence": 0,
            "stop_loss": None,
            "take_profit": None,
            "analysis_details": {"error": "Yetersiz veri"}
        }