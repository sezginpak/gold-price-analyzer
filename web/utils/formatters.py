"""
Veri formatlama fonksiyonları
"""
from typing import Dict, Any
import logging
from datetime import datetime
import pytz
from utils.timezone import to_turkey_time

logger = logging.getLogger(__name__)

def format_analysis_summary(analysis: Dict) -> str:
    """Analiz özetini daha okunabilir hale getir"""
    try:
        # Eğer zaten formatlanmış bir summary varsa ve teknik terimler içermiyorsa, olduğu gibi dön
        existing_summary = analysis.get("summary", "")
        if existing_summary and "TrendType" not in existing_summary and "🟢" in existing_summary:
            return existing_summary
        
        signal = analysis.get("signal", "HOLD")
        signal_strength = analysis.get("signal_strength", "WEAK")
        confidence = analysis.get("confidence", 0.5)
        gram_price = analysis.get("gram_price", 0)
        
        # Global trend ve currency risk bilgileri - flexible parsing
        global_trend = analysis.get("global_trend", "NEUTRAL")
        if isinstance(global_trend, dict):
            global_direction = global_trend.get("direction", "NEUTRAL")
            global_strength = global_trend.get("strength", "WEAK")
        else:
            global_direction = str(global_trend)
            global_strength = "MODERATE"
            
        currency_risk = analysis.get("currency_risk", "MEDIUM")
        if isinstance(currency_risk, dict):
            risk_level = currency_risk.get("level", "MEDIUM")
        else:
            risk_level = str(currency_risk)
        
        # Temel mesaj
        if signal == "BUY":
            base_msg = f"🟢 **ALIŞ SİNYALİ** ({signal_strength.lower()} güçte)"
        elif signal == "SELL":
            base_msg = f"🔴 **SATIŞ SİNYALİ** ({signal_strength.lower()} güçte)"
        else:
            base_msg = f"🟡 **BEKLE** - Henüz uygun giriş noktası yok"
        
        # Global durum açıklaması
        if global_direction == "BULLISH":
            global_msg = "Global altın piyasası yükseliş trendinde."
        elif global_direction == "BEARISH":
            global_msg = "Global altın piyasası düşüş trendinde."
        else:
            global_msg = "Global altın piyasası yatay seyrediyor."
        
        # Risk değerlendirmesi
        if risk_level == "LOW":
            risk_msg = "USD/TRY volatilitesi düşük, işlem riski minimal."
        elif risk_level == "HIGH":
            risk_msg = "USD/TRY volatilitesi yüksek, dikkatli olun."
        else:
            risk_msg = "USD/TRY volatilitesi orta seviyede."
        
        # Güven oranı açıklaması
        confidence_pct = int(confidence * 100)
        if confidence_pct >= 75:
            confidence_msg = f"Analiz güven oranı çok yüksek (%{confidence_pct})."
        elif confidence_pct >= 60:
            confidence_msg = f"Analiz güven oranı yüksek (%{confidence_pct})."
        elif confidence_pct >= 40:
            confidence_msg = f"Analiz güven oranı orta (%{confidence_pct})."
        else:
            confidence_msg = f"Analiz güven oranı düşük (%{confidence_pct}), dikkatli olun."
        
        # Öneriler
        recommendations = []
        if signal in ["BUY", "SELL"]:
            if analysis.get("stop_loss"):
                recommendations.append(f"Stop Loss: ₺{analysis['stop_loss']:.2f}")
            if analysis.get("take_profit"):
                recommendations.append(f"Hedef: ₺{analysis['take_profit']:.2f}")
            
            # Risk/Ödül oranı
            risk_reward = analysis.get("risk_reward_ratio", 0)
            if risk_reward > 0:
                recommendations.append(f"Risk/Ödül oranı: 1:{risk_reward:.1f}")
        
        # Pozisyon boyutu önerisi
        position_size = analysis.get("position_size", 0)
        if isinstance(position_size, dict):
            position_value = position_size.get('lots', 0)
        else:
            position_value = position_size
        
        if position_value > 0:
            recommendations.append(f"Önerilen pozisyon: %{position_value*100:.0f}")
        
        # Final mesajı birleştir
        summary_parts = [base_msg, global_msg, risk_msg, confidence_msg]
        
        if recommendations:
            summary_parts.append("💡 **Öneriler:** " + " • ".join(recommendations))
        
        return " ".join(summary_parts)
        
    except Exception as e:
        logger.error(f"Summary formatting error: {e}")
        return analysis.get("summary", "Analiz özeti mevcut değil.")


def parse_log_line(line: str) -> Dict[str, str]:
    """Log satırını parse et ve Türkiye saatine çevir"""
    # Format: 2024-01-17 15:30:45 - module - LEVEL - message
    parts = line.split(' - ', 3)
    
    if len(parts) >= 4:
        timestamp_str = parts[0]
        
        # Timestamp'i parse et ve Türkiye saatine çevir
        try:
            # Log timestamp'ini datetime objesine çevir
            log_dt = datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S")
            # UTC olarak varsay ve Türkiye saatine çevir
            utc_dt = pytz.UTC.localize(log_dt)
            turkey_dt = to_turkey_time(utc_dt)
            # Türkiye saatinde formatla
            turkey_timestamp = turkey_dt.strftime("%Y-%m-%d %H:%M:%S")
        except Exception:
            # Parse edilemezse orijinalini kullan
            turkey_timestamp = timestamp_str
        
        return {
            "timestamp": turkey_timestamp,
            "module": parts[1],
            "level": parts[2],
            "message": parts[3],
            "raw": line
        }
    else:
        return {
            "timestamp": "",
            "module": "",
            "level": "INFO",
            "message": line,
            "raw": line
        }