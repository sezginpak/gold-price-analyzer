#!/usr/bin/env python3
"""
Simülasyon başlatma scripti
"""
import asyncio
import sys
sys.path.append('.')

from storage.sqlite_storage import SQLiteStorage
from simulation.simulation_manager import SimulationManager
from models.simulation import StrategyType
from utils.logger import setup_logger

logger = setup_logger("simulation_starter")

async def create_simulations():
    """Farklı strateji tiplerinde simülasyonlar oluştur"""
    storage = SQLiteStorage()
    manager = SimulationManager(storage)
    
    simulations = [
        {
            "name": "Ana Strateji - Genel",
            "strategy_type": StrategyType.MAIN,
            "min_confidence": 0.6
        },
        {
            "name": "Konservatif - Güvenli",
            "strategy_type": StrategyType.CONSERVATIVE,
            "min_confidence": 0.7,
            "max_risk": 0.01  # %1 risk
        },
        {
            "name": "Momentum Takibi",
            "strategy_type": StrategyType.MOMENTUM,
            "min_confidence": 0.65
        },
        {
            "name": "Ortalamaya Dönüş",
            "strategy_type": StrategyType.MEAN_REVERSION,
            "min_confidence": 0.65
        }
    ]
    
    print("📊 Simülasyonlar oluşturuluyor...\n")
    
    for sim in simulations:
        try:
            sim_id = await manager.create_simulation(**sim)
            print(f"✅ '{sim['name']}' oluşturuldu (ID: {sim_id})")
        except Exception as e:
            print(f"❌ '{sim['name']}' oluşturulamadı: {str(e)}")
    
    print("\n✨ Tüm simülasyonlar hazır!")
    print("🚀 Ana program başlatıldığında otomatik olarak çalışacaklar.")

if __name__ == "__main__":
    asyncio.run(create_simulations())