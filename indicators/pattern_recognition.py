"""
Pattern Recognition - Teknik analiz formasyonları tanıma
"""
from typing import List, Dict, Optional, Tuple
from decimal import Decimal
import logging
from models.price_data import PriceCandle

logger = logging.getLogger(__name__)


class PatternRecognition:
    """Grafik formasyonları tanıma"""
    
    def __init__(self, min_pattern_size: int = 5):
        """
        Args:
            min_pattern_size: Minimum formasyon boyutu
        """
        self.min_pattern_size = min_pattern_size
    
    def _empty_result(self) -> Dict[str, any]:
        """Boş sonuç döndür"""
        return {
            "patterns": [],
            "strongest_pattern": None,
            "signal": None,
            "pattern_count": 0
        }
    
    def detect_patterns(self, candles: List[PriceCandle]) -> Dict[str, any]:
        """Tüm formasyonları tespit et"""
        try:
            if not candles:
                logger.warning("No candles provided for pattern detection")
                return self._empty_result()
            
            if len(candles) < 20:
                logger.debug(f"Not enough candles for pattern detection: {len(candles)}")
                return self._empty_result()
        
            patterns = []
            
            # Candlestick patterns (mum formasyonları)
            try:
                candlestick_patterns = self._detect_candlestick_patterns(candles)
                patterns.extend(candlestick_patterns)
            except Exception as e:
                logger.error(f"Error detecting candlestick patterns: {e}")
            
            # Chart patterns (grafik formasyonları)
            try:
                chart_patterns = self._detect_chart_patterns(candles)
                patterns.extend(chart_patterns)
            except Exception as e:
                logger.error(f"Error detecting chart patterns: {e}")
            
            # Support/Resistance patterns
            try:
                sr_patterns = self._detect_sr_patterns(candles)
                patterns.extend(sr_patterns)
            except Exception as e:
                logger.error(f"Error detecting S/R patterns: {e}")
            
            # En güçlü formasyonu bul
            strongest = max(patterns, key=lambda x: x.get("confidence", 0)) if patterns else None
            
            # Sinyal üret
            signal = self._generate_signal_from_patterns(patterns)
            
            return {
                "patterns": patterns,
                "strongest_pattern": strongest,
                "signal": signal,
                "pattern_count": len(patterns)
            }
            
        except Exception as e:
            logger.error(f"Unexpected error in pattern detection: {e}", exc_info=True)
            return self._empty_result()
    
    def _detect_candlestick_patterns(self, candles: List[PriceCandle]) -> List[Dict[str, any]]:
        """Mum formasyonlarını tespit et"""
        patterns = []
        
        if len(candles) < 3:
            return patterns
        
        # Hammer (Çekiç)
        hammer = self._detect_hammer(candles[-1], candles[-2])
        if hammer:
            patterns.append(hammer)
        
        # Doji
        doji = self._detect_doji(candles[-1])
        if doji:
            patterns.append(doji)
        
        # Engulfing (Yutan)
        engulfing = self._detect_engulfing(candles[-2:])
        if engulfing:
            patterns.append(engulfing)
        
        # Three White Soldiers / Three Black Crows
        if len(candles) >= 3:
            three_pattern = self._detect_three_pattern(candles[-3:])
            if three_pattern:
                patterns.append(three_pattern)
        
        # Morning/Evening Star
        if len(candles) >= 3:
            star = self._detect_star_pattern(candles[-3:])
            if star:
                patterns.append(star)
        
        return patterns
    
    def _detect_hammer(self, current: PriceCandle, previous: PriceCandle) -> Optional[Dict[str, any]]:
        """Hammer formasyonu tespiti"""
        try:
            body = abs(float(current.close - current.open))
            upper_shadow = float(current.high - max(current.open, current.close))
            lower_shadow = float(min(current.open, current.close) - current.low)
            total_range = float(current.high - current.low)
            
            if total_range == 0 or body == 0:
                return None
            
            # Hammer kriterleri
            # 1. Alt gölge gövdenin en az 2 katı
            # 2. Üst gölge çok küçük veya yok
            # 3. Düşüş trendinde
            if (lower_shadow >= body * 2 and 
                upper_shadow < body * 0.3 and
                current.close < previous.close):
                
                return {
                    "name": "HAMMER",
                    "type": "BULLISH",
                    "confidence": 0.7,
                    "position": len([current]),
                    "description": "Hammer - Potansiyel dip formasyonu"
                }
            
            # Inverted Hammer
            if (upper_shadow >= body * 2 and 
                lower_shadow < body * 0.3 and
                current.close < previous.close):
                
                return {
                    "name": "INVERTED_HAMMER",
                    "type": "BULLISH",
                    "confidence": 0.6,
                    "position": len([current]),
                    "description": "Inverted Hammer - Potansiyel dönüş sinyali"
                }
            
            return None
            
        except Exception as e:
            logger.error(f"Error detecting hammer pattern: {e}")
            return None
    
    def _detect_doji(self, candle: PriceCandle) -> Optional[Dict[str, any]]:
        """Doji formasyonu tespiti"""
        body = abs(float(candle.close - candle.open))
        total_range = float(candle.high - candle.low)
        
        if total_range == 0:
            return None
        
        # Doji: Açılış ve kapanış neredeyse eşit
        if body / total_range < 0.1:
            return {
                "name": "DOJI",
                "type": "NEUTRAL",
                "confidence": 0.5,
                "position": len([candle]),
                "description": "Doji - Kararsızlık"
            }
        
        return None
    
    def _detect_engulfing(self, candles: List[PriceCandle]) -> Optional[Dict[str, any]]:
        """Engulfing pattern tespiti"""
        if len(candles) < 2:
            return None
        
        prev = candles[0]
        curr = candles[1]
        
        prev_body = abs(float(prev.close - prev.open))
        curr_body = abs(float(curr.close - curr.open))
        
        # Bullish Engulfing
        if (prev.close < prev.open and  # Önceki kırmızı
            curr.close > curr.open and  # Şimdiki yeşil
            curr.open < prev.close and  # Açılış önceki kapanıştan düşük
            curr.close > prev.open and  # Kapanış önceki açılıştan yüksek
            curr_body > prev_body):     # Gövde daha büyük
            
            return {
                "name": "BULLISH_ENGULFING",
                "type": "BULLISH",
                "confidence": 0.8,
                "position": 2,
                "description": "Bullish Engulfing - Güçlü alım sinyali"
            }
        
        # Bearish Engulfing
        if (prev.close > prev.open and  # Önceki yeşil
            curr.close < curr.open and  # Şimdiki kırmızı
            curr.open > prev.close and  # Açılış önceki kapanıştan yüksek
            curr.close < prev.open and  # Kapanış önceki açılıştan düşük
            curr_body > prev_body):     # Gövde daha büyük
            
            return {
                "name": "BEARISH_ENGULFING",
                "type": "BEARISH",
                "confidence": 0.8,
                "position": 2,
                "description": "Bearish Engulfing - Güçlü satış sinyali"
            }
        
        return None
    
    def _detect_three_pattern(self, candles: List[PriceCandle]) -> Optional[Dict[str, any]]:
        """Three White Soldiers / Three Black Crows tespiti"""
        if len(candles) < 3:
            return None
        
        # Three White Soldiers kontrolü
        all_bullish = all(c.close > c.open for c in candles)
        ascending = all(candles[i].close > candles[i-1].close for i in range(1, 3))
        
        if all_bullish and ascending:
            # Her mumun gövdesi makul boyutta olmalı
            bodies = [abs(float(c.close - c.open)) for c in candles]
            avg_body = sum(bodies) / len(bodies)
            
            if all(b > avg_body * 0.5 for b in bodies):
                return {
                    "name": "THREE_WHITE_SOLDIERS",
                    "type": "BULLISH",
                    "confidence": 0.85,
                    "position": 3,
                    "description": "Three White Soldiers - Güçlü yükseliş trendi"
                }
        
        # Three Black Crows kontrolü
        all_bearish = all(c.close < c.open for c in candles)
        descending = all(candles[i].close < candles[i-1].close for i in range(1, 3))
        
        if all_bearish and descending:
            bodies = [abs(float(c.close - c.open)) for c in candles]
            avg_body = sum(bodies) / len(bodies)
            
            if all(b > avg_body * 0.5 for b in bodies):
                return {
                    "name": "THREE_BLACK_CROWS",
                    "type": "BEARISH",
                    "confidence": 0.85,
                    "position": 3,
                    "description": "Three Black Crows - Güçlü düşüş trendi"
                }
        
        return None
    
    def _detect_star_pattern(self, candles: List[PriceCandle]) -> Optional[Dict[str, any]]:
        """Morning Star / Evening Star tespiti"""
        if len(candles) < 3:
            return None
        
        first = candles[0]
        middle = candles[1]
        last = candles[2]
        
        # Morning Star (Bullish reversal)
        if (first.close < first.open and  # İlk mum bearish
            abs(float(middle.close - middle.open)) < abs(float(first.close - first.open)) * 0.3 and  # Orta mum küçük
            last.close > last.open and  # Son mum bullish
            last.close > first.open):   # Son kapanış ilk açılıştan yüksek
            
            return {
                "name": "MORNING_STAR",
                "type": "BULLISH",
                "confidence": 0.75,
                "position": 3,
                "description": "Morning Star - Dip dönüş formasyonu"
            }
        
        # Evening Star (Bearish reversal)
        if (first.close > first.open and  # İlk mum bullish
            abs(float(middle.close - middle.open)) < abs(float(first.close - first.open)) * 0.3 and  # Orta mum küçük
            last.close < last.open and  # Son mum bearish
            last.close < first.open):   # Son kapanış ilk açılıştan düşük
            
            return {
                "name": "EVENING_STAR",
                "type": "BEARISH",
                "confidence": 0.75,
                "position": 3,
                "description": "Evening Star - Zirve dönüş formasyonu"
            }
        
        return None
    
    def _detect_chart_patterns(self, candles: List[PriceCandle]) -> List[Dict[str, any]]:
        """Grafik formasyonlarını tespit et"""
        patterns = []
        
        # Double Top/Bottom
        double_pattern = self._detect_double_pattern(candles)
        if double_pattern:
            patterns.append(double_pattern)
        
        # Triangle patterns
        triangle = self._detect_triangle_pattern(candles)
        if triangle:
            patterns.append(triangle)
        
        # Flag/Pennant
        flag = self._detect_flag_pattern(candles)
        if flag:
            patterns.append(flag)
        
        return patterns
    
    def _detect_double_pattern(self, candles: List[PriceCandle]) -> Optional[Dict[str, any]]:
        """Double Top/Bottom tespiti"""
        try:
            if len(candles) < 20:
                return None
            
            # Son 20 mumda local high/low bul
            highs = []
            lows = []
            
            for i in range(1, len(candles) - 1):
                try:
                    # Local high
                    if candles[i].high > candles[i-1].high and candles[i].high > candles[i+1].high:
                        highs.append((i, float(candles[i].high)))
                    
                    # Local low
                    if candles[i].low < candles[i-1].low and candles[i].low < candles[i+1].low:
                        lows.append((i, float(candles[i].low)))
                except (IndexError, AttributeError) as e:
                    logger.debug(f"Error finding local extremes at index {i}: {e}")
                    continue
        
            # Double Top kontrolü
            if len(highs) >= 2:
                last_two_highs = highs[-2:]
                if last_two_highs[0][1] > 0:  # Sıfıra bölme kontrolü
                    diff_percent = abs(last_two_highs[0][1] - last_two_highs[1][1]) / last_two_highs[0][1]
                    
                    if diff_percent < 0.02:  # %2'den az fark
                        # Target hesaplama için slice kontrolü
                        start_idx = max(0, last_two_highs[0][0])
                        end_idx = min(len(candles), last_two_highs[1][0])
                        if start_idx < end_idx:
                            target_candles = candles[start_idx:end_idx]
                            if target_candles:
                                return {
                                    "name": "DOUBLE_TOP",
                                    "type": "BEARISH",
                                    "confidence": 0.7,
                                    "position": last_two_highs[1][0],
                                    "description": "Double Top - Potansiyel düşüş",
                                    "target": min(target_candles, key=lambda x: x.low).low
                                }
        
            # Double Bottom kontrolü
            if len(lows) >= 2:
                last_two_lows = lows[-2:]
                if last_two_lows[0][1] > 0:  # Sıfıra bölme kontrolü
                    diff_percent = abs(last_two_lows[0][1] - last_two_lows[1][1]) / last_two_lows[0][1]
                    
                    if diff_percent < 0.02:  # %2'den az fark
                        # Target hesaplama için slice kontrolü
                        start_idx = max(0, last_two_lows[0][0])
                        end_idx = min(len(candles), last_two_lows[1][0])
                        if start_idx < end_idx:
                            target_candles = candles[start_idx:end_idx]
                            if target_candles:
                                return {
                                    "name": "DOUBLE_BOTTOM",
                                    "type": "BULLISH",
                                    "confidence": 0.7,
                                    "position": last_two_lows[1][0],
                                    "description": "Double Bottom - Potansiyel yükseliş",
                                    "target": max(target_candles, key=lambda x: x.high).high
                                }
            
            return None
            
        except Exception as e:
            logger.error(f"Error detecting double pattern: {e}")
            return None
    
    def _detect_triangle_pattern(self, candles: List[PriceCandle]) -> Optional[Dict[str, any]]:
        """Üçgen formasyonu tespiti"""
        try:
            if len(candles) < 10:
                return None
            
            # Son 10 mumun high ve low'larını al
            highs = [float(c.high) for c in candles[-10:]]
            lows = [float(c.low) for c in candles[-10:]]
            
            if not highs or not lows or len(highs) == 0:
                return None
            
            # Trend çizgilerinin eğimini hesapla
            period_length = max(len(highs), 1)  # Sıfıra bölme kontrolü
            high_slope = (highs[-1] - highs[0]) / period_length
            low_slope = (lows[-1] - lows[0]) / period_length
            
            # Ascending Triangle (Yükselen üçgen)
            if abs(high_slope) < 0.001 and low_slope > 0:
                return {
                    "name": "ASCENDING_TRIANGLE",
                    "type": "BULLISH",
                    "confidence": 0.65,
                    "position": len(candles),
                    "description": "Ascending Triangle - Yükseliş formasyonu"
                }
            
            # Descending Triangle (Düşen üçgen)
            if high_slope < 0 and abs(low_slope) < 0.001:
                return {
                    "name": "DESCENDING_TRIANGLE",
                    "type": "BEARISH",
                    "confidence": 0.65,
                    "position": len(candles),
                    "description": "Descending Triangle - Düşüş formasyonu"
                }
            
            # Symmetrical Triangle (Simetrik üçgen)
            if high_slope < -0.001 and low_slope > 0.001:
                return {
                    "name": "SYMMETRICAL_TRIANGLE",
                    "type": "NEUTRAL",
                    "confidence": 0.6,
                    "position": len(candles),
                    "description": "Symmetrical Triangle - Kırılım bekleniyor"
                }
                
            return None
            
        except Exception as e:
            logger.error(f"Error detecting triangle pattern: {e}")
            return None
    
    def _detect_flag_pattern(self, candles: List[PriceCandle]) -> Optional[Dict[str, any]]:
        """Flag/Pennant formasyonu tespiti"""
        if len(candles) < 15:
            return None
        
        # İlk 5 mum: güçlü hareket (flagpole)
        flagpole = candles[-15:-10]
        flag = candles[-10:]
        
        # Flagpole hareketi
        pole_move = float(flagpole[-1].close - flagpole[0].open)
        pole_range = abs(pole_move)
        
        # Flag konsolidasyonu
        flag_high = max(c.high for c in flag)
        flag_low = min(c.low for c in flag)
        flag_range = float(flag_high - flag_low)
        
        # Flag, pole'un %50'sinden küçük olmalı
        if flag_range < pole_range * 0.5:
            if pole_move > 0:
                return {
                    "name": "BULL_FLAG",
                    "type": "BULLISH",
                    "confidence": 0.7,
                    "position": len(candles),
                    "description": "Bull Flag - Yükseliş devamı",
                    "target": float(flag[-1].close) + pole_range
                }
            else:
                return {
                    "name": "BEAR_FLAG",
                    "type": "BEARISH",
                    "confidence": 0.7,
                    "position": len(candles),
                    "description": "Bear Flag - Düşüş devamı",
                    "target": float(flag[-1].close) - pole_range
                }
        
        return None
    
    def _detect_sr_patterns(self, candles: List[PriceCandle]) -> List[Dict[str, any]]:
        """Support/Resistance bazlı formasyonlar"""
        patterns = []
        
        # Breakout tespiti
        breakout = self._detect_breakout(candles)
        if breakout:
            patterns.append(breakout)
        
        # False breakout (trap) tespiti
        trap = self._detect_false_breakout(candles)
        if trap:
            patterns.append(trap)
        
        return patterns
    
    def _detect_breakout(self, candles: List[PriceCandle]) -> Optional[Dict[str, any]]:
        """Breakout tespiti"""
        if len(candles) < 20:
            return None
        
        # Son 20 mumun direncini bul
        recent_high = max(c.high for c in candles[-20:-1])
        recent_low = min(c.low for c in candles[-20:-1])
        
        current = candles[-1]
        
        # Upside breakout
        if current.close > recent_high:
            return {
                "name": "RESISTANCE_BREAKOUT",
                "type": "BULLISH",
                "confidence": 0.75,
                "position": len(candles),
                "description": f"Direnç kırılımı: {recent_high}",
                "breakout_level": float(recent_high)
            }
        
        # Downside breakout
        if current.close < recent_low:
            return {
                "name": "SUPPORT_BREAKDOWN",
                "type": "BEARISH",
                "confidence": 0.75,
                "position": len(candles),
                "description": f"Destek kırılımı: {recent_low}",
                "breakdown_level": float(recent_low)
            }
        
        return None
    
    def _detect_false_breakout(self, candles: List[PriceCandle]) -> Optional[Dict[str, any]]:
        """False breakout (bull/bear trap) tespiti"""
        try:
            if len(candles) < 20:
                return None
            
            # Son 3 mumda breakout olup geri dönüş var mı?
            recent = candles[-5:]
            
            # Recent high/low
            historical_candles = candles[-20:-5]
            if not historical_candles:
                return None
            
            prev_high = max(c.high for c in historical_candles)
            prev_low = min(c.low for c in historical_candles)
        
            # Bull trap: Direnç kırılıp geri dönüş
            for i in range(len(recent) - 1):
                try:
                    if (recent[i].high > prev_high and  # Breakout
                        i + 1 < len(recent) and
                        recent[i+1].close < prev_high):  # Geri dönüş
                        
                        return {
                            "name": "BULL_TRAP",
                            "type": "BEARISH",
                            "confidence": 0.8,
                            "position": len(candles),
                            "description": "Bull Trap - Yanlış kırılım"
                        }
                except (IndexError, AttributeError) as e:
                    logger.debug(f"Error checking bull trap at index {i}: {e}")
                    continue
            
            # Bear trap: Destek kırılıp geri dönüş
            for i in range(len(recent) - 1):
                try:
                    if (recent[i].low < prev_low and  # Breakdown
                        i + 1 < len(recent) and
                        recent[i+1].close > prev_low):  # Geri dönüş
                        
                        return {
                            "name": "BEAR_TRAP",
                            "type": "BULLISH",
                            "confidence": 0.8,
                            "position": len(candles),
                            "description": "Bear Trap - Yanlış kırılım"
                        }
                except (IndexError, AttributeError) as e:
                    logger.debug(f"Error checking bear trap at index {i}: {e}")
                    continue
            
            return None
            
        except Exception as e:
            logger.error(f"Error detecting false breakout: {e}")
            return None
    
    def _generate_signal_from_patterns(self, patterns: List[Dict[str, any]]) -> Optional[Dict[str, any]]:
        """Formasyonlardan sinyal üret"""
        if not patterns:
            return None
        
        # Bullish ve bearish pattern'leri ayır
        bullish = [p for p in patterns if p["type"] == "BULLISH"]
        bearish = [p for p in patterns if p["type"] == "BEARISH"]
        
        # En güçlü sinyali belirle
        if bullish and not bearish:
            strongest = max(bullish, key=lambda x: x["confidence"])
            return {
                "type": "BUY",
                "confidence": strongest["confidence"],
                "reason": strongest["description"],
                "pattern": strongest["name"]
            }
        elif bearish and not bullish:
            strongest = max(bearish, key=lambda x: x["confidence"])
            return {
                "type": "SELL",
                "confidence": strongest["confidence"],
                "reason": strongest["description"],
                "pattern": strongest["name"]
            }
        elif bullish and bearish:
            # Çelişkili sinyaller varsa en güçlüsünü al
            strongest_bull = max(bullish, key=lambda x: x["confidence"])
            strongest_bear = max(bearish, key=lambda x: x["confidence"])
            
            if strongest_bull["confidence"] > strongest_bear["confidence"]:
                return {
                    "type": "BUY",
                    "confidence": strongest_bull["confidence"] * 0.8,  # Çelişki nedeniyle azalt
                    "reason": strongest_bull["description"],
                    "pattern": strongest_bull["name"]
                }
            else:
                return {
                    "type": "SELL",
                    "confidence": strongest_bear["confidence"] * 0.8,
                    "reason": strongest_bear["description"],
                    "pattern": strongest_bear["name"]
                }
        
        return None
    
    def get_signal_weight(self, result: Dict[str, any]) -> Tuple[Optional[str], float]:
        """
        Pattern'e göre sinyal ve güven skoru
        
        Returns:
            (signal_type, confidence): ("BUY"/"SELL"/None, 0.0-1.0)
        """
        try:
            if not result:
                return None, 0.0
            
            signal = result.get("signal")
            if not signal:
                return None, 0.0
            
            # Pattern sayısına göre güveni artır
            pattern_count = result.get("pattern_count", 0)
            confidence_boost = min(pattern_count * 0.1, 0.3)  # Max %30 boost
            
            base_confidence = signal.get("confidence", 0.0)
            final_confidence = min(base_confidence + confidence_boost, 1.0)
            
            signal_type = signal.get("type")
            if signal_type not in ["BUY", "SELL"]:
                return None, 0.0
            
            return signal_type, final_confidence
            
        except Exception as e:
            logger.error(f"Error calculating pattern signal weight: {e}")
            return None, 0.0
    
    def get_pattern_summary(self, result: Dict[str, any]) -> str:
        """Pattern özetini döndür"""
        try:
            if not result or not result.get("patterns"):
                return "No patterns detected"
            
            patterns = result["patterns"]
            summary_parts = []
            
            # Pattern tiplerini grupla
            bullish_patterns = [p for p in patterns if p.get("type") == "BULLISH"]
            bearish_patterns = [p for p in patterns if p.get("type") == "BEARISH"]
            neutral_patterns = [p for p in patterns if p.get("type") == "NEUTRAL"]
            
            if bullish_patterns:
                names = [p.get("name", "Unknown") for p in bullish_patterns]
                summary_parts.append(f"Bullish: {', '.join(names)}")
            
            if bearish_patterns:
                names = [p.get("name", "Unknown") for p in bearish_patterns]
                summary_parts.append(f"Bearish: {', '.join(names)}")
            
            if neutral_patterns:
                names = [p.get("name", "Unknown") for p in neutral_patterns]
                summary_parts.append(f"Neutral: {', '.join(names)}")
            
            return " | ".join(summary_parts) if summary_parts else "No significant patterns"
            
        except Exception as e:
            logger.error(f"Error getting pattern summary: {e}")
            return "Error in pattern summary"
    
    def is_reversal_pattern(self, pattern_name: str) -> bool:
        """Pattern dönüş formasyonu mu?"""
        reversal_patterns = [
            "HAMMER", "INVERTED_HAMMER", "DOJI",
            "BULLISH_ENGULFING", "BEARISH_ENGULFING",
            "MORNING_STAR", "EVENING_STAR",
            "DOUBLE_TOP", "DOUBLE_BOTTOM",
            "BULL_TRAP", "BEAR_TRAP"
        ]
        return pattern_name in reversal_patterns
    
    def is_continuation_pattern(self, pattern_name: str) -> bool:
        """Pattern devam formasyonu mu?"""
        continuation_patterns = [
            "THREE_WHITE_SOLDIERS", "THREE_BLACK_CROWS",
            "BULL_FLAG", "BEAR_FLAG",
            "ASCENDING_TRIANGLE", "DESCENDING_TRIANGLE"
        ]
        return pattern_name in continuation_patterns