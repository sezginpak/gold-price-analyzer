#!/usr/bin/env python3
"""
Son düzeltme - Confidence threshold problemi
"""

print("=== PROBLEM ANALİZİ ===")
print("- Gram analyzer BUY/SELL sinyali veriyor (confidence %40-50)")
print("- Ama hybrid_analysis'te hepsi HOLD olarak kaydediliyor")
print("- BEARISH + RSI 20 durumunda bile HOLD")
print("\n🔍 SEBEP: Signal combiner'da confidence eşikleri hala yüksek olabilir")

print("\n💡 ÇÖZÜM:")
print("1. Confidence eşiklerini daha da düşür")
print("2. BEARISH dip için özel muafiyet ekle")

# utils/constants.py için yeni değerler
constants_fix = '''
# Timeframe bazlı minimum güven eşikleri
MIN_CONFIDENCE_THRESHOLDS: Dict[str, float] = {
    "15m": 0.25,  # %25 - Agresif sinyal üretimi
    "1h": 0.30,   # %30 - Dengeli
    "4h": 0.35,   # %35 - Uzun vade
    "1d": 0.30    # %30 - Günlük
}
'''

# signal_combiner.py için ek fix
combiner_fix = '''
# _apply_filters metodunda - line 308 civarı
# Eğer gram analizi güçlü sinyal veriyorsa filter'ı bypass et
gram_signal = self._last_gram_signal if hasattr(self, '_last_gram_signal') else None
if gram_signal and gram_signal.get('signal') in ['BUY', 'SELL']:
    gram_conf = gram_signal.get('confidence', 0)
    if gram_conf >= 0.4:  # Gram %40+ güven varsa
        logger.debug(f"🎯 FILTER: Bypassing for strong gram signal ({gram_conf:.2%})")
        # Sinyal gücü belirleme
        strength = self._calculate_signal_strength(confidence, risk_level)
        return signal, strength
'''

print("\n📝 UYGULAMA:")
print("1. utils/constants.py'de MIN_CONFIDENCE_THRESHOLDS'u %25-35'e düşür")
print("2. signal_combiner.py'de gram signal bypass ekle")
print("3. Deploy et ve test et")

print("\n✅ BEKLENEN SONUÇ:")
print("- BEARISH + RSI<30 durumunda BUY sinyali")
print("- Günde 3-5 sinyal")
print("- Confidence %40+ olan gram sinyalleri geçecek")

with open('final_constants_fix.txt', 'w') as f:
    f.write(constants_fix)

with open('final_combiner_fix.txt', 'w') as f:
    f.write(combiner_fix)

print("\n📄 Fix dosyaları oluşturuldu:")
print("- final_constants_fix.txt")
print("- final_combiner_fix.txt")