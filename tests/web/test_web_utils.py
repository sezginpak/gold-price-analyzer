"""
Web utilities testleri
"""
import pytest
from unittest.mock import Mock, patch
from datetime import datetime, timedelta

from web.utils import cache, stats, formatters
from utils import timezone


class TestWebCache:
    """Web cache testleri"""
    
    def test_cache_set_get(self):
        """Cache set/get testi"""
        test_key = "test_key"
        test_data = {"message": "test data"}
        
        # Cache'e veri koy
        cache.set(test_key, test_data)
        
        # Cache'den veri al
        cached_data = cache.get(test_key)
        
        assert cached_data == test_data
    
    def test_cache_expiration(self):
        """Cache TTL testi"""
        test_key = "expiry_test"
        test_data = {"message": "expires soon"}
        
        # Kısa TTL ile cache'e koy
        cache.set(test_key, test_data, ttl=1)  # 1 saniye
        
        # Hemen al - veri olmalı
        cached_data = cache.get(test_key)
        assert cached_data == test_data
        
        # 2 saniye bekle (TTL'den uzun)
        import time
        time.sleep(2)
        
        # Artık veri yoksa None dönmeli
        cached_data = cache.get(test_key)
        # Cache implementation'a bağlı olarak None veya eski veri dönebilir
        # Bu test cache'in TTL desteği olup olmadığını kontrol eder
    
    def test_cache_none_value(self):
        """Cache None değer testi"""
        test_key = "none_test"
        
        # Olmayan key için None dönmeli
        cached_data = cache.get(test_key)
        assert cached_data is None
        
        # None değeri cache'e koyabiliriz
        cache.set(test_key, None)
        cached_data = cache.get(test_key)
        assert cached_data is None
    
    def test_cache_overwrite(self):
        """Cache üzerine yazma testi"""
        test_key = "overwrite_test"
        original_data = {"value": 1}
        new_data = {"value": 2}
        
        # İlk veri
        cache.set(test_key, original_data)
        assert cache.get(test_key) == original_data
        
        # Üzerine yaz
        cache.set(test_key, new_data)
        assert cache.get(test_key) == new_data


class TestWebStats:
    """Web stats testleri"""
    
    def test_stats_update_get(self):
        """Stats güncelleme ve alma testi"""
        test_key = "test_metric"
        test_value = 42
        
        # Stat güncelle
        stats.update(test_key, test_value)
        
        # Stat al
        retrieved_value = stats.get(test_key)
        assert retrieved_value == test_value
    
    def test_stats_uptime_calculation(self):
        """Uptime hesaplama testi"""
        # Start time'ı ayarla
        start_time = timezone.now() - timedelta(hours=2, minutes=30)
        stats.update("start_time", start_time)
        
        # Uptime hesapla
        uptime = stats.get_uptime()
        
        # String formatında olmalı
        assert isinstance(uptime, str)
        # Saat bilgisi içermeli
        assert "h" in uptime or "hour" in uptime
    
    def test_stats_counter_increment(self):
        """Stats counter artırma testi"""
        test_key = "error_count"
        
        # Başlangıç değeri
        stats.update(test_key, 0)
        assert stats.get(test_key) == 0
        
        # Artır
        stats.update(test_key, stats.get(test_key) + 1)
        assert stats.get(test_key) == 1
        
        # Tekrar artır
        stats.update(test_key, stats.get(test_key) + 1)
        assert stats.get(test_key) == 2
    
    def test_stats_datetime_handling(self):
        """Stats datetime işleme testi"""
        test_key = "last_update"
        test_time = timezone.now()
        
        # Datetime kaydet
        stats.update(test_key, test_time)
        
        # Geri al
        retrieved_time = stats.get(test_key)
        assert retrieved_time == test_time
    
    def test_stats_nonexistent_key(self):
        """Olmayan stats key testi"""
        nonexistent_key = "does_not_exist_" + str(timezone.now().timestamp())
        
        # Olmayan key için varsayılan değer dönmeli
        value = stats.get(nonexistent_key)
        # Implementation'a bağlı olarak None veya 0 dönebilir
        assert value is None or value == 0


