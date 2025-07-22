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
        
        # Ağırlıklar
        self.weights = {
            "gram_analysis": 0.5,    # %50 - Ana sinyal
            "global_trend": 0.3,     # %30 - Trend doğrulama
            "currency_risk": 0.2     # %20 - Risk ayarlama
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
            
            # 4. Sinyalleri birleştir
            combined_signal = self._combine_signals(
                gram_analysis, global_analysis, currency_analysis
            )
            
            # 5. Risk ayarlı pozisyon hesapla
            position_size = self._calculate_position_size(
                combined_signal, currency_analysis
            )
            
            # 6. Stop-loss ve take-profit ayarla
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
                "position_size": position_size,
                "stop_loss": risk_levels["stop_loss"],
                "take_profit": risk_levels["take_profit"],
                "risk_reward_ratio": risk_levels["risk_reward_ratio"],
                
                # Detaylı analizler
                "gram_analysis": gram_analysis,
                "global_trend": global_analysis,
                "currency_risk": currency_analysis,
                
                # Özet ve öneriler
                "summary": self._create_summary(
                    combined_signal, gram_analysis, global_analysis, currency_analysis
                ),
                "recommendations": self._get_recommendations(
                    combined_signal, position_size, currency_analysis
                )
            }
            
        except Exception as e:
            logger.error(f"Hibrit strateji hatası: {e}", exc_info=True)
            return self._empty_result()
    
    def _combine_signals(self, gram: Dict, global_trend: Dict, 
                        currency: Dict) -> Dict[str, Any]:
        """Sinyalleri birleştir"""
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
        """Sinyal gücünü hesapla"""
        # Temel güç
        if score >= 0.7:
            base_strength = "STRONG"
        elif score >= 0.5:
            base_strength = "MODERATE"
        else:
            base_strength = "WEAK"
        
        # Trend ve risk ayarlaması
        if trend in ["BULLISH", "BEARISH"] and risk in ["LOW", "MEDIUM"]:
            # İdeal koşullar
            if base_strength == "MODERATE":
                return "STRONG"
        elif risk in ["HIGH", "EXTREME"]:
            # Riskli koşullar
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
        
        logger.info(f"Position calculation: base={base_position}, strength_mult={strength_multipliers.get(signal['strength'], 0.5)}, currency_mult={currency_multiplier}, confidence_mult={confidence_multiplier:.2f}, final={result['recommended_size']}")
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
            distance = abs(current_price - stop_loss)
            stop_loss = current_price - (distance * Decimal("0.8"))
        
        # Risk/Ödül oranı
        if gram.get("signal") == "BUY":
            risk = float(gram["price"] - stop_loss)
            reward = float(take_profit - gram["price"])
        else:
            risk = float(stop_loss - gram["price"])
            reward = float(gram["price"] - take_profit)
        
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
        size = position["recommended_size"]
        if size < 0.5:
            recommendations.append(f"Düşük pozisyon büyüklüğü önerilir (%{int(size*100)})")
        elif size < 0.8:
            recommendations.append(f"Orta pozisyon büyüklüğü önerilir (%{int(size*100)})")
        else:
            recommendations.append(f"Normal pozisyon büyüklüğü uygun (%{int(size*100)})")
        
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
            "position_size": {"recommended_size": 0},
            "stop_loss": None,
            "take_profit": None,
            "risk_reward_ratio": None,
            "gram_analysis": {},
            "global_trend": {"trend_direction": "NEUTRAL"},
            "currency_risk": {"risk_level": "UNKNOWN"},
            "summary": "Analiz yapılamadı",
            "recommendations": ["Veri bekleniyor"]
        }