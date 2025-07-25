#!/usr/bin/env python3
"""
Basit backtest analizi
"""
import sqlite3
from datetime import datetime, timedelta

def analyze_dip_opportunities():
    """Dip fırsatlarını analiz et"""
    conn = sqlite3.connect('gold_prices.db')
    cursor = conn.cursor()
    
    print("=== DİP YAKALAMA ANALİZİ ===\n")
    
    # 1. BEARISH trend'deki düşük RSI durumları
    print("1. BEARISH Trend + Düşük RSI Kombinasyonu:")
    try:
        cursor.execute('''
            SELECT COUNT(*) as total,
                   AVG(json_extract(gram_analysis, '$.indicators.rsi')) as avg_rsi
            FROM hybrid_analysis 
            WHERE json_extract(gram_analysis, '$.trend') = 'BEARISH'
            AND json_extract(gram_analysis, '$.indicators.rsi') < 40
            AND timestamp > datetime('now', '-30 days')
        ''')
        result = cursor.fetchone()
        print(f"   - Son 30 günde BEARISH + RSI<40 durumu: {result[0]} kez")
        print(f"   - Ortalama RSI: {result[1]:.1f}")
    except Exception as e:
        print(f"   Hata: {e}")
    
    # 2. Mevcut strateji analizi
    print("\n2. Mevcut BUY Sinyal Dağılımı:")
    try:
        cursor.execute('''
            SELECT json_extract(gram_analysis, '$.trend') as trend,
                   COUNT(*) as count,
                   AVG(confidence) as avg_conf
            FROM hybrid_analysis 
            WHERE signal = 'BUY'
            AND timestamp > datetime('now', '-30 days')
            GROUP BY trend
        ''')
        for row in cursor.fetchall():
            print(f"   - {row[0]}: {row[1]} sinyal (Ort. güven: {row[2]*100:.1f}%)")
    except Exception as e:
        print(f"   Hata: {e}")
    
    # 3. Optimal dip yakalama zamanları
    print("\n3. En İyi Dip Yakalama Saatleri:")
    try:
        cursor.execute('''
            SELECT strftime('%H', timestamp, 'localtime') as hour,
                   COUNT(*) as bearish_count,
                   AVG(json_extract(gram_analysis, '$.indicators.rsi')) as avg_rsi
            FROM hybrid_analysis 
            WHERE json_extract(gram_analysis, '$.trend') = 'BEARISH'
            AND timestamp > datetime('now', '-30 days')
            GROUP BY hour
            HAVING bearish_count > 5
            ORDER BY avg_rsi ASC
            LIMIT 5
        ''')
        for row in cursor.fetchall():
            print(f"   - Saat {row[0]}:00 - {row[1]} BEARISH durum, Ort. RSI: {row[2]:.1f}")
    except Exception as e:
        print(f"   Hata: {e}")
    
    conn.close()

def suggest_improved_strategy():
    """İyileştirilmiş strateji önerileri"""
    print("\n=== ÖNERİLEN DİP YAKALAMA STRATEJİSİ ===\n")
    
    print("1. AKILLI BEARISH FİLTRESİ:")
    print("   ❌ Basit engelleme: if trend == 'BEARISH': return HOLD")
    print("   ✅ Akıllı yaklaşım:")
    print("      - BEARISH + RSI < 30 → BUY (Güçlü oversold)")
    print("      - BEARISH + Bullish Divergence → BUY (Trend dönüşü)")
    print("      - BEARISH + Momentum Exhaustion → BUY (Satış tükenmesi)")
    print("      - BEARISH + Support Bounce → BUY (Destek tepkisi)")
    
    print("\n2. RİSK YÖNETİMİ:")
    print("   - BEARISH BUY için daha küçük pozisyon (0.5x)")
    print("   - Daha sıkı stop-loss (%0.3 yerine %0.5)")
    print("   - Kademeli giriş önerisi")
    
    print("\n3. GÜVEN SKORU AYARLAMASI:")
    print("   - Normal BUY: Min %50 güven")
    print("   - BEARISH dip BUY: Min %40 güven + ek kriterler")
    print("   - Divergence varsa: +%10 güven boost")
    print("   - RSI < 30 ise: +%15 güven boost")
    
    print("\n4. BAŞARI KRİTERLERİ:")
    print("   - Hedef: %50+ BUY başarı oranı")
    print("   - BEARISH dipler için: %40+ yeterli (yüksek ödül/risk)")
    print("   - Günlük 1-5 kaliteli sinyal")

# Çalıştır
if __name__ == "__main__":
    analyze_dip_opportunities()
    suggest_improved_strategy()
    
    print("\n" + "="*50)
    print("SONUÇ: BEARISH trend'de tamamen BUY engellemek yerine,")
    print("akıllı kriterlerle dip yakalama fırsatlarını değerlendirmeliyiz!")
    print("="*50)