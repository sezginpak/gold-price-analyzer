"""
Hibrit Strateji - Gram altın, global trend ve kur riskini birleştiren ana strateji
"""
from typing import Dict, Any, List, Tuple, Optional
from decimal import Decimal
from datetime import datetime
import logging
from collections import defaultdict

from models.market_data import MarketData, GramAltinCandle
from analyzers.gram_altin_analyzer import GramAltinAnalyzer
from analyzers.global_trend_analyzer import GlobalTrendAnalyzer
from analyzers.currency_risk_analyzer import CurrencyRiskAnalyzer
from indicators.cci import CCI
from indicators.mfi import MFI
from indicators.advanced_patterns import AdvancedPatternRecognition
from utils.risk_management import KellyRiskManager
from utils.constants import (
    SignalType, RiskLevel, StrengthLevel,
    SIGNAL_STRENGTH_MULTIPLIERS, 
    RISK_POSITION_MULTIPLIERS,
    CONFIDENCE_POSITION_MULTIPLIERS
)

logger = logging.getLogger(__name__)


class HybridStrategy:
    """Tüm analizleri birleştiren hibrit strateji"""
    
    def __init__(self):
        self.gram_analyzer = GramAltinAnalyzer()
        self.global_analyzer = GlobalTrendAnalyzer()
        self.currency_analyzer = CurrencyRiskAnalyzer()
        
        # Yeni göstergeler
        self.cci = CCI(period=20)
        self.mfi = MFI(period=14)
        self.pattern_recognizer = AdvancedPatternRecognition()
        self.risk_manager = KellyRiskManager()
        
        # Güncellenmiş ağırlıklar
        self.weights = {
            "gram_analysis": 0.35,      # %35 - Ana sinyal
            "global_trend": 0.20,       # %20 - Trend doğrulama
            "currency_risk": 0.15,      # %15 - Risk ayarlama
            "advanced_indicators": 0.20, # %20 - CCI + MFI
            "pattern_recognition": 0.10  # %10 - Pattern bonus
        }
    
    def analyze(self, gram_candles: List[GramAltinCandle], 
                market_data: List[MarketData]) -> Dict[str, Any]:
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
            
            # 6. Sinyalleri birleştir
            combined_signal = self._combine_signals(
                gram_analysis, global_analysis, currency_analysis,
                advanced_indicators, pattern_analysis
            )
            
            # 7. Kelly Criterion ile pozisyon boyutu hesapla
            position_details = self._calculate_kelly_position(
                combined_signal, gram_analysis, currency_analysis
            )
            
            # 8. Stop-loss ve take-profit ayarla
            risk_levels = self._adjust_risk_levels(
                gram_analysis, currency_analysis
            )
            
            return {
                "timestamp": datetime.utcnow(),
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
    
    def _combine_signals(self, gram: Dict, global_trend: Dict, 
                        currency: Dict, advanced: Dict, patterns: Dict) -> Dict[str, Any]:
        """Sinyalleri birleştir - Gelişmiş göstergeler ve pattern'ler dahil"""
        # Temel sinyaller
        gram_signal = gram.get("signal", "HOLD")
        gram_confidence = gram.get("confidence", 0)
        global_direction = global_trend.get("trend_direction", "NEUTRAL")
        risk_level = currency.get("risk_level", "MEDIUM")
        
        # Sinyal puanları - defaultdict kullanarak optimize et
        signal_scores = defaultdict(float)
        
        # 1. Gram altın sinyali (ana ağırlık)
        signal_scores[gram_signal] += self.weights["gram_analysis"] * (gram_confidence if gram_signal != "HOLD" else 1.0)
        
        # 2. Global trend uyumu - lookup table ile optimize et
        trend_weight = self.weights["global_trend"]
        trend_signal_map = {
            ("BULLISH", "BUY"): ("BUY", 1.0),
            ("BEARISH", "SELL"): ("SELL", 1.0),
            ("BULLISH", "SELL"): ("HOLD", 0.5),
            ("BEARISH", "BUY"): ("HOLD", 0.5),
        }
        
        signal_to_add, multiplier = trend_signal_map.get(
            (global_direction, gram_signal), 
            ("HOLD", 0.3)
        )
        signal_scores[signal_to_add] += trend_weight * multiplier
        
        # 3. Kur riski etkisi
        risk_weight = self.weights["currency_risk"]
        is_high_risk = risk_level in ["HIGH", "EXTREME"]
        
        if is_high_risk:
            signal_scores["HOLD"] += risk_weight * 0.7
            # Mevcut sinyalleri zayıflat
            for sig in ["BUY", "SELL"]:
                signal_scores[sig] *= 0.7
        elif gram_signal in ["BUY", "SELL"]:
            signal_scores[gram_signal] += risk_weight * 0.5
        
        # 4. Gelişmiş göstergeler (CCI + MFI)
        advanced_weight = self.weights["advanced_indicators"]
        advanced_signal = advanced.get("combined_signal", "NEUTRAL")
        advanced_confidence = advanced.get("combined_confidence", 0)
        
        if advanced_signal != "NEUTRAL":
            signal_scores[advanced_signal] += advanced_weight * advanced_confidence
            
            # Divergence varsa ekstra güç
            if advanced.get("divergence"):
                signal_scores[advanced_signal] += advanced_weight * 0.3
        
        # 5. Pattern tanıma bonusu
        pattern_weight = self.weights["pattern_recognition"]
        if patterns.get("pattern_found"):
            pattern_signal = patterns.get("signal", "NEUTRAL")
            pattern_confidence = patterns.get("confidence", 0)
            
            if pattern_signal != "NEUTRAL":
                signal_scores[pattern_signal] += pattern_weight * pattern_confidence
                
                # Head & Shoulders gibi güçlü pattern'ler için ekstra bonus
                best_pattern = patterns.get("best_pattern", {})
                if best_pattern.get("pattern") in ["HEAD_AND_SHOULDERS", "INVERSE_HEAD_AND_SHOULDERS"]:
                    signal_scores[pattern_signal] += pattern_weight * 0.5
        
        # Nihai sinyal - daha optimize
        max_score = max(signal_scores.values())
        final_signal = max(signal_scores.items(), key=lambda x: x[1])[0]
        
        # Debug log ekle
        logger.info(f"Signal scores: {signal_scores}")
        logger.info(f"Final signal: {final_signal}, max_score: {max_score}")
        
        # Güven skorunu hesapla - gram analizörünün güven değerini de kullan
        gram_confidence = gram.get("confidence", 0.5)
        
        # Hibrit güven hesaplaması:
        # 1. Sinyal skoru bazlı güven - sadece o sinyali destekleyen analizörlerin ağırlıklarını kullan
        supporting_analyzers_weight = 0
        if gram.get("signal") == final_signal:
            supporting_analyzers_weight += self.weights["gram_analysis"]
        # Global trend'in doğrudan sinyali yok, yön kontrolü yap
        if (final_signal == "BUY" and global_trend.get("trend_direction") == "BULLISH") or \
           (final_signal == "SELL" and global_trend.get("trend_direction") == "BEARISH"):
            supporting_analyzers_weight += self.weights["global_trend"]
        # Currency risk'in de doğrudan sinyali yok, risk seviyesi kontrolü yap
        if final_signal == "HOLD" and currency.get("risk_level") in ["HIGH", "EXTREME"]:
            supporting_analyzers_weight += self.weights["currency_risk"]
        
        # En az bir analizör destekliyorsa, destekleyen analizörlerin toplam ağırlığına göre hesapla
        if supporting_analyzers_weight > 0:
            score_confidence = min(signal_scores[final_signal] / supporting_analyzers_weight, 1.0)
        else:
            score_confidence = 0.3  # Hiçbir analizör desteklemiyorsa düşük güven
        
        # 2. Final güven: Gram güveni ve skor güveninin ağırlıklı ortalaması
        if final_signal == "HOLD":
            # HOLD için gram analizörünün güveni daha önemli
            normalized_confidence = (gram_confidence * 0.7) + (score_confidence * 0.3)
        else:
            # BUY/SELL için gram güveni ve skor güveni daha dengeli
            # Ayrıca minimum güven seviyesi belirle
            normalized_confidence = (gram_confidence * 0.6) + (score_confidence * 0.4)
            # BUY/SELL sinyalleri için minimum %40 güven
            normalized_confidence = max(normalized_confidence, 0.4)
        
        logger.info(f"Confidence calculation: gram={gram_confidence:.3f}, score={score_confidence:.3f}, final={normalized_confidence:.3f}")
        
        # Sinyal gücü
        if final_signal != "HOLD":
            strength = self._calculate_signal_strength(
                normalized_confidence, global_direction, risk_level
            )
        else:
            strength = "WEAK"
        
        return {
            "signal": final_signal,
            "confidence": normalized_confidence,
            "strength": strength,
            "scores": signal_scores,
            "raw_confidence": signal_scores[final_signal]
        }
    
    def _calculate_signal_strength(self, score: float, trend: str, risk: str) -> str:
        """Sinyal gücünü hesapla - güven skoruna dayalı"""
        # Güven skoruna göre temel güç
        if score >= 0.75:
            base_strength = "STRONG"
        elif score >= 0.55:
            base_strength = "MODERATE"
        else:
            base_strength = "WEAK"
        
        # Risk seviyesine göre ayarlama (trend uyumu bonusu kaldırıldı)
        if risk in ["HIGH", "EXTREME"]:
            # Yüksek risk durumunda güç seviyesini düşür
            if base_strength == "STRONG":
                return "MODERATE"
            elif base_strength == "MODERATE":
                return "WEAK"
        
        return base_strength
    
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
        """Stop-loss ve take-profit seviyelerini ayarla"""
        stop_loss = gram.get("stop_loss")
        take_profit = gram.get("take_profit")
        
        if not stop_loss or not take_profit:
            return {
                "stop_loss": None,
                "take_profit": None,
                "risk_reward_ratio": None
            }
        
        # Yüksek kur riski varsa stop-loss'u sıkılaştır
        risk_level = currency.get("risk_level", "MEDIUM")
        if risk_level in ["HIGH", "EXTREME"]:
            # Stop-loss'u %20 daha yakına al
            current_price = gram.get("price", stop_loss)
            if gram.get("signal") == "BUY":
                # BUY için stop_loss fiyatın altında olmalı
                distance = abs(current_price - stop_loss)
                stop_loss = current_price - (distance * Decimal("0.8"))
            else:  # SELL
                # SELL için stop_loss fiyatın üstünde olmalı
                distance = abs(stop_loss - current_price)
                stop_loss = current_price + (distance * Decimal("0.8"))
        
        # Risk/Ödül oranı
        if gram.get("signal") == "BUY":
            risk = abs(float(gram["price"] - stop_loss))
            reward = abs(float(take_profit - gram["price"]))
        else:  # SELL
            risk = abs(float(stop_loss - gram["price"]))
            reward = abs(float(gram["price"] - take_profit))
        
        risk_reward_ratio = reward / risk if risk > 0 else 0
        
        return {
            "stop_loss": stop_loss,
            "take_profit": take_profit,
            "risk_reward_ratio": round(risk_reward_ratio, 2)
        }
    
    def _create_summary(self, signal: Dict, gram: Dict, 
                       global_trend: Dict, currency: Dict) -> str:
        """Analiz özeti oluştur"""
        parts = []
        
        # Sinyal özeti
        if signal["signal"] != "HOLD":
            parts.append(f"{signal['signal']} sinyali ({signal['strength']} güçte)")
        else:
            parts.append("Bekleme pozisyonunda kalın")
        
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
        
        # Sinyal önerisi
        if signal["signal"] == "BUY":
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
            "timestamp": datetime.utcnow(),
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
                    'volume': float(candle.volume) if hasattr(candle, 'volume') else 0
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
            
            return {
                'cci': cci_analysis,
                'mfi': mfi_analysis,
                'combined_signal': combined_signal,
                'combined_confidence': combined_confidence,
                'divergence': cci_analysis.get('divergence') or mfi_analysis.get('divergence')
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
            # Varsayılan sermaye (kullanıcı tarafından ayarlanabilir)
            capital = 100000  # 100K TL varsayılan
            
            # Fiyat ve stop loss
            current_price = float(gram.get('price', 0))
            stop_loss = float(gram.get('stop_loss', current_price * 0.98))
            
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
            
            # Pozisyon hesapla
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