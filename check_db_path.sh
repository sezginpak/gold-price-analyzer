#!/bin/bash

expect << 'EOF'
set timeout 30
spawn ssh root@152.42.143.169

expect {
    "password:" {
        send "sezgin64.Pak\r"
    }
}

expect "~#"
send "cd /root/gold-price-analyzer\r"

expect "gold-price-analyzer#"
send "find . -name '*.db' -type f 2>/dev/null | head -20\r"

expect "gold-price-analyzer#"
send "ls -la gold_prices.db 2>/dev/null || echo 'File not found in current dir'\r"

expect "gold-price-analyzer#"
send "ls -la data/ 2>/dev/null || echo 'No data directory'\r"

expect "gold-price-analyzer#"
send "exit\r"
expect eof
EOF