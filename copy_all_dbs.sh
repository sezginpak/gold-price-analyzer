#!/bin/bash

echo "📦 Copying all databases from server with original names..."

# Create data directory if not exists
mkdir -p ./data

# Database files to copy
DB_FILES=(
    "gold_prices.db"
    "data/gold_analyzer.db"
    "gold_analyzer.db"
)

# Copy each database
for db in "${DB_FILES[@]}"; do
    echo "📥 Copying $db..."
    
    # Get filename only (remove path)
    filename=$(basename "$db")
    
    expect << EOF
spawn scp root@152.42.143.169:/root/gold-price-analyzer/$db ./$filename
expect {
    "password:" {
        send "sezgin64.Pak\r"
        exp_continue
    }
    "100%" {
        puts "✅ $filename copied successfully"
    }
    "No such file" {
        puts "⚠️  $filename not found on server"
    }
    eof
}
EOF
    
    # Check if file was copied
    if [ -f "./$filename" ]; then
        echo "✅ $filename: $(ls -lh ./$filename | awk '{print $5}')"
    fi
done

# Also copy the data directory version
echo "📥 Copying data/gold_analyzer.db to data/ directory..."
expect << EOF
spawn scp root@152.42.143.169:/root/gold-price-analyzer/data/gold_analyzer.db ./data/gold_analyzer.db
expect {
    "password:" {
        send "sezgin64.Pak\r"
        exp_continue
    }
    "100%" {
        puts "✅ data/gold_analyzer.db copied successfully"
    }
    eof
}
EOF

echo ""
echo "📊 Database files summary:"
echo "========================"
ls -lh *.db 2>/dev/null || echo "No .db files in root"
echo ""
echo "Data directory:"
ls -lh data/*.db 2>/dev/null || echo "No .db files in data/"