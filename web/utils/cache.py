"""
Cache yönetimi için utility modülü
"""
import time
import sys
from typing import Any, Optional

class CacheManager:
    """Ultra optimized cache sistemi - Advanced TTL, LRU, compression ve memory management"""
    
    def __init__(self, default_ttl: int = 180, max_entries: int = 2000, enable_compression: bool = True):
        """
        Cache manager başlat - Performance oriented
        
        Args:
            default_ttl: Varsayılan cache süresi (saniye) - 3 dakika (optimized)
            max_entries: Maksimum cache entry sayısı - Increased for better performance
            enable_compression: Large objects için compression aktif et
        """
        self.cache = {}
        self.default_ttl = default_ttl
        self.max_entries = max_entries
        self.enable_compression = enable_compression
        self._hits = 0
        self._misses = 0
        self._last_cleanup = time.time()
        self._cleanup_interval = 300  # 5 dakikada bir cleanup
    
    def get(self, key: str) -> Optional[Any]:
        """Cache'den veri al - Ultra optimized with auto-cleanup"""
        current_time = time.time()
        
        # Periodic cleanup for better performance
        if current_time - self._last_cleanup > self._cleanup_interval:
            self._cleanup_expired()
            self._last_cleanup = current_time
        
        if key in self.cache:
            data, timestamp, ttl, access_count, is_compressed = self.cache[key]
            if current_time - timestamp < ttl:
                # Update access pattern for LRU
                self.cache[key] = (data, timestamp, ttl, access_count + 1, is_compressed)
                self._hits += 1
                
                # Decompress if needed
                if is_compressed and self.enable_compression:
                    import json, zlib
                    return json.loads(zlib.decompress(data).decode('utf-8'))
                return data
            else:
                del self.cache[key]
        
        self._misses += 1
        return None
    
    def set(self, key: str, data: Any, ttl: Optional[int] = None):
        """Cache'e veri kaydet - Smart compression and optimized storage"""
        cache_ttl = ttl if ttl is not None else self.default_ttl
        current_time = time.time()
        
        # Smart compression for large objects
        is_compressed = False
        stored_data = data
        
        if self.enable_compression:
            try:
                import json, zlib
                json_data = json.dumps(data)
                if len(json_data) > 1000:  # Compress if larger than 1KB
                    stored_data = zlib.compress(json_data.encode('utf-8'), level=6)
                    is_compressed = True
            except (TypeError, ValueError):
                pass  # Fallback to uncompressed
        
        # Efficient cache size management
        if len(self.cache) >= self.max_entries:
            self._cleanup_expired()
            
            # Intelligent eviction strategy
            if len(self.cache) >= self.max_entries:
                self._evict_lru()
        
        self.cache[key] = (stored_data, current_time, cache_ttl, 1, is_compressed)
    
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
        """Süresi dolmuş cache entry'leri temizle - Batch processing optimized"""
        current_time = time.time()
        expired_keys = []
        
        # Batch processing for better performance
        for key, (data, timestamp, ttl, access_count, is_compressed) in self.cache.items():
            if current_time - timestamp >= ttl:
                expired_keys.append(key)
                # Early break for large caches to avoid blocking
                if len(expired_keys) > 100:
                    break
        
        # Batch delete
        for key in expired_keys:
            self.cache.pop(key, None)
    
    def _evict_lru(self):
        """En az kullanılan entry'leri çıkar - Advanced LRU with time decay"""
        if not self.cache:
            return
        
        # Aggressive eviction for better performance - %25
        evict_count = max(1, len(self.cache) // 4)
        
        current_time = time.time()
        
        # Advanced LRU: Consider both access count and age
        def lru_score(item):
            key, (data, timestamp, ttl, access_count, is_compressed) = item
            age_factor = (current_time - timestamp) / 3600  # Hours since creation
            return access_count / max(1, age_factor)  # Access frequency adjusted by age
        
        # Sort by LRU score (lowest first)
        sorted_items = sorted(self.cache.items(), key=lru_score)
        
        # Batch eviction
        for i in range(evict_count):
            if i < len(sorted_items):
                key = sorted_items[i][0]
                self.cache.pop(key, None)
    
    def get_stats(self) -> dict:
        """Cache istatistiklerini döndür - Enhanced metrics"""
        total_requests = self._hits + self._misses
        hit_rate = (self._hits / total_requests * 100) if total_requests > 0 else 0
        
        # Advanced statistics
        current_time = time.time()
        expired_count = 0
        compressed_count = 0
        
        for key, (data, timestamp, ttl, access_count, is_compressed) in self.cache.items():
            if current_time - timestamp >= ttl:
                expired_count += 1
            if is_compressed:
                compressed_count += 1
        
        return {
            "size": len(self.cache),
            "max_entries": self.max_entries,
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": round(hit_rate, 2),
            "expired_entries": expired_count,
            "compressed_entries": compressed_count,
            "compression_ratio": round((compressed_count / len(self.cache) * 100), 2) if self.cache else 0,
            "memory_usage_bytes": self.get_memory_usage(),
            "efficiency_score": round(hit_rate * (len(self.cache) / self.max_entries), 2)
        }
    
    def get_memory_usage(self) -> int:
        """Cache'in memory kullanımını döndür (bytes)"""
        total_size = sys.getsizeof(self.cache)
        for key, value in self.cache.items():
            total_size += sys.getsizeof(key) + sys.getsizeof(value)
        return total_size