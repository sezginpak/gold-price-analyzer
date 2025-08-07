#!/usr/bin/env python3
"""
Performans indexlerini ekleyen script
"""
import sqlite3
from pathlib import Path

def add_performance_indexes():
    """Kritik performans indexlerini ekle"""
    
    # Database path
    db_path = Path("gold_prices.db")
    
    if not db_path.exists():
        print(f"❌ Database dosyası bulunamadı: {db_path}")
        return False
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        print("🔍 Mevcut tablolar kontrol ediliyor...")
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        print(f"📋 Mevcut tablolar: {', '.join(tables)}")
        
        print("\n🔍 Mevcut indexler kontrol ediliyor...")
        
        # Mevcut indexleri kontrol et
        cursor.execute("SELECT name FROM sqlite_master WHERE type='index'")
        existing_indexes = {row[0] for row in cursor.fetchall()}
        print(f"📋 Mevcut index sayısı: {len(existing_indexes)}")
        
        # Eklenecek indexler - gerçek tablo isimleriyle
        indexes_to_add = [
            # Price_data tablosu için - en kritik
            ("idx_price_data_timestamp", "CREATE INDEX IF NOT EXISTS idx_price_data_timestamp ON price_data (timestamp DESC)"),
            ("idx_price_data_gram_timestamp", "CREATE INDEX IF NOT EXISTS idx_price_data_gram_timestamp ON price_data (gram_altin, timestamp DESC)"),
            
            # Hybrid analysis tablosu için
            ("idx_hybrid_analysis_timestamp", "CREATE INDEX IF NOT EXISTS idx_hybrid_analysis_timestamp ON hybrid_analysis (timestamp DESC)"),
            ("idx_hybrid_analysis_signal_timestamp", "CREATE INDEX IF NOT EXISTS idx_hybrid_analysis_signal_timestamp ON hybrid_analysis (signal, timestamp DESC)"),
            ("idx_hybrid_analysis_timeframe", "CREATE INDEX IF NOT EXISTS idx_hybrid_analysis_timeframe ON hybrid_analysis (timeframe, timestamp DESC)"),
            
            # Simulation positions tablosu için
            ("idx_sim_positions_status", "CREATE INDEX IF NOT EXISTS idx_sim_positions_status ON sim_positions (status)"),
            ("idx_sim_positions_exit_time", "CREATE INDEX IF NOT EXISTS idx_sim_positions_exit_time ON sim_positions (exit_time DESC)"),
            ("idx_sim_positions_entry_time", "CREATE INDEX IF NOT EXISTS idx_sim_positions_entry_time ON sim_positions (entry_time DESC)"),
            ("idx_sim_positions_status_exit", "CREATE INDEX IF NOT EXISTS idx_sim_positions_status_exit ON sim_positions (status, exit_time DESC)"),
            
            # Gram candles için
            ("idx_gram_candles_timestamp", "CREATE INDEX IF NOT EXISTS idx_gram_candles_timestamp ON gram_candles (timestamp DESC)"),
        ]
        
        added_count = 0
        
        for index_name, create_sql in indexes_to_add:
            if index_name not in existing_indexes:
                print(f"➕ Adding index: {index_name}")
                cursor.execute(create_sql)
                added_count += 1
            else:
                print(f"✅ Index already exists: {index_name}")
        
        if added_count > 0:
            conn.commit()
            print(f"✅ {added_count} yeni index eklendi!")
        else:
            print("✅ Tüm indexler zaten mevcut")
        
        # Index istatistiklerini göster
        cursor.execute("SELECT name FROM sqlite_master WHERE type='index' AND name NOT LIKE 'sqlite_%'")
        all_indexes = [row[0] for row in cursor.fetchall()]
        print(f"📊 Toplam index sayısı: {len(all_indexes)}")
        
        # Analyze çalıştır (index istatistiklerini güncelle)
        print("📈 ANALYZE komutu çalıştırılıyor...")
        cursor.execute("ANALYZE")
        conn.commit()
        
        return True
        
    except Exception as e:
        print(f"❌ Index ekleme hatası: {e}")
        return False
        
    finally:
        if 'conn' in locals():
            conn.close()

def check_database_size():
    """Veritabanı boyutunu kontrol et"""
    db_path = Path("gold_prices.db")
    if db_path.exists():
        size_mb = db_path.stat().st_size / (1024 * 1024)
        print(f"💾 Database boyutu: {size_mb:.2f} MB")
    else:
        print("❌ Database dosyası bulunamadı")

if __name__ == "__main__":
    print("🚀 Performans indexleri ekleniyor...\n")
    
    check_database_size()
    print()
    
    success = add_performance_indexes()
    
    print()
    check_database_size()
    
    if success:
        print("\n✅ Index ekleme tamamlandı! Sorgu performansı artmalı.")
        print("\n💡 Öneriler:")
        print("- VACUUM komutu ile database'i optimize edebilirsiniz")
        print("- Yüksek volume'da PRAGMA journal_mode=WAL kullanın")
        print("- PRAGMA cache_size artırılabilir")
    else:
        print("\n❌ Index ekleme başarısız!")