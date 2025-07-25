#!/usr/bin/env python3
"""
Dip yakalama stratejisi backtest
"""
import sqlite3
import json
from datetime import datetime, timedelta
from typing import Dict, List, Tuple

def analyze_bearish_buy_signals():
    """BEARISH trend'deki BUY sinyallerini analiz et"""
    conn = sqlite3.connect('gold_prices.db')
    cursor = conn.cursor()
    
    # Tüm BUY sinyallerini trend bazında analiz et
    cursor.execute('''
        WITH buy_performance AS (
            SELECT 
                h.timestamp,
                h.timeframe,
                h.gram_price as entry_price,
                h.confidence,
                json_extract(h.gram_analysis, '$.trend') as trend,
                json_extract(h.gram_analysis, '$.indicators.rsi') as rsi,
                -- 24 saat içindeki max fiyat
                (SELECT MAX(p.gram_altin) FROM price_data p 
                 WHERE p.timestamp BETWEEN h.timestamp AND datetime(h.timestamp, '+24 hours')) as max_24h,
                -- Yüzde değişim
                ((SELECT MAX(p.gram_altin) FROM price_data p 
                  WHERE p.timestamp BETWEEN h.timestamp AND datetime(h.timestamp, '+24 hours')) - h.gram_price) / h.gram_price * 100 as pct_change
            FROM hybrid_analysis h
            WHERE h.signal = 'BUY'
            AND h.timestamp < datetime('now', '-24 hours')
        )
        SELECT 
            trend,
            COUNT(*) as total,
            SUM(CASE WHEN pct_change > 0.5 THEN 1 ELSE 0 END) as successful,
            AVG(pct_change) as avg_change,
            MIN(pct_change) as worst_loss,
            MAX(pct_change) as best_gain
        FROM buy_performance
        GROUP BY trend
    ''')
    
    print("=== TREND BAZINDA BUY PERFORMANSI ===")
    print(f"{'Trend':<10} {'Toplam':<8} {'Başarılı':<10} {'Başarı %':<10} {'Ort.Değişim':<12} {'En Kötü':<10} {'En İyi':<10}")
    print("-" * 80)
    
    results = cursor.fetchall()
    for row in results:
        trend, total, successful, avg_change, worst_loss, best_gain = row
        success_rate = (successful/total*100) if total > 0 else 0
        print(f"{trend:<10} {total:<8} {successful:<10} {success_rate:<10.1f} {avg_change:<12.2f} {worst_loss:<10.2f} {best_gain:<10.2f}")
    
    conn.close()

def find_successful_dips():
    """Başarılı dip yakalama örneklerini bul"""
    conn = sqlite3.connect('gold_prices.db')
    cursor = conn.cursor()
    
    # BEARISH trend'de başarılı BUY sinyalleri
    cursor.execute('''
        SELECT 
            h.timestamp,
            h.gram_price,
            h.confidence,
            json_extract(h.gram_analysis, '$.indicators.rsi') as rsi,
            ((SELECT MAX(p.gram_altin) FROM price_data p 
              WHERE p.timestamp BETWEEN h.timestamp AND datetime(h.timestamp, '+24 hours')) - h.gram_price) / h.gram_price * 100 as gain
        FROM hybrid_analysis h
        WHERE h.signal = 'BUY'
        AND json_extract(h.gram_analysis, '$.trend') = 'BEARISH'
        AND ((SELECT MAX(p.gram_altin) FROM price_data p 
              WHERE p.timestamp BETWEEN h.timestamp AND datetime(h.timestamp, '+24 hours')) - h.gram_price) / h.gram_price * 100 > 1.0
        ORDER BY gain DESC
        LIMIT 10
    ''')
    
    print("\n=== BEARISH'TE BAŞARILI DİP YAKALAMALARI ===")
    print(f"{'Tarih':<20} {'Giriş':<10} {'Güven':<8} {'RSI':<6} {'Kazanç %':<10}")
    print("-" * 60)
    
    results = cursor.fetchall()
    for row in results:
        timestamp, entry, confidence, rsi, gain = row
        print(f"{timestamp[:19]:<20} {entry:<10.2f} {confidence*100:<8.1f} {rsi or 0:<6.1f} {gain:<10.2f}")
    
    conn.close()

