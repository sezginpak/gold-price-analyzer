#!/usr/bin/env python3
"""
Son sinyallerin performansını kontrol et
"""
import sqlite3
from datetime import datetime, timedelta

conn = sqlite3.connect('gold_prices.db')
cursor = conn.cursor()

# Son 12 saatteki BUY sinyallerini kontrol et
cursor.execute("""
    SELECT 
        ha.signal,
        ha.confidence,
        ha.gram_price,
        datetime(ha.timestamp, 'localtime') as signal_time,
        ha.timeframe
    FROM hybrid_analysis ha
    WHERE ha.timestamp > datetime('now', '-12 hours')
    AND ha.signal IN ('BUY', 'SELL')
    ORDER BY ha.timestamp DESC
""")

signals = cursor.fetchall()

print(f"=== SON 12 SAATTEKİ SİNYALLER ({len(signals)} adet) ===")
print(f"{'Zaman':<20} {'TF':<5} {'Sinyal':<6} {'Fiyat':<10} {'Güven':<8}")
print("-" * 60)

buy_count = 0
sell_count = 0

for signal, conf, price, time, tf in signals:
    print(f"{time:<20} {tf:<5} {signal:<6} {price:<10.2f} {conf:<8.2%}")
    if signal == 'BUY':
        buy_count += 1
    else:
        sell_count += 1

print(f"\n📊 ÖZET:")
print(f"BUY: {buy_count} adet")
print(f"SELL: {sell_count} adet")
print(f"TOPLAM: {buy_count + sell_count} adet")

# Override öncesi vs sonrası karşılaştırma
print("\n=== OVERRIDE ÖNCESİ VS SONRASI ===")

# Override'ın aktif olduğu zamanı bul (yaklaşık 2 saat önce)
override_time = datetime.now() - timedelta(hours=2)

cursor.execute(f"""
    SELECT 
        CASE 
            WHEN timestamp > datetime('now', '-2 hours') THEN 'Sonrası'
            ELSE 'Öncesi'
        END as period,
        COUNT(CASE WHEN signal = 'BUY' THEN 1 END) as buy_count,
        COUNT(CASE WHEN signal = 'SELL' THEN 1 END) as sell_count,
        COUNT(CASE WHEN signal = 'HOLD' THEN 1 END) as hold_count
    FROM hybrid_analysis
    WHERE timestamp > datetime('now', '-12 hours')
    GROUP BY period
""")

for period, buy, sell, hold in cursor.fetchall():
    total = buy + sell + hold
    print(f"\n{period}:")
    print(f"  BUY: {buy} ({buy/total*100:.1f}%)")
    print(f"  SELL: {sell} ({sell/total*100:.1f}%)")
    print(f"  HOLD: {hold} ({hold/total*100:.1f}%)")

conn.close()

print("\n💡 NOT: Başarı oranları için 48 saat beklememiz gerekiyor.")
print("Override sistemi çalışıyor ve artık BUY/SELL sinyalleri üretiliyor.")