#!/usr/bin/env python3
"""
Analysis tablosunu eklemek için migration scripti
"""
import sqlite3
import sys

def add_analysis_table():
    """Analysis results tablosunu ekle"""
    try:
        conn = sqlite3.connect('gold_prices.db')
        cursor = conn.cursor()
        
        # Tablo var mı kontrol et
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='analysis_results'
        """)
        
        if cursor.fetchone():
            print("✓ analysis_results tablosu zaten mevcut")
            return
        
        # Analiz sonuçları tablosu
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS analysis_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME NOT NULL,
                price REAL NOT NULL,
                price_change REAL,
                price_change_pct REAL,
                trend TEXT NOT NULL,
                trend_strength TEXT NOT NULL,
                nearest_support REAL,
                nearest_resistance REAL,
                signal TEXT,
                signal_strength REAL,
                confidence REAL NOT NULL,
                risk_level TEXT,
                stop_loss REAL,
                take_profit REAL,
                rsi REAL,
                rsi_signal TEXT,
                ma_short REAL,
                ma_long REAL,
                ma_cross TEXT,
                support_levels TEXT,
                resistance_levels TEXT,
                analysis_details TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Index ekle
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_analysis_timestamp ON analysis_results(timestamp)")
        
        conn.commit()
        print("✅ analysis_results tablosu başarıyla oluşturuldu")
        
    except Exception as e:
        print(f"❌ Hata: {e}")
        sys.exit(1)
    finally:
        conn.close()

if __name__ == "__main__":
    add_analysis_table()