def test_dip_strategy():
    """Yeni dip yakalama stratejisini test et"""
    conn = sqlite3.connect('gold_prices.db')
    cursor = conn.cursor()
    
    # Potansiyel dip noktalarını bul
    cursor.execute('''
        WITH potential_dips AS (
            SELECT 
                h.timestamp,
                h.gram_price,
                json_extract(h.gram_analysis, '$.trend') as trend,
                json_extract(h.gram_analysis, '$.indicators.rsi') as rsi,
                h.confidence,
                -- Sonraki 24 saatte ne oldu?
                (SELECT MAX(p.gram_altin) FROM price_data p 
                 WHERE p.timestamp BETWEEN h.timestamp AND datetime(h.timestamp, '+24 hours')) as max_24h,
                ((SELECT MAX(p.gram_altin) FROM price_data p 
                  WHERE p.timestamp BETWEEN h.timestamp AND datetime(h.timestamp, '+24 hours')) - h.gram_price) / h.gram_price * 100 as potential_gain
            FROM hybrid_analysis h
            WHERE json_extract(h.gram_analysis, '$.trend') = 'BEARISH'
            AND json_extract(h.gram_analysis, '$.indicators.rsi') < 40
            AND h.timestamp < datetime('now', '-24 hours')
        )
        SELECT 
            COUNT(*) as total_opportunities,
            SUM(CASE WHEN potential_gain > 0.5 THEN 1 ELSE 0 END) as successful,
            AVG(potential_gain) as avg_gain,
            SUM(CASE WHEN rsi < 30 THEN 1 ELSE 0 END) as extreme_oversold,
            AVG(CASE WHEN rsi < 30 THEN potential_gain ELSE NULL END) as oversold_avg_gain
        FROM potential_dips
    ''')
    
    result = cursor.fetchone()
    print("\n=== YENİ DİP STRATEJİSİ BACKTEST ===")
    print(f"BEARISH + RSI<40 durumları: {result[0]}")
    print(f"Başarılı (>0.5% kazanç): {result[1]} ({result[1]/result[0]*100:.1f}%)")
    print(f"Ortalama kazanç: {result[2]:.2f}%")
    print(f"RSI<30 durumları: {result[3]}")
    print(f"RSI<30 ortalama kazanç: {result[4]:.2f}%")
    
    conn.close()

def simulate_new_strategy():
    """Önerilen stratejiyi simüle et"""
    conn = sqlite3.connect('gold_prices.db')
    cursor = conn.cursor()
    
    # Son 30 günlük veri üzerinde test
    cursor.execute('''
        WITH simulated_signals AS (
            SELECT 
                h.timestamp,
                h.timeframe,
                h.gram_price,
                h.signal as original_signal,
                json_extract(h.gram_analysis, '$.trend') as trend,
                json_extract(h.gram_analysis, '$.indicators.rsi') as rsi,
                h.confidence,
                CASE 
                    -- Dip yakalama kriterleri
                    WHEN json_extract(h.gram_analysis, '$.trend') = 'BEARISH' 
                         AND json_extract(h.gram_analysis, '$.indicators.rsi') < 35
                         AND h.confidence > 0.4
                    THEN 'BUY'
                    -- Normal BUY sinyalleri (BEARISH hariç)
                    WHEN h.signal = 'BUY' 
                         AND json_extract(h.gram_analysis, '$.trend') != 'BEARISH'
                    THEN 'BUY'
                    -- SELL sinyalleri
                    WHEN h.signal = 'SELL'
                    THEN 'SELL'
                    ELSE 'HOLD'
                END as new_signal,
                -- Performans hesaplama
                CASE 
                    WHEN h.signal = 'BUY' THEN
                        ((SELECT MAX(p.gram_altin) FROM price_data p 
                          WHERE p.timestamp BETWEEN h.timestamp AND datetime(h.timestamp, '+24 hours')) - h.gram_price) / h.gram_price * 100
                    WHEN h.signal = 'SELL' THEN
                        (h.gram_price - (SELECT MIN(p.gram_altin) FROM price_data p 
                          WHERE p.timestamp BETWEEN h.timestamp AND datetime(h.timestamp, '+24 hours'))) / h.gram_price * 100
                    ELSE 0
                END as performance
            FROM hybrid_analysis h
            WHERE h.timestamp > datetime('now', '-30 days')
            AND h.timestamp < datetime('now', '-24 hours')
        )
        SELECT 
            new_signal,
            COUNT(*) as count,
            AVG(CASE WHEN performance > 0.5 THEN 1 ELSE 0 END) * 100 as success_rate,
            AVG(performance) as avg_performance
        FROM simulated_signals
        WHERE new_signal != 'HOLD'
        GROUP BY new_signal
    ''')
    
    print("\n=== YENİ STRATEJİ SİMÜLASYONU ===")
    print(f"{'Sinyal':<10} {'Sayı':<8} {'Başarı %':<10} {'Ort.Performans':<15}")
    print("-" * 45)
    
    results = cursor.fetchall()
    for row in results:
        signal, count, success_rate, avg_perf = row
        print(f"{signal:<10} {count:<8} {success_rate:<10.1f} {avg_perf:<15.2f}")
    
    conn.close()

if __name__ == "__main__":
    print("Gold Price Analyzer - Dip Yakalama Stratejisi Backtest")
    print("=" * 80)
    
    analyze_bearish_buy_signals()
    find_successful_dips()
    test_dip_strategy()
    simulate_new_strategy()