#!/bin/bash
# VPS Deployment Script

echo "🚀 Gold Price Analyzer VPS Deployment"
echo "===================================="

# Renk kodları
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# VPS bilgileri
read -p "VPS IP Adresi: " VPS_IP
read -p "VPS Kullanıcı (default: root): " VPS_USER
VPS_USER=${VPS_USER:-root}

echo -e "\n${YELLOW}1. VPS'e bağlanılıyor...${NC}"

# Deployment script'ini oluştur
cat > /tmp/vps_setup.sh << 'EOF'
#!/bin/bash

# Sistem güncelleme
echo "📦 Sistem güncelleniyor..."
apt update && apt upgrade -y

# Gerekli paketler
echo "🔧 Paketler yükleniyor..."
apt install -y python3 python3-pip python3-venv git nginx certbot python3-certbot-nginx

# Firewall ayarları
echo "🔥 Firewall ayarlanıyor..."
ufw allow 22/tcp
ufw allow 80/tcp
ufw allow 443/tcp
ufw allow 8080/tcp
ufw --force enable

# Proje dizini
echo "📁 Proje kuruluyor..."
cd /opt
if [ -d "gold_price_analyzer" ]; then
    cd gold_price_analyzer
    git pull
else
    git clone https://github.com/YOUR_USERNAME/gold_price_analyzer.git
    cd gold_price_analyzer
fi

# Python environment
echo "🐍 Python environment kuruluyor..."
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
pip install uvicorn jinja2 python-multipart

# Dizinleri oluştur
mkdir -p logs signals data templates

# Systemd service
echo "⚙️ Systemd service kuruluyor..."
cat > /etc/systemd/system/gold-analyzer.service << 'SERVICE'
[Unit]
Description=Gold Price Analyzer with Web Dashboard
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/gold_price_analyzer
Environment="PATH=/opt/gold_price_analyzer/venv/bin:/usr/local/bin:/usr/bin:/bin"
Environment="PYTHONUNBUFFERED=1"
ExecStart=/opt/gold_price_analyzer/venv/bin/python main_with_web.py
Restart=always
RestartSec=30

[Install]
WantedBy=multi-user.target
SERVICE

# Nginx config
echo "🌐 Nginx ayarlanıyor..."
cat > /etc/nginx/sites-available/gold-analyzer << 'NGINX'
server {
    listen 80;
    server_name _;
    
    location / {
        proxy_pass http://localhost:8080;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
    
    location /ws {
        proxy_pass http://localhost:8080/ws;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "Upgrade";
        proxy_set_header Host $host;
    }
}
NGINX

ln -sf /etc/nginx/sites-available/gold-analyzer /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default

# Servisleri başlat
echo "🚀 Servisler başlatılıyor..."
systemctl daemon-reload
systemctl enable gold-analyzer
systemctl start gold-analyzer
systemctl restart nginx

echo "✅ Kurulum tamamlandı!"
echo "🌐 Web arayüzüne http://$(curl -s ifconfig.me) adresinden erişebilirsiniz"
EOF

# Script'i VPS'e kopyala ve çalıştır
echo -e "\n${YELLOW}2. Kurulum script'i VPS'e kopyalanıyor...${NC}"
scp /tmp/vps_setup.sh ${VPS_USER}@${VPS_IP}:/tmp/

echo -e "\n${YELLOW}3. Kurulum başlatılıyor...${NC}"
ssh ${VPS_USER}@${VPS_IP} "chmod +x /tmp/vps_setup.sh && /tmp/vps_setup.sh"

echo -e "\n${GREEN}✅ Deployment tamamlandı!${NC}"
echo -e "${GREEN}🌐 Web arayüzü: http://${VPS_IP}${NC}"
echo -e "${YELLOW}📊 Durumu kontrol et: ssh ${VPS_USER}@${VPS_IP} 'systemctl status gold-analyzer'${NC}"