"""
SQLite storage for price data
"""
import sqlite3
from datetime import datetime, timedelta
from decimal import Decimal
from typing import List, Optional, Dict, Tuple
import logging
from contextlib import contextmanager
from models.price_data import PriceData, PriceCandle

logger = logging.getLogger(__name__)


class SQLiteStorage:
    """SQLite tabanlı fiyat veri depolama"""
    
    def __init__(self, db_path: str = "gold_prices.db"):
        self.db_path = db_path
        self._init_database()
    
    @contextmanager
    def get_connection(self):
        """Context manager for database connections"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()
    
    def _init_database(self):
        """Veritabanı tablolarını oluştur"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Raw price data tablosu
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS price_data (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME NOT NULL,
                    ons_usd REAL NOT NULL,
                    usd_try REAL NOT NULL,
                    ons_try REAL NOT NULL,
                    source TEXT DEFAULT 'api',
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(timestamp)
                )
            """)
            
            # OHLC candle tablosu
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS price_candles (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME NOT NULL,
                    interval TEXT NOT NULL,
                    open REAL NOT NULL,
                    high REAL NOT NULL,
                    low REAL NOT NULL,
                    close REAL NOT NULL,
                    volume REAL,
                    tick_count INTEGER DEFAULT 0,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(timestamp, interval)
                )
            """)
            
            # Sinyal tablosu
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS trading_signals (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME NOT NULL,
                    signal_type TEXT NOT NULL,
                    price_level REAL NOT NULL,
                    confidence REAL NOT NULL,
                    risk_level TEXT NOT NULL,
                    target_price REAL,
                    stop_loss REAL,
                    reasons TEXT,
                    executed BOOLEAN DEFAULT 0,
                    result TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Index'ler
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_price_timestamp ON price_data(timestamp)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_candle_timestamp ON price_candles(timestamp, interval)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_signal_timestamp ON trading_signals(timestamp)")
            
            logger.info("Database initialized successfully")
    
    def save_price(self, price_data: PriceData):
        """Tek bir fiyat verisi kaydet"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO price_data 
                (timestamp, ons_usd, usd_try, ons_try, source)
                VALUES (?, ?, ?, ?, ?)
            """, (
                price_data.timestamp,
                float(price_data.ons_usd),
                float(price_data.usd_try),
                float(price_data.ons_try),
                price_data.source
            ))
    
    def get_latest_price(self) -> Optional[PriceData]:
        """En son fiyat verisini getir"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM price_data 
                ORDER BY timestamp DESC 
                LIMIT 1
            """)
            row = cursor.fetchone()
            if row:
                return PriceData(
                    timestamp=datetime.fromisoformat(row['timestamp']),
                    ons_usd=Decimal(str(row['ons_usd'])),
                    usd_try=Decimal(str(row['usd_try'])),
                    ons_try=Decimal(str(row['ons_try'])),
                    source=row['source']
                )
        return None
    
    def get_price_range(self, start_time: datetime, end_time: datetime) -> List[PriceData]:
        """Belirli zaman aralığındaki fiyatları getir"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM price_data 
                WHERE timestamp BETWEEN ? AND ?
                ORDER BY timestamp ASC
            """, (start_time, end_time))
            
            return [
                PriceData(
                    timestamp=datetime.fromisoformat(row['timestamp']),
                    ons_usd=Decimal(str(row['ons_usd'])),
                    usd_try=Decimal(str(row['usd_try'])),
                    ons_try=Decimal(str(row['ons_try'])),
                    source=row['source']
                )
                for row in cursor.fetchall()
            ]
    
    def generate_candles(self, interval_minutes: int, limit: int = 100) -> List[PriceCandle]:
        """Raw veriden OHLC mumları oluştur"""
        interval_map = {
            15: "15m",
            60: "1h",
            240: "4h",
            1440: "1d"
        }
        
        interval_str = interval_map.get(interval_minutes, f"{interval_minutes}m")
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # SQLite datetime fonksiyonları ile gruplama
            cursor.execute(f"""
                WITH grouped_data AS (
                    SELECT 
                        datetime(
                            strftime('%s', timestamp) / ({interval_minutes} * 60) * ({interval_minutes} * 60), 
                            'unixepoch'
                        ) as candle_time,
                        ons_try,
                        timestamp,
                        ROW_NUMBER() OVER (PARTITION BY datetime(strftime('%s', timestamp) / ({interval_minutes} * 60) * ({interval_minutes} * 60), 'unixepoch') ORDER BY timestamp ASC) as rn_first,
                        ROW_NUMBER() OVER (PARTITION BY datetime(strftime('%s', timestamp) / ({interval_minutes} * 60) * ({interval_minutes} * 60), 'unixepoch') ORDER BY timestamp DESC) as rn_last
                    FROM price_data
                )
                SELECT 
                    candle_time,
                    MIN(ons_try) as low,
                    MAX(ons_try) as high,
                    MAX(CASE WHEN rn_first = 1 THEN ons_try END) as open,
                    MAX(CASE WHEN rn_last = 1 THEN ons_try END) as close,
                    COUNT(*) as tick_count
                FROM grouped_data
                GROUP BY candle_time
                ORDER BY candle_time DESC
                LIMIT ?
            """, (limit,))
            
            candles = []
            for row in cursor.fetchall():
                candle = PriceCandle(
                    timestamp=datetime.fromisoformat(row['candle_time']),
                    open=Decimal(str(row['open'])),
                    high=Decimal(str(row['high'])),
                    low=Decimal(str(row['low'])),
                    close=Decimal(str(row['close'])),
                    interval=interval_str
                )
                candles.append(candle)
            
            return list(reversed(candles))  # Eski->Yeni sıralama
    
    def cleanup_old_data(self, days_to_keep: int = 30):
        """Eski verileri temizle"""
        cutoff_date = datetime.now() - timedelta(days=days_to_keep)
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                DELETE FROM price_data 
                WHERE timestamp < ?
            """, (cutoff_date,))
            
            deleted = cursor.rowcount
            logger.info(f"Cleaned up {deleted} old price records")
    
    def get_statistics(self) -> Dict[str, any]:
        """Veritabanı istatistikleri"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            stats = {}
            
            # Toplam kayıt sayısı
            cursor.execute("SELECT COUNT(*) as count FROM price_data")
            stats['total_records'] = cursor.fetchone()['count']
            
            # En eski/yeni kayıt
            cursor.execute("SELECT MIN(timestamp) as oldest, MAX(timestamp) as newest FROM price_data")
            row = cursor.fetchone()
            stats['oldest_record'] = row['oldest']
            stats['newest_record'] = row['newest']
            
            # Ortalama fiyatlar
            cursor.execute("SELECT AVG(ons_try) as avg_price FROM price_data")
            stats['average_price'] = cursor.fetchone()['avg_price']
            
            return stats