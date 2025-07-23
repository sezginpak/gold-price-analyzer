"""
Varsayılan simülasyonları oluştur ve düşük confidence değerleri ile başlat
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


def init_simulations(db_path: str = "gold_prices.db"):
    """Varsayılan simülasyonları oluştur"""
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Varsayılan simülasyonlar - DÜŞÜK CONFIDENCE DEĞERLERİ İLE
        simulations = [
            {
                "name": "Ana Strateji - Genel",
                "strategy_type": StrategyType.MAIN.value,
                "config": {
                    "name": "Ana Strateji - Genel",
                    "strategy_type": StrategyType.MAIN.value,
                    "initial_capital": 1000.0,
                    "min_confidence": 0.35,  # DÜŞÜRÜLDÜ
                    "max_risk": 0.02,
                    "max_daily_risk": 0.02,
                    "spread": 15.0,
                    "commission_rate": 0.001,
                    "capital_distribution": {"15m": 250.0, "1h": 250.0, "4h": 250.0, "1d": 250.0},
                    "trading_hours": [9, 17],
                    "atr_multiplier_sl": 1.5,
                    "risk_reward_ratio": 2.0,
                    "trailing_stop_activation": 0.5,
                    "trailing_stop_distance": 0.3,
                    "time_limits": {"15m": 4, "1h": 24, "4h": 72, "1d": 168},
                    "strategy_params": {}
                }
            },
            {
                "name": "Konservatif - Güvenli",
                "strategy_type": StrategyType.CONSERVATIVE.value,
                "config": {
                    "name": "Konservatif - Güvenli",
                    "strategy_type": StrategyType.CONSERVATIVE.value,
                    "initial_capital": 1000.0,
                    "min_confidence": 0.45,  # DÜŞÜRÜLDÜ
                    "max_risk": 0.01,
                    "max_daily_risk": 0.02,
                    "spread": 15.0,
                    "commission_rate": 0.001,
                    "capital_distribution": {"15m": 250.0, "1h": 250.0, "4h": 250.0, "1d": 250.0},
                    "trading_hours": [9, 17],
                    "atr_multiplier_sl": 1.5,
                    "risk_reward_ratio": 2.0,
                    "trailing_stop_activation": 0.5,
                    "trailing_stop_distance": 0.3,
                    "time_limits": {"15m": 4, "1h": 24, "4h": 72, "1d": 168},
                    "strategy_params": {}
                }
            },
            {
                "name": "Momentum Takibi",
                "strategy_type": StrategyType.MOMENTUM.value,
                "config": {
                    "name": "Momentum Takibi",
                    "strategy_type": StrategyType.MOMENTUM.value,
                    "initial_capital": 1000.0,
                    "min_confidence": 0.40,  # DÜŞÜRÜLDÜ
                    "max_risk": 0.02,
                    "max_daily_risk": 0.02,
                    "spread": 15.0,
                    "commission_rate": 0.001,
                    "capital_distribution": {"15m": 250.0, "1h": 250.0, "4h": 250.0, "1d": 250.0},
                    "trading_hours": [9, 17],
                    "atr_multiplier_sl": 1.5,
                    "risk_reward_ratio": 2.0,
                    "trailing_stop_activation": 0.5,
                    "trailing_stop_distance": 0.3,
                    "time_limits": {"15m": 4, "1h": 24, "4h": 72, "1d": 168},
                    "strategy_params": {}
                }
            },
            {
                "name": "Ortalamaya Dönüş",
                "strategy_type": StrategyType.MEAN_REVERSION.value,
                "config": {
                    "name": "Ortalamaya Dönüş",
                    "strategy_type": StrategyType.MEAN_REVERSION.value,
                    "initial_capital": 1000.0,
                    "min_confidence": 0.38,  # DÜŞÜRÜLDÜ
                    "max_risk": 0.02,
                    "max_daily_risk": 0.02,
                    "spread": 15.0,
                    "commission_rate": 0.001,
                    "capital_distribution": {"15m": 250.0, "1h": 250.0, "4h": 250.0, "1d": 250.0},
                    "trading_hours": [9, 17],
                    "atr_multiplier_sl": 1.5,
                    "risk_reward_ratio": 2.0,
                    "trailing_stop_activation": 0.5,
                    "trailing_stop_distance": 0.3,
                    "time_limits": {"15m": 4, "1h": 24, "4h": 72, "1d": 168},
                    "strategy_params": {}
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
                    SET config = ?
                    WHERE name = ?
                """, (json.dumps(sim["config"]), sim["name"]))
                logger.info(f"Simülasyon güncellendi: {sim['name']}")
            else:
                # Yeni ekle
                cursor.execute("""
                    INSERT INTO simulations (name, strategy_type, config, status)
                    VALUES (?, ?, ?, ?)
                """, (sim["name"], sim["strategy_type"], json.dumps(sim["config"]), SimulationStatus.ACTIVE.value))
                
                sim_id = cursor.lastrowid
                
                # Timeframe capitals'i de ekle
                for timeframe, capital in sim["config"]["capital_distribution"].items():
                    cursor.execute("""
                        INSERT OR REPLACE INTO sim_timeframe_capital 
                        (simulation_id, timeframe, allocated_capital, current_capital)
                        VALUES (?, ?, ?, ?)
                    """, (sim_id, timeframe, capital, capital))
                
                logger.info(f"Yeni simülasyon oluşturuldu: {sim['name']}")
        
        conn.commit()
        logger.info("Simülasyonlar başarıyla başlatıldı")
        return True
        
    except Exception as e:
        logger.error(f"Simülasyon başlatma hatası: {str(e)}")
        return False
    finally:
        conn.close()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    if init_simulations():
        print("Simülasyonlar başarıyla oluşturuldu/güncellendi")
        print("Confidence değerleri:")
        print("- Ana Strateji: 0.35")
        print("- Konservatif: 0.45")
        print("- Momentum: 0.40")
        print("- Mean Reversion: 0.38")
    else:
        print("Hata: Simülasyonlar oluşturulamadı")