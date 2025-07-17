"""
Analysis results tablosuna timeframe kolonu ekle
"""
import sqlite3

def add_timeframe_column():
    conn = sqlite3.connect('gold_prices.db')
    cursor = conn.cursor()
    
    try:
        # Timeframe kolonu ekle (varsayılan 15m)
        cursor.execute("""
            ALTER TABLE analysis_results 
            ADD COLUMN timeframe TEXT DEFAULT '15m'
        """)
        
        # Index ekle
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_analysis_timeframe 
            ON analysis_results(timeframe, timestamp)
        """)
        
        conn.commit()
        print("✅ Timeframe kolonu başarıyla eklendi")
        
    except sqlite3.OperationalError as e:
        if "duplicate column name" in str(e):
            print("ℹ️ Timeframe kolonu zaten mevcut")
        else:
            print(f"❌ Hata: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    add_timeframe_column()