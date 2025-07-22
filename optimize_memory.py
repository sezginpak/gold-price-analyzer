#!/usr/bin/env python3
"""
Memory optimization ve I/O error çözümü
"""
import sys
sys.path.append('/root/gold-price-analyzer')

import sqlite3
from datetime import datetime, timedelta
import os
import gc
import resource

def optimize_database():
    """Veritabanını optimize et"""
    print("🔧 Veritabanı optimizasyonu başlıyor...")
    
    db_path = '/root/gold-price-analyzer/gold_prices.db'
    conn = sqlite3.connect(db_path)
    
    try:
        # WAL mode'u etkinleştir (Write-Ahead Logging)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        conn.execute("PRAGMA cache_size=10000")
        conn.execute("PRAGMA temp_store=MEMORY")
        
        # Eski price_data kayıtlarını sil (7 günden eski)
        cursor = conn.cursor()
        cursor.execute("""
            DELETE FROM price_data 
            WHERE timestamp < datetime('now', '-7 days')
        """)
        deleted_price = cursor.rowcount
        
        # Eski analysis_results kayıtlarını sil (3 günden eski)
        cursor.execute("""
            DELETE FROM analysis_results 
            WHERE timestamp < datetime('now', '-3 days')
        """)
        deleted_analysis = cursor.rowcount
        
        # İndeksleri yeniden oluştur
        cursor.execute("REINDEX")
        
        conn.commit()
        
        print(f"✅ {deleted_price} eski fiyat kaydı silindi")
        print(f"✅ {deleted_analysis} eski analiz kaydı silindi")
        
    finally:
        conn.close()
    
    # VACUUM ayrı connection'da çalıştır
    conn2 = sqlite3.connect(db_path)
    conn2.execute("VACUUM")
    conn2.close()
    print("✅ Veritabanı optimize edildi")

def set_memory_limits():
    """Python process memory limitlerini ayarla"""
    print("\n🧠 Memory limitleri ayarlanıyor...")
    
    # Max 256MB memory kullanımı
    max_memory = 256 * 1024 * 1024  # 256MB in bytes
    
    try:
        resource.setrlimit(resource.RLIMIT_AS, (max_memory, max_memory))
        print("✅ Memory limit: 256MB")
    except:
        print("⚠️ Memory limit ayarlanamadı")

def cleanup_logs():
    """Log dosyalarını temizle"""
    print("\n📝 Log temizliği yapılıyor...")
    
    log_dir = '/root/gold-price-analyzer'
    for file in os.listdir(log_dir):
        if file.endswith('.log'):
            file_path = os.path.join(log_dir, file)
            try:
                # 10MB'dan büyük log dosyalarını truncate et
                if os.path.getsize(file_path) > 10 * 1024 * 1024:
                    with open(file_path, 'w') as f:
                        f.write('')
                    print(f"✅ {file} temizlendi")
            except:
                pass

def check_disk_space():
    """Disk alanını kontrol et"""
    print("\n💾 Disk durumu:")
    stat = os.statvfs('/')
    
    # Bytes to GB
    total = (stat.f_blocks * stat.f_frsize) / (1024**3)
    free = (stat.f_bavail * stat.f_frsize) / (1024**3)
    used = total - free
    percent = (used / total) * 100
    
    print(f"   Toplam: {total:.1f} GB")
    print(f"   Kullanılan: {used:.1f} GB ({percent:.1f}%)")
    print(f"   Boş: {free:.1f} GB")
    
    if percent > 80:
        print("⚠️ UYARI: Disk %80'den fazla dolu!")

def fix_io_errors():
    """I/O error düzeltmeleri"""
    print("\n🔧 I/O optimizasyonları yapılıyor...")
    
    # SQLite config dosyası oluştur
    config = """
# SQLite performans ayarları
PRAGMA journal_mode = WAL;
PRAGMA synchronous = NORMAL;
PRAGMA cache_size = 10000;
PRAGMA temp_store = MEMORY;
PRAGMA mmap_size = 268435456;
"""
    
    with open('/root/gold-price-analyzer/sqlite_config.sql', 'w') as f:
        f.write(config)
    
    print("✅ SQLite config oluşturuldu")
    
    # Swap kullanımını azalt
    try:
        os.system("echo 10 > /proc/sys/vm/swappiness")
        print("✅ Swappiness 10 olarak ayarlandı")
    except:
        print("⚠️ Swappiness ayarlanamadı")

if __name__ == "__main__":
    print("=== Gold Analyzer Memory Optimization ===\n")
    
    # Optimizasyonları çalıştır
    check_disk_space()
    optimize_database()
    cleanup_logs()
    fix_io_errors()
    
    # Garbage collection
    gc.collect()
    
    print("\n✅ Optimizasyon tamamlandı!")
    print("🔄 Servisi yeniden başlatmanız önerilir: systemctl restart gold-analyzer")