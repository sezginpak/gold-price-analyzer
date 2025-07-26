"""
Hibrit Strateji - Gram altın, global trend ve kur riskini birleştiren ana strateji
"""
from typing import Dict, Any, List, Tuple, Optional
from decimal import Decimal
import logging
from collections import defaultdict
from utils import timezone

from models.market_data import MarketData, GramAltinCandle
from analyzers.gram_altin_analyzer import GramAltinAnalyzer
from analyzers.global_trend_analyzer import GlobalTrendAnalyzer
from analyzers.currency_risk_analyzer import CurrencyRiskAnalyzer
from indicators.cci import CCI
from indicators.mfi import MFI
from indicators.advanced_patterns import AdvancedPatternRecognition
from analyzers.multi_day_pattern import MultiDayPatternAnalyzer
from utils.risk_management import KellyRiskManager
from utils.constants import (
    SignalType, RiskLevel, StrengthLevel,
    SIGNAL_STRENGTH_MULTIPLIERS, 
    RISK_POSITION_MULTIPLIERS,
    CONFIDENCE_POSITION_MULTIPLIERS,
    MIN_CONFIDENCE_THRESHOLDS,
    MIN_VOLATILITY_THRESHOLD,
    GLOBAL_TREND_MISMATCH_PENALTY
)

# Modüler bileşenler
from .hybrid.signal_combiner import SignalCombiner
from .hybrid.confluence_manager import ConfluenceManager
from .hybrid.divergence_manager import DivergenceManager
from .hybrid.structure_manager import StructureManager
from .hybrid.momentum_manager import MomentumManager
from .hybrid.smart_money_manager import SmartMoneyManager

logger = logging.getLogger(__name__)


