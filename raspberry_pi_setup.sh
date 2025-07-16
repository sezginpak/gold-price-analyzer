#!/bin/bash
# Raspberry Pi Gold Analyzer Kurulum Script'i

echo "🍓 Raspberry Pi Gold Analyzer Kurulumu Başlıyor..."

# 1. Sistem güncellemesi
echo "📦 Sistem güncelleniyor..."
sudo apt update && sudo apt upgrade -y

# 2. Gerekli paketler
echo "🔧 Paketler yükleniyor..."
sudo apt install -y python3-pip python3-venv git sqlite3 htop

# 3. Swap alanı (RAM az ise)
echo "💾 Swap alanı ayarlanıyor..."
sudo dphys-swapfile swapoff
sudo sed -i 's/CONF_SWAPSIZE=100/CONF_SWAPSIZE=1024/g' /etc/dphys-swapfile
sudo dphys-swapfile setup
sudo dphys-swapfile swapon

# 4. Proje dizini
echo "📁 Proje kuruluyor..."
cd /home/pi
git clone <your-repo-url> gold_price_analyzer
cd gold_price_analyzer

# 5. Python environment
echo "🐍 Python environment kuruluyor..."
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# 6. Systemd service
echo "⚙️ Servis ayarlanıyor..."
sudo tee /etc/systemd/system/gold-analyzer.service > /dev/null << EOF
[Unit]
Description=Gold Price Analyzer
After=network.target

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/gold_price_analyzer
Environment="PATH=/home/pi/gold_price_analyzer/venv/bin:/usr/local/bin:/usr/bin:/bin"
ExecStart=/home/pi/gold_price_analyzer/venv/bin/python main_robust.py
Restart=always
RestartSec=30

[Install]
WantedBy=multi-user.target
EOF

# 7. Servisi başlat
echo "🚀 Servis başlatılıyor..."
sudo systemctl daemon-reload
sudo systemctl enable gold-analyzer
sudo systemctl start gold-analyzer

# 8. Log rotation
echo "📋 Log rotation ayarlanıyor..."
sudo tee /etc/logrotate.d/gold-analyzer > /dev/null << EOF
/home/pi/gold_price_analyzer/logs/*.log {
    daily
    rotate 7
    compress
    delaycompress
    missingok
    notifempty
    create 0644 pi pi
}
EOF

echo "✅ Kurulum tamamlandı!"
echo "📊 Durumu kontrol et: sudo systemctl status gold-analyzer"
echo "📝 Logları izle: tail -f /home/pi/gold_price_analyzer/logs/gold_analyzer.log"