"""
Simülasyon istatistikleri yönetimi modülü
"""
import logging
from datetime import datetime
from decimal import Decimal
from typing import Dict

from storage.sqlite_storage import SQLiteStorage

logger = logging.getLogger("gold_analyzer")


class StatisticsManager:
    """Simülasyon istatistikleri güncelleme işlemleri"""
    
    def __init__(self, storage: SQLiteStorage):
        self.storage = storage
    
    async def update_simulation_stats(self, sim_id: int, timeframe_capitals: Dict):
        """Simülasyon istatistiklerini güncelle"""
        try:
            with self.storage.get_connection() as conn:
                cursor = conn.cursor()
                
                # Toplam sermayeyi hesapla
                total_capital = sum(
                    tf.current_capital 
                    for tf in timeframe_capitals[sim_id].values()
                )
                
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
                    float(total_capital),
                    total_trades,
                    winning_trades,
                    losing_trades,
                    float(total_pnl),
                    float((total_capital - 1000) / 10),  # %
                    win_rate,
                    profit_factor,
                    float(avg_win),
                    float(avg_loss),
                    datetime.now(),
                    sim_id
                ))
                
                conn.commit()
                logger.debug(f"Updated stats for sim {sim_id}: trades={total_trades}, pnl={total_pnl}, capital={total_capital}")
                
        except Exception as e:
            logger.error(f"Simülasyon istatistik güncelleme hatası: {str(e)}")
    
    async def update_daily_performance(self, sim_id: int, timeframe_capitals: Dict, active_simulations: Dict):
        """Günlük performansı güncelle"""
        try:
            today = datetime.now().date()
            
            with self.storage.get_connection() as conn:
                cursor = conn.cursor()
                
                # Toplam sermayeyi hesapla
                tf_capitals = timeframe_capitals.get(sim_id, {})
                if not tf_capitals:
                    return
                
                total_capital = sum(
                    float(tf.current_capital) if tf.current_capital is not None else 0
                    for tf in tf_capitals.values()
                ) or 1000.0  # Varsayılan sermaye
                
                # Günün başlangıç sermayesini al (veya varsayılan)
                cursor.execute("""
                    SELECT ending_capital FROM sim_daily_performance
                    WHERE simulation_id = ? AND date < ?
                    ORDER BY date DESC LIMIT 1
                """, (sim_id, today))
                
                row = cursor.fetchone()
                starting_capital = row[0] if row else 1000.0
                
                # Bugünkü işlemleri al - timeframe bazlı
                cursor.execute("""
                    SELECT 
                        COUNT(*) as total,
                        SUM(CASE WHEN net_profit_loss > 0 THEN 1 ELSE 0 END) as wins,
                        SUM(CASE WHEN net_profit_loss < 0 THEN 1 ELSE 0 END) as losses,
                        SUM(net_profit_loss) as total_pnl,
                        SUM(CASE WHEN timeframe = '15m' THEN 1 ELSE 0 END) as trades_15m,
                        SUM(CASE WHEN timeframe = '1h' THEN 1 ELSE 0 END) as trades_1h,
                        SUM(CASE WHEN timeframe = '4h' THEN 1 ELSE 0 END) as trades_4h,
                        SUM(CASE WHEN timeframe = '1d' THEN 1 ELSE 0 END) as trades_1d,
                        SUM(CASE WHEN timeframe = '15m' THEN net_profit_loss ELSE 0 END) as pnl_15m,
                        SUM(CASE WHEN timeframe = '1h' THEN net_profit_loss ELSE 0 END) as pnl_1h,
                        SUM(CASE WHEN timeframe = '4h' THEN net_profit_loss ELSE 0 END) as pnl_4h,
                        SUM(CASE WHEN timeframe = '1d' THEN net_profit_loss ELSE 0 END) as pnl_1d
                    FROM sim_positions
                    WHERE simulation_id = ? 
                    AND DATE(exit_time) = ?
                    AND status = 'CLOSED'
                """, (sim_id, today))
                
                stats = cursor.fetchone()
                
                # Debug log
                if stats:
                    logger.debug(f"Daily performance stats for sim {sim_id}: {list(stats)}")
                else:
                    logger.debug(f"No daily performance stats for sim {sim_id}")
                
                # Değerleri al
                total_trades = stats[0] or 0
                winning_trades = stats[1] or 0
                losing_trades = stats[2] or 0
                daily_pnl = stats[3] or 0.0
                
                # Mevcut kaydı kontrol et
                cursor.execute("""
                    SELECT id FROM sim_daily_performance
                    WHERE simulation_id = ? AND date = ?
                """, (sim_id, today))
                
                if cursor.fetchone():
                    # Güncelle
                    cursor.execute("""
                        UPDATE sim_daily_performance
                        SET ending_capital = ?, daily_pnl = ?, daily_pnl_pct = ?,
                            total_trades = ?, winning_trades = ?, losing_trades = ?,
                            trades_15m = ?, trades_1h = ?, trades_4h = ?, trades_1d = ?,
                            pnl_15m = ?, pnl_1h = ?, pnl_4h = ?, pnl_1d = ?
                        WHERE simulation_id = ? AND date = ?
                    """, (
                        float(total_capital), float(daily_pnl), 
                        float(daily_pnl / starting_capital * 100) if starting_capital > 0 else 0,
                        total_trades, winning_trades, losing_trades,
                        stats[4] or 0, stats[5] or 0, stats[6] or 0, stats[7] or 0,
                        float(stats[8] or 0), float(stats[9] or 0), float(stats[10] or 0), float(stats[11] or 0),
                        sim_id, today
                    ))
                else:
                    # Yeni kayıt
                    cursor.execute("""
                        INSERT INTO sim_daily_performance (
                            simulation_id, date, starting_capital, ending_capital,
                            daily_pnl, daily_pnl_pct, total_trades, winning_trades, losing_trades,
                            trades_15m, trades_1h, trades_4h, trades_1d,
                            pnl_15m, pnl_1h, pnl_4h, pnl_1d
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        sim_id, today, float(starting_capital), float(total_capital),
                        float(daily_pnl), float(daily_pnl / starting_capital * 100) if starting_capital > 0 else 0,
                        total_trades, winning_trades, losing_trades,
                        stats[4] or 0, stats[5] or 0, stats[6] or 0, stats[7] or 0,
                        float(stats[8] or 0), float(stats[9] or 0), float(stats[10] or 0), float(stats[11] or 0)
                    ))
                
                conn.commit()
                
        except Exception as e:
            import traceback
            logger.error(f"Günlük performans güncelleme hatası: {str(e)}")
            logger.error(f"Traceback: {traceback.format_exc()}")
    
    async def update_timeframe_capital(self, sim_id: int, timeframe: str, tf_capital):
        """Timeframe sermayesini güncelle"""
        with self.storage.get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                UPDATE sim_timeframe_capital
                SET current_capital = ?, in_position = ?, last_update = ?
                WHERE simulation_id = ? AND timeframe = ?
            """, (
                float(tf_capital.current_capital),
                1 if tf_capital.in_position else 0,
                datetime.now(),
                sim_id,
                timeframe
            ))
            
            conn.commit()
    
    def get_simulation_summary(self, sim_id: int, config) -> dict:
        """Simülasyon özet bilgilerini getir"""
        with self.storage.get_connection() as conn:
            cursor = conn.cursor()
            
            # Simülasyon temel bilgileri
            cursor.execute("""
                SELECT current_capital, total_trades, winning_trades, losing_trades,
                       total_profit_loss, win_rate, profit_factor, max_drawdown
                FROM simulations WHERE id = ?
            """, (sim_id,))
            
            sim_stats = cursor.fetchone()
            
            # Açık pozisyonlar
            cursor.execute("""
                SELECT COUNT(*) as open_positions,
                       SUM(allocated_capital) as locked_capital
                FROM sim_positions
                WHERE simulation_id = ? AND status = 'OPEN'
            """, (sim_id,))
            
            open_stats = cursor.fetchone()
            
            # Son 24 saat performansı
            cursor.execute("""
                SELECT SUM(net_profit_loss) as last_24h_pnl,
                       COUNT(*) as last_24h_trades
                FROM sim_positions
                WHERE simulation_id = ? 
                AND exit_time > datetime('now', '-1 day')
                AND status = 'CLOSED'
            """, (sim_id,))
            
            last_24h = cursor.fetchone()
            
            return {
                "simulation_id": sim_id,
                "name": config.name,
                "strategy_type": config.strategy_type.value,
                "current_capital": sim_stats[0] if sim_stats else 1000.0,
                "total_trades": sim_stats[1] if sim_stats else 0,
                "winning_trades": sim_stats[2] if sim_stats else 0,
                "losing_trades": sim_stats[3] if sim_stats else 0,
                "total_profit_loss": sim_stats[4] if sim_stats else 0.0,
                "win_rate": sim_stats[5] if sim_stats else 0.0,
                "profit_factor": sim_stats[6] if sim_stats else 0.0,
                "max_drawdown": sim_stats[7] if sim_stats else 0.0,
                "open_positions": open_stats[0] if open_stats else 0,
                "locked_capital": open_stats[1] if open_stats else 0.0,
                "last_24h_pnl": last_24h[0] if last_24h else 0.0,
                "last_24h_trades": last_24h[1] if last_24h else 0
            }