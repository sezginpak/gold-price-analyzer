#!/usr/bin/env python3
"""
Yeni stratejiyi (gram override) backtest et
"""
import sys
sys.path.insert(0, '.')

import sqlite3
from datetime import datetime, timedelta
from collections import defaultdict

def analyze_signal_success(conn, hours_back=168):  # 7 gün
    """Son X saatteki sinyallerin başarısını analiz et"""
    cursor = conn.cursor()
    
    # Tüm sinyalleri al
    cursor.execute(f"""
        SELECT 
            ha.timestamp,
            ha.signal,
            ha.confidence,
            ha.gram_price,
            ha.timeframe,
            json_extract(ha.gram_analysis, '$.signal') as gram_signal,
            json_extract(ha.gram_analysis, '$.confidence') as gram_conf
        FROM hybrid_analysis ha
        WHERE ha.timestamp > datetime('now', '-{hours_back} hours')
        AND ha.signal != 'HOLD'
        ORDER BY ha.timestamp
    """)
    
    signals = cursor.fetchall()
    
    results = {
        'BUY': {'total': 0, 'successful': 0, 'failed': 0},
        'SELL': {'total': 0, 'successful': 0, 'failed': 0},
        'STRONG_BUY': {'total': 0, 'successful': 0, 'failed': 0},
        'STRONG_SELL': {'total': 0, 'successful': 0, 'failed': 0}
    }
    
    print(f"\n=== BACKTEST: SON {hours_back} SAAT ===")
    print(f"Toplam sinyal sayısı: {len(signals)}")
    
    for i, (timestamp, signal, conf, entry_price, tf, gram_sig, gram_conf) in enumerate(signals):
        results[signal]['total'] += 1
        
        # Gelecekteki fiyatları kontrol et
        cursor.execute("""
            SELECT 
                MIN(gram_altin) as min_price,
                MAX(gram_altin) as max_price,
                AVG(gram_altin) as avg_price
            FROM price_data
            WHERE gram_altin IS NOT NULL
            AND timestamp > ?
            AND timestamp <= datetime(?, '+4 hours')
        """, (timestamp, timestamp))
        
        future_data = cursor.fetchone()
        
        if future_data and future_data[0]:  # min_price var
            min_price = future_data[0]
            max_price = future_data[1]
            avg_price = future_data[2]
            
            if signal == 'BUY' or signal == 'STRONG_BUY':
                # BUY için: fiyat %0.5 artarsa başarılı
                target = entry_price * 1.005
                stop_loss = entry_price * 0.995
                
                if max_price >= target:
                    results[signal]['successful'] += 1
                elif min_price <= stop_loss:
                    results[signal]['failed'] += 1
                    
            elif signal == 'SELL' or signal == 'STRONG_SELL':
                # SELL için: fiyat %0.5 düşerse başarılı
                target = entry_price * 0.995
                stop_loss = entry_price * 1.005
                
                if min_price <= target:
                    results[signal]['successful'] += 1
                elif max_price >= stop_loss:
                    results[signal]['failed'] += 1
    
    # Sonuçları göster
    print("\n📊 BACKTEST SONUÇLARI:")
    print("-" * 50)
    
    for signal_type in ['BUY', 'SELL', 'STRONG_BUY', 'STRONG_SELL']:
        data = results[signal_type]
        total = data['total']
        if total > 0:
            success_rate = (data['successful'] / total) * 100
            print(f"\n{signal_type} Sinyalleri:")
            print(f"  Toplam: {total}")
            print(f"  Başarılı: {data['successful']} ({success_rate:.1f}%)")
            print(f"  Başarısız: {data['failed']} ({data['failed']/total*100:.1f}%)")
            print(f"  Belirsiz: {total - data['successful'] - data['failed']}")
    
    # Override öncesi/sonrası karşılaştırma
    print("\n=== GRAM OVERRIDE ANALİZİ ===")
    cursor.execute("""
        SELECT 
            CASE 
                WHEN json_extract(gram_analysis, '$.confidence') >= 0.40 
                AND json_extract(gram_analysis, '$.signal') IN ('BUY', 'SELL')
                THEN 'Override'
                ELSE 'Normal'
            END as strategy_type,
            COUNT(*) as count,
            signal
        FROM hybrid_analysis
        WHERE timestamp > datetime('now', '-24 hours')
        AND signal != 'HOLD'
        GROUP BY strategy_type, signal
    """)
    
    override_stats = cursor.fetchall()
    print("\nSon 24 saatteki dağılım:")
    for strategy_type, count, signal in override_stats:
        print(f"  {strategy_type} {signal}: {count} adet")

# Ana program
if __name__ == "__main__":
    conn = sqlite3.connect('gold_prices.db')
    
    # Son 7 gün
    analyze_signal_success(conn, 168)
    
    # Son 24 saat
    print("\n" + "="*60)
    analyze_signal_success(conn, 24)
    
    conn.close()