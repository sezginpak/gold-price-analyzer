#!/bin/bash

# Database copy script
echo "📦 Copying database from server..."

# Create backup of local database if exists
if [ -f "./data/gold_prices.db" ]; then
    echo "📋 Backing up local database..."
    cp ./data/gold_prices.db ./data/gold_prices_local_backup_$(date +%Y%m%d_%H%M%S).db
fi

# Use expect to handle password
expect << 'EOF'
spawn scp root@152.42.143.169:/root/gold-price-analyzer/gold_prices.db ./data/gold_prices_from_server.db
expect {
    "password:" {
        send "sezgin64.Pak\r"
        exp_continue
    }
    "100%" {
        puts "\n✅ Database copied successfully"
    }
    eof
}
EOF

# Check if copy was successful
if [ -f "./data/gold_prices_from_server.db" ]; then
    echo "✅ Database file copied: ./data/gold_prices_from_server.db"
    echo "📊 File size: $(ls -lh ./data/gold_prices_from_server.db | awk '{print $5}')"
    
    # Replace local database with server version
    mv ./data/gold_prices_from_server.db ./data/gold_prices.db
    echo "✅ Local database updated with server version"
else
    echo "❌ Failed to copy database"
    exit 1
fi