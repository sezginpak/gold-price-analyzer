#!/bin/bash

# Gold Price Analyzer Web Service Setup Script

echo "Gold Price Analyzer Web Service kurulumu başlıyor..."

# Service dosyasını oluştur
cat > /tmp/gold-web.service << EOF
[Unit]
Description=Gold Price Analyzer Web Interface
After=network.target gold-analyzer.service

[Service]
Type=simple
User=root
WorkingDirectory=/opt/gold-price-analyzer
Environment="PYTHONPATH=/opt/gold-price-analyzer"
ExecStart=/usr/bin/python3 /opt/gold-price-analyzer/web_server.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# Service dosyasını kopyala
sudo cp /tmp/gold-web.service /etc/systemd/system/

# Systemd'yi yenile
sudo systemctl daemon-reload

# Service'i etkinleştir ve başlat
sudo systemctl enable gold-web
sudo systemctl start gold-web

# Durumu kontrol et
echo "Web service durumu:"
sudo systemctl status gold-web

echo "Web service kurulumu tamamlandı!"
echo "Web arayüzüne http://YOUR_VPS_IP:8000 adresinden erişebilirsiniz."