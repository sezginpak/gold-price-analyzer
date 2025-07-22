#!/bin/bash

# SSH connection details
HOST="152.42.143.169"
USER="root"
PASS="sezgin64.Pak"

# Execute commands on remote server
sshpass -p "$PASS" ssh -o StrictHostKeyChecking=no $USER@$HOST << 'EOF'
cd /root/gold-price-analyzer
echo "=== Git Pull ==="
git pull
echo ""
echo "=== Stopping old process ==="
pkill -f main.py
sleep 2
echo ""
echo "=== Starting new process ==="
nohup ./venv/bin/python main.py > /tmp/gold_analyzer.log 2>&1 &
echo "Process started with PID: $!"
echo ""
echo "Waiting 120 seconds for analysis to complete..."
sleep 120
echo ""
echo "=== Signal Count (Last 10 minutes) ==="
sqlite3 gold_prices.db "SELECT signal, COUNT(*) as count FROM hybrid_analysis WHERE datetime(timestamp) > datetime('now', '-10 minutes') GROUP BY signal;"
echo ""
echo "=== Last 10 Analyses ==="
sqlite3 gold_prices.db "SELECT datetime(timestamp), gram_price, signal, confidence, signal_strength FROM hybrid_analysis ORDER BY timestamp DESC LIMIT 10;"
echo ""
echo "=== Recent Log Output ==="
tail -50 /tmp/gold_analyzer.log
EOF