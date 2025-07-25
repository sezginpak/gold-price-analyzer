#!/usr/bin/env python3
"""
BEARISH trend durumlarını kontrol et
"""
import sqlite3
from datetime import datetime, timedelta

def check_bearish_trends():
    """Son 24 saatte BEARISH trend ve düşük RSI durumları"""
    conn = sqlite3.connect('gold_prices.db')
    cursor = conn.cursor()
    
    print("=== BEARISH TREND ANALİZİ ===\n")
    
    # 1. Son 24 saatteki trend dağılımı
    cursor.execute('''
        SELECT 
            json_extract(gram_analysis, '$.trend') as trend,
            COUNT(*) as count,
            AVG(json_extract(gram_analysis, '$.indicators.rsi')) as avg_rsi
        FROM hybrid_analysis
        WHERE timestamp > datetime('now', '-24 hours')
        GROUP BY trend
    ''')
    
    print("📊 Son 24 Saatte Trend Dağılımı:")
    print(f"{'Trend':<12} {'Sayı':<8} {'Ort. RSI':<10}")
    print("-" * 30)
    for row in cursor.fetchall():
        trend, count, avg_rsi = row
        print(f"{trend or 'NULL':<12} {count:<8} {avg_rsi or 0:<10.1f}")
    
    # 2. BEARISH + düşük RSI durumları
    cursor.execute('''
        SELECT 
            timeframe,
            json_extract(gram_analysis, '$.indicators.rsi') as rsi,
            signal,
            confidence,
            datetime(timestamp, 'localtime') as time
        FROM hybrid_analysis
        WHERE json_extract(gram_analysis, '$.trend') = 'BEARISH'
        AND json_extract(gram_analysis, '$.indicators.rsi') < 40
        AND timestamp > datetime('now', '-24 hours')
        ORDER BY timestamp DESC
        LIMIT 10
    ''')
    
    results = cursor.fetchall()
    print(f"\n\n🎯 BEARISH + RSI<40 Durumları (Son 24 saat):")
    
    if results:
        print(f"{'Timeframe':<10} {'RSI':<6} {'Signal':<8} {'Conf':<6} {'Time':<20}")
        print("-" * 50)
        for row in results:
            tf, rsi, signal, conf, time = row
            print(f"{tf:<10} {rsi or 0:<6.1f} {signal:<8} {conf*100:<6.1f} {time:<20}")
    else:
        print("❌ BEARISH + düşük RSI durumu bulunamadı")
    
    # 3. En son BEARISH trend ne zaman görüldü?
    cursor.execute('''
        SELECT 
            datetime(timestamp, 'localtime') as last_bearish,
            timeframe,
            json_extract(gram_analysis, '$.indicators.rsi') as rsi
        FROM hybrid_analysis
        WHERE json_extract(gram_analysis, '$.trend') = 'BEARISH'
        ORDER BY timestamp DESC
        LIMIT 1
    ''')
    
    last_bearish = cursor.fetchone()
    if last_bearish:
        print(f"\n📅 En son BEARISH trend: {last_bearish[0]} ({last_bearish[1]}, RSI: {last_bearish[2]:.1f})")
    else:
        print("\n📅 Son dönemde BEARISH trend tespit edilmedi")
    
    # 4. Potansiyel dip fırsatları (trend dönüşleri)
    cursor.execute('''
        WITH trend_changes AS (
            SELECT 
                timestamp,
                timeframe,
                json_extract(gram_analysis, '$.trend') as current_trend,
                LAG(json_extract(gram_analysis, '$.trend')) OVER (PARTITION BY timeframe ORDER BY timestamp) as prev_trend,
                json_extract(gram_analysis, '$.indicators.rsi') as rsi,
                signal
            FROM hybrid_analysis
            WHERE timestamp > datetime('now', '-48 hours')
        )
        SELECT 
            datetime(timestamp, 'localtime') as time,
            timeframe,
            prev_trend || ' -> ' || current_trend as trend_change,
            rsi,
            signal
        FROM trend_changes
        WHERE prev_trend = 'BEARISH' AND current_trend != 'BEARISH'
        ORDER BY timestamp DESC
        LIMIT 5
    ''')
    
    print("\n\n🔄 Son Trend Dönüşleri (BEARISH'ten çıkışlar):")
    results = cursor.fetchall()
    if results:
        print(f"{'Time':<20} {'TF':<5} {'Trend Değişimi':<20} {'RSI':<6} {'Signal':<8}")
        print("-" * 60)
        for row in results:
            time, tf, change, rsi, signal = row
            print(f"{time:<20} {tf:<5} {change:<20} {rsi or 0:<6.1f} {signal:<8}")
    else:
        print("❌ Son 48 saatte trend dönüşü tespit edilmedi")
    
    conn.close()

if __name__ == "__main__":
    check_bearish_trends()