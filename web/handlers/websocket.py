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
    """WebSocket bağlantılarını yönet - Optimize edilmiş"""
    
    def __init__(self, storage: SQLiteStorage):
        """
        WebSocket manager başlat
        
        Args:
            storage: SQLite storage instance
        """
        self.active_connections: List[WebSocket] = []
        self.storage = storage
        self.last_broadcast_time = 0
        self.connection_stats = {"total_connections": 0, "failed_connections": 0}
    
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
    
    async def send_price_update(self, websocket: WebSocket):
        """Fiyat güncellemesi gönder - Optimize edilmiş"""
        try:
            # Cache'den fiyat bilgisini al
            cached_price = cache.get("ws_current_price")
            if not cached_price:
                latest_price = self.storage.get_latest_price()
                if latest_price:
                    cached_price = {
                        "timestamp": latest_price.timestamp.isoformat(),
                        "gram_altin": float(latest_price.gram_altin) if latest_price.gram_altin else None,
                        "ons_usd": float(latest_price.ons_usd),
                        "usd_try": float(latest_price.usd_try),
                        "ons_try": float(latest_price.ons_try)
                    }
                    # 10 saniye cache
                    cache.set("ws_current_price", cached_price, ttl=10)
                else:
                    return
            
            data = {
                "type": "price_update",
                "data": cached_price
            }
            await websocket.send_json(data)
            
        except WebSocketDisconnect:
            self.disconnect(websocket)
        except Exception as e:
            logger.error(f"Price update hatası: {e}")
            self.disconnect(websocket)
    
    async def send_performance_update(self, websocket: WebSocket):
        """Basit performans güncellemesi gönder - Optimize edilmiş"""
        try:
            # Cache'den performans bilgisini al
            cached_performance = cache.get("ws_performance_summary")
            if not cached_performance:
                with self.storage.get_connection() as conn:
                    cursor = conn.cursor()
                    
                    # Sadece temel istatistikler
                    cursor.execute("""
                        SELECT COUNT(*) as open_count,
                               SUM(allocated_capital) as total_capital
                        FROM sim_positions
                        WHERE status = 'OPEN'
                    """)
                    open_stats = cursor.fetchone()
                    
                    # Son 24 saat basit istatistik
                    yesterday = timezone.now() - timedelta(hours=24)
                    cursor.execute("""
                        SELECT COUNT(*) as total,
                               SUM(CASE WHEN net_profit_loss > 0 THEN 1 ELSE 0 END) as wins
                        FROM sim_positions
                        WHERE status = 'CLOSED' AND exit_time >= ?
                    """, (yesterday,))
                    daily_stats = cursor.fetchone()
                    
                    win_rate = (daily_stats[1] / daily_stats[0] * 100) if daily_stats[0] > 0 else 0
                    
                    cached_performance = {
                        "open_positions": open_stats[0] or 0,
                        "total_capital": round(float(open_stats[1] or 0), 2),
                        "daily_trades": daily_stats[0] or 0,
                        "daily_win_rate": round(win_rate, 1)
                    }
                    # 30 saniye cache
                    cache.set("ws_performance_summary", cached_performance, ttl=30)
            
            data = {
                "type": "performance_update",
                "data": cached_performance
            }
            await websocket.send_json(data)
            
        except WebSocketDisconnect:
            self.disconnect(websocket)
        except Exception as e:
            logger.error(f"Performance update error: {e}")
            self.disconnect(websocket)
    
    async def send_signals_update(self, websocket: WebSocket):
        """Son sinyalleri gönder - Basitleştirilmiş"""
        try:
            # Cache'den son sinyalleri al
            cached_signals = cache.get("ws_recent_signals")
            if not cached_signals:
                with self.storage.get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute("""
                        SELECT timestamp, timeframe, signal, confidence, gram_price
                        FROM hybrid_analysis
                        WHERE signal IN ('BUY', 'SELL')
                        ORDER BY timestamp DESC
                        LIMIT 5
                    """)
                    
                    signals = []
                    for row in cursor.fetchall():
                        signals.append({
                            "timestamp": row[0],
                            "timeframe": row[1], 
                            "signal": row[2],
                            "confidence": float(row[3]),
                            "price": float(row[4])
                        })
                    
                    cached_signals = signals
                    # 60 saniye cache
                    cache.set("ws_recent_signals", cached_signals, ttl=60)
            
            data = {
                "type": "signals_update",
                "data": {"signals": cached_signals}
            }
            await websocket.send_json(data)
            
        except WebSocketDisconnect:
            self.disconnect(websocket)
        except Exception as e:
            logger.error(f"Signals update error: {e}")
            self.disconnect(websocket)
    
    async def broadcast_update(self, update_type: str, data: Dict[Any, Any]):
        """Tüm bağlantılara güncelleme gönder - Optimize edilmiş"""
        if not self.active_connections:
            return
            
        message = {
            "type": update_type,
            "data": data,
            "timestamp": timezone.now().isoformat()
        }
        
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except (WebSocketDisconnect, ConnectionClosed):
                disconnected.append(connection)
            except Exception as e:
                logger.warning(f"WebSocket broadcast error: {e}")
                disconnected.append(connection)
        
        # Kopan bağlantıları temizle
        for ws in disconnected:
            self.disconnect(ws)
    
    async def handle_connection(self, websocket: WebSocket):
        """WebSocket bağlantısını yönet - Basitleştirilmiş"""
        await self.connect(websocket)
        
        try:
            # İlk bağlantıda temel verileri gönder
            await self.send_price_update(websocket)
            await self.send_performance_update(websocket)
            await self.send_signals_update(websocket)
            
            # Ana döngü - sadece fiyat güncellemeleri
            while True:
                await asyncio.sleep(10)  # 10 saniye aralık
                
                # Fiyat güncellemesi
                await self.send_price_update(websocket)
                
                # Her 60 saniyede bir performans ve sinyaller
                current_time = int(time.time())
                if current_time % 60 == 0:
                    await self.send_performance_update(websocket)
                    await self.send_signals_update(websocket)
                
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
        """Bağlantı istatistiklerini döndür"""
        return {
            "active_connections": len(self.active_connections),
            **self.connection_stats
        }