#!/usr/bin/env python3
"""
Debug log'larını aktif et
"""
import os

print("=== DEBUG LOG'LARINI AKTİF ET ===\n")

# main.py'de logger level'ı DEBUG yap
main_py_fix = '''
# main.py başında logger setup kısmı
import logging
from utils.logger import setup_logger

# Debug için log level'ı değiştir
logger = setup_logger(__name__, log_level=logging.DEBUG)

# Ayrıca signal_combiner için özel debug logger
signal_logger = logging.getLogger('strategies.hybrid.signal_combiner')
signal_logger.setLevel(logging.DEBUG)
'''

# signal_combiner.py'ye daha fazla debug log ekle
signal_combiner_debug = '''
# combine_signals metodunun başına ekle
logger.debug(f"📍 SIGNAL COMBINE START - Timeframe: {timeframe}")
logger.debug(f"   Gram: {gram_signal.get('signal')} ({gram_signal.get('confidence', 0):.2%})")
logger.debug(f"   Global: {global_trend.get('trend_direction')}")
logger.debug(f"   Volatility: {market_volatility:.3f}%")

# _apply_filters sonrasına ekle
logger.debug(f"🎯 AFTER FILTERS - Signal: {final_signal}, Original: {original_signal}")
'''

print("📝 YAPILACAKLAR:")
print("1. main.py'de logger level'ı DEBUG yap")
print("2. signal_combiner logger'ını da DEBUG yap")
print("3. Kritik noktalara debug log ekle")
print("4. Deploy et ve log'ları kontrol et")

print("\n🔍 KONTROL EDİLECEKLER:")
print("- Gram signal nedir?")
print("- Filter'a girmeden önce signal nedir?")
print("- Filter'dan sonra signal nedir?")
print("- Confidence threshold check sonucu nedir?")

# Logger config dosyasını kontrol et
print("\n📄 LOGGER CONFIG:")
if os.path.exists('/root/gold-price-analyzer/utils/logger.py'):
    with open('/root/gold-price-analyzer/utils/logger.py', 'r') as f:
        content = f.read()
        if 'DEBUG' in content:
            print("✅ Logger'da DEBUG modu var")
        else:
            print("❌ Logger'da DEBUG modu yok, eklenmeli")

# Environment variable ile debug açma
print("\n🔧 HIZLI ÇÖZÜM:")
print("export LOG_LEVEL=DEBUG")
print("sudo systemctl restart gold-analyzer")

with open('debug_enable_commands.sh', 'w') as f:
    f.write('''#!/bin/bash
# Debug log'ları aç
export LOG_LEVEL=DEBUG

# Config'e debug ekle
echo "LOG_LEVEL=DEBUG" >> /root/gold-price-analyzer/.env

# Servisi restart et
sudo systemctl restart gold-analyzer

# Log'ları takip et
echo "Debug log'lar aktif. İzlemek için:"
echo "tail -f /root/gold-price-analyzer/logs/gold_analyzer.log | grep -E 'FILTER|SIGNAL COMBINER|confidence'"
''')