"""
Gelişmiş log yönetim sistemi
- Otomatik log rotation
- Eski logları sıkıştırma
- Disk alanı kontrolü
- Log istatistikleri
"""
import os
import gzip
import shutil
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional
import asyncio

logger = logging.getLogger(__name__)


class LogManager:
    """Log dosyalarını yöneten sınıf"""
    
    def __init__(self, 
                 log_dir: str = "logs",
                 max_total_size_mb: int = 100,  # Toplam log boyutu limiti (MB)
                 max_age_days: int = 7,  # Maksimum log yaşı (gün)
                 compress_after_days: int = 1,  # Kaç gün sonra sıkıştırılacak
                 check_interval_minutes: int = 60):  # Kontrol sıklığı
        """
        Args:
            log_dir: Log dizini
            max_total_size_mb: Maksimum toplam log boyutu (MB)
            max_age_days: Maksimum log yaşı (gün)
            compress_after_days: Sıkıştırma için bekleme süresi (gün)
            check_interval_minutes: Kontrol sıklığı (dakika)
        """
        self.log_dir = Path(log_dir)
        self.max_total_size_bytes = max_total_size_mb * 1024 * 1024
        self.max_age_days = max_age_days
        self.compress_after_days = compress_after_days
        self.check_interval = check_interval_minutes * 60
        self.running = False
        
        # Log dizini yoksa oluştur
        self.log_dir.mkdir(exist_ok=True)
    
    async def start(self):
        """Log yönetimini başlat"""
        self.running = True
        logger.info(f"Log manager started - Max size: {self.max_total_size_bytes/1024/1024:.1f}MB, Max age: {self.max_age_days} days")
        
        while self.running:
            try:
                await self.cleanup_logs()
                await asyncio.sleep(self.check_interval)
            except Exception as e:
                logger.error(f"Error in log manager: {e}")
                await asyncio.sleep(60)  # Hata durumunda 1 dakika bekle
    
    def stop(self):
        """Log yönetimini durdur"""
        self.running = False
        logger.info("Log manager stopped")
    
    async def cleanup_logs(self):
        """Log temizleme işlemi"""
        try:
            # 1. Eski logları sıkıştır
            await self._compress_old_logs()
            
            # 2. Çok eski logları sil
            await self._delete_old_logs()
            
            # 3. Toplam boyut kontrolü
            await self._check_total_size()
            
            # 4. İstatistikleri logla
            stats = self.get_log_statistics()
            logger.info(f"Log cleanup completed - {stats}")
            
        except Exception as e:
            logger.error(f"Error during log cleanup: {e}")
    
    async def _compress_old_logs(self):
        """Eski log dosyalarını sıkıştır"""
        cutoff_date = datetime.now() - timedelta(days=self.compress_after_days)
        
        for log_file in self.log_dir.glob("*.log*"):
            # Zaten sıkıştırılmış dosyaları atla
            if log_file.suffix == '.gz':
                continue
            
            # Dosya yaşını kontrol et
            file_time = datetime.fromtimestamp(log_file.stat().st_mtime)
            if file_time < cutoff_date:
                # Sıkıştır
                gz_file = log_file.with_suffix(log_file.suffix + '.gz')
                
                try:
                    with open(log_file, 'rb') as f_in:
                        with gzip.open(gz_file, 'wb') as f_out:
                            shutil.copyfileobj(f_in, f_out)
                    
                    # Orijinal dosyayı sil
                    log_file.unlink()
                    logger.debug(f"Compressed log file: {log_file.name} -> {gz_file.name}")
                    
                except Exception as e:
                    logger.error(f"Failed to compress {log_file}: {e}")
    
    async def _delete_old_logs(self):
        """Çok eski log dosyalarını sil"""
        cutoff_date = datetime.now() - timedelta(days=self.max_age_days)
        
        for log_file in self.log_dir.glob("*"):
            if log_file.is_file():
                file_time = datetime.fromtimestamp(log_file.stat().st_mtime)
                if file_time < cutoff_date:
                    try:
                        log_file.unlink()
                        logger.info(f"Deleted old log file: {log_file.name}")
                    except Exception as e:
                        logger.error(f"Failed to delete {log_file}: {e}")
    
    async def _check_total_size(self):
        """Toplam log boyutunu kontrol et ve gerekirse temizle"""
        total_size = 0
        files_by_date = []
        
        # Tüm dosyaları topla ve boyutlarını hesapla
        for log_file in self.log_dir.glob("*"):
            if log_file.is_file():
                size = log_file.stat().st_size
                mtime = log_file.stat().st_mtime
                total_size += size
                files_by_date.append((mtime, log_file, size))
        
        # Boyut limitini aşıyorsa
        if total_size > self.max_total_size_bytes:
            logger.warning(f"Total log size ({total_size/1024/1024:.1f}MB) exceeds limit ({self.max_total_size_bytes/1024/1024:.1f}MB)")
            
            # En eski dosyalardan başlayarak sil
            files_by_date.sort()  # En eski önce
            
            for mtime, file_path, size in files_by_date:
                if total_size <= self.max_total_size_bytes:
                    break
                
                try:
                    file_path.unlink()
                    total_size -= size
                    logger.info(f"Deleted {file_path.name} to free up space ({size/1024:.1f}KB)")
                except Exception as e:
                    logger.error(f"Failed to delete {file_path}: {e}")
    
    def get_log_statistics(self) -> Dict[str, any]:
        """Log istatistiklerini döndür"""
        stats = {
            "total_files": 0,
            "total_size_mb": 0,
            "compressed_files": 0,
            "uncompressed_files": 0,
            "oldest_file": None,
            "newest_file": None,
            "by_type": {}
        }
        
        oldest_time = float('inf')
        newest_time = 0
        
        for log_file in self.log_dir.glob("*"):
            if log_file.is_file():
                stats["total_files"] += 1
                size = log_file.stat().st_size
                stats["total_size_mb"] += size / 1024 / 1024
                
                mtime = log_file.stat().st_mtime
                if mtime < oldest_time:
                    oldest_time = mtime
                    stats["oldest_file"] = log_file.name
                if mtime > newest_time:
                    newest_time = mtime
                    stats["newest_file"] = log_file.name
                
                # Dosya tipine göre sayım
                if log_file.suffix == '.gz':
                    stats["compressed_files"] += 1
                else:
                    stats["uncompressed_files"] += 1
                
                # Log tipine göre grupla
                if 'error' in log_file.name:
                    log_type = 'error'
                elif 'critical' in log_file.name:
                    log_type = 'critical'
                else:
                    log_type = 'general'
                
                if log_type not in stats["by_type"]:
                    stats["by_type"][log_type] = {"count": 0, "size_mb": 0}
                
                stats["by_type"][log_type]["count"] += 1
                stats["by_type"][log_type]["size_mb"] += size / 1024 / 1024
        
        # Yuvarlama
        stats["total_size_mb"] = round(stats["total_size_mb"], 2)
        for log_type in stats["by_type"]:
            stats["by_type"][log_type]["size_mb"] = round(stats["by_type"][log_type]["size_mb"], 2)
        
        return stats
    
    def get_recent_errors(self, count: int = 10) -> List[str]:
        """Son hataları getir"""
        errors = []
        error_files = sorted(
            self.log_dir.glob("*error*.log"),
            key=lambda f: f.stat().st_mtime,
            reverse=True
        )
        
        for error_file in error_files[:2]:  # Son 2 error dosyasına bak
            try:
                with open(error_file, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                    # Son hatalar
                    for line in reversed(lines):
                        if 'ERROR' in line or 'CRITICAL' in line:
                            errors.append(line.strip())
                            if len(errors) >= count:
                                return errors
            except Exception as e:
                logger.error(f"Failed to read error file {error_file}: {e}")
        
        return errors