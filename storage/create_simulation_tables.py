"""
Simülasyon sistemi için veritabanı tablolarını oluştur
"""
import sqlite3
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

def create_simulation_tables(db_path: str = "gold_analyzer.db"):
    """Simülasyon tablolarını oluştur"""
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 1. simulations - Ana simülasyon tablosu
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS simulations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                strategy_type TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'ACTIVE',
                
                -- Başlangıç parametreleri
                initial_capital REAL NOT NULL DEFAULT 1000.0,
                min_confidence REAL NOT NULL DEFAULT 0.6,
                max_risk REAL NOT NULL DEFAULT 0.02,
                spread REAL NOT NULL DEFAULT 15.0,
                commission_rate REAL NOT NULL DEFAULT 0.001,
                
                -- Mevcut durum
                current_capital REAL NOT NULL DEFAULT 1000.0,
                total_trades INTEGER DEFAULT 0,
                winning_trades INTEGER DEFAULT 0,
                losing_trades INTEGER DEFAULT 0,
                
                -- Performans metrikleri
                total_profit_loss REAL DEFAULT 0.0,
                total_profit_loss_pct REAL DEFAULT 0.0,
                max_drawdown REAL DEFAULT 0.0,
                max_drawdown_pct REAL DEFAULT 0.0,
                win_rate REAL DEFAULT 0.0,
                profit_factor REAL DEFAULT 0.0,
                sharpe_ratio REAL DEFAULT 0.0,
                avg_win REAL DEFAULT 0.0,
                avg_loss REAL DEFAULT 0.0,
                
                -- Zaman bilgileri
                start_date DATETIME NOT NULL,
                end_date DATETIME,
                last_update DATETIME,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                
                -- Ek bilgiler
                config TEXT,
                metadata TEXT
            )
        """)
        
        # 2. sim_positions - Pozisyon/İşlem tablosu
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sim_positions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                simulation_id INTEGER NOT NULL,
                timeframe TEXT NOT NULL,
                
                -- Pozisyon detayları
                position_type TEXT NOT NULL DEFAULT 'LONG',
                status TEXT NOT NULL DEFAULT 'OPEN',
                
                -- Giriş bilgileri
                entry_signal_id INTEGER,
                entry_time DATETIME NOT NULL,
                entry_price REAL NOT NULL,
                entry_spread REAL NOT NULL,
                entry_commission REAL NOT NULL,
                
                -- Pozisyon boyutu
                position_size REAL NOT NULL,
                allocated_capital REAL NOT NULL,
                risk_amount REAL NOT NULL,
                
                -- Risk yönetimi
                stop_loss REAL NOT NULL,
                take_profit REAL NOT NULL,
                trailing_stop REAL,
                max_profit REAL DEFAULT 0.0,
                
                -- Çıkış bilgileri
                exit_time DATETIME,
                exit_price REAL,
                exit_spread REAL,
                exit_commission REAL,
                exit_reason TEXT,
                
                -- Sonuç
                gross_profit_loss REAL,
                net_profit_loss REAL,
                profit_loss_pct REAL,
                holding_period_minutes INTEGER,
                
                -- Analiz bilgileri
                entry_confidence REAL,
                entry_indicators TEXT,
                exit_indicators TEXT,
                
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME,
                
                FOREIGN KEY (simulation_id) REFERENCES simulations(id)
            )
        """)
        
        # 3. sim_daily_performance - Günlük performans özeti
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sim_daily_performance (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                simulation_id INTEGER NOT NULL,
                date DATE NOT NULL,
                
                -- Sermaye durumu
                starting_capital REAL NOT NULL,
                ending_capital REAL NOT NULL,
                daily_pnl REAL,
                daily_pnl_pct REAL,
                
                -- İşlem istatistikleri
                total_trades INTEGER DEFAULT 0,
                winning_trades INTEGER DEFAULT 0,
                losing_trades INTEGER DEFAULT 0,
                
                -- Timeframe bazlı dağılım
                trades_15m INTEGER DEFAULT 0,
                trades_1h INTEGER DEFAULT 0,
                trades_4h INTEGER DEFAULT 0,
                trades_1d INTEGER DEFAULT 0,
                
                pnl_15m REAL DEFAULT 0.0,
                pnl_1h REAL DEFAULT 0.0,
                pnl_4h REAL DEFAULT 0.0,
                pnl_1d REAL DEFAULT 0.0,
                
                -- Risk metrikleri
                max_intraday_drawdown REAL DEFAULT 0.0,
                risk_limit_hit INTEGER DEFAULT 0,
                
                -- Detaylar
                summary TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                
                FOREIGN KEY (simulation_id) REFERENCES simulations(id),
                UNIQUE(simulation_id, date)
            )
        """)
        
        # 4. sim_timeframe_capital - Timeframe bazlı sermaye takibi
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sim_timeframe_capital (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                simulation_id INTEGER NOT NULL,
                timeframe TEXT NOT NULL,
                allocated_capital REAL NOT NULL DEFAULT 250.0,
                current_capital REAL NOT NULL DEFAULT 250.0,
                in_position INTEGER DEFAULT 0,
                last_update DATETIME DEFAULT CURRENT_TIMESTAMP,
                
                FOREIGN KEY (simulation_id) REFERENCES simulations(id),
                UNIQUE(simulation_id, timeframe)
            )
        """)
        
        # İndeksler
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_sim_positions_simulation_id ON sim_positions(simulation_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_sim_positions_status ON sim_positions(status)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_sim_positions_timeframe ON sim_positions(timeframe)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_sim_daily_performance_date ON sim_daily_performance(date)")
        
        conn.commit()
        logger.info("Simülasyon tabloları başarıyla oluşturuldu")
        
        return True
        
    except Exception as e:
        logger.error(f"Tablo oluşturma hatası: {str(e)}")
        return False
    finally:
        conn.close()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    if create_simulation_tables():
        print("Simülasyon tabloları başarıyla oluşturuldu")
    else:
        print("Hata: Tablolar oluşturulamadı")