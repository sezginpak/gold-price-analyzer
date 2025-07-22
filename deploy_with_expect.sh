#!/usr/bin/expect -f

set timeout 150

spawn ssh root@152.42.143.169

expect {
    "Are you sure you want to continue connecting*" {
        send "yes\r"
        expect "password:"
        send "sezgin64.Pak\r"
    }
    "password:" {
        send "sezgin64.Pak\r"
    }
}

expect "~#"
send "cd /root/gold-price-analyzer\r"
expect "gold-price-analyzer#"

send "echo '=== Git Pull ==='\r"
expect "gold-price-analyzer#"
send "git pull\r"
expect "gold-price-analyzer#"

send "echo ''\r"
expect "gold-price-analyzer#"
send "echo '=== Stopping old process ==='\r"
expect "gold-price-analyzer#"
send "pkill -f main.py\r"
expect "gold-price-analyzer#"
send "sleep 2\r"
expect "gold-price-analyzer#"

send "echo ''\r"
expect "gold-price-analyzer#"
send "echo '=== Starting new process ==='\r"
expect "gold-price-analyzer#"
send "nohup ./venv/bin/python main.py > /tmp/gold_analyzer.log 2>&1 &\r"
expect "gold-price-analyzer#"

send "echo 'Process started, waiting 120 seconds for analysis...'\r"
expect "gold-price-analyzer#"
send "sleep 120\r"
expect "gold-price-analyzer#"

send "echo ''\r"
expect "gold-price-analyzer#"
send "echo '=== Signal Count (Last 10 minutes) ==='\r"
expect "gold-price-analyzer#"
send "sqlite3 gold_prices.db \"SELECT signal, COUNT(*) as count FROM hybrid_analysis WHERE datetime(timestamp) > datetime('now', '-10 minutes') GROUP BY signal;\"\r"
expect "gold-price-analyzer#"

send "echo ''\r"
expect "gold-price-analyzer#"
send "echo '=== Last 10 Analyses ==='\r"
expect "gold-price-analyzer#"
send "sqlite3 gold_prices.db \"SELECT datetime(timestamp), gram_price, signal, confidence, signal_strength FROM hybrid_analysis ORDER BY timestamp DESC LIMIT 10;\"\r"
expect "gold-price-analyzer#"

send "echo ''\r"
expect "gold-price-analyzer#"
send "echo '=== Recent Log Output ==='\r"
expect "gold-price-analyzer#"
send "tail -50 /tmp/gold_analyzer.log\r"
expect "gold-price-analyzer#"

send "exit\r"
expect eof