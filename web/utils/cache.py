"""
Cache yönetimi için utility modülü
"""
import time
from typing import Any, Optional

class CacheManager:
    """Basit cache sistemi - TTL destekli"""
    
    def __init__(self, default_ttl: int = 30):
        """
        Cache manager başlat
        
        Args:
            default_ttl: Varsayılan cache süresi (saniye)
        """
        self.cache = {}
        self.default_ttl = default_ttl
    
    def get(self, key: str) -> Optional[Any]:
        """Cache'den veri al"""
        if key in self.cache:
            data, timestamp = self.cache[key]
            if time.time() - timestamp < self.default_ttl:
                return data
            else:
                del self.cache[key]
        return None
    
    def set(self, key: str, data: Any, ttl: Optional[int] = None):
        """Cache'e veri kaydet"""
        cache_ttl = ttl if ttl is not None else self.default_ttl
        self.cache[key] = (data, time.time())
    
    def clear(self, key: Optional[str] = None):
        """Cache'i temizle"""
        if key:
            self.cache.pop(key, None)
        else:
            self.cache.clear()
    
    def get_size(self) -> int:
        """Cache boyutunu döndür"""
        return len(self.cache)