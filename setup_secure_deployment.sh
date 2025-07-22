#!/bin/bash
# Güvenli deployment kurulum scripti

echo "🔒 Gold Price Analyzer - Güvenli Deployment Kurulumu"
echo "=================================================="

# .env dosyası kontrolü
if [ ! -f .env ]; then
    echo "📝 .env dosyası oluşturuluyor..."
    cp .env.example .env
    echo "⚠️  Lütfen .env dosyasını düzenleyin ve VPS bilgilerini girin!"
    echo "   nano .env"
    exit 1
fi

# SSH key kontrolü
if [ ! -f ~/.ssh/id_rsa ]; then
    echo "🔑 SSH key bulunamadı. Yeni bir tane oluşturulacak..."
    ssh-keygen -t rsa -b 4096 -f ~/.ssh/id_rsa -N ""
    echo "✅ SSH key oluşturuldu!"
fi

# VPS bilgilerini .env'den oku
source .env

if [ -z "$VPS_HOST" ] || [ -z "$VPS_USER" ]; then
    echo "❌ .env dosyasında VPS_HOST ve VPS_USER tanımlı olmalı!"
    exit 1
fi

echo "🔑 SSH key'inizi VPS'e kopyalamak için şifrenizi girmeniz gerekecek:"
ssh-copy-id -i ~/.ssh/id_rsa.pub ${VPS_USER}@${VPS_HOST}

if [ $? -eq 0 ]; then
    echo "✅ SSH key başarıyla kopyalandı!"
    echo ""
    echo "🎉 Artık güvenli deployment yapabilirsiniz:"
    echo "   ./deploy_to_vps.sh"
    echo ""
    echo "📌 Not: Deployment sırasında 'SSH Key kullan' seçeneğini seçin."
else
    echo "❌ SSH key kopyalanamadı. Lütfen manuel olarak deneyin:"
    echo "   ssh-copy-id ${VPS_USER}@${VPS_HOST}"
fi