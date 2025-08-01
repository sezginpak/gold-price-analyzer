"""
Yüksek işlem maliyeti (%0.45) için optimize edilmiş simülasyonlar
Spread: 4.5 TL (~%0.11) + Komisyon: %0.10 = Toplam ~%0.21 tek yön, %0.42 gidiş-dönüş
"""
import sqlite3
import json
import logging
from datetime import datetime
import sys
import os

# Proje root'unu path'e ekle
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.simulation import StrategyType, SimulationStatus

logger = logging.getLogger(__name__)


def init_high_cost_simulations(db_path: str = "gold_prices.db"):
    """Yüksek işlem maliyeti için optimize edilmiş simülasyonları oluştur"""
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Yüksek maliyet simülasyonları - SIKI FİLTRELER VE YÜKSEK CONFIDENCE
        simulations = [
            {
                "name": "Yüksek Maliyet - Ultra Konservatif",
                "strategy_type": "HIGH_COST_CONSERVATIVE",
                "config": {
                    "name": "Yüksek Maliyet - Ultra Konservatif",
                    "strategy_type": "HIGH_COST_CONSERVATIVE",
                    "initial_capital": 1000.0,
                    "min_confidence": 0.85,  # %85 minimum güven
                    "max_risk": 0.012,       # %1.2 maksimum risk
                    "max_daily_risk": 0.015, # %1.5 günlük risk
                    "spread": 4.5,           # Gerçek spread değeri
                    "commission_rate": 0.001, # %0.10 komisyon
                    "capital_distribution": {"15m": 200.0, "1h": 300.0, "4h": 300.0, "1d": 200.0},
                    "trading_hours": [9, 17],
                    "atr_multiplier_sl": 0.8,     # Çok sıkı stop loss
                    "risk_reward_ratio": 5.0,     # 5:1 minimum RR
                    "trailing_stop_activation": 0.7, # TP'nin %70'ine gelince aktif
                    "trailing_stop_distance": 0.2,   # Mevcut kârın %20'sini bırak
                    "time_limits": {"15m": 3, "1h": 12, "4h": 48, "1d": 120},
                    "strategy_params": {
                        "high_cost_mode": True,
                        "volatility_threshold": 0.6,
                        "trend_alignment_required": True
                    }
                }
            },
            {
                "name": "Yüksek Maliyet - Trend Takipçisi",
                "strategy_type": "HIGH_COST_TREND",
                "config": {
                    "name": "Yüksek Maliyet - Trend Takipçisi",
                    "strategy_type": "HIGH_COST_TREND",
                    "initial_capital": 1000.0,
                    "min_confidence": 0.80,  # %80 minimum güven
                    "max_risk": 0.015,       # %1.5 maksimum risk
                    "max_daily_risk": 0.02,  # %2 günlük risk
                    "spread": 4.5,
                    "commission_rate": 0.001,
                    "capital_distribution": {"15m": 150.0, "1h": 250.0, "4h": 400.0, "1d": 200.0},
                    "trading_hours": [9, 17],
                    "atr_multiplier_sl": 1.0,     # Sıkı stop loss
                    "risk_reward_ratio": 4.0,     # 4:1 minimum RR
                    "trailing_stop_activation": 0.6,
                    "trailing_stop_distance": 0.25,
                    "time_limits": {"15m": 2, "1h": 8, "4h": 72, "1d": 168},
                    "strategy_params": {
                        "high_cost_mode": True,
                        "trend_following": True,
                        "volatility_threshold": 0.5,
                        "momentum_required": True
                    }
                }
            },
            {
                "name": "Yüksek Maliyet - Dip Yakalayıcı",
                "strategy_type": "HIGH_COST_DIP_BUYER",
                "config": {
                    "name": "Yüksek Maliyet - Dip Yakalayıcı",
                    "strategy_type": "HIGH_COST_DIP_BUYER",
                    "initial_capital": 1000.0,
                    "min_confidence": 0.75,  # %75 minimum güven
                    "max_risk": 0.018,       # %1.8 maksimum risk
                    "max_daily_risk": 0.025, # %2.5 günlük risk
                    "spread": 4.5,
                    "commission_rate": 0.001,
                    "capital_distribution": {"15m": 100.0, "1h": 200.0, "4h": 400.0, "1d": 300.0},
                    "trading_hours": [9, 17],
                    "atr_multiplier_sl": 1.2,     # Biraz gevşek stop loss (dip için)
                    "risk_reward_ratio": 4.5,     # 4.5:1 minimum RR
                    "trailing_stop_activation": 0.5,
                    "trailing_stop_distance": 0.3,
                    "time_limits": {"15m": 6, "1h": 24, "4h": 96, "1d": 240},
                    "strategy_params": {
                        "high_cost_mode": True,
                        "dip_buying_specialist": True,
                        "volatility_threshold": 0.4,
                        "oversold_focus": True
                    }
                }
            }
        ]
        
        # Mevcut simülasyonları güncelle veya yeni ekle
        for sim in simulations:
            # Önce var mı kontrol et
            cursor.execute("SELECT id FROM simulations WHERE name = ?", (sim["name"],))
            existing = cursor.fetchone()
            
            if existing:
                # Güncelle
                cursor.execute("""
                    UPDATE simulations 
                    SET config = ?, strategy_type = ?
                    WHERE name = ?
                """, (json.dumps(sim["config"]), sim["strategy_type"], sim["name"]))
                logger.info(f"Yüksek maliyet simülasyonu güncellendi: {sim['name']}")
            else:
                # Yeni ekle
                cursor.execute("""
                    INSERT INTO simulations (name, strategy_type, config, status, start_date, initial_capital, min_confidence, max_risk, spread, commission_rate, current_capital)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (sim["name"], sim["strategy_type"], json.dumps(sim["config"]), SimulationStatus.ACTIVE.value,
                      datetime.now(), sim["config"]["initial_capital"], sim["config"]["min_confidence"],
                      sim["config"]["max_risk"], sim["config"]["spread"], sim["config"]["commission_rate"],
                      sim["config"]["initial_capital"]))
                
                sim_id = cursor.lastrowid
                
                # Timeframe capitals'i de ekle
                for timeframe, capital in sim["config"]["capital_distribution"].items():
                    cursor.execute("""
                        INSERT OR REPLACE INTO sim_timeframe_capital 
                        (simulation_id, timeframe, allocated_capital, current_capital)
                        VALUES (?, ?, ?, ?)
                    """, (sim_id, timeframe, capital, capital))
                
                logger.info(f"Yeni yüksek maliyet simülasyonu oluşturuldu: {sim['name']}")
        
        conn.commit()
        logger.info("Yüksek maliyet simülasyonları başarıyla oluşturuldu")
        return True
        
    except Exception as e:
        logger.error(f"Yüksek maliyet simülasyonu oluşturma hatası: {str(e)}")
        return False
    finally:
        conn.close()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    if init_high_cost_simulations():
        print("=== YÜKSEK MALİYET SİMÜLASYONLARI OLUŞTURULDU ===")
        print("Toplam işlem maliyeti: ~%0.45 (spread + komisyon)")
        print()
        print("1. Ultra Konservatif:")
        print("   - Min confidence: %85")
        print("   - Risk/Reward: 5:1")
        print("   - Max risk: %1.2")
        print()
        print("2. Trend Takipçisi:")
        print("   - Min confidence: %80") 
        print("   - Risk/Reward: 4:1")
        print("   - Max risk: %1.5")
        print()
        print("3. Dip Yakalayıcı:")
        print("   - Min confidence: %75")
        print("   - Risk/Reward: 4.5:1")
        print("   - Max risk: %1.8")
        print()
        print("Bu stratejiler %0.45 işlem maliyeti ile kar etmek için optimize edildi.")
    else:
        print("HATA: Yüksek maliyet simülasyonları oluşturulamadı")