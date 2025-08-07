"""
WebSocket bağlantı testleri
"""
import pytest
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from fastapi.testclient import TestClient
from fastapi import WebSocket
import json
import asyncio

from web_server import app
from web.handlers.websocket import WebSocketManager
from utils import timezone
from models.price_data import PriceData


class TestWebSocket:
    """WebSocket testleri"""
    
    @pytest.fixture
    def client(self):
        """Test client'i oluştur"""
        return TestClient(app)
    
    @pytest.fixture
    def mock_storage(self):
        """Mock storage nesnesi oluştur"""
        mock = Mock()
        
        mock_price = PriceData(
            timestamp=timezone.now(),
            ons_usd=2000.0,
            usd_try=30.0,
            ons_try=60000.0,
            gram_altin=1932.0
        )
        
        mock.get_latest_price.return_value = mock_price
        mock.get_latest_prices.return_value = [mock_price]
        mock.get_statistics.return_value = {
            "total_records": 1000,
            "oldest_record": "2024-01-01T00:00:00",
            "newest_record": "2024-01-02T00:00:00",
            "average_price": 2500.0
        }
        
        return mock
    
    @pytest.fixture
    def websocket_manager(self, mock_storage):
        """WebSocket manager nesnesi oluştur"""
        return WebSocketManager(mock_storage)
    
    @pytest.mark.asyncio
    async def test_websocket_manager_initialization(self, websocket_manager):
        """WebSocket manager başlatma testi"""
        assert websocket_manager.storage is not None
        assert len(websocket_manager.connections) == 0
        assert websocket_manager.broadcast_task is None
    
    @pytest.mark.asyncio
    async def test_websocket_connection_accept(self, websocket_manager):
        """WebSocket bağlantı kabul testi"""
        # Mock WebSocket nesnesi
        mock_websocket = AsyncMock(spec=WebSocket)
        mock_websocket.accept = AsyncMock()
        mock_websocket.send_json = AsyncMock()
        mock_websocket.receive_text = AsyncMock()
        mock_websocket.receive_text.side_effect = Exception("Connection closed")
        
        # Bağlantı testi
        with pytest.raises(Exception):
            await websocket_manager.handle_connection(mock_websocket)
        
        # accept() çağrıldığını kontrol et
        mock_websocket.accept.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_websocket_connection_tracking(self, websocket_manager):
        """WebSocket bağlantı takibi testi"""
        mock_websocket1 = AsyncMock(spec=WebSocket)
        mock_websocket2 = AsyncMock(spec=WebSocket)
        
        # Bağlantı sayısını kontrol et
        assert websocket_manager.get_connection_count() == 0
        
        # Bağlantıları ekle
        websocket_manager.connections.add(mock_websocket1)
        websocket_manager.connections.add(mock_websocket2)
        
        assert websocket_manager.get_connection_count() == 2
        
        # Bağlantı çıkar
        websocket_manager.connections.remove(mock_websocket1)
        assert websocket_manager.get_connection_count() == 1
    
    @pytest.mark.asyncio
    async def test_websocket_broadcast_message(self, websocket_manager):
        """WebSocket broadcast mesaj testi"""
        # Mock WebSocket bağlantıları oluştur
        mock_websocket1 = AsyncMock(spec=WebSocket)
        mock_websocket2 = AsyncMock(spec=WebSocket)
        mock_websocket1.send_json = AsyncMock()
        mock_websocket2.send_json = AsyncMock()
        
        # Bağlantıları ekle
        websocket_manager.connections.add(mock_websocket1)
        websocket_manager.connections.add(mock_websocket2)
        
        test_message = {"type": "price_update", "data": {"price": 1932.0}}
        
        # Broadcast yap
        await websocket_manager.broadcast(test_message)
        
        # Tüm bağlantılara mesaj gönderildiğini kontrol et
        mock_websocket1.send_json.assert_called_once_with(test_message)
        mock_websocket2.send_json.assert_called_once_with(test_message)
    
    @pytest.mark.asyncio
    async def test_websocket_broadcast_with_failed_connection(self, websocket_manager):
        """Başarısız bağlantı ile broadcast testi"""
        # Mock WebSocket bağlantıları oluştur
        mock_websocket_good = AsyncMock(spec=WebSocket)
        mock_websocket_bad = AsyncMock(spec=WebSocket)
        
        mock_websocket_good.send_json = AsyncMock()
        mock_websocket_bad.send_json = AsyncMock(side_effect=Exception("Connection failed"))
        
        # Bağlantıları ekle
        websocket_manager.connections.add(mock_websocket_good)
        websocket_manager.connections.add(mock_websocket_bad)
        
        test_message = {"type": "test", "data": "test"}
        
        # Broadcast yap
        await websocket_manager.broadcast(test_message)
        
        # İyi bağlantıya mesaj gönderildi
        mock_websocket_good.send_json.assert_called_once_with(test_message)
        
        # Kötü bağlantı kaldırıldı
        assert mock_websocket_bad not in websocket_manager.connections
        assert mock_websocket_good in websocket_manager.connections
    
    @pytest.mark.asyncio
    async def test_websocket_price_data_broadcast(self, websocket_manager, mock_storage):
        """Fiyat verisi broadcast testi"""
        # Mock WebSocket bağlantısı
        mock_websocket = AsyncMock(spec=WebSocket)
        mock_websocket.send_json = AsyncMock()
        
        websocket_manager.connections.add(mock_websocket)
        
        # Fiyat verisi broadcast'i simüle et
        price_data = {
            "type": "price_update",
            "data": {
                "timestamp": timezone.now().isoformat(),
                "gram_altin": 1932.0,
                "ons_usd": 2000.0,
                "usd_try": 30.0
            }
        }
        
        await websocket_manager.broadcast(price_data)
        
        # Mesajın gönderildiğini kontrol et
        mock_websocket.send_json.assert_called_once_with(price_data)
    
    @pytest.mark.asyncio
    async def test_websocket_analysis_broadcast(self, websocket_manager):
        """Analiz sonucu broadcast testi"""
        # Mock WebSocket bağlantısı
        mock_websocket = AsyncMock(spec=WebSocket)
        mock_websocket.send_json = AsyncMock()
        
        websocket_manager.connections.add(mock_websocket)
        
        # Analiz sonucu broadcast'i simüle et
        analysis_data = {
            "type": "analysis_update",
            "data": {
                "timestamp": timezone.now().isoformat(),
                "signal": "BUY",
                "confidence": 85.5,
                "timeframe": "15m",
                "price": 1932.0
            }
        }
        
        await websocket_manager.broadcast(analysis_data)
        
        # Mesajın gönderildiğini kontrol et
        mock_websocket.send_json.assert_called_once_with(analysis_data)
    
    def test_websocket_endpoint_integration(self, client):
        """WebSocket endpoint entegrasyon testi"""
        # Bu test gerçek WebSocket bağlantısı kurmaya çalışır
        # Test client ile WebSocket testleri sınırlı olduğu için
        # sadece endpoint'in var olduğunu kontrol edelim
        
        # WebSocket endpoint'i app içinde tanımlı mı?
        websocket_routes = [route for route in app.routes if hasattr(route, 'path') and route.path == '/ws']
        assert len(websocket_routes) == 1
    
    @pytest.mark.asyncio 
    async def test_websocket_connection_cleanup(self, websocket_manager):
        """WebSocket bağlantı temizleme testi"""
        # Mock WebSocket bağlantıları ekle
        mock_websocket1 = AsyncMock(spec=WebSocket)
        mock_websocket2 = AsyncMock(spec=WebSocket)
        
        websocket_manager.connections.add(mock_websocket1)
        websocket_manager.connections.add(mock_websocket2)
        
        assert websocket_manager.get_connection_count() == 2
        
        # Bağlantıları temizle
        websocket_manager.connections.clear()
        
        assert websocket_manager.get_connection_count() == 0
    
    @pytest.mark.asyncio
    async def test_websocket_message_types(self, websocket_manager):
        """Farklı mesaj tiplerini test et"""
        mock_websocket = AsyncMock(spec=WebSocket)
        mock_websocket.send_json = AsyncMock()
        
        websocket_manager.connections.add(mock_websocket)
        
        # Farklı mesaj tiplerini test et
        message_types = [
            {"type": "price_update", "data": {"price": 1932.0}},
            {"type": "signal_update", "data": {"signal": "BUY"}},
            {"type": "analysis_update", "data": {"confidence": 85.0}},
            {"type": "log_update", "data": {"message": "Test log"}},
            {"type": "stats_update", "data": {"active_connections": 1}}
        ]
        
        for message in message_types:
            await websocket_manager.broadcast(message)
            
        # Tüm mesajların gönderildiğini kontrol et
        assert mock_websocket.send_json.call_count == len(message_types)
    
    @pytest.mark.asyncio
    async def test_websocket_concurrent_connections(self, websocket_manager):
        """Eş zamanlı bağlantı testi"""
        # Birden fazla mock bağlantı oluştur
        connections = []
        for i in range(5):
            mock_websocket = AsyncMock(spec=WebSocket)
            mock_websocket.send_json = AsyncMock()
            connections.append(mock_websocket)
            websocket_manager.connections.add(mock_websocket)
        
        assert websocket_manager.get_connection_count() == 5
        
        # Broadcast mesajı
        test_message = {"type": "test", "data": "concurrent test"}
        await websocket_manager.broadcast(test_message)
        
        # Tüm bağlantılara mesaj gönderildiğini kontrol et
        for connection in connections:
            connection.send_json.assert_called_once_with(test_message)
    
    @pytest.mark.asyncio
    async def test_websocket_data_formatting(self, websocket_manager, mock_storage):
        """WebSocket veri formatlama testi"""
        mock_websocket = AsyncMock(spec=WebSocket)
        mock_websocket.send_json = AsyncMock()
        
        websocket_manager.connections.add(mock_websocket)
        
        # Gerçekçi veri yapısı ile test
        formatted_data = {
            "type": "dashboard_update",
            "timestamp": timezone.now().isoformat(),
            "data": {
                "current_price": {
                    "gram_altin": 1932.50,
                    "ons_usd": 2000.25,
                    "usd_try": 30.15,
                    "change_pct": 0.5
                },
                "signals": [
                    {
                        "type": "BUY",
                        "timeframe": "15m",
                        "confidence": 85.0,
                        "price": 1932.50
                    }
                ],
                "stats": {
                    "active_connections": 1,
                    "uptime": "2h 30m"
                }
            }
        }
        
        await websocket_manager.broadcast(formatted_data)
        
        # Mesajın doğru formatla gönderildiğini kontrol et
        mock_websocket.send_json.assert_called_once_with(formatted_data)
        
        # Gönderilen mesajın yapısını kontrol et
        sent_message = mock_websocket.send_json.call_args[0][0]
        assert sent_message["type"] == "dashboard_update"
        assert "timestamp" in sent_message
        assert "data" in sent_message
        assert sent_message["data"]["current_price"]["gram_altin"] == 1932.50