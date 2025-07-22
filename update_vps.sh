#\!/bin/bash

# VPS'te çalıştırılacak komutlar
echo "cd /opt/gold_price_analyzer && git pull && sudo systemctl restart gold-analyzer gold-web && echo 'Güncelleme tamamlandı'"
