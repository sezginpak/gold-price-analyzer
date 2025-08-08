"""
WebSocket bağlantı yönetimi - Optimize edilmiş
"""
from typing import List, Dict, Any
from fastapi import WebSocket, WebSocketDisconnect
import asyncio
import logging
from datetime import timedelta
import time
from websockets.exceptions import ConnectionClosed
from storage.sqlite_storage import SQLiteStorage
from utils import timezone
from web.utils import cache

logger = logging.getLogger(__name__)

class WebSocketManager:
    """WebSocket bağlantılarını yönet - Ultra Optimized with Smart Updates"""
    
    def __init__(self, storage: SQLiteStorage):
        """
        WebSocket manager başlat - Performance focused
        
        Args:
            storage: SQLite storage instance
        """
        self.active_connections: List[WebSocket] = []
        self.storage = storage
        self.last_broadcast_time = 0
        self.connection_stats = {"total_connections": 0, "failed_connections": 0}
        
        # Performance optimization variables
        self._last_price_hash = None
        self._last_performance_hash = None
        self._last_signals_hash = None
        self._update_intervals = {
            "price": 15,      # Price updates every 15 seconds (reduced from 10)
            "performance": 60,  # Performance updates every 60 seconds
            "signals": 120      # Signal updates every 2 minutes (reduced frequency)
        }
    
    async def connect(self, websocket: WebSocket):
        """Yeni bağlantı kabul et"""
        try:
            await websocket.accept()
            self.active_connections.append(websocket)
            self.connection_stats["total_connections"] += 1
            logger.info(f"WebSocket bağlantısı kabul edildi. Toplam: {len(self.active_connections)}")
        except Exception as e:
            logger.error(f"WebSocket connect hatası: {e}")
            self.connection_stats["failed_connections"] += 1
    
    def disconnect(self, websocket: WebSocket):
        """Bağlantıyı kapat"""
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            logger.debug(f"WebSocket bağlantısı kapatıldı. Toplam: {len(self.active_connections)}")
    
    async def send_price_update(self, websocket: WebSocket, force_update: bool = False):
        """Fiyat güncellemesi gönder - Smart change detection"""
        try:
            # Smart cache with change detection
            cached_price = cache.get("ws_current_price_v2")
            if not cached_price:
                latest_price = self.storage.get_latest_price()
                if latest_price:
                    cached_price = {
                        "t": latest_price.timestamp.isoformat(),
                        "g": float(latest_price.gram_altin) if latest_price.gram_altin else None,
                        "o": float(latest_price.ons_usd),
                        "u": float(latest_price.usd_try)
                    }
                    # 20 saniye cache (increased for better performance)
                    cache.set("ws_current_price_v2", cached_price, ttl=20)
                else:
                    return
            
            # Change detection to avoid unnecessary updates
            price_hash = hash(str(cached_price))
            if not force_update and price_hash == self._last_price_hash:
                return  # No change, skip update
            
            self._last_price_hash = price_hash
            
            # Minimized data structure for faster transmission
            data = {
                "type": "price",
                "data": cached_price
            }
            await websocket.send_json(data)
            
        except WebSocketDisconnect:
            self.disconnect(websocket)
        except Exception as e:
            logger.error(f"Price update hatası: {e}")
            self.disconnect(websocket)
    
    async def send_performance_update(self, websocket: WebSocket, force_update: bool = False):
        """Basit performans güncellemesi gönder - Ultra optimized with minimal data"""
        try:
            # Enhanced cache with change detection
            cached_performance = cache.get("ws_performance_v2")
            if not cached_performance:
                with self.storage.get_connection() as conn:
                    cursor = conn.cursor()
                    
                    # Single optimized query for all performance data
                    yesterday = timezone.now() - timedelta(hours=24)
                    cursor.execute("""
                        WITH perf_data AS (
                            SELECT 
                                COUNT(CASE WHEN status = 'OPEN' THEN 1 END) as open_count,
                                SUM(CASE WHEN status = 'OPEN' THEN allocated_capital ELSE 0 END) as total_capital,
                                COUNT(CASE WHEN status = 'CLOSED' AND exit_time >= ? THEN 1 END) as daily_trades,
                                SUM(CASE WHEN status = 'CLOSED' AND exit_time >= ? AND net_profit_loss > 0 THEN 1 ELSE 0 END) as daily_wins
                            FROM sim_positions
                        )
                        SELECT open_count, total_capital, daily_trades, daily_wins FROM perf_data
                    """, (yesterday, yesterday))
                    
                    stats = cursor.fetchone()
                    win_rate = (stats[3] / stats[2] * 100) if stats[2] > 0 else 0
                    
                    # Minimized data structure
                    cached_performance = {
                        "op": stats[0] or 0,                          # open_positions
                        "tc": round(float(stats[1] or 0), 1),        # total_capital
                        "dt": stats[2] or 0,                         # daily_trades
                        "wr": round(win_rate, 1)                     # win_rate
                    }
                    # 90 saniye cache (increased for better performance)
                    cache.set("ws_performance_v2", cached_performance, ttl=90)
            
            # Change detection
            perf_hash = hash(str(cached_performance))
            if not force_update and perf_hash == self._last_performance_hash:
                return  # No significant change
                
            self._last_performance_hash = perf_hash
            
            data = {
                "type": "perf",
                "data": cached_performance
            }
            await websocket.send_json(data)
            
        except WebSocketDisconnect:
            self.disconnect(websocket)
        except Exception as e:
            logger.error(f"Performance update error: {e}")
            self.disconnect(websocket)
    
    async def send_signals_update(self, websocket: WebSocket, force_update: bool = False):
        """Son sinyalleri gönder - Optimized with smart filtering"""
        try:
            # Enhanced cache with reduced data size
            cached_signals = cache.get("ws_signals_v2")
            if not cached_signals:
                with self.storage.get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute("""
                        SELECT timestamp, timeframe, signal, confidence, gram_price
                        FROM hybrid_analysis
                        WHERE signal IN ('BUY', 'SELL')
                        AND timestamp > datetime('now', '-6 hours')
                        ORDER BY timestamp DESC
                        LIMIT 3
                    """)
                    
                    # Minimized data structure for signals
                    signals = [
                        {
                            "t": row[0],                    # timestamp
                            "tf": row[1],                   # timeframe  
                            "s": row[2],                    # signal
                            "c": round(float(row[3]), 2),  # confidence
                            "p": round(float(row[4]), 1)   # price
                        }
                        for row in cursor.fetchall()
                    ]
                    
                    cached_signals = signals
                    # 2 dakika cache (increased for lower frequency updates)
                    cache.set("ws_signals_v2", cached_signals, ttl=120)
            
            # Change detection for signals
            signals_hash = hash(str(cached_signals))
            if not force_update and signals_hash == self._last_signals_hash:
                return  # No new signals
                
            self._last_signals_hash = signals_hash
            
            data = {
                "type": "signals",
                "data": cached_signals
            }
            await websocket.send_json(data)
            
        except WebSocketDisconnect:
            self.disconnect(websocket)
        except Exception as e:
            logger.error(f"Signals update error: {e}")
            self.disconnect(websocket)
    
    async def broadcast_update(self, update_type: str, data: Dict[Any, Any]):
        """Tüm bağlantılara güncelleme gönder - Batch optimized"""
        if not self.active_connections:
            return
            
        # Minimized message structure for better performance
        message = {
            "type": update_type,
            "data": data
        }
        
        # Batch processing for better performance
        disconnected = []
        successful_sends = 0
        
        # Process connections in batches to avoid blocking
        batch_size = 50
        for i in range(0, len(self.active_connections), batch_size):
            batch = self.active_connections[i:i + batch_size]
            
            for connection in batch:
                try:
                    await connection.send_json(message)
                    successful_sends += 1
                except (WebSocketDisconnect, ConnectionClosed):
                    disconnected.append(connection)
                except Exception as e:
                    logger.warning(f"WebSocket broadcast error: {e}")
                    disconnected.append(connection)
            
            # Small delay between batches to prevent overwhelming
            if i + batch_size < len(self.active_connections):
                await asyncio.sleep(0.01)
        
        # Cleanup disconnected sockets
        for ws in disconnected:
            self.disconnect(ws)
            
        # Update connection stats
        if disconnected:
            logger.info(f"Broadcast completed: {successful_sends} successful, {len(disconnected)} disconnected")
    
    async def handle_connection(self, websocket: WebSocket):
        """WebSocket bağlantısını yönet - Ultra optimized with intelligent scheduling"""
        await self.connect(websocket)
        
        try:
            # İlk bağlantıda tüm verileri force update ile gönder
            await self.send_price_update(websocket, force_update=True)
            await self.send_performance_update(websocket, force_update=True)
            await self.send_signals_update(websocket, force_update=True)
            
            # Intelligent update loop with variable intervals
            last_updates = {
                "price": 0,
                "performance": 0,
                "signals": 0
            }
            
            while True:
                await asyncio.sleep(5)  # Base loop interval - 5 seconds
                current_time = time.time()
                
                # Smart scheduling based on defined intervals
                if current_time - last_updates["price"] >= self._update_intervals["price"]:
                    await self.send_price_update(websocket)
                    last_updates["price"] = current_time
                
                if current_time - last_updates["performance"] >= self._update_intervals["performance"]:
                    await self.send_performance_update(websocket)
                    last_updates["performance"] = current_time
                
                if current_time - last_updates["signals"] >= self._update_intervals["signals"]:
                    await self.send_signals_update(websocket)
                    last_updates["signals"] = current_time
                
        except WebSocketDisconnect:
            logger.info("WebSocket bağlantısı normal şekilde kesildi")
        except Exception as e:
            logger.error(f"WebSocket error: {e}")
        finally:
            self.disconnect(websocket)
    
    def get_connection_count(self) -> int:
        """Aktif bağlantı sayısını döndür"""
        return len(self.active_connections)
    
    def get_connection_stats(self) -> dict:
        """Bağlantı istatistiklerini döndür - Enhanced metrics"""
        return {
            "active_connections": len(self.active_connections),
            "update_intervals": self._update_intervals,
            "last_broadcast_time": self.last_broadcast_time,
            "performance_optimizations": {
                "change_detection_enabled": True,
                "smart_scheduling_enabled": True,
                "batch_broadcasting_enabled": True
            },
            **self.connection_stats
        }