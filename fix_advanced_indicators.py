#!/usr/bin/env python3
"""
Advanced indicators (CCI, MFI, Pattern) sorununu düzelt
"""
import sys
sys.path.append('/root/gold-price-analyzer')

from storage.sqlite_storage import SQLiteStorage
from strategies.hybrid_strategy import HybridStrategy
from datetime import datetime, timedelta
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def check_data():
    """Veritabanındaki veriyi kontrol et"""
    storage = SQLiteStorage()
    
    # Gram altın verisi var mı?
    with storage.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM price_data WHERE gram_altin IS NOT NULL")
        gram_count = cursor.fetchone()[0]
        print(f"✓ Gram altın kayıt sayısı: {gram_count}")
        
        # Son kayıtları göster
        cursor.execute("""
            SELECT timestamp, gram_altin, ons_usd, usd_try 
            FROM price_data 
            WHERE gram_altin IS NOT NULL 
            ORDER BY timestamp DESC 
            LIMIT 5
        """)
        print("\nSon 5 kayıt:")
        for row in cursor.fetchall():
            print(f"  {row[0]}: {row[1]:.2f} TRY (ONS: ${row[2]:.2f}, USD/TRY: {row[3]:.2f})")
    
    # Candle verisi oluşturuluyor mu?
    for interval in [15, 60, 240]:
        candles = storage.generate_candles(interval, limit=30)
        print(f"\n{interval} dakika candle sayısı: {len(candles)}")
        if candles:
            c = candles[-1]
            print(f"  Son candle: {c.timestamp} - O:{c.open:.2f} H:{c.high:.2f} L:{c.low:.2f} C:{c.close:.2f}")
            print(f"  Volume: {getattr(c, 'volume', None)}")

def test_indicators():
    """Göstergeleri test et"""
    storage = SQLiteStorage()
    strategy = HybridStrategy()
    
    # 15 dakikalık candle'ları al
    candles = storage.generate_candles(15, limit=50)
    print(f"\n15m candle sayısı: {len(candles)}")
    
    if len(candles) < 30:
        print("❌ Yeterli candle verisi yok!")
        return
    
    # Advanced indicators test
    result = strategy._analyze_advanced_indicators(candles)
    print("\nAdvanced Indicators Sonucu:")
    print(f"CCI: {result['cci']}")
    print(f"MFI: {result['mfi']}")
    
    # Pattern test
    pattern_result = strategy._analyze_patterns(candles)
    print(f"\nPattern Analizi: {pattern_result}")
    
    # Son hybrid analizi kontrol et
    with storage.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT timestamp, advanced_indicators, pattern_analysis 
            FROM hybrid_analysis 
            ORDER BY id DESC 
            LIMIT 5
        """)
        print("\nSon 5 hybrid analiz:")
        for row in cursor.fetchall():
            print(f"  {row[0]}: Adv.Ind={row[1]}, Pattern={row[2]}")

def fix_generate_candles():
    """generate_candles metodunu düzelt"""
    print("\n\n=== generate_candles Düzeltmesi ===")
    
    # Mevcut kodu oku
    with open('/root/gold-price-analyzer/storage/sqlite_storage.py', 'r') as f:
        content = f.read()
    
    # gram_altin yerine gram price_data kullan
    if 'WHERE gram_altin IS NOT NULL' in content:
        print("✓ generate_candles gram_altin filtresi bulundu, düzeltiliyor...")
        
        # Backup al
        import shutil
        shutil.copy('/root/gold-price-analyzer/storage/sqlite_storage.py', 
                   '/root/gold-price-analyzer/storage/sqlite_storage.py.backup')
        
        # Düzelt - sadece gram_altin kontrolünü kaldır, tüm price_data'yı kullan
        new_content = content.replace(
            'WHERE gram_altin IS NOT NULL',
            'WHERE 1=1'
        )
        
        with open('/root/gold-price-analyzer/storage/sqlite_storage.py', 'w') as f:
            f.write(new_content)
        
        print("✓ generate_candles düzeltildi!")
    else:
        print("⚠️ generate_candles'da gram_altin filtresi bulunamadı")

if __name__ == "__main__":
    print("=== Advanced Indicators Sorun Tespiti ===\n")
    
    # Veri kontrolü
    check_data()
    
    # Gösterge testi
    test_indicators()
    
    # Sorun varsa düzelt
    response = input("\ngenerate_candles metodunu düzeltmek ister misiniz? (y/n): ")
    if response.lower() == 'y':
        fix_generate_candles()
        print("\nDüzeltmeden sonra tekrar test ediliyor...")
        test_indicators()