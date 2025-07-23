"""
Simülasyon istatistiklerini güncelle
"""
import sqlite3
import logging
from datetime import datetime
from decimal import Decimal

logger = logging.getLogger(__name__)


def update_all_simulation_stats(db_path: str = "gold_prices.db"):
    """Tüm simülasyon istatistiklerini güncelle"""
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Tüm simülasyonları al
        cursor.execute("SELECT id FROM simulations")
        sim_ids = [row[0] for row in cursor.fetchall()]
        
        for sim_id in sim_ids:
            # Timeframe sermayelerini topla
            cursor.execute("""
                SELECT SUM(current_capital) FROM sim_timeframe_capital
                WHERE simulation_id = ?
            """, (sim_id,))
            total_capital = cursor.fetchone()[0] or 1000.0
            
            # İşlem istatistikleri
            cursor.execute("""
                SELECT 
                    COUNT(*) as total_trades,
                    SUM(CASE WHEN net_profit_loss > 0 THEN 1 ELSE 0 END) as winning_trades,
                    SUM(CASE WHEN net_profit_loss < 0 THEN 1 ELSE 0 END) as losing_trades,
                    AVG(CASE WHEN net_profit_loss > 0 THEN net_profit_loss ELSE NULL END) as avg_win,
                    AVG(CASE WHEN net_profit_loss < 0 THEN ABS(net_profit_loss) ELSE NULL END) as avg_loss,
                    SUM(net_profit_loss) as total_pnl
                FROM sim_positions
                WHERE simulation_id = ? AND status = 'CLOSED'
            """, (sim_id,))
            
            stats = cursor.fetchone()
            
            # Metrikleri hesapla
            total_trades = stats[0] or 0
            winning_trades = stats[1] or 0
            losing_trades = stats[2] or 0
            avg_win = stats[3] or 0
            avg_loss = stats[4] or 0
            total_pnl = stats[5] or 0
            
            # Açık pozisyonları da hesaba kat (unrealized P&L)
            cursor.execute("""
                SELECT 
                    COUNT(*) as open_positions,
                    SUM(allocated_capital) as locked_capital
                FROM sim_positions
                WHERE simulation_id = ? AND status = 'OPEN'
            """, (sim_id,))
            
            open_stats = cursor.fetchone()
            open_positions = open_stats[0] or 0
            
            # Current capital = initial capital + realized P&L
            current_capital = 1000.0 + float(total_pnl)
            
            win_rate = winning_trades / total_trades if total_trades > 0 else 0
            profit_factor = (winning_trades * avg_win) / (losing_trades * avg_loss) if losing_trades > 0 and avg_loss > 0 else 0
            
            # Simülasyonu güncelle
            cursor.execute("""
                UPDATE simulations
                SET current_capital = ?, total_trades = ?, winning_trades = ?,
                    losing_trades = ?, total_profit_loss = ?, total_profit_loss_pct = ?,
                    win_rate = ?, profit_factor = ?, avg_win = ?, avg_loss = ?,
                    last_update = ?
                WHERE id = ?
            """, (
                current_capital,
                total_trades,
                winning_trades,
                losing_trades,
                float(total_pnl),
                float((current_capital - 1000) / 10),  # %
                win_rate,
                profit_factor,
                float(avg_win),
                float(avg_loss),
                datetime.now(),
                sim_id
            ))
            
            logger.info(f"Updated sim {sim_id}: trades={total_trades}, open={open_positions}, pnl={total_pnl:.2f}, capital={current_capital:.2f}")
        
        conn.commit()
        logger.info(f"Simülasyon istatistikleri güncellendi: {len(sim_ids)} simülasyon")
        return True
        
    except Exception as e:
        logger.error(f"Simülasyon istatistik güncelleme hatası: {str(e)}")
        return False
    finally:
        conn.close()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    if update_all_simulation_stats():
        print("Simülasyon istatistikleri başarıyla güncellendi")
        
        # Güncel durumu göster
        conn = sqlite3.connect("gold_prices.db")
        cursor = conn.cursor()
        cursor.execute("""
            SELECT name, current_capital, total_trades, winning_trades, 
                   total_profit_loss, win_rate
            FROM simulations
        """)
        
        print("\nGüncel Simülasyon Durumları:")
        print("-" * 80)
        for row in cursor.fetchall():
            name, capital, trades, wins, pnl, win_rate = row
            print(f"{name:<30} | Sermaye: {capital:>8.2f}g | İşlem: {trades:>3} | "
                  f"Kazanç: {wins:>3} | P&L: {pnl:>8.2f}g | Win: {win_rate*100:>5.1f}%")
        
        conn.close()
    else:
        print("Hata: Simülasyon istatistikleri güncellenemedi")