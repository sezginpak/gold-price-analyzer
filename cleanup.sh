#!/bin/bash
# Cleanup script for gold-price-analyzer

echo "🧹 Gold Price Analyzer Temizlik Scripti"
echo "====================================="

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# Count files before cleanup
echo -e "${YELLOW}📊 Temizlik öncesi durum:${NC}"
echo "- __pycache__ dizinleri: $(find . -type d -name "__pycache__" | wc -l)"
echo "- .pyc dosyaları: $(find . -name "*.pyc" | wc -l)"
echo "- Log dosyaları: $(find . -name "*.log" | wc -l)"
echo "- Veritabanı dosyaları: $(find . -name "*.db" -o -name "*.sqlite" | wc -l)"

echo -e "\n${YELLOW}🗑️  Temizlenecekler:${NC}"

# 1. Python cache dosyaları
echo -e "\n1. Python cache temizleniyor..."
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null
find . -name "*.pyc" -delete
find . -name "*.pyo" -delete
find . -name "*.pyd" -delete
echo -e "${GREEN}✅ Python cache temizlendi${NC}"

# 2. Geçici dosyalar
echo -e "\n2. Geçici dosyalar temizleniyor..."
find . -name "*.tmp" -delete
find . -name "*.bak" -delete
find . -name "*~" -delete
find . -name ".DS_Store" -delete
echo -e "${GREEN}✅ Geçici dosyalar temizlendi${NC}"

# 3. Test ve log dosyaları (opsiyonel)
echo -e "\n${YELLOW}Log dosyaları bulundu:${NC}"
find . -name "*.log" -not -path "./logs/*" | while read file; do
    echo "  - $file"
done

echo -n -e "\n${YELLOW}Root dizindeki log dosyalarını silmek ister misiniz? (y/n): ${NC}"
read -r response
if [[ "$response" == "y" ]]; then
    find . -maxdepth 1 -name "*.log" -delete
    echo -e "${GREEN}✅ Root log dosyaları temizlendi${NC}"
fi

# 4. Veritabanı dosyaları (opsiyonel)
echo -e "\n${YELLOW}Lokal veritabanı dosyaları:${NC}"
find . -name "*.db" -o -name "*.sqlite" -o -name "*.sqlite3" | while read file; do
    size=$(du -h "$file" | cut -f1)
    echo "  - $file ($size)"
done

echo -n -e "\n${RED}DİKKAT: Veritabanı dosyalarını silmek ister misiniz? (y/n): ${NC}"
read -r response
if [[ "$response" == "y" ]]; then
    rm -f gold_analyzer.db gold_prices.db
    echo -e "${GREEN}✅ Veritabanı dosyaları silindi${NC}"
else
    echo -e "${YELLOW}⏭️  Veritabanı dosyaları korundu${NC}"
fi

# 5. Gereksiz olabilecek dosyalar
echo -e "\n${YELLOW}Diğer temizlenebilecek dosyalar:${NC}"
if [ -f "deploy_and_check.exp" ]; then
    echo "  - deploy_and_check.exp (eski deployment scripti)"
fi
if [ -f "create_sim_tables.py" ]; then
    echo "  - create_sim_tables.py (artık storage/ altında)"
fi

# 6. Özet
echo -e "\n${GREEN}✅ Temizlik tamamlandı!${NC}"
echo -e "\n${YELLOW}📊 Temizlik sonrası:${NC}"
echo "- Toplam dosya sayısı: $(find . -type f | wc -l)"
echo "- Python dosyaları: $(find . -name "*.py" | wc -l)"
echo "- Dizin boyutu: $(du -sh . | cut -f1)"