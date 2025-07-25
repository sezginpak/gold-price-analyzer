#!/usr/bin/env python3
"""
Günlük 1-5 sinyal üretecek şekilde parametreleri optimize et
"""

print("=== SİNYAL ÜRETİM OPTİMİZASYONU ===\n")

print("📊 MEVCUT DURUM:")
print("- Son 24 saatte 0 BUY/SELL sinyali")
print("- BEARISH + RSI<40 durumlarında bile HOLD")
print("- Confidence eşikleri çok yüksek")

print("\n🎯 ÖNERİLEN DEĞİŞİKLİKLER:\n")

print("1. gram_altin_analyzer.py:")
print("""
   # Sinyal üretim eşiklerini düşür
   - if buy_signals > sell_signals and buy_signals >= total_weight * 0.25:
   + if buy_signals > sell_signals and buy_signals >= total_weight * 0.20:  # %25'ten %20'ye
   
   - elif sell_signals > buy_signals and sell_signals >= total_weight * 0.35:
   + elif sell_signals > buy_signals and sell_signals >= total_weight * 0.30:  # %35'ten %30'a
""")

print("\n2. utils/constants.py:")
print("""
   MIN_CONFIDENCE_THRESHOLDS = {
       "15m": 0.45,  # %50'den %45'e
       "1h": 0.50,   # %55'ten %50'ye  
       "4h": 0.55,   # %60'tan %55'e
       "1d": 0.50    # %55'ten %50'ye
   }
""")

print("\n3. signal_combiner.py - Dip Detection Boost:")
print("""
   # BEARISH dip yakalama için daha agresif
   if global_direction == "BEARISH" and dip_score >= 0.5:  # 0.6'dan 0.5'e düşür
       final_signal = "BUY"
       confidence = max(confidence, dip_score * 1.2)  # %20 boost ekle
""")

print("\n4. Volatilite Eşiği:")
print("""
   MIN_VOLATILITY_THRESHOLD = 0.3  # %0.5'ten %0.3'e düşür
""")

print("\n📈 BEKLENEN SONUÇLAR:")
print("- Günlük 2-5 sinyal")
print("- BEARISH dip'lerde BUY sinyali")
print("- %50-60 başarı oranı hedefi")

print("\n⚠️ RİSK YÖNETİMİ:")
print("- BEARISH BUY için pozisyon boyutu %50")
print("- Sıkı stop-loss (%1)")
print("- Kademeli giriş önerisi")

# Dosyaları güncelle
import os

def update_file(filepath, old_value, new_value, description):
    """Dosyada değişiklik yap"""
    if os.path.exists(filepath):
        with open(filepath, 'r') as f:
            content = f.read()
        
        if old_value in content:
            new_content = content.replace(old_value, new_value)
            with open(filepath, 'w') as f:
                f.write(new_content)
            print(f"\n✅ {description} - {filepath} güncellendi")
            return True
        else:
            print(f"\n❌ {description} - Değer bulunamadı: {old_value[:50]}...")
    else:
        print(f"\n❌ Dosya bulunamadı: {filepath}")
    return False

# Değişiklikleri uygula
changes = [
    # 1. Gram analyzer eşikleri
    ("analyzers/gram_altin_analyzer.py", 
     "buy_signals >= total_weight * 0.25",
     "buy_signals >= total_weight * 0.20",
     "BUY eşiği %25->%20"),
     
    ("analyzers/gram_altin_analyzer.py",
     "sell_signals >= total_weight * 0.35",
     "sell_signals >= total_weight * 0.30", 
     "SELL eşiği %35->%30"),
     
    # 2. Confidence eşikleri
    ("utils/constants.py",
     '''MIN_CONFIDENCE_THRESHOLDS: Dict[str, float] = {
    "15m": 0.50,  # %50 - 15 dakikalık için yüksek güven
    "1h": 0.55,   # %55 - 1 saatlik için orta-yüksek güven
    "4h": 0.60,   # %60 - 4 saatlik için yüksek güven
    "1d": 0.55    # %55 - Günlük için orta-yüksek güven
}''',
     '''MIN_CONFIDENCE_THRESHOLDS: Dict[str, float] = {
    "15m": 0.45,  # %45 - Daha fazla sinyal için düşürüldü
    "1h": 0.50,   # %50 - Dengeli
    "4h": 0.55,   # %55 - Uzun vade için uygun
    "1d": 0.50    # %50 - Günlük için dengeli
}''',
     "Confidence eşikleri düşürüldü"),
     
    # 3. Dip detection eşiği
    ("strategies/hybrid/signal_combiner.py",
     "if global_direction == \"BEARISH\" and dip_score >= 0.6:",
     "if global_direction == \"BEARISH\" and dip_score >= 0.5:",
     "Dip detection eşiği 0.6->0.5"),
     
    # 4. Volatilite eşiği
    ("utils/constants.py",
     "MIN_VOLATILITY_THRESHOLD = 0.5",
     "MIN_VOLATILITY_THRESHOLD = 0.3",
     "Volatilite eşiği %0.5->%0.3")
]

print("\n" + "="*50)
print("DEĞİŞİKLİKLER UYGULANACAK...")
print("="*50)

# Kullanıcıdan onay al
response = input("\nDevam edilsin mi? (e/h): ")
if response.lower() == 'e':
    for filepath, old, new, desc in changes:
        update_file(filepath, old, new, desc)
    print("\n✅ Tüm değişiklikler uygulandı!")
    print("\n🚀 Şimdi deploy yapın: ./quick_deploy.sh")
else:
    print("\n❌ İptal edildi")