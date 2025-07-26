"""
Sistem istatistikleri yönetimi
"""
from datetime import datetime
from typing import Dict, Any, Optional
from utils import timezone

class StatsManager:
    """Global sistem istatistikleri yönetimi"""
    
    def __init__(self):
        """Stats manager başlat"""
        self.stats = {
            "start_time": timezone.now(),
            "last_price_update": None,
            "total_signals": 0,
            "active_connections": 0,
            "errors_today": 0
        }
    
    def update(self, key: str, value: Any):
        """İstatistik güncelle"""
        self.stats[key] = value
    
    def get(self, key: str) -> Any:
        """İstatistik değeri al"""
        return self.stats.get(key)
    
    def get_all(self) -> Dict[str, Any]:
        """Tüm istatistikleri al"""
        return self.stats.copy()
    
    def increment(self, key: str, amount: int = 1):
        """Sayaç tipindeki istatistiği artır"""
        if key in self.stats and isinstance(self.stats[key], (int, float)):
            self.stats[key] += amount
    
    def reset_daily_stats(self):
        """Günlük istatistikleri sıfırla"""
        self.stats["errors_today"] = 0
    
    def get_uptime(self) -> str:
        """Çalışma süresini hesapla"""
        uptime = timezone.now() - self.stats["start_time"]
        return str(uptime).split('.')[0]