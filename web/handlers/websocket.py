"""
WebSocket bağlantı yönetimi
"""
from typing import List
from fastapi import WebSocket
import asyncio
import logging
from datetime import timedelta
from storage.sqlite_storage import SQLiteStorage
from utils import timezone

logger = logging.getLogger(__name__)

class WebSocketManager:
    """WebSocket bağlantılarını yönet"""
    
    def __init__(self, storage: SQLiteStorage):
        """
        WebSocket manager başlat
        
        Args:
            storage: SQLite storage instance
        """
        self.active_connections: List[WebSocket] = []
        self.storage = storage
    
    async def connect(self, websocket: WebSocket):
        """Yeni bağlantı kabul et"""
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"WebSocket bağlantısı kabul edildi. Toplam: {len(self.active_connections)}")
    
    def disconnect(self, websocket: WebSocket):
        """Bağlantıyı kapat"""
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            logger.info(f"WebSocket bağlantısı kapatıldı. Toplam: {len(self.active_connections)}")
    
    async def send_price_update(self, websocket: WebSocket):
        """Fiyat güncellemesi gönder"""
        latest_price = self.storage.get_latest_price()
        if latest_price:
            # Günlük değişim hesapla
            daily_change_pct = self._calculate_daily_change_percentage(latest_price)
            
            data = {
                "type": "price_update",
                "data": {
                    "timestamp": latest_price.timestamp.isoformat(),
                    "ons_usd": float(latest_price.ons_usd),
                    "usd_try": float(latest_price.usd_try),
                    "ons_try": float(latest_price.ons_try),
                    "gram_altin": float(latest_price.gram_altin) if latest_price.gram_altin else None,
                    "daily_change_pct": daily_change_pct
                }
            }
            await websocket.send_json(data)
    
    async def broadcast_price_update(self):
        """Tüm bağlantılara fiyat güncellemesi gönder"""
        disconnected = []
        
        for connection in self.active_connections:
            try:
                await self.send_price_update(connection)
            except Exception as e:
                logger.error(f"WebSocket broadcast error: {e}")
                disconnected.append(connection)
        
        # Bağlantısı kopan WebSocket'leri listeden çıkar
        for ws in disconnected:
            self.disconnect(ws)
    
    async def handle_connection(self, websocket: WebSocket):
        """WebSocket bağlantısını yönet"""
        await self.connect(websocket)
        
        try:
            while True:
                # Her 5 saniyede bir güncelleme gönder
                await asyncio.sleep(5)
                await self.send_price_update(websocket)
                
        except Exception as e:
            logger.error(f"WebSocket error: {e}")
        finally:
            self.disconnect(websocket)
    
    def get_connection_count(self) -> int:
        """Aktif bağlantı sayısını döndür"""
        return len(self.active_connections)
    
    def _calculate_daily_change_percentage(self, latest_price) -> float:
        """
        Günlük değişim yüzdesini hesapla
        API endpoint'indeki mantığı kullanır
        """
        try:
            if not latest_price or not latest_price.gram_altin:
                return 0.0
            
            # 24 saat önceki fiyatı al
            now = timezone.now()
            yesterday = now - timedelta(hours=24)
            
            with self.storage.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT gram_altin FROM price_data 
                    WHERE timestamp >= ? 
                    ORDER BY timestamp ASC 
                    LIMIT 1
                """, (yesterday,))
                
                yesterday_price = cursor.fetchone()
                
                if yesterday_price and yesterday_price[0]:
                    old_price = float(yesterday_price[0])
                    new_price = float(latest_price.gram_altin)
                    
                    if old_price > 0:
                        daily_change = new_price - old_price
                        daily_change_pct = (daily_change / old_price) * 100
                        return round(daily_change_pct, 2)
                
                return 0.0
                
        except Exception as e:
            logger.error(f"Günlük değişim yüzdesi hesaplama hatası: {e}")
            return 0.0