class HybridStrategy:
    """Tüm analizleri birleştiren hibrit strateji - Orchestrator"""
    
    def __init__(self, storage=None):
        # Ana analizörler
        self.gram_analyzer = GramAltinAnalyzer()
        self.global_analyzer = GlobalTrendAnalyzer()
        self.currency_analyzer = CurrencyRiskAnalyzer()
        
        # Yeni göstergeler
        self.cci = CCI(period=20)
        self.mfi = MFI(period=14)
        self.pattern_recognizer = AdvancedPatternRecognition()
        self.risk_manager = KellyRiskManager()
        
        # Modüler bileşenler
        self.signal_combiner = SignalCombiner()
        self.confluence_manager = ConfluenceManager(storage)
        self.divergence_manager = DivergenceManager()
        self.structure_manager = StructureManager()
        self.momentum_manager = MomentumManager()
        self.smart_money_manager = SmartMoneyManager()
        self.multi_day_analyzer = MultiDayPatternAnalyzer(lookback_days=3)
        
        # Storage referansı
        self.storage = storage
    
    def analyze(self, gram_candles: List[GramAltinCandle], 
                market_data: List[MarketData], timeframe: str = "15m") -> Dict[str, Any]:
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
            self._last_gram_analysis = gram_analysis  # RSI için sakla
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
            
            # 6. Divergence analizi
            divergence_analysis = self.divergence_manager.analyze_divergences(
                gram_candles, gram_analysis.get('indicators', {})
            )
            
            # 7. Confluence analizi
            confluence_analysis = self.confluence_manager.analyze_confluence(
                timeframe, 
                gram_analysis.get('signal', 'HOLD'),
                gram_analysis
            )
            
            # 8. Market structure analizi
            structure_analysis = self.structure_manager.analyze_market_structure(
                gram_candles, 
                float(gram_analysis.get('price', 0))
            )
            
            # 9. Momentum exhaustion analizi
            momentum_analysis = self.momentum_manager.analyze_momentum_exhaustion(
                gram_candles,
                gram_analysis.get('indicators', {})
            )
            
            # 10. Smart money analizi
            key_levels = structure_analysis.get('key_levels', {})
            smart_money_analysis = self.smart_money_manager.analyze_smart_money(
                gram_candles,
                key_levels
            )
            
            # 11. Multi-day pattern analizi
            multi_day_pattern = self.multi_day_analyzer.analyze(gram_candles)
            
            # 12. Volatilite kontrolü
            current_price = float(gram_analysis.get('price', 0))
            atr_data = gram_analysis.get('indicators', {}).get('atr', {})
            # ATR bir dict ise value'sunu al, değilse direkt kullan
            if isinstance(atr_data, dict):
                atr_value = atr_data.get('value', 1.0)
            else:
                atr_value = atr_data if atr_data else 1.0
            market_volatility = (atr_value / current_price * 100) if current_price > 0 else 0
            
            # 12. Sinyalleri birleştir
            logger.debug(f"🔄 HYBRID: Calling signal combiner for {timeframe}")
            logger.debug(f"🔄 HYBRID: Gram signal = {gram_analysis.get('signal')}")
            combined_signal = self._combine_signals(
                gram_analysis, global_analysis, currency_analysis,
                advanced_indicators, pattern_analysis, timeframe, market_volatility,
                divergence_analysis, momentum_analysis, smart_money_analysis, multi_day_pattern
            )
            logger.debug(f"🔄 HYBRID: Combined signal = {combined_signal.get('signal')}")
            
            # 7. Kelly Criterion ile pozisyon boyutu hesapla
            position_details = self._calculate_kelly_position(
                combined_signal, gram_analysis, currency_analysis
            )
            
            # 8. Stop-loss ve take-profit ayarla
            risk_levels = self._adjust_risk_levels(
                gram_analysis, currency_analysis
            )
            
            return {
                "timestamp": timezone.utc_now(),
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
                "divergence_analysis": divergence_analysis,
                "confluence_analysis": confluence_analysis,
                "structure_analysis": structure_analysis,
                "momentum_analysis": momentum_analysis,
                "smart_money_analysis": smart_money_analysis,
                
                # Dip Detection bilgileri
                "dip_detection": combined_signal.get("dip_detection", {}),
                
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
                        currency: Dict, advanced: Dict, patterns: Dict, 
                        timeframe: str, market_volatility: float,
                        divergence: Dict = None, momentum: Dict = None,
                        smart_money: Dict = None, multi_day_pattern: Dict = None) -> Dict[str, Any]:
        """Sinyalleri birleştir - Modüler signal combiner kullan"""
        return self.signal_combiner.combine_signals(
            gram_signal=gram,
            global_trend=global_trend,
            currency_risk=currency,
            advanced_indicators=advanced,
            patterns=patterns,
            timeframe=timeframe,
            market_volatility=market_volatility,
            divergence_data=divergence,
            momentum_data=momentum,
            smart_money_data=smart_money,
            multi_day_pattern=multi_day_pattern
        )
    
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
        
        # Dip detection varsa ekle
        dip_detection = signal.get("dip_detection", {})
        if dip_detection.get("is_dip_opportunity"):
            parts.append(f"DIP FIRSAT TESPİTİ (skor: {dip_detection.get('score', 0):.2f})")
            
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
        
        # Dip detection özel durumu
        dip_detection = signal.get("dip_detection", {})
        if dip_detection.get("is_dip_opportunity") and signal["signal"] == "BUY":
            recommendations.append("🎯 DIP YAKALAMA FIRSATI - Güçlü alım sinyali")
            if signal.get("position_size_recommendation"):
                recommendations.append(f"Önerilen pozisyon: %{signal['position_size_recommendation']*100:.0f}")
            if signal.get("stop_loss_recommendation"):
                recommendations.append(signal["stop_loss_recommendation"])
            # Dip sinyallerini ekle
            for dip_signal in dip_detection.get("signals", []):
                recommendations.append(f"• {dip_signal}")
        # Normal sinyal önerisi
        elif signal["signal"] == "BUY":
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
            "timestamp": timezone.utc_now(),
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
                    'volume': float(candle.volume) if hasattr(candle, 'volume') and candle.volume is not None else 0
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
            
            # Gram analizinden RSI değerini al
            rsi_value = None
            if hasattr(self, '_last_gram_analysis') and self._last_gram_analysis:
                rsi_value = self._last_gram_analysis.get('indicators', {}).get('rsi')
            
            return {
                'cci': cci_analysis,
                'mfi': mfi_analysis,
                'combined_signal': combined_signal,
                'combined_confidence': combined_confidence,
                'divergence': cci_analysis.get('divergence') or mfi_analysis.get('divergence'),
                'rsi': rsi_value  # RSI değerini ekle
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
            # Varsayılan sermaye (gram altın ticareti için makul miktar)
            capital = 10000  # 10K TL varsayılan (daha makul)
            
            # Fiyat ve stop loss
            current_price = float(gram.get('price', 0))
            
            # Stop loss kontrolü - HOLD durumunda da geçerli bir değer olmalı
            stop_loss_value = gram.get('stop_loss')
            if stop_loss_value is None or stop_loss_value == 0:
                # HOLD veya None durumunda varsayılan %2 risk kullan
                stop_loss = current_price * 0.98  # BUY için
            else:
                stop_loss = float(stop_loss_value)
            
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
            
            # HOLD sinyali için özel durum
            if signal.get('signal') == 'HOLD':
                # HOLD durumunda minimal pozisyon boyutu dön
                position = {
                    'lots': 0.01,  # Minimal lot
                    'position_size': capital * 0.0001,  # %0.01 pozisyon
                    'risk_percentage': 0.01,
                    'risk_amount': capital * 0.0001,
                    'kelly_percentage': 0.0,
                    'confidence_adjusted': adjusted_confidence * 100,
                    'price_risk': 2.0,  # %2 varsayılan risk
                    'max_loss': capital * 0.0001
                }
            else:
                # Normal BUY/SELL pozisyon hesapla
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