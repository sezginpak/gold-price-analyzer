"""
Gram Altın Analiz Motoru - Ana analiz sistemi
"""
from typing import List, Dict, Any, Optional, Tuple
from decimal import Decimal, InvalidOperation
import decimal
from datetime import timedelta
import logging
import numpy as np
from utils import timezone

from models.market_data import MarketData, GramAltinCandle
from indicators.rsi import RSIIndicator
from indicators.macd import MACDIndicator
from indicators.bollinger_bands import BollingerBandsIndicator
from indicators.stochastic import StochasticIndicator
from indicators.atr import ATRIndicator
from indicators.pattern_recognition import PatternRecognition
from models.analysis_result import TrendType, TrendStrength, SupportResistanceLevel

logger = logging.getLogger("gold_analyzer")


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
            
            # Fiyat dizisi hazırla - numpy array kullan (daha hızlı)
            prices = np.array([float(c.close) for c in candles])
            high_prices = np.array([float(c.high) for c in candles])
            low_prices = np.array([float(c.low) for c in candles])
            
            current_price = Decimal(str(prices[-1]))
            logger.info(f"Mevcut gram altın fiyatı: {current_price}")
            
            # Teknik göstergeler
            rsi_value, rsi_signal = self.rsi.calculate(prices.tolist())  # RSI List[float] bekliyor
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
            
            # RSI Divergence ve Volume analizi
            rsi_divergence = self._detect_rsi_divergence(candles, prices)
            volume_spike = self._detect_volume_spike(candles)
            
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
                patterns=patterns,
                resistance_levels=resistance_levels,
                rsi_divergence=rsi_divergence,
                volume_spike=volume_spike
            )
            
            # Risk hesaplama
            stop_loss, take_profit = self._calculate_risk_levels(
                current_price, signal, atr_value, support_levels, resistance_levels
            )
            
            result = {
                "timestamp": timezone.utc_now(),
                "price": float(current_price),
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
    
    def _analyze_trend(self, prices: np.ndarray, macd: Dict) -> Tuple[TrendType, TrendStrength]:
        """Trend yönü ve gücünü belirle"""
        current_price = float(prices[-1])
        
        # Yeterli veri varsa MA20 kullan, yoksa daha kısa MA kullan
        ma_period = min(20, len(prices) // 2 if len(prices) > 2 else 2)
        
        ma = float(np.mean(prices[-ma_period:]))
        
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
        # Numpy array'e çevir - daha hızlı işlem
        candle_count = len(candles)
        look_back = min(50, candle_count)
        
        highs = np.array([float(c.high) for c in candles[-look_back:]])
        lows = np.array([float(c.low) for c in candles[-look_back:]])
        
        # En yüksek ve en düşük 5 nokta
        unique_highs = np.unique(highs)[-5:][::-1]  # Benzersiz ve sıralı
        unique_lows = np.unique(lows)[:5]  # Benzersiz ve sıralı
        
        # Destek seviyeleri
        support_levels = []
        for i, low in enumerate(unique_lows):
            support_levels.append(SupportResistanceLevel(
                level=Decimal(str(low)),
                strength="strong" if i == 0 else "moderate" if i < 3 else "weak",
                touches=int(np.sum(np.isclose(highs, low, rtol=0.0001)) + np.sum(np.isclose(lows, low, rtol=0.0001)))
            ))
        
        # Direnç seviyeleri
        resistance_levels = []
        for i, high in enumerate(unique_highs):
            resistance_levels.append(SupportResistanceLevel(
                level=Decimal(str(high)),
                strength="strong" if i == 0 else "moderate" if i < 3 else "weak",
                touches=int(np.sum(np.isclose(highs, high, rtol=0.0001)) + np.sum(np.isclose(lows, high, rtol=0.0001)))
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
        
        # RSI Divergence bonusu (DIP/TEPE yakalama için kritik)
        rsi_divergence = kwargs.get("rsi_divergence", {})
        if rsi_divergence.get("detected"):
            div_type = rsi_divergence.get("type")
            div_strength = rsi_divergence.get("strength", 0)
            
            if div_type == "bullish":  # DIP sinyali
                buy_signals += div_strength * 3  # Güçlü bonus
                total_weight += 2
                logger.info(f"🎯 BULLISH DIVERGENCE detected - strength: {div_strength:.2f}")
            elif div_type == "bearish":  # TEPE sinyali
                sell_signals += div_strength * 3  # Güçlü bonus
                total_weight += 2
                logger.info(f"🎯 BEARISH DIVERGENCE detected - strength: {div_strength:.2f}")
        
        # Volume Spike bonusu
        volume_spike = kwargs.get("volume_spike", {})
        if volume_spike.get("detected"):
            spike_ratio = volume_spike.get("spike_ratio", 1)
            volume_bonus = min((spike_ratio - 1) * 2, 2)  # Max 2 puan
            
            # Mevcut trend yönünde volume spike bonusu ver
            if buy_signals > sell_signals:
                buy_signals += volume_bonus
            elif sell_signals > buy_signals:
                sell_signals += volume_bonus
            total_weight += 1
            logger.info(f"📊 VOLUME SPIKE detected - ratio: {spike_ratio:.1f}x, bonus: {volume_bonus:.1f}")
        
        # MACD sinyali
        macd = kwargs["macd"]
        if macd.get("signal") == "BUY":
            buy_signals += 3
        elif macd.get("signal") == "SELL":
            sell_signals += 3
        total_weight += 3
        
        # Bollinger Bands
        bb = kwargs["bollinger"]
        bb_position = bb.get("position", "middle")
        if bb_position == "below_lower":
            buy_signals += 2
        elif bb_position == "above_upper":
            sell_signals += 2
        elif bb_position == "near_lower":  # Alt banda yakın
            buy_signals += 1
        elif bb_position == "near_upper":  # Üst banda yakın
            sell_signals += 1
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
        
        # SELL sinyalı için ek kriterler
        # RSI değerini kontrol et
        if rsi_value is not None:
            if rsi_value > 70:  # Aşırı alım
                sell_signals += 1.5
                total_weight += 1.5
            elif rsi_value > 80:  # Kuvvetli aşırı alım
                sell_signals += 1
                total_weight += 1
        
        # MACD histogram negatif mi?
        macd_hist = macd.get("histogram", 0)
        if macd_hist is not None and macd_hist < 0:
            sell_signals += 1
            total_weight += 1
            
        # Fiyat direnç seviyesinde mi?
        current_price = kwargs.get("current_price")
        resistances = kwargs.get("resistance_levels", [])
        if current_price and resistances:
            for res in resistances[:2]:  # En yakın 2 direnç
                price_diff = abs(float(current_price - res.level) / float(res.level))
                if price_diff < 0.005:  # %0.5'ten yakın
                    sell_signals += 1.5
                    total_weight += 1.5
                    break
        
        # Trend uyumu
        trend = kwargs["trend"]
        if trend == TrendType.BULLISH and buy_signals > sell_signals:
            buy_signals += 1
        elif trend == TrendType.BEARISH and sell_signals > buy_signals:
            sell_signals += 1
        
        # Sinyal kararı (altın için daha hassas - %20'ye düşürüldü)
        if buy_signals > sell_signals and buy_signals >= total_weight * 0.20:  # %20 eşik - daha dengeli hassasiyet
            signal = "BUY"
            # BUY/SELL için basit güven hesabı
            base_confidence = buy_signals / total_weight
            # Trend uyumu bonusu
            if trend == TrendType.BULLISH:
                base_confidence = min(base_confidence * 1.2, 1.0)
            confidence = base_confidence
        elif sell_signals > buy_signals and sell_signals >= total_weight * 0.20:  # %20 eşik - daha dengeli hassasiyet
            signal = "SELL"
            # BUY/SELL için basit güven hesabı
            base_confidence = sell_signals / total_weight
            # Trend uyumu bonusu
            if trend == TrendType.BEARISH:
                base_confidence = min(base_confidence * 1.2, 1.0)
            confidence = base_confidence
        # Eşit sinyal durumunda trend yönünde karar ver
        elif buy_signals == sell_signals and buy_signals > 0:
            base_confidence = (buy_signals + sell_signals) / (total_weight * 2)  # Base confidence tanımla
            if trend == TrendType.BULLISH and rsi_value and rsi_value < 50:
                signal = "BUY"
                confidence = base_confidence * 0.8
            elif trend == TrendType.BEARISH and rsi_value and rsi_value > 50:
                signal = "SELL"
                confidence = base_confidence * 0.8
            else:
                signal = "HOLD"
                confidence = 0.5  # HOLD durumu için default confidence
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
            if bb_width is not None and bb_width > 0:
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
            prices = kwargs.get("prices", np.array([]))
            if len(prices) >= 5:
                recent_prices = prices[-5:]
                price_change = (recent_prices[-1] - recent_prices[0]) / recent_prices[0] if recent_prices[0] != 0 else 0
                # Altın için %0.5'lik değişim bile önemli
                volatility_score = min(abs(price_change) * 200, 1.0)  # %0.5 = 1.0 skor
                components.append(("price_change", 1 - volatility_score, 0.1))
                
                # Son 10 mumun standart sapması (volatilite)
                if len(prices) >= 10:
                    last_10_prices = prices[-10:]
                    std_dev = float(np.std(last_10_prices))
                    avg_price = float(np.mean(last_10_prices))
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
            if len(prices) > 0:
                data_sufficiency = min(len(prices) / 35, 1.0)  # 35 mum = %100 yeterlilik (main.py'deki 15m requirement ile uyumlu)
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
        """Stop-loss ve take-profit hesapla - Dinamik ATR bazlı"""
        if signal == "HOLD":
            return None, None
        
        # ATR None veya geçersizse varsayılan değer kullan
        try:
            if atr is None or atr == 0 or not isinstance(atr, (int, float)):
                atr_decimal = Decimal("10")  # Varsayılan ATR
            else:
                atr_decimal = Decimal(str(float(atr)))
        except (TypeError, ValueError, InvalidOperation) as e:
            logger.warning(f"ATR conversion error: {e}, using default value")
            atr_decimal = Decimal("10")
        
        if signal == "BUY":
            # Stop Loss: En yakın desteğin altı veya ATR bazlı - ATR çarpanı 1.5'e çıkarıldı
            if support_levels:
                sl_from_support = support_levels[0].level * Decimal("0.995")
                sl_from_atr = current_price - (atr_decimal * Decimal("1.5"))
                stop_loss = max(sl_from_support, sl_from_atr)  # Daha güvenli olanı seç
            else:
                stop_loss = current_price - (atr_decimal * Decimal("1.5"))
            
            # Take Profit: Dinamik hesaplama
            # 1. Resistance varsa ve makul mesafedeyse kullan
            if resistance_levels:
                nearest_resistance = resistance_levels[0].level
                resistance_distance = (nearest_resistance - current_price) / current_price
                logger.info(f"BUY TP Check - Price: {current_price}, Resistance: {nearest_resistance}, Distance: {resistance_distance:.1%}")
                
                # Eğer resistance çok uzaksa (fiyatın %2'sinden fazla) ATR bazlı hesapla
                if resistance_distance > Decimal("0.02"):
                    # Volatiliteye göre dinamik TP çarpanı
                    volatility = float(atr_decimal) / float(current_price) * 100
                    if volatility < 0.5:  # Düşük volatilite
                        tp_multiplier = Decimal("2.0")
                    elif volatility > 1.0:  # Yüksek volatilite
                        tp_multiplier = Decimal("3.5")
                    else:
                        tp_multiplier = Decimal("2.5")
                    take_profit = current_price + (atr_decimal * tp_multiplier)
                    logger.info(f"Resistance too far ({resistance_distance:.1%}), using dynamic ATR-based TP (vol={volatility:.2f}%, mult={tp_multiplier})")
                else:
                    take_profit = nearest_resistance * Decimal("0.995")
                    logger.info(f"Using resistance-based TP at {take_profit}")
            else:
                # Resistance yoksa volatilite bazlı dinamik TP
                volatility = float(atr_decimal) / float(current_price) * 100
                if volatility < 0.5:
                    tp_multiplier = Decimal("2.0")
                elif volatility > 1.0:
                    tp_multiplier = Decimal("3.5")
                else:
                    tp_multiplier = Decimal("2.5")
                take_profit = current_price + (atr_decimal * tp_multiplier)
                logger.debug(f"No resistance found, using ATR-based TP")
                
        else:  # SELL
            # Stop Loss: En yakın direncin üstü veya ATR bazlı - ATR çarpanı 1.5'e çıkarıldı
            if resistance_levels:
                sl_from_resistance = resistance_levels[0].level * Decimal("1.005")
                sl_from_atr = current_price + (atr_decimal * Decimal("1.5"))
                stop_loss = min(sl_from_resistance, sl_from_atr)
            else:
                stop_loss = current_price + (atr_decimal * Decimal("1.5"))
            
            # Take Profit: Dinamik hesaplama
            if support_levels:
                nearest_support = support_levels[0].level
                support_distance = (current_price - nearest_support) / current_price
                
                # Eğer destek çok uzaksa ATR bazlı hesapla
                if support_distance > Decimal("0.02"):
                    # Volatiliteye göre dinamik TP çarpanı
                    volatility = float(atr_decimal) / float(current_price) * 100
                    if volatility < 0.5:
                        tp_multiplier = Decimal("2.0")
                    elif volatility > 1.0:
                        tp_multiplier = Decimal("3.5")
                    else:
                        tp_multiplier = Decimal("2.5")
                    take_profit = current_price - (atr_decimal * tp_multiplier)
                    logger.debug(f"Support too far ({support_distance:.1%}), using dynamic ATR-based TP (vol={volatility:.2f}%, mult={tp_multiplier})")
                else:
                    take_profit = nearest_support * Decimal("1.005")
                    logger.debug(f"Using support-based TP at {take_profit}")
            else:
                # Support yoksa volatilite bazlı dinamik TP
                volatility = float(atr_decimal) / float(current_price) * 100
                if volatility < 0.5:
                    tp_multiplier = Decimal("2.0")
                elif volatility > 1.0:
                    tp_multiplier = Decimal("3.5")
                else:
                    tp_multiplier = Decimal("2.5")
                take_profit = current_price - (atr_decimal * tp_multiplier)
                logger.debug(f"No support found, using ATR-based TP")
        
        # Risk/Reward kontrolü - minimum 1.5:1 olmalı
        risk = abs(current_price - stop_loss)
        reward = abs(take_profit - current_price)
        
        if risk > 0 and reward / risk < Decimal("1.5"):
            # TP'yi genişlet
            if signal == "BUY":
                take_profit = current_price + (risk * Decimal("2"))
            else:
                take_profit = current_price - (risk * Decimal("2"))
            logger.debug(f"Adjusted TP for better R:R ratio")
        
        logger.debug(f"Risk levels - Price: {current_price}, SL: {stop_loss}, TP: {take_profit}, R:R: {reward/risk if risk > 0 else 0:.2f}")
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
            "timestamp": timezone.utc_now(),
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
    
    def _detect_rsi_divergence(self, candles: List[GramAltinCandle], prices: np.ndarray) -> Dict[str, Any]:
        """RSI Divergence tespiti - dip/tepe yakalama için kritik"""
        try:
            if len(candles) < 20:
                return {"detected": False, "type": None, "strength": 0}
            
            # Son 20 mumun RSI değerlerini hesapla
            lookback = min(20, len(prices))
            recent_prices = prices[-lookback:]
            
            # RSI hesapla
            rsi_values = []
            for i in range(14, len(recent_prices)):
                price_slice = recent_prices[i-13:i+1]
                gains = []
                losses = []
                
                for j in range(1, len(price_slice)):
                    change = price_slice[j] - price_slice[j-1]
                    if change > 0:
                        gains.append(change)
                        losses.append(0)
                    else:
                        gains.append(0)
                        losses.append(abs(change))
                
                avg_gain = np.mean(gains) if gains else 0
                avg_loss = np.mean(losses) if losses else 0
                
                if avg_loss == 0:
                    rsi = 100
                else:
                    rs = avg_gain / avg_loss
                    rsi = 100 - (100 / (1 + rs))
                
                rsi_values.append(rsi)
            
            if len(rsi_values) < 6:
                return {"detected": False, "type": None, "strength": 0}
            
            # Son 6 periyotta divergence ara
            recent_rsi = rsi_values[-6:]
            recent_prices_for_div = recent_prices[-6:]
            
            # Fiyat düşer ama RSI yükselirse = Bullish Divergence (dip sinyali)
            price_trend = recent_prices_for_div[-1] - recent_prices_for_div[0]
            rsi_trend = recent_rsi[-1] - recent_rsi[0]
            
            divergence_strength = 0
            divergence_type = None
            
            # Bullish Divergence (DIP SINYALI)
            if price_trend < 0 and rsi_trend > 0:
                divergence_type = "bullish"
                # Güç hesapla: RSI ne kadar fazla yükselmiş, fiyat ne kadar düşmüş
                price_decline_pct = abs(price_trend) / recent_prices_for_div[0] * 100
                rsi_increase = rsi_trend
                
                if price_decline_pct > 0.5 and rsi_increase > 5:  # Belirgin divergence
                    divergence_strength = min(0.8, (price_decline_pct + rsi_increase/10) / 2)
                else:
                    divergence_strength = 0.3
            
            # Bearish Divergence (TEPE SINYALI)  
            elif price_trend > 0 and rsi_trend < 0:
                divergence_type = "bearish"
                price_increase_pct = price_trend / recent_prices_for_div[0] * 100
                rsi_decrease = abs(rsi_trend)
                
                if price_increase_pct > 0.5 and rsi_decrease > 5:
                    divergence_strength = min(0.8, (price_increase_pct + rsi_decrease/10) / 2)
                else:
                    divergence_strength = 0.3
            
            return {
                "detected": divergence_type is not None,
                "type": divergence_type,
                "strength": divergence_strength,
                "price_trend": price_trend,
                "rsi_trend": rsi_trend
            }
            
        except Exception as e:
            logger.error(f"RSI divergence tespiti hatası: {e}")
            return {"detected": False, "type": None, "strength": 0}
    
    def _detect_volume_spike(self, candles: List[GramAltinCandle]) -> Dict[str, Any]:
        """Volume spike tespiti - güçlü hareket onayı için"""
        try:
            if len(candles) < 20:
                return {"detected": False, "spike_ratio": 0}
            
            # Volume değerlerini topla
            volumes = []
            for candle in candles:
                volume = getattr(candle, 'volume', 0) or 0
                volumes.append(float(volume))
            
            # Volume değeri yoksa varsayılan analiz
            if all(v == 0 for v in volumes):
                return {"detected": False, "spike_ratio": 0, "note": "Volume data not available"}
            
            # Son 20 mumun ortalama volume'ü
            lookback = min(20, len(volumes))
            recent_volumes = volumes[-lookback:]
            avg_volume = np.mean(recent_volumes[:-1])  # Son mum hariç
            current_volume = recent_volumes[-1]
            
            if avg_volume == 0:
                return {"detected": False, "spike_ratio": 0}
            
            spike_ratio = current_volume / avg_volume
            
            # 1.5x ve üzeri volume spike sayılır
            spike_detected = spike_ratio >= 1.5
            
            return {
                "detected": spike_detected,
                "spike_ratio": spike_ratio,
                "current_volume": current_volume,
                "average_volume": avg_volume,
                "threshold": 1.5
            }
            
        except Exception as e:
            logger.error(f"Volume spike tespiti hatası: {e}")
            return {"detected": False, "spike_ratio": 0}