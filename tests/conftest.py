"""
Pytest global configuration ve fixtures
"""
import pytest
import asyncio
from unittest.mock import Mock, MagicMock
import os
import sys

# Proje root'unu Python path'e ekle
project_root = os.path.dirname(os.path.dirname(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)


@pytest.fixture(scope="session")
def event_loop():
    """Oturum için event loop oluştur"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def mock_storage():
    """Mock SQLite storage"""
    mock = Mock()
    
    # Temel methodları mock'la
    mock.get_latest_price.return_value = None
    mock.get_latest_prices.return_value = []
    mock.get_statistics.return_value = {
        "total_records": 0,
        "oldest_record": None,
        "newest_record": None,
        "average_price": 0
    }
    mock.get_connection.return_value = Mock()
    mock.generate_candles.return_value = []
    mock.generate_gram_candles.return_value = []
    mock.get_hybrid_analysis_history.return_value = []
    
    return mock


@pytest.fixture
def mock_websocket():
    """Mock WebSocket"""
    mock = MagicMock()
    mock.accept = MagicMock()
    mock.send_json = MagicMock()
    mock.receive_text = MagicMock()
    mock.close = MagicMock()
    return mock


@pytest.fixture
def mock_logger():
    """Mock logger"""
    mock = Mock()
    mock.info = Mock()
    mock.error = Mock()
    mock.warning = Mock()
    mock.debug = Mock()
    return mock


@pytest.fixture
def mock_timezone():
    """Mock timezone utilities"""
    from datetime import datetime, timezone as dt_timezone
    
    mock = Mock()
    mock.now.return_value = datetime.now(dt_timezone.utc)
    mock.get_day_start.return_value = datetime.now(dt_timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    mock.format_for_display.return_value = "01.01.2024 12:00"
    
    return mock


@pytest.fixture
def sample_price_data():
    """Örnek fiyat verisi"""
    from datetime import datetime, timezone
    from models.price_data import PriceData
    
    return PriceData(
        timestamp=datetime.now(timezone.utc),
        ons_usd=2000.0,
        usd_try=30.0,
        ons_try=60000.0,
        gram_altin=1932.0
    )


@pytest.fixture
def sample_candle_data():
    """Örnek mum verisi"""
    from datetime import datetime, timezone
    from models.price_data import Candle
    
    return Candle(
        timestamp=datetime.now(timezone.utc),
        open=1930.0,
        high=1940.0,
        low=1925.0,
        close=1935.0
    )


@pytest.fixture
def sample_analysis_data():
    """Örnek analiz verisi"""
    return {
        "timestamp": "2024-01-01T12:00:00",
        "timeframe": "15m",
        "signal": "BUY",
        "confidence": 85.0,
        "gram_price": 1932.0,
        "stop_loss": 1920.0,
        "take_profit": 1950.0,
        "indicators": {
            "rsi": 65.0,
            "macd_signal": "BULLISH",
            "bb_position": "MIDDLE"
        }
    }


@pytest.fixture(autouse=True)
def setup_test_environment(monkeypatch):
    """Her test için test ortamını hazırla"""
    # Test ortamı için gerekli environment variable'ları ayarla
    monkeypatch.setenv("TESTING", "1")
    monkeypatch.setenv("LOG_LEVEL", "ERROR")  # Test sırasında log gürültüsünü azalt
    
    # Database path'ini test database'e yönlendir
    monkeypatch.setenv("DATABASE_PATH", ":memory:")


@pytest.fixture
def temp_log_file(tmp_path):
    """Geçici log dosyası"""
    log_file = tmp_path / "test.log"
    log_file.write_text("2024-01-01 12:00:00 - INFO - Test log message\\n")
    return str(log_file)


# Pytest configuration
def pytest_configure(config):
    """Pytest konfigürasyonu"""
    # Custom marker'ları tanımla
    config.addinivalue_line(
        "markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')"
    )
    config.addinivalue_line(
        "markers", "integration: marks tests as integration tests"
    )
    config.addinivalue_line(
        "markers", "unit: marks tests as unit tests"
    )


def pytest_collection_modifyitems(config, items):
    """Test toplama sonrası modifikasyonlar"""
    for item in items:
        # AsyncIO testlerini işaretle
        if "asyncio" in item.keywords:
            item.add_marker(pytest.mark.asyncio)
        
        # Yavaş testleri işaretle
        if "test_performance" in item.name or "test_load" in item.name:
            item.add_marker(pytest.mark.slow)


# Test sırasında warning'leri filtrele
import warnings

def pytest_runtest_setup(item):
    """Her test öncesi setup"""
    # DeprecationWarning'leri görmezden gel
    warnings.filterwarnings("ignore", category=DeprecationWarning)
    warnings.filterwarnings("ignore", category=PendingDeprecationWarning)


# Async test helper'ları
class AsyncTestHelper:
    """Async test yardımcı sınıfı"""
    
    @staticmethod
    async def wait_for_condition(condition_func, timeout=5.0, interval=0.1):
        """Bir koşulun gerçekleşmesini bekle"""
        import asyncio
        
        end_time = asyncio.get_event_loop().time() + timeout
        
        while asyncio.get_event_loop().time() < end_time:
            if await condition_func():
                return True
            await asyncio.sleep(interval)
        
        return False
    
    @staticmethod
    async def collect_websocket_messages(websocket, count=1, timeout=5.0):
        """WebSocket mesajlarını topla"""
        import asyncio
        
        messages = []
        
        async def collect():
            for _ in range(count):
                try:
                    message = await asyncio.wait_for(websocket.receive_json(), timeout=1.0)
                    messages.append(message)
                except asyncio.TimeoutError:
                    break
        
        await asyncio.wait_for(collect(), timeout=timeout)
        return messages


@pytest.fixture
def async_helper():
    """Async test helper fixture"""
    return AsyncTestHelper()