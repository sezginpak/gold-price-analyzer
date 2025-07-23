#!/usr/bin/env python3
"""
Simülasyonları sıfırla ve yeniden başlat
"""
import sqlite3
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def reset_simulations():
    """Tüm simülasyon verilerini sıfırla"""
    try:
        conn = sqlite3.connect('gold_prices.db')
        cursor = conn.cursor()
        
        # 1. Tüm pozisyonları sil
        cursor.execute("DELETE FROM sim_positions")
        deleted_positions = cursor.rowcount
        logger.info(f"{deleted_positions} pozisyon silindi")
        
        # 2. Günlük performans kayıtlarını sil
        cursor.execute("DELETE FROM sim_daily_performance")
        deleted_daily = cursor.rowcount
        logger.info(f"{deleted_daily} günlük performans kaydı silindi")
        
        # 3. Timeframe sermayelerini sıfırla
        cursor.execute("""
            UPDATE sim_timeframe_capital 
            SET current_capital = allocated_capital, 
                in_position = 0,
                last_update = ?
        """, (datetime.now(),))
        updated_capitals = cursor.rowcount
        logger.info(f"{updated_capitals} timeframe sermayesi sıfırlandı")
        
        # 4. Simülasyon istatistiklerini sıfırla
        cursor.execute("""
            UPDATE simulations 
            SET current_capital = initial_capital,
                total_trades = 0,
                winning_trades = 0,
                losing_trades = 0,
                total_profit_loss = 0,
                total_profit_loss_pct = 0,
                win_rate = 0,
                profit_factor = 0,
                avg_win = 0,
                avg_loss = 0,
                sharpe_ratio = 0,
                max_drawdown = 0,
                max_drawdown_pct = 0,
                last_update = ?
            WHERE status = 'ACTIVE'
        """, (datetime.now(),))
        updated_sims = cursor.rowcount
        logger.info(f"{updated_sims} simülasyon sıfırlandı")
        
        # 5. Mevcut simülasyonları göster
        cursor.execute("""
            SELECT id, name, initial_capital, min_confidence, max_risk 
            FROM simulations 
            WHERE status = 'ACTIVE'
        """)
        
        print("\n=== Aktif Simülasyonlar ===")
        for row in cursor.fetchall():
            print(f"ID: {row[0]}, İsim: {row[1]}, Sermaye: {row[2]}g, Min Conf: {row[3]}, Risk: {row[4]}")
        
        conn.commit()
        conn.close()
        
        logger.info("\n✅ Simülasyonlar başarıyla sıfırlandı!")
        
    except Exception as e:
        logger.error(f"Hata: {str(e)}")
        if conn:
            conn.rollback()
            conn.close()

if __name__ == "__main__":
    reset_simulations()