#!/bin/bash

echo "=== SON SİNYALLER ==="

sshpass -p 'sezgin64.Pak' ssh root@152.42.143.169 << 'EOF'
cd /root/gold-price-analyzer

echo -e "\n📊 Son 1 saatte üretilen BUY/SELL sinyalleri:"
sqlite3 gold_prices.db << 'SQL'
.mode column
.headers on
SELECT 
    signal,
    timeframe,
    printf("%.2f%%", confidence*100) as conf,
    datetime(timestamp, 'localtime') as time
FROM hybrid_analysis 
WHERE signal IN ('BUY', 'SELL')
AND timestamp > datetime('now', '-1 hour')
ORDER BY timestamp DESC;
SQL

echo -e "\n\n📈 Son 6 saatte sinyal dağılımı:"
sqlite3 gold_prices.db << 'SQL'
.mode column
.headers on
SELECT 
    strftime('%H', timestamp, 'localtime') as hour,
    signal,
    COUNT(*) as count
FROM hybrid_analysis 
WHERE timestamp > datetime('now', '-6 hours')
GROUP BY hour, signal
ORDER BY hour DESC, signal;
SQL

echo -e "\n\n🎯 BEARISH trend'de son durumlar:"
sqlite3 gold_prices.db << 'SQL'
.mode column
.headers on
SELECT 
    timeframe,
    signal,
    printf("%.1f", json_extract(gram_analysis, '$.indicators.rsi')) as rsi,
    printf("%.2f%%", confidence*100) as conf,
    datetime(timestamp, 'localtime') as time
FROM hybrid_analysis 
WHERE json_extract(gram_analysis, '$.trend') = 'BEARISH'
AND timestamp > datetime('now', '-2 hours')
ORDER BY timestamp DESC
LIMIT 10;
SQL

EOF