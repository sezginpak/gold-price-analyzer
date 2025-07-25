#!/bin/bash

echo "=== DEBUG LOG DÜZELTME ==="

sshpass -p 'sezgin64.Pak' ssh root@152.42.143.169 << 'EOF'
cd /root/gold-price-analyzer

# .env'i temizle ve düzelt
echo "📝 .env dosyası düzeltiliyor..."
grep -v "LOG_LEVEL" .env > .env.tmp && mv .env.tmp .env
echo "LOG_LEVEL=DEBUG" >> .env

# Systemd service dosyasına environment ekle
echo -e "\n🔧 Systemd service'e LOG_LEVEL ekleniyor..."
sudo sed -i '/\[Service\]/a Environment="LOG_LEVEL=DEBUG"' /etc/systemd/system/gold-analyzer.service

# Systemd'yi reload et
sudo systemctl daemon-reload

# Logger.py'yi kontrol et ve DEBUG olduğundan emin ol
echo -e "\n📄 logger.py kontrolü:"
sed -i 's/log_level = logging.INFO/log_level = logging.DEBUG/g' utils/logger.py

# Servisi restart et
echo -e "\n🔄 Servis restart ediliyor..."
sudo systemctl restart gold-analyzer

sleep 5

# Test log yaz
echo -e "\n🧪 Test log yazılıyor..."
python3 -c "
import sys
sys.path.insert(0, '.')
from strategies.hybrid.signal_combiner import SignalCombiner
import logging

# Force debug
logging.getLogger().setLevel(logging.DEBUG)
for handler in logging.getLogger().handlers:
    handler.setLevel(logging.DEBUG)

# Test
logger = logging.getLogger('strategies.hybrid.signal_combiner')
logger.debug('TEST: Debug log çalışıyor mu?')
print('Test log yazıldı')
"

# Log'ları kontrol et
echo -e "\n📊 Son debug log'ları:"
tail -100 logs/gold_analyzer.log | grep -i "debug\|filter\|signal combiner" | tail -20

echo -e "\n✅ Debug log düzeltmesi tamamlandı!"
EOF