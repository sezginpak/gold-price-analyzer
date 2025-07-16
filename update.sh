#!/bin/bash

# Gold Price Analyzer - Auto Update Script
# VPS'de projeyi güncellemek için kullanılır

echo "🔄 Gold Price Analyzer güncelleniyor..."

# Proje dizinine git
cd /opt/gold_price_analyzer || exit 1

# Mevcut branch'i kontrol et
CURRENT_BRANCH=$(git branch --show-current)
echo "📌 Mevcut branch: $CURRENT_BRANCH"

# Değişiklikleri çek
echo "📥 GitHub'dan güncellemeler çekiliyor..."
git fetch origin

# Local değişiklikler var mı kontrol et
if [[ -n $(git status -s) ]]; then
    echo "⚠️  Local değişiklikler tespit edildi!"
    echo "Devam etmek için bu değişiklikleri temizlemek gerekiyor."
    read -p "Local değişiklikleri silmek istiyor musunuz? (y/n): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        git reset --hard
        echo "✅ Local değişiklikler temizlendi"
    else
        echo "❌ Güncelleme iptal edildi"
        exit 1
    fi
fi

# Pull yap
echo "📦 Güncellemeler uygulanıyor..."
git pull origin $CURRENT_BRANCH

# Sanal ortamı aktive et
echo "🐍 Python sanal ortamı aktive ediliyor..."
source venv/bin/activate

# Bağımlılıkları güncelle
echo "📚 Python bağımlılıkları güncelleniyor..."
pip install -r requirements.txt --upgrade

# Veritabanı migration'ları kontrol et (eğer varsa)
if [ -f "migrate.py" ]; then
    echo "🗄️  Veritabanı migration'ları çalıştırılıyor..."
    python migrate.py
fi

# Servisi yeniden başlat
echo "🔄 Gold Analyzer servisi yeniden başlatılıyor..."
sudo systemctl restart gold-analyzer

# Servis durumunu kontrol et
sleep 2
if systemctl is-active --quiet gold-analyzer; then
    echo "✅ Servis başarıyla başlatıldı!"
    echo "📊 Servis durumu:"
    sudo systemctl status gold-analyzer --no-pager | head -n 10
else
    echo "❌ Servis başlatılamadı!"
    echo "Hata detayları için: sudo journalctl -u gold-analyzer -n 50"
    exit 1
fi

# Web sunucuyu yeniden başlat (eğer nginx kullanılıyorsa)
if systemctl is-enabled --quiet nginx; then
    echo "🌐 Nginx yeniden başlatılıyor..."
    sudo systemctl reload nginx
fi

echo "✅ Güncelleme tamamlandı!"
echo "🌐 Dashboard: http://$(hostname -I | awk '{print $1}'):80"
echo "📝 Logları görmek için: sudo journalctl -u gold-analyzer -f"