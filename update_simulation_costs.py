#!/usr/bin/env python3
"""
Simülasyon maliyetlerini güncelleme scripti
Spread ve komisyon oranlarını gerçekçi değerlere düşürür
"""

import sqlite3
import json
import logging

logger = logging.getLogger(__name__)

def update_simulation_costs():
    """Simülasyon maliyetlerini güncelle"""
    
    db_path = "/Users/sezginpaksoy/Desktop/gold_price_analyzer/gold_prices.db"
    
    # Yeni değerler
    new_spread = 2.0  # TL
    new_commission_rate = 0.0003  # %0.03
    
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        
        # Mevcut simülasyonları getir
        cursor.execute("SELECT id, config FROM simulations")
        simulations = cursor.fetchall()
        
        for sim_id, config_json in simulations:
            config = json.loads(config_json)
            
            # Maliyetleri güncelle
            old_spread = config.get('spread', 15.0)
            old_commission = config.get('commission_rate', 0.001)
            
            config['spread'] = new_spread
            config['commission_rate'] = new_commission_rate
            
            # Güncellenen config'i kaydet
            cursor.execute("""
                UPDATE simulations
                SET spread = ?, commission_rate = ?, config = ?
                WHERE id = ?
            """, (new_spread, new_commission_rate, json.dumps(config), sim_id))
            
            print(f"Simülasyon {sim_id}: Spread {old_spread} -> {new_spread} TL, "
                  f"Komisyon {old_commission*100:.2f}% -> {new_commission_rate*100:.2f}%")
        
        conn.commit()
        print(f"✅ {len(simulations)} simülasyon güncellendi")

if __name__ == "__main__":
    update_simulation_costs()