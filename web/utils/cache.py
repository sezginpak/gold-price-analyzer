"""
Cache yönetimi için utility modülü
"""
import time
import sys
from typing import Any, Optional

class CacheManager:
    """Gelişmiş cache sistemi - TTL, boyut limiti ve otomatik temizlik destekli"""
    
    def __init__(self, default_ttl: int = 300, max_entries: int = 1000):
        """
        Cache manager başlat
        
        Args:
            default_ttl: Varsayılan cache süresi (saniye) - 5 dakika
            max_entries: Maksimum cache entry sayısı
        """
        self.cache = {}
        self.default_ttl = default_ttl
        self.max_entries = max_entries
        self._hits = 0
        self._misses = 0
    
    def get(self, key: str) -> Optional[Any]:
        """Cache'den veri al"""
        if key in self.cache:
            data, timestamp, ttl, access_count = self.cache[key]
            if time.time() - timestamp < ttl:
                # Access count'u güncelle (LRU için)
                self.cache[key] = (data, timestamp, ttl, access_count + 1)
                self._hits += 1
                return data
            else:
                del self.cache[key]
        
        self._misses += 1
        return None
    
    def set(self, key: str, data: Any, ttl: Optional[int] = None):
        """Cache'e veri kaydet"""
        cache_ttl = ttl if ttl is not None else self.default_ttl
        current_time = time.time()
        
        # Cache boyutu kontrolü
        if len(self.cache) >= self.max_entries:
            self._cleanup_expired()
            
            # Hala doluysa, LRU ile temizle
            if len(self.cache) >= self.max_entries:
                self._evict_lru()
        
        self.cache[key] = (data, current_time, cache_ttl, 1)
    
    def clear(self, key: Optional[str] = None):
        """Cache'i temizle"""
        if key:
            self.cache.pop(key, None)
        else:
            self.cache.clear()
    
    def get_size(self) -> int:
        """Cache boyutunu döndür"""
        return len(self.cache)
    
    def _cleanup_expired(self):
        """Süresi dolmuş cache entry'leri temizle"""
        current_time = time.time()
        expired_keys = []
        
        for key, (data, timestamp, ttl, access_count) in self.cache.items():
            if current_time - timestamp >= ttl:
                expired_keys.append(key)
        
        for key in expired_keys:
            del self.cache[key]
    
    def _evict_lru(self):
        """En az kullanılan entry'leri çıkar (LRU eviction)"""
        if not self.cache:
            return
        
        # En az kullanılan %20'sini çıkar
        evict_count = max(1, len(self.cache) // 5)
        
        # Access count'a göre sırala
        sorted_items = sorted(
            self.cache.items(), 
            key=lambda x: x[1][3]  # access_count
        )
        
        for i in range(evict_count):
            key = sorted_items[i][0]
            del self.cache[key]
    
    def get_stats(self) -> dict:
        """Cache istatistiklerini döndür"""
        total_requests = self._hits + self._misses
        hit_rate = (self._hits / total_requests * 100) if total_requests > 0 else 0
        
        return {
            "size": len(self.cache),
            "max_entries": self.max_entries,
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": round(hit_rate, 2),
            "memory_usage_bytes": sys.getsizeof(self.cache)
        }
    
    def get_memory_usage(self) -> int:
        """Cache'in memory kullanımını döndür (bytes)"""
        total_size = sys.getsizeof(self.cache)
        for key, value in self.cache.items():
            total_size += sys.getsizeof(key) + sys.getsizeof(value)
        return total_size