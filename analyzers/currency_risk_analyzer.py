"""
USD/TRY Risk Değerlendirme Motoru
"""
from typing import List, Dict, Any
from decimal import Decimal
from datetime import datetime, timedelta
import logging
import numpy as np

from models.market_data import MarketData

logger = logging.getLogger(__name__)


class CurrencyRiskAnalyzer:
    """USD/TRY kuru üzerinden risk değerlendirmesi"""
    
    def __init__(self):
        # Risk seviyeleri için eşikler
        self.volatility_thresholds = {
            "LOW": 0.5,      # %0.5'ten az günlük volatilite
            "MEDIUM": 1.0,   # %0.5-1.0 arası
            "HIGH": 2.0,     # %1.0-2.0 arası
            "EXTREME": 100   # %2.0'den fazla
        }
        
        # Müdahale risk göstergeleri
        self.intervention_indicators = {
            "rapid_rise_threshold": 1.5,  # Günlük %1.5'ten fazla artış
            "psychological_levels": [35.0, 36.0, 37.0, 38.0, 39.0, 40.0],  # Psikolojik seviyeler
            "historical_high_buffer": 0.98  # Tarihi zirveye yakınlık
        }
    
    def analyze(self, market_data: List[MarketData]) -> Dict[str, Any]:
        """
        USD/TRY verilerini analiz ederek risk seviyesini belirle
        
        Args:
            market_data: Son piyasa verileri
            
        Returns:
            Risk analiz sonuçları
        """
        try:
            if len(market_data) < 20:
                logger.warning(f"Yetersiz veri: {len(market_data)}")
                return self._empty_analysis()
            
            # USD/TRY değerlerini çıkar
            usd_try_values = [float(d.usd_try) for d in market_data]
            current_rate = usd_try_values[-1]
            
            # Volatilite hesapla
            volatility = self._calculate_volatility(usd_try_values)
            
            # Risk seviyesi
            risk_level = self._determine_risk_level(volatility["daily"])
            
            # Müdahale riski
            intervention_risk = self._check_intervention_risk(
                current_rate, usd_try_values
            )
            
            # Trend analizi
            trend_analysis = self._analyze_currency_trend(usd_try_values)
            
            # Pozisyon önerisi
            position_recommendation = self._get_position_recommendation(
                risk_level, intervention_risk, trend_analysis
            )
            
            return {
                "timestamp": datetime.utcnow(),
                "usd_try": Decimal(str(current_rate)),
                "volatility": volatility,
                "risk_level": risk_level,
                "intervention_risk": intervention_risk,
                "trend": trend_analysis,
                "position_size_multiplier": position_recommendation["multiplier"],
                "analysis": self._create_risk_analysis(
                    risk_level, intervention_risk, volatility, trend_analysis
                ),
                "recommendations": position_recommendation["recommendations"]
            }
            
        except Exception as e:
            logger.error(f"Kur riski analiz hatası: {e}", exc_info=True)
            return self._empty_analysis()
    
    def _calculate_volatility(self, values: List[float]) -> Dict[str, float]:
        """Volatilite hesapla"""
        if len(values) < 2:
            return {"daily": 0, "weekly": 0, "monthly": 0}
        
        # Günlük değişimler
        daily_returns = np.diff(values) / values[:-1] * 100
        
        # Farklı periyotlar için volatilite
        volatility = {
            "daily": np.std(daily_returns[-20:]) if len(daily_returns) >= 20 else np.std(daily_returns),
            "weekly": np.std(daily_returns[-5:]) if len(daily_returns) >= 5 else 0,
            "monthly": np.std(daily_returns[-30:]) if len(daily_returns) >= 30 else 0
        }
        
        # Son günün değişimi
        if len(values) >= 2:
            volatility["last_change"] = (values[-1] - values[-2]) / values[-2] * 100
        else:
            volatility["last_change"] = 0
            
        return volatility
    
    def _determine_risk_level(self, daily_volatility: float) -> str:
        """Risk seviyesini belirle"""
        for level, threshold in self.volatility_thresholds.items():
            if daily_volatility < threshold:
                return level
        return "EXTREME"
    
    def _check_intervention_risk(self, current_rate: float, values: List[float]) -> Dict[str, Any]:
        """Merkez bankası müdahale riskini kontrol et"""
        risk_factors = []
        
        # Hızlı yükseliş kontrolü
        if len(values) >= 2:
            daily_change = (values[-1] - values[-2]) / values[-2] * 100
            if daily_change > self.intervention_indicators["rapid_rise_threshold"]:
                risk_factors.append("rapid_rise")
        
        # Psikolojik seviye kontrolü
        for level in self.intervention_indicators["psychological_levels"]:
            if abs(current_rate - level) < 0.1:  # Psikolojik seviyeye yakın
                risk_factors.append(f"near_psychological_{level}")
                break
        
        # Tarihi zirve kontrolü
        historical_high = max(values) if values else current_rate
        if current_rate >= historical_high * self.intervention_indicators["historical_high_buffer"]:
            risk_factors.append("near_historical_high")
        
        # 5 günlük ortalama değişim
        if len(values) >= 5:
            five_day_change = (values[-1] - values[-5]) / values[-5] * 100
            if five_day_change > 3:  # 5 günde %3'ten fazla artış
                risk_factors.append("sustained_rise")
        
        return {
            "has_risk": len(risk_factors) > 0,
            "risk_factors": risk_factors,
            "risk_score": len(risk_factors) / 4  # Maksimum 4 risk faktörü
        }
    
    def _analyze_currency_trend(self, values: List[float]) -> Dict[str, Any]:
        """Kur trendini analiz et"""
        if len(values) < 10:
            return {"direction": "UNKNOWN", "strength": "WEAK"}
        
        # Basit trend hesaplama
        ma10 = np.mean(values[-10:])
        ma20 = np.mean(values[-20:]) if len(values) >= 20 else ma10
        current = values[-1]
        
        # Trend yönü
        if current > ma10 > ma20:
            direction = "UPTREND"
        elif current < ma10 < ma20:
            direction = "DOWNTREND"
        else:
            direction = "SIDEWAYS"
        
        # Trend gücü
        if len(values) >= 20:
            change_20d = (values[-1] - values[-20]) / values[-20] * 100
            if abs(change_20d) > 5:
                strength = "STRONG"
            elif abs(change_20d) > 2:
                strength = "MODERATE"
            else:
                strength = "WEAK"
        else:
            strength = "UNKNOWN"
        
        return {
            "direction": direction,
            "strength": strength,
            "ma10": ma10,
            "ma20": ma20
        }
    
    def _get_position_recommendation(self, risk_level: str, intervention_risk: Dict, 
                                   trend: Dict) -> Dict[str, Any]:
        """Pozisyon büyüklüğü önerisi"""
        # Temel çarpan
        base_multipliers = {
            "LOW": 1.0,
            "MEDIUM": 0.8,
            "HIGH": 0.5,
            "EXTREME": 0.3
        }
        
        multiplier = base_multipliers.get(risk_level, 0.5)
        recommendations = []
        
        # Müdahale riski varsa azalt
        if intervention_risk["has_risk"]:
            multiplier *= (1 - intervention_risk["risk_score"] * 0.3)
            recommendations.append("Müdahale riski nedeniyle pozisyon azaltıldı")
        
        # Güçlü yükseliş trendinde ekstra azaltma
        if trend["direction"] == "UPTREND" and trend["strength"] == "STRONG":
            multiplier *= 0.8
            recommendations.append("Güçlü TRY değer kaybı, dikkatli olun")
        
        # Öneriler
        if risk_level == "EXTREME":
            recommendations.append("Yeni pozisyon açmayın, mevcut pozisyonları azaltın")
        elif risk_level == "HIGH":
            recommendations.append("Minimum pozisyon büyüklüğü kullanın")
        elif risk_level == "LOW":
            recommendations.append("Normal pozisyon büyüklüğü uygun")
        
        return {
            "multiplier": round(multiplier, 2),
            "recommendations": recommendations
        }
    
    def _create_risk_analysis(self, risk_level: str, intervention_risk: Dict,
                            volatility: Dict, trend: Dict) -> Dict[str, str]:
        """Risk analizi özeti"""
        analysis = {
            "summary": f"USD/TRY risk seviyesi: {risk_level}",
            "volatility": f"Günlük volatilite %{volatility['daily']:.2f}",
            "intervention": "Müdahale riski yüksek" if intervention_risk["has_risk"] else "Müdahale riski düşük",
            "trend": f"Kur {trend['direction']} trendinde",
            "impact": self._get_impact_analysis(risk_level, trend)
        }
        
        if intervention_risk["has_risk"]:
            analysis["risk_factors"] = ", ".join(intervention_risk["risk_factors"])
        
        return analysis
    
    def _get_impact_analysis(self, risk_level: str, trend: Dict) -> str:
        """Gram altın üzerindeki etkiyi analiz et"""
        if risk_level in ["HIGH", "EXTREME"]:
            return "Yüksek kur volatilitesi gram altın fiyatlarını etkileyebilir"
        elif trend["direction"] == "UPTREND":
            return "TRY değer kaybı gram altın fiyatlarını yukarı itebilir"
        elif trend["direction"] == "DOWNTREND":
            return "TRY değer kazancı gram altın üzerinde baskı oluşturabilir"
        else:
            return "Kur hareketi normal seviyelerde"
    
    def _empty_analysis(self) -> Dict[str, Any]:
        """Boş analiz sonucu"""
        return {
            "timestamp": datetime.utcnow(),
            "usd_try": None,
            "volatility": {"daily": 0, "weekly": 0, "monthly": 0},
            "risk_level": "UNKNOWN",
            "intervention_risk": {"has_risk": False, "risk_factors": []},
            "trend": {"direction": "UNKNOWN", "strength": "WEAK"},
            "position_size_multiplier": 0.5,
            "analysis": {"summary": "Yetersiz veri"},
            "recommendations": ["Veri bekleniyor"]
        }