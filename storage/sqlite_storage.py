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
from models.analysis_result import AnalysisResult, TrendType, TrendStrength
import json

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
            
            # Analiz sonuçları tablosu
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS analysis_results (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME NOT NULL,
                    timeframe TEXT DEFAULT '15m',
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
                    support_levels TEXT,  -- JSON
                    resistance_levels TEXT,  -- JSON
                    analysis_details TEXT,  -- JSON
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Index'ler
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_price_timestamp ON price_data(timestamp)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_candle_timestamp ON price_candles(timestamp, interval)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_signal_timestamp ON trading_signals(timestamp)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_analysis_timestamp ON analysis_results(timestamp)")
            
            # Eksik kolonları kontrol et ve ekle
            self._check_and_add_missing_columns(cursor)
            
            logger.info("Database initialized successfully")
    
    def _check_and_add_missing_columns(self, cursor):
        """Eksik kolonları kontrol et ve ekle"""
        # analysis_results tablosundaki kolonları kontrol et
        cursor.execute("PRAGMA table_info(analysis_results)")
        columns = [col[1] for col in cursor.fetchall()]
        
        # Timeframe kolonu yoksa ekle
        if 'timeframe' not in columns:
            try:
                cursor.execute("ALTER TABLE analysis_results ADD COLUMN timeframe TEXT DEFAULT '15m'")
                logger.info("Added missing 'timeframe' column to analysis_results table")
            except Exception as e:
                # Kolon zaten varsa veya başka bir hata varsa logla
                logger.debug(f"Could not add timeframe column: {e}")
    
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
    
    def save_analysis_result(self, analysis: AnalysisResult):
        """Analiz sonucunu kaydet"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # JSON alanları hazırla
            support_levels_json = json.dumps([
                {
                    "level": float(s.level),
                    "strength": s.strength,
                    "touches": s.touches
                } for s in analysis.support_levels
            ])
            
            resistance_levels_json = json.dumps([
                {
                    "level": float(r.level),
                    "strength": r.strength,
                    "touches": r.touches
                } for r in analysis.resistance_levels
            ])
            
            analysis_details_json = json.dumps(analysis.analysis_details)
            
            cursor.execute("""
                INSERT INTO analysis_results (
                    timestamp, timeframe, price, price_change, price_change_pct,
                    trend, trend_strength, nearest_support, nearest_resistance,
                    signal, signal_strength, confidence, risk_level,
                    stop_loss, take_profit, rsi, rsi_signal,
                    ma_short, ma_long, ma_cross,
                    support_levels, resistance_levels, analysis_details
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                analysis.timestamp,
                analysis.timeframe,
                float(analysis.price) if analysis.price else None,
                float(analysis.price_change) if analysis.price_change else None,
                analysis.price_change_pct,
                analysis.trend.value,
                analysis.trend_strength.value,
                float(analysis.nearest_support) if analysis.nearest_support else None,
                float(analysis.nearest_resistance) if analysis.nearest_resistance else None,
                analysis.signal,
                analysis.signal_strength,
                analysis.confidence,
                analysis.risk_level,
                float(analysis.stop_loss) if analysis.stop_loss else None,
                float(analysis.take_profit) if analysis.take_profit else None,
                analysis.indicators.rsi if analysis.indicators else None,
                analysis.indicators.rsi_signal if analysis.indicators else None,
                float(analysis.indicators.ma_short) if analysis.indicators and analysis.indicators.ma_short else None,
                float(analysis.indicators.ma_long) if analysis.indicators and analysis.indicators.ma_long else None,
                analysis.indicators.ma_cross if analysis.indicators else None,
                support_levels_json,
                resistance_levels_json,
                analysis_details_json
            ))
            
            logger.info(f"Analysis result saved: {analysis.trend.value} - Signal: {analysis.signal} - Confidence: {analysis.confidence:.2%}")
    
    def get_latest_analysis(self) -> Optional[AnalysisResult]:
        """En son analiz sonucunu getir"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM analysis_results 
                ORDER BY timestamp DESC 
                LIMIT 1
            """)
            
            row = cursor.fetchone()
            if row:
                return self._row_to_analysis_result(row)
            return None
    
    def get_analysis_history(self, limit: int = 10, timeframe: str = None) -> List[AnalysisResult]:
        """Son analiz sonuçlarını getir"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            if timeframe:
                cursor.execute("""
                    SELECT * FROM analysis_results 
                    WHERE timeframe = ?
                    ORDER BY timestamp DESC 
                    LIMIT ?
                """, (timeframe, limit))
            else:
                cursor.execute("""
                    SELECT * FROM analysis_results 
                    ORDER BY timestamp DESC 
                    LIMIT ?
                """, (limit,))
            
            results = []
            for row in cursor.fetchall():
                results.append(self._row_to_analysis_result(row))
            
            return results
    
    def _row_to_analysis_result(self, row) -> AnalysisResult:
        """Veritabanı satırını AnalysisResult nesnesine dönüştür"""
        from models.analysis_result import TechnicalIndicators, SupportResistanceLevel
        
        # JSON alanları parse et
        support_levels = []
        if row['support_levels']:
            for s in json.loads(row['support_levels']):
                support_levels.append(SupportResistanceLevel(
                    level=Decimal(str(s['level'])),
                    strength=s['strength'],
                    touches=s['touches']
                ))
        
        resistance_levels = []
        if row['resistance_levels']:
            for r in json.loads(row['resistance_levels']):
                resistance_levels.append(SupportResistanceLevel(
                    level=Decimal(str(r['level'])),
                    strength=r['strength'],
                    touches=r['touches']
                ))
        
        # Teknik göstergeler
        indicators = None
        if row['rsi'] is not None:
            indicators = TechnicalIndicators(
                rsi=row['rsi'],
                rsi_signal=row['rsi_signal'],
                ma_short=Decimal(str(row['ma_short'])) if row['ma_short'] else None,
                ma_long=Decimal(str(row['ma_long'])) if row['ma_long'] else None,
                ma_cross=row['ma_cross']
            )
        
        return AnalysisResult(
            id=row['id'],
            timestamp=datetime.fromisoformat(row['timestamp']),
            timeframe=row['timeframe'] if 'timeframe' in row.keys() else '15m',  # Eski veriler için varsayılan
            price=Decimal(str(row['price'])) if row['price'] else None,
            price_change=Decimal(str(row['price_change'])) if row['price_change'] else None,
            price_change_pct=row['price_change_pct'],
            trend=TrendType(row['trend']),
            trend_strength=TrendStrength(row['trend_strength']),
            support_levels=support_levels,
            resistance_levels=resistance_levels,
            nearest_support=Decimal(str(row['nearest_support'])) if row['nearest_support'] else None,
            nearest_resistance=Decimal(str(row['nearest_resistance'])) if row['nearest_resistance'] else None,
            signal=row['signal'],
            signal_strength=row['signal_strength'],
            confidence=row['confidence'],
            indicators=indicators,
            risk_level=row['risk_level'],
            stop_loss=Decimal(str(row['stop_loss'])) if row['stop_loss'] else None,
            take_profit=Decimal(str(row['take_profit'])) if row['take_profit'] else None,
            analysis_details=json.loads(row['analysis_details']) if row['analysis_details'] else {}
        )