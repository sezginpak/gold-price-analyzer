#!/bin/bash

echo "=== DEBUG MODU AKTİF EDİLİYOR ==="

# SSH ile VPS'e bağlan ve debug modunu aç
sshpass -p 'sezgin64.Pak' ssh root@152.42.143.169 << 'EOF'
cd /root/gold-price-analyzer

# .env dosyasına LOG_LEVEL ekle
if ! grep -q "LOG_LEVEL" .env 2>/dev/null; then
    echo "LOG_LEVEL=DEBUG" >> .env
    echo "✅ LOG_LEVEL=DEBUG eklendi"
else
    # Varsa DEBUG yap
    sed -i 's/LOG_LEVEL=.*/LOG_LEVEL=DEBUG/' .env
    echo "✅ LOG_LEVEL=DEBUG olarak güncellendi"
fi

# utils/logger.py'de default level'ı kontrol et
echo -e "\n📄 Logger config kontrolü:"
grep -n "logging.INFO\|logging.DEBUG" utils/logger.py | head -5

# Servisi yeniden başlat
echo -e "\n🔄 Servis yeniden başlatılıyor..."
sudo systemctl restart gold-analyzer

sleep 3

# Debug log'larını kontrol et
echo -e "\n📊 Debug log'ları aktif mi?"
tail -50 logs/gold_analyzer.log | grep -E "SIGNAL COMBINER|FILTER|DEBUG" | tail -10

echo -e "\n✅ Debug modu aktif! Log'ları izlemek için:"
echo "tail -f logs/gold_analyzer.log | grep -E 'FILTER|SIGNAL COMBINER|confidence'"

EOF