#\!/usr/bin/env python3
"""
Basit backtest - son sinyalleri kontrol et
"""
import sqlite3
from datetime import datetime, timedelta

conn = sqlite3.connect('gold_prices.db')
cursor = conn.cursor()

# Son 24 saatteki BUY sinyallerini al
cursor.execute("""
    SELECT 
        ha.timestamp,
        ha.signal,
        ha.gram_price,
        ha.confidence,
        datetime(ha.timestamp, 'localtime') as signal_time
    FROM hybrid_analysis ha
    WHERE ha.timestamp > datetime('now', '-24 hours')
    AND ha.signal IN ('BUY', 'SELL')
    ORDER BY ha.timestamp DESC
    LIMIT 10
""")

signals = cursor.fetchall()

print("=== SON 10 SİNYAL VE SONUÇLARI ===")
print(f"{'Zaman':<20} {'Sinyal':<6} {'Giriş':<8} {'Güven':<6} {'4h Sonra':<8} {'Sonuç':<10}")
print("-" * 80)

for timestamp, signal, entry_price, conf, signal_time in signals:
    # 4 saat sonraki fiyatı bul
    cursor.execute("""
        SELECT gram_altin
        FROM price_data
        WHERE gram_altin IS NOT NULL
        AND timestamp > ?
        AND timestamp <= datetime(?, '+4 hours')
        ORDER BY timestamp DESC
        LIMIT 1
    """, (timestamp, timestamp))
    
    future = cursor.fetchone()
    
    if future and future[0]:
        exit_price = future[0]
        pnl_pct = ((exit_price - entry_price) / entry_price) * 100
        
        if signal == 'BUY':
            result = "✅ Başarılı" if pnl_pct > 0.5 else ("❌ Zarar" if pnl_pct < -0.5 else "➖ Nötr")
        else:  # SELL
            result = "✅ Başarılı" if pnl_pct < -0.5 else ("❌ Zarar" if pnl_pct > 0.5 else "➖ Nötr")
            
        print(f"{signal_time:<20} {signal:<6} {entry_price:<8.2f} {conf:<6.1%} {exit_price:<8.2f} {result} ({pnl_pct:+.2f}%)")
    else:
        print(f"{signal_time:<20} {signal:<6} {entry_price:<8.2f} {conf:<6.1%} {'?':<8} Veri yok")

# Override öncesi vs sonrası
print("\n=== OVERRIDE ÖNCESİ VS SONRASI (Son 48 saat) ===")

# 2 saat önce override başladı
cursor.execute("""
    SELECT 
        CASE WHEN timestamp > datetime('now', '-3 hours') THEN 'Override Sonrası' ELSE 'Override Öncesi' END as period,
        COUNT(*) as total_signals,
        COUNT(CASE WHEN signal IN ('BUY', 'SELL') THEN 1 END) as action_signals,
        COUNT(CASE WHEN signal = 'HOLD' THEN 1 END) as hold_signals
    FROM hybrid_analysis
    WHERE timestamp > datetime('now', '-48 hours')
    GROUP BY period
""")

for period, total, action, hold in cursor.fetchall():
    action_pct = (action / total * 100) if total > 0 else 0
    print(f"\n{period}:")
    print(f"  Toplam: {total} sinyal")
    print(f"  BUY/SELL: {action} ({action_pct:.1f}%)")
    print(f"  HOLD: {hold} ({100-action_pct:.1f}%)")

conn.close()
EOF < /dev/null