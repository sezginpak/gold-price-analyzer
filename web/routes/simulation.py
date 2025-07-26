"""
Simülasyon API endpoint'leri
"""
from fastapi import APIRouter
import logging

from storage.sqlite_storage import SQLiteStorage
from simulation.simulation_manager import SimulationManager
from models.simulation import SimulationStatus, StrategyType

router = APIRouter(prefix="/api/simulations")
logger = logging.getLogger(__name__)

# Storage ve manager instances
storage = SQLiteStorage()
simulation_manager = SimulationManager(storage)

@router.get("/list")
async def get_simulations():
    """Tüm simülasyonları listele"""
    try:
        with storage.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, name, strategy_type, status, current_capital, 
                       total_profit_loss, total_profit_loss_pct, win_rate,
                       total_trades, winning_trades, losing_trades,
                       created_at
                FROM simulations
                ORDER BY id
            """)
            
            simulations = []
            
            # Güncel fiyatı al
            current_price = None
            latest = storage.get_latest_price()
            if latest and latest.gram_altin:
                current_price = float(latest.gram_altin)
            
            for row in cursor.fetchall():
                total_pnl_tl = row[5]
                total_pnl_gram = total_pnl_tl / current_price if current_price else 0
                
                simulations.append({
                    "id": row[0],
                    "name": row[1],
                    "strategy_type": row[2],
                    "status": row[3],
                    "current_capital": row[4],
                    "total_profit_loss": total_pnl_tl,
                    "total_profit_loss_gram": total_pnl_gram,
                    "total_profit_loss_pct": row[6],
                    "win_rate": row[7],
                    "total_trades": row[8],
                    "winning_trades": row[9],
                    "losing_trades": row[10],
                    "created_at": row[11]
                })
            
            return {"simulations": simulations, "current_price": current_price}
    except Exception as e:
        logger.error(f"Error getting simulations: {e}")
        return {"error": str(e)}

@router.get("/{sim_id}/positions")
async def get_simulation_positions(sim_id: int, status: str = "all"):
    """Simülasyon pozisyonlarını getir"""
    try:
        with storage.get_connection() as conn:
            cursor = conn.cursor()
            
            if status == "all":
                query = """
                    SELECT * FROM sim_positions 
                    WHERE simulation_id = ?
                    ORDER BY entry_time DESC
                    LIMIT 50
                """
                params = (sim_id,)
            else:
                query = """
                    SELECT * FROM sim_positions 
                    WHERE simulation_id = ? AND status = ?
                    ORDER BY entry_time DESC
                    LIMIT 50
                """
                params = (sim_id, status.upper())
            
            cursor.execute(query, params)
            columns = [desc[0] for desc in cursor.description]
            
            positions = []
            
            # Anlık fiyatı al
            current_price = None
            latest = storage.get_latest_price()
            if latest and latest.gram_altin:
                current_price = float(latest.gram_altin)
            
            for row in cursor.fetchall():
                pos = dict(zip(columns, row))
                
                # Açık pozisyonlar için anlık kar/zarar hesapla
                if pos['status'] == 'OPEN' and current_price:
                    entry_price = float(pos['entry_price'])
                    position_size = float(pos['position_size'])
                    
                    if pos['position_type'] == 'LONG':
                        pnl_tl = (current_price - entry_price) * position_size
                    else:
                        pnl_tl = (entry_price - current_price) * position_size
                    
                    # Maliyetleri çıkar
                    total_costs = float(pos['entry_spread']) + float(pos['entry_commission'])
                    pnl_tl -= total_costs
                    
                    # Gram cinsinden kar/zarar
                    pnl_gram = pnl_tl / current_price
                    
                    pos['current_price'] = current_price
                    pos['current_pnl_tl'] = pnl_tl
                    pos['current_pnl_gram'] = pnl_gram
                    pos['current_pnl_pct'] = (pnl_tl / float(pos['allocated_capital'])) * 100
                
                # Kapalı pozisyonlar için gram cinsinden kar/zarar ekle
                elif pos['status'] == 'CLOSED' and pos.get('net_profit_loss'):
                    # TL cinsinden kar/zarar zaten var
                    # Çıkış fiyatını kullanarak gram'a çevir
                    exit_price = float(pos.get('exit_price', pos.get('entry_price', current_price)))
                    if exit_price and exit_price > 0:
                        pos['net_profit_loss_gram'] = float(pos['net_profit_loss']) / exit_price
                    else:
                        pos['net_profit_loss_gram'] = 0
                
                positions.append(pos)
            
            return {"positions": positions, "current_price": current_price}
    except Exception as e:
        logger.error(f"Error getting positions: {e}")
        return {"error": str(e)}

@router.get("/{sim_id}/performance")
async def get_simulation_performance(sim_id: int, days: int = 30):
    """Simülasyon performans grafiği verisi"""
    try:
        with storage.get_connection() as conn:
            cursor = conn.cursor()
            
            # Son N günlük performans
            cursor.execute("""
                SELECT date, starting_capital, ending_capital, daily_pnl, daily_pnl_pct,
                       total_trades, winning_trades, losing_trades
                FROM sim_daily_performance
                WHERE simulation_id = ?
                ORDER BY date DESC
                LIMIT ?
            """, (sim_id, days))
            
            performance = []
            for row in cursor.fetchall():
                performance.append({
                    "date": row[0],
                    "starting_capital": row[1],
                    "ending_capital": row[2],
                    "daily_pnl": row[3],
                    "daily_pnl_pct": row[4],
                    "total_trades": row[5],
                    "winning_trades": row[6],
                    "losing_trades": row[7]
                })
            
            # Sırayı düzelt (eskiden yeniye)
            performance.reverse()
            
            return {"performance": performance}
    except Exception as e:
        logger.error(f"Error getting performance: {e}")
        return {"error": str(e)}

@router.get("/{sim_id}/summary")
async def get_simulation_summary(sim_id: int):
    """Simülasyon özeti"""
    try:
        summary = await simulation_manager.get_simulation_status(sim_id)
        if summary:
            return summary.dict()
        return {"error": "Simulation not found"}
    except Exception as e:
        logger.error(f"Error getting simulation summary: {e}")
        return {"error": str(e)}

# Yeni endpoint'ler ekleyelim

@router.get("/{sim_id}/trades/recent")
async def get_recent_trades(sim_id: int, limit: int = 20):
    """Son işlemleri detaylı olarak getir"""
    try:
        with storage.get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT 
                    p.id,
                    p.entry_time,
                    p.exit_time,
                    p.position_type,
                    p.timeframe,
                    p.entry_price,
                    p.exit_price,
                    p.position_size,
                    p.status,
                    p.net_profit_loss,
                    p.net_profit_loss_pct,
                    p.exit_reason
                FROM sim_positions p
                WHERE p.simulation_id = ? AND p.status = 'CLOSED'
                ORDER BY p.exit_time DESC
                LIMIT ?
            """, (sim_id, limit))
            
            trades = []
            for row in cursor.fetchall():
                trades.append({
                    "id": row[0],
                    "entry_time": row[1],
                    "exit_time": row[2],
                    "position_type": row[3],
                    "timeframe": row[4],
                    "entry_price": row[5],
                    "exit_price": row[6],
                    "position_size": row[7],
                    "status": row[8],
                    "net_profit_loss": row[9],
                    "net_profit_loss_pct": row[10],
                    "exit_reason": row[11],
                    "duration": _calculate_duration(row[1], row[2]) if row[2] else None
                })
            
            return {"trades": trades, "count": len(trades)}
            
    except Exception as e:
        logger.error(f"Error getting recent trades: {e}")
        return {"error": str(e)}

