#!/usr/bin/env python3
"""
Database şemasını güncelleyen script
Advanced indicators ve pattern analysis kolonlarını ekler
"""

import sqlite3
import sys
import os

# Proje root'una path ekle
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def update_database_schema():
    """Database şemasını güncelle"""
    
    db_path = "gold_prices.db"
    
    if not os.path.exists(db_path):
        print(f"Database bulunamadı: {db_path}")
        return False
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Mevcut kolonları kontrol et
        cursor.execute("PRAGMA table_info(hybrid_analysis)")
        columns = [col[1] for col in cursor.fetchall()]
        
        # Advanced indicators kolonu ekle
        if "advanced_indicators" not in columns:
            print("Adding advanced_indicators column...")
            cursor.execute("""
                ALTER TABLE hybrid_analysis 
                ADD COLUMN advanced_indicators TEXT
            """)
            print("✓ advanced_indicators column added")
        else:
            print("✓ advanced_indicators column already exists")
        
        # Pattern analysis kolonu ekle
        if "pattern_analysis" not in columns:
            print("Adding pattern_analysis column...")
            cursor.execute("""
                ALTER TABLE hybrid_analysis 
                ADD COLUMN pattern_analysis TEXT
            """)
            print("✓ pattern_analysis column added")
        else:
            print("✓ pattern_analysis column already exists")
        
        # Değişiklikleri kaydet
        conn.commit()
        
        # Güncel şemayı göster
        print("\nGüncel şema:")
        cursor.execute("PRAGMA table_info(hybrid_analysis)")
        for col in cursor.fetchall():
            print(f"  - {col[1]}: {col[2]}")
        
        conn.close()
        print("\n✅ Database şeması başarıyla güncellendi!")
        return True
        
    except Exception as e:
        print(f"❌ Hata: {e}")
        return False

if __name__ == "__main__":
    update_database_schema()