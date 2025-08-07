"""
Dashboard API endpoint testleri
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from fastapi.testclient import TestClient
import json
from datetime import datetime, timedelta

from web_server import app
from utils import timezone
from models.price_data import PriceData


class TestAPIEndpoints:
    """API endpoint testleri"""
    
    @pytest.fixture
    def client(self):
        """Test client'i oluştur"""
        return TestClient(app)
    
    @pytest.fixture
    def mock_storage(self):
        """Mock storage nesnesi oluştur"""
        mock = Mock()
        mock.get_statistics.return_value = {
            "total_records": 1000,
            "oldest_record": "2024-01-01T00:00:00",
            "newest_record": "2024-01-02T00:00:00",
            "average_price": 2500.0
        }
        
        # Mock price data
        mock_price = PriceData(
            timestamp=timezone.now(),
            ons_usd=2000.0,
            usd_try=30.0,
            ons_try=60000.0,
            gram_altin=1932.0
        )
        mock.get_latest_price.return_value = mock_price
        mock.get_latest_prices.return_value = [mock_price]
        
        return mock
    
    @pytest.fixture
    def mock_stats(self):
        """Mock stats nesnesi oluştur"""
        mock = Mock()
        mock.get_uptime.return_value = "2h 30m"
        mock.get.return_value = 0
        return mock
    
    def test_stats_endpoint(self, client, mock_storage, mock_stats):
        """İstatistik endpoint'i testi"""
        # Mock veritabanı connection'ı hazırla
        mock_cursor = Mock()
        mock_cursor.fetchone.return_value = (0,)  # Today signals count
        
        mock_conn = Mock()
        mock_conn.cursor.return_value = mock_cursor
        mock_conn.__enter__ = Mock(return_value=mock_conn)
        mock_conn.__exit__ = Mock(return_value=None)
        
        mock_storage.get_connection.return_value = mock_conn
        
        with patch('web.routes.api.storage', mock_storage), \
             patch('web.routes.api.stats', mock_stats), \
             patch('web.routes.api.cache.get', return_value=None), \
             patch('web.routes.api.cache.set'), \
             patch('utils.timezone.get_day_start', return_value=timezone.now()):
            
            response = client.get("/api/stats")
            assert response.status_code == 200
            
            data = response.json()
            assert "system" in data
            assert "database" in data
            assert "signals" in data
            assert data["database"]["total_records"] == 1000
    
    def test_current_price_endpoint(self, client, mock_storage):
        """Anlık fiyat endpoint'i testi"""
        with patch('web.routes.api.storage', mock_storage):
            response = client.get("/api/prices/current")
            assert response.status_code == 200
            
            data = response.json()
            assert "gram_altin" in data
            assert "ons_usd" in data
            assert "usd_try" in data
            assert "timestamp" in data
            assert data["gram_altin"] == 1932.0
    
    def test_current_price_no_data(self, client):
        """Fiyat verisi yoksa hata testi"""
        mock_storage = Mock()
        mock_storage.get_latest_price.return_value = None
        
        with patch('web.routes.api.storage', mock_storage):
            response = client.get("/api/prices/current")
            assert response.status_code == 200
            
            data = response.json()
            assert "error" in data
            assert data["error"] == "No price data available"
    
    def test_latest_prices_endpoint(self, client, mock_storage):
        """Son fiyatlar endpoint'i testi"""
        # 30 dakikalık mock veriler oluştur
        now = timezone.now()
        mock_prices = []
        for i in range(10):
            price = PriceData(
                timestamp=now - timedelta(minutes=i*3),
                ons_usd=2000.0 + i,
                usd_try=30.0,
                ons_try=60000.0 + i*100,
                gram_altin=1932.0 + i
            )
            mock_prices.append(price)
        
        mock_storage.get_latest_prices.return_value = mock_prices
        
        with patch('web.routes.api.storage', mock_storage):
            response = client.get("/api/prices/latest")
            assert response.status_code == 200
            
            data = response.json()
            assert "prices" in data
            assert len(data["prices"]) == 10
            
            # İlk fiyatın doğruluğunu kontrol et
            first_price = data["prices"][0]
            assert "timestamp" in first_price
            assert "gram_altin" in first_price
            assert first_price["gram_altin"] == 1932.0
    
    def test_daily_range_endpoint(self, client):
        """Günlük fiyat aralığı endpoint'i testi"""
        mock_storage = Mock()
        
        # Mock veritabanı bağlantısı
        mock_cursor = Mock()
        mock_cursor.fetchone.return_value = (1900.0, 1950.0, 1980.0, 2020.0, 29.5, 30.5)
        
        mock_conn = Mock()
        mock_conn.cursor.return_value = mock_cursor
        mock_conn.__enter__ = Mock(return_value=mock_conn)
        mock_conn.__exit__ = Mock(return_value=None)
        
        mock_storage.get_connection.return_value = mock_conn
        
        with patch('web.routes.api.storage', mock_storage), \
             patch('web.routes.api.cache.get', return_value=None), \
             patch('web.routes.api.cache.set'), \
             patch('utils.timezone.now', return_value=timezone.now()):
            
            response = client.get("/api/prices/daily-range")
            assert response.status_code == 200
            
            data = response.json()
            assert "gram_altin" in data
            assert "ons_usd" in data
            assert "usd_try" in data
            assert data["gram_altin"]["low"] == 1900.0
            assert data["gram_altin"]["high"] == 1950.0
    
    def test_recent_signals_endpoint(self, client):
        """Son sinyaller endpoint'i testi"""
        mock_storage = Mock()
        
        # Mock veritabanı bağlantısı
        mock_cursor = Mock()
        mock_signals_data = [
            (timezone.now().isoformat(), "15m", "BUY", 85.5, 1932.0, 1920.0, 1950.0, 100.0, 2.5),
            (timezone.now().isoformat(), "1h", "SELL", 78.2, 1935.0, 1945.0, 1925.0, 150.0, 2.0)
        ]
        mock_cursor.fetchall.return_value = mock_signals_data
        
        mock_conn = Mock()
        mock_conn.cursor.return_value = mock_cursor
        mock_conn.__enter__ = Mock(return_value=mock_conn)
        mock_conn.__exit__ = Mock(return_value=None)
        
        mock_storage.get_connection.return_value = mock_conn
        
        with patch('web.routes.api.storage', mock_storage), \
             patch('web.routes.api.cache.get', return_value=None), \
             patch('web.routes.api.cache.set'), \
             patch('utils.timezone.now', return_value=timezone.now()):
            
            response = client.get("/api/signals/recent")
            assert response.status_code == 200
            
            data = response.json()
            assert data["status"] == "success"
            assert "signals" in data
            assert data["count"] == 2
            assert data["signals"][0]["signal"] == "BUY"
            assert data["signals"][0]["confidence"] == 85.5
    
    def test_candles_endpoint(self, client, mock_storage):
        """Mum verileri endpoint'i testi"""
        from models.price_data import Candle
        
        # Mock candle verisi
        mock_candles = [
            Candle(
                timestamp=timezone.now(),
                open=1930.0,
                high=1940.0,
                low=1925.0,
                close=1935.0
            )
        ]
        mock_storage.generate_candles.return_value = mock_candles
        
        with patch('web.routes.api.storage', mock_storage):
            response = client.get("/api/candles/15m")
            assert response.status_code == 200
            
            data = response.json()
            assert "candles" in data
            assert len(data["candles"]) == 1
            
            candle = data["candles"][0]
            assert candle["open"] == 1930.0
            assert candle["high"] == 1940.0
            assert candle["low"] == 1925.0
            assert candle["close"] == 1935.0
    
    def test_gram_candles_endpoint(self, client, mock_storage):
        """Gram altın mum verileri endpoint'i testi"""
        from models.price_data import Candle
        
        # Mock candle verisi
        mock_candles = [
            Candle(
                timestamp=timezone.now(),
                open=1930.0,
                high=1940.0,
                low=1925.0,
                close=1935.0
            )
        ]
        mock_storage.generate_gram_candles.return_value = mock_candles
        
        with patch('web.routes.api.storage', mock_storage), \
             patch('web.routes.api.cache.get', return_value=None), \
             patch('web.routes.api.cache.set'):
            
            response = client.get("/api/gram-candles/1h")
            assert response.status_code == 200
            
            data = response.json()
            assert "candles" in data
            assert len(data["candles"]) == 1
    
    def test_logs_recent_endpoint(self, client):
        """Son log kayıtları endpoint'i testi"""
        mock_log_content = "2024-01-01 12:00:00 - INFO - Test log mesajı\n"
        
        with patch('builtins.open', mock_open(read_data=mock_log_content)), \
             patch('os.path.exists', return_value=True):
            
            response = client.get("/api/logs/recent?category=analyzer&lines=10")
            assert response.status_code == 200
            
            data = response.json()
            assert "analyzer" in data
            assert len(data["analyzer"]) == 1
    
    def test_performance_metrics_endpoint(self, client):
        """Performans metrikleri endpoint'i testi"""
        mock_storage = Mock()
        
        # Mock veritabanı sonuçları
        month_stats = (10, 6, 4, 250.0, 50.0, 25.0, 100.0, -50.0)
        week_stats = (5, 3, 125.0)
        daily_stats = (2, 1, 75.0)
        timeframe_stats = [("15m", 3, 2, 100.0, 33.33), ("1h", 4, 2, 50.0, 12.5)]
        open_positions = (3, 300.0)
        
        mock_cursor = Mock()
        mock_cursor.fetchone.side_effect = [month_stats, week_stats, daily_stats, open_positions]
        mock_cursor.fetchall.return_value = timeframe_stats
        
        mock_conn = Mock()
        mock_conn.cursor.return_value = mock_cursor
        mock_conn.__enter__ = Mock(return_value=mock_conn)
        mock_conn.__exit__ = Mock(return_value=None)
        
        mock_storage.get_connection.return_value = mock_conn
        mock_storage.get_latest_price.return_value = Mock(gram_altin=1932.0)
        
        with patch('web.routes.api.storage', mock_storage), \
             patch('web.routes.api.cache.get', return_value=None), \
             patch('web.routes.api.cache.set'):
            
            response = client.get("/api/performance/metrics")
            assert response.status_code == 200
            
            data = response.json()
            assert "overview" in data
            assert "performance" in data
            assert "timeframes" in data
            assert data["overview"]["current_price"] == 1932.0
            assert data["performance"]["monthly"]["trades"] == 10
            assert data["performance"]["monthly"]["win_rate"] == 60.0
    
    def test_market_overview_endpoint(self, client, mock_storage):
        """Piyasa genel görünümü endpoint'i testi"""
        # Şu anki ve eski fiyat verileri
        current_price = PriceData(
            timestamp=timezone.now(),
            ons_usd=2000.0,
            usd_try=30.0,
            ons_try=60000.0,
            gram_altin=1932.0
        )
        
        mock_cursor = Mock()
        mock_cursor.fetchone.return_value = (1925.0, 1990.0, 29.8)
        
        mock_conn = Mock()
        mock_conn.cursor.return_value = mock_cursor
        mock_conn.__enter__ = Mock(return_value=mock_conn)
        mock_conn.__exit__ = Mock(return_value=None)
        
        mock_storage.get_latest_price.return_value = current_price
        mock_storage.get_connection.return_value = mock_conn
        mock_storage.get_hybrid_analysis_history.return_value = [
            {
                "signal": "BUY",
                "confidence": 85.0,
                "global_trend": {"direction": "UP"},
                "currency_risk": {"level": "MEDIUM"}
            }
        ]
        
        with patch('web.routes.api.storage', mock_storage):
            response = client.get("/api/market/overview")
            assert response.status_code == 200
            
            data = response.json()
            assert "prices" in data
            assert "analysis" in data
            assert data["analysis"]["signal"] == "BUY"
            assert data["analysis"]["confidence"] == 85.0


def mock_open(read_data=""):
    """Mock open fonksiyonu"""
    from unittest.mock import mock_open as original_mock_open
    return original_mock_open(read_data=read_data)