@router.get("/{sim_id}/statistics")
async def get_simulation_statistics(sim_id: int):
    """Detaylı simülasyon istatistikleri"""
    try:
        with storage.get_connection() as conn:
            cursor = conn.cursor()
            
            # Temel simülasyon bilgileri
            cursor.execute("""
                SELECT * FROM simulations WHERE id = ?
            """, (sim_id,))
            
            sim_data = cursor.fetchone()
            if not sim_data:
                return {"error": "Simulation not found"}
            
            # Timeframe bazlı performans
            cursor.execute("""
                SELECT 
                    timeframe,
                    COUNT(*) as total_trades,
                    SUM(CASE WHEN net_profit_loss > 0 THEN 1 ELSE 0 END) as winning_trades,
                    SUM(CASE WHEN net_profit_loss < 0 THEN 1 ELSE 0 END) as losing_trades,
                    SUM(net_profit_loss) as total_pnl,
                    AVG(net_profit_loss_pct) as avg_pnl_pct,
                    MAX(net_profit_loss) as best_trade,
                    MIN(net_profit_loss) as worst_trade
                FROM sim_positions
                WHERE simulation_id = ? AND status = 'CLOSED'
                GROUP BY timeframe
            """, (sim_id,))
            
            timeframe_stats = []
            for row in cursor.fetchall():
                win_rate = (row[2] / row[1] * 100) if row[1] > 0 else 0
                timeframe_stats.append({
                    "timeframe": row[0],
                    "total_trades": row[1],
                    "winning_trades": row[2],
                    "losing_trades": row[3],
                    "win_rate": win_rate,
                    "total_pnl": row[4],
                    "avg_pnl_pct": row[5],
                    "best_trade": row[6],
                    "worst_trade": row[7]
                })
            
            # Exit reason dağılımı
            cursor.execute("""
                SELECT 
                    exit_reason,
                    COUNT(*) as count,
                    AVG(net_profit_loss_pct) as avg_pnl_pct
                FROM sim_positions
                WHERE simulation_id = ? AND status = 'CLOSED'
                GROUP BY exit_reason
            """, (sim_id,))
            
            exit_reasons = []
            for row in cursor.fetchall():
                exit_reasons.append({
                    "reason": row[0],
                    "count": row[1],
                    "avg_pnl_pct": row[2]
                })
            
            # Günlük en iyi/kötü performans
            cursor.execute("""
                SELECT 
                    MAX(daily_pnl_pct) as best_day_pct,
                    MIN(daily_pnl_pct) as worst_day_pct,
                    AVG(daily_pnl_pct) as avg_daily_pct,
                    COUNT(DISTINCT date) as trading_days
                FROM sim_daily_performance
                WHERE simulation_id = ?
            """, (sim_id,))
            
            daily_stats = cursor.fetchone()
            
            return {
                "simulation_id": sim_id,
                "timeframe_performance": timeframe_stats,
                "exit_reason_distribution": exit_reasons,
                "daily_statistics": {
                    "best_day_pct": daily_stats[0],
                    "worst_day_pct": daily_stats[1],
                    "avg_daily_pct": daily_stats[2],
                    "trading_days": daily_stats[3]
                }
            }
            
    except Exception as e:
        logger.error(f"Error getting simulation statistics: {e}")
        return {"error": str(e)}

def _calculate_duration(entry_time: str, exit_time: str) -> str:
    """İşlem süresini hesapla"""
    try:
        from datetime import datetime
        entry = datetime.fromisoformat(entry_time)
        exit = datetime.fromisoformat(exit_time)
        duration = exit - entry
        
        days = duration.days
        hours = duration.seconds // 3600
        minutes = (duration.seconds % 3600) // 60
        
        if days > 0:
            return f"{days}g {hours}s"
        elif hours > 0:
            return f"{hours}s {minutes}d"
        else:
            return f"{minutes}d"
    except:
        return "N/A"