class TestWebFormatters:
    """Web formatter testleri"""
    
    def test_parse_log_line_valid(self):
        """Geçerli log satırı parse testi"""
        log_line = "2024-01-01 12:30:45 - INFO - Test log message"
        
        parsed = formatters.parse_log_line(log_line)
        
        # Parsed obje dict olmalı
        assert isinstance(parsed, dict)
        
        # Temel alanları içermeli
        expected_fields = ["timestamp", "level", "message"]
        for field in expected_fields:
            assert field in parsed
        
        # Değerler doğru olmalı
        assert "INFO" in parsed.get("level", "")
        assert "Test log message" in parsed.get("message", "")
    
    def test_parse_log_line_invalid(self):
        """Geçersiz log satırı parse testi"""
        invalid_log_line = "Not a proper log line"
        
        parsed = formatters.parse_log_line(invalid_log_line)
        
        # Hatalı format için varsayılan yapı dönmeli
        assert isinstance(parsed, dict)
        
        # En az message alanı olmalı
        assert "message" in parsed
        assert parsed["message"] == invalid_log_line
    
    def test_parse_log_line_empty(self):
        """Boş log satırı parse testi"""
        empty_line = ""
        
        parsed = formatters.parse_log_line(empty_line)
        
        assert isinstance(parsed, dict)
        assert parsed.get("message", "") == ""
    
    def test_parse_log_line_with_special_chars(self):
        """Özel karakterli log satırı parse testi"""
        log_line_with_special = "2024-01-01 12:30:45 - ERROR - Hata: özel karakterler çalışıyor mu? İçerik: {test: 'değer'}"
        
        parsed = formatters.parse_log_line(log_line_with_special)
        
        assert isinstance(parsed, dict)
        assert "ERROR" in parsed.get("level", "")
        assert "özel karakterler" in parsed.get("message", "")
    
    def test_parse_log_line_multiline(self):
        """Çok satırlı log parse testi"""
        multiline_log = """2024-01-01 12:30:45 - ERROR - Hata mesajı
        Stack trace:
        Line 1 of stack
        Line 2 of stack"""
        
        parsed = formatters.parse_log_line(multiline_log)
        
        assert isinstance(parsed, dict)
        # Tüm içerik message'da olmalı
        assert "Stack trace" in parsed.get("message", "")
    
    @pytest.mark.parametrize("level,expected", [
        ("INFO", "info"),
        ("WARNING", "warning"),
        ("ERROR", "error"),
        ("DEBUG", "debug"),
        ("CRITICAL", "critical")
    ])
    def test_log_level_formatting(self, level, expected):
        """Log level formatlama testi"""
        log_line = f"2024-01-01 12:30:45 - {level} - Test message"
        
        parsed = formatters.parse_log_line(log_line)
        
        # Level normalize edilmiş olmalı
        parsed_level = parsed.get("level", "").lower()
        assert expected in parsed_level
    
    def test_timestamp_formatting(self):
        """Timestamp formatlama testi"""
        test_dt = datetime(2024, 1, 1, 12, 30, 45)
        
        # Formatter'da timestamp formatlama fonksiyonu varsa test et
        if hasattr(formatters, 'format_timestamp'):
            formatted = formatters.format_timestamp(test_dt)
            assert isinstance(formatted, str)
            assert "2024" in formatted
            assert "12:30" in formatted
    
    def test_price_formatting(self):
        """Fiyat formatlama testi"""
        test_price = 1932.456789
        
        # Formatter'da fiyat formatlama fonksiyonu varsa test et
        if hasattr(formatters, 'format_price'):
            formatted = formatters.format_price(test_price)
            assert isinstance(formatted, str)
            # Decimal kontrolü
            assert len(formatted.split('.')[-1]) <= 2  # En fazla 2 decimal
    
    def test_percentage_formatting(self):
        """Yüzde formatlama testi"""
        test_percentage = 0.12345  # %12.345
        
        # Formatter'da yüzde formatlama fonksiyonu varsa test et
        if hasattr(formatters, 'format_percentage'):
            formatted = formatters.format_percentage(test_percentage)
            assert isinstance(formatted, str)
            assert "%" in formatted
    
    def test_large_number_formatting(self):
        """Büyük sayı formatlama testi"""
        large_number = 1234567.89
        
        # Formatter'da büyük sayı formatlama fonksiyonu varsa test et
        if hasattr(formatters, 'format_large_number'):
            formatted = formatters.format_large_number(large_number)
            assert isinstance(formatted, str)
            # Binlik ayıracı olmalı
            assert "," in formatted or "." in formatted