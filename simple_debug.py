#!/usr/bin/env python3
"""
Basit debug - Log'ları kontrol et
"""
import subprocess
import re

print("=== SIGNAL FLOW DEBUG - LOG ANALİZİ ===\n")

# Son 5 dakikanın log'larını al
cmd = "tail -500 /root/gold-price-analyzer/logs/gold_analyzer.log | grep -E 'Signal generation|FILTER|SIGNAL COMBINER|confidence|Final signal|override' | tail -100"
result = subprocess.run(cmd, shell=True, capture_output=True, text=True)

if result.stdout:
    print("📊 SON LOG KAYITLARI:")
    print("-" * 80)
    
    lines = result.stdout.strip().split('\n')
    
    # Farklı log tiplerini ayır
    signal_gen_logs = []
    filter_logs = []
    combiner_logs = []
    
    for line in lines:
        if 'Signal generation' in line:
            signal_gen_logs.append(line)
        elif 'FILTER' in line:
            filter_logs.append(line)
        elif 'SIGNAL COMBINER' in line or 'Final signal' in line:
            combiner_logs.append(line)
    
    # Signal generation log'ları
    if signal_gen_logs:
        print("\n1️⃣ GRAM ANALYZER - Signal Generation:")
        for log in signal_gen_logs[-5:]:  # Son 5 log
            # Extract key info
            match = re.search(r'signal=(\w+), confidence=([\d.]+)', log)
            if match:
                signal, conf = match.groups()
                print(f"   → Signal: {signal}, Confidence: {float(conf):.2%}")
                
                # Buy/sell oranları
                weights = re.search(r'buy=(\d+), sell=(\d+), total_weight=(\d+)', log)
                if weights:
                    buy, sell, total = map(int, weights.groups())
                    print(f"     (buy={buy}, sell={sell}, total={total})")
    
    # Filter log'ları
    if filter_logs:
        print("\n2️⃣ SIGNAL COMBINER - Filters:")
        for log in filter_logs[-10:]:  # Son 10 log
            print(f"   → {log.split('- ')[-1]}")
    
    # Combiner log'ları
    if combiner_logs:
        print("\n3️⃣ SIGNAL COMBINER - Final:")
        for log in combiner_logs[-5:]:  # Son 5 log
            print(f"   → {log.split('- ')[-1]}")

# Sistemd log'larını da kontrol et
print("\n\n📋 SYSTEMD LOG'LARI:")
print("-" * 80)

systemd_cmd = "sudo journalctl -u gold-analyzer -n 200 --no-pager | grep -E 'FILTER|DIP DETECTION|confidence .* for 15m' | tail -20"
systemd_result = subprocess.run(systemd_cmd, shell=True, capture_output=True, text=True)

if systemd_result.stdout:
    for line in systemd_result.stdout.strip().split('\n'):
        if 'FILTER' in line:
            # Extract filter mesajları
            parts = line.split('gold_analyzer: ')
            if len(parts) > 1:
                msg = parts[1]
                print(f"   → {msg}")

# En son hybrid_analysis kaydı
print("\n\n📊 EN SON HYBRID ANALYSIS KAYDI:")
print("-" * 80)

db_cmd = '''sqlite3 /root/gold-price-analyzer/gold_prices.db "
SELECT 
    timeframe,
    signal,
    printf('%.2f%%', confidence*100) as conf,
    datetime(timestamp, 'localtime') as time,
    json_extract(gram_analysis, '$.signal') as gram_signal,
    printf('%.1f%%', json_extract(gram_analysis, '$.confidence')*100) as gram_conf
FROM hybrid_analysis 
WHERE timeframe = '15m'
ORDER BY timestamp DESC 
LIMIT 5"
'''

db_result = subprocess.run(db_cmd, shell=True, capture_output=True, text=True)
if db_result.stdout:
    print(db_result.stdout)

print("\n💡 ANALIZ:")
print("-" * 80)
print("Yukarıdaki log'larda:")
print("1. Gram analyzer hangi sinyal veriyor?")
print("2. Filter'larda takılıyor mu?")
print("3. Final signal ne oluyor?")
print("4. Database'e ne kaydediliyor?")