"""
Test script - Analiz değerlerinin dinamik olup olmadığını kontrol et
"""
import sqlite3
from datetime import datetime, timedelta
import json

def check_analysis_values(db_path="gold_prices.db"):
    """Veritabanındaki analiz değerlerini kontrol et"""
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Tablo var mı kontrol et
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='hybrid_analysis'
        """)
        
        if not cursor.fetchone():
            print("❌ 'hybrid_analysis' tablosu bulunamadı!")
            
            # Mevcut tabloları listele
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = cursor.fetchall()
            print("\nMevcut tablolar:")
            for table in tables:
                print(f"  - {table[0]}")
            return
        
        # Son 20 analizi getir
        cursor.execute("""
            SELECT 
                created_at,
                confidence,
                position_size,
                signal,
                signal_strength,
                global_trend,
                currency_risk_level
            FROM hybrid_analysis 
            ORDER BY created_at DESC 
            LIMIT 20
        """)
        
        results = cursor.fetchall()
        
        if not results:
            print("❌ Henüz analiz verisi yok!")
            return
        
        print(f"\n📊 Son {len(results)} Analiz Sonucu:")
        print("-" * 100)
        print(f"{'Tarih':^20} | {'Güven':^10} | {'Pozisyon':^10} | {'Sinyal':^10} | {'Güç':^10} | {'Global':^10} | {'Risk':^10}")
        print("-" * 100)
        
        confidences = []
        positions = []
        
        for row in results:
            created_at, confidence, position, signal, strength, global_trend, risk = row
            confidences.append(confidence)
            positions.append(position)
            
            # Tarihi formatla
            date_str = created_at[:19] if created_at else "N/A"
            
            print(f"{date_str:^20} | {confidence:^10.2%} | {position:^10.2%} | {signal:^10} | {strength:^10} | {global_trend:^10} | {risk:^10}")
        
        print("-" * 100)
        
        # İstatistikler
        print("\n📈 İstatistikler:")
        print(f"  Güven - Min: {min(confidences):.2%}, Max: {max(confidences):.2%}, Ortalama: {sum(confidences)/len(confidences):.2%}")
        print(f"  Pozisyon - Min: {min(positions):.2%}, Max: {max(positions):.2%}, Ortalama: {sum(positions)/len(positions):.2%}")
        
        # Tekrar eden değerler var mı?
        unique_confidences = len(set(confidences))
        unique_positions = len(set(positions))
        
        print(f"\n  Benzersiz güven değeri sayısı: {unique_confidences}/{len(confidences)}")
        print(f"  Benzersiz pozisyon değeri sayısı: {unique_positions}/{len(positions)}")
        
        if unique_confidences == 1:
            print("  ⚠️  UYARI: Tüm güven değerleri aynı!")
        if unique_positions == 1:
            print("  ⚠️  UYARI: Tüm pozisyon değerleri aynı!")
        
        # Detaylı analiz için JSON alanları
        cursor.execute("""
            SELECT 
                gram_analysis,
                global_analysis,
                currency_analysis
            FROM hybrid_analysis 
            ORDER BY created_at DESC 
            LIMIT 1
        """)
        
        latest = cursor.fetchone()
        if latest:
            print("\n📋 En Son Analiz Detayları:")
            gram, global_a, currency = latest
            
            if gram:
                gram_data = json.loads(gram)
                print(f"\n  Gram Altın Analizi:")
                print(f"    - Sinyal: {gram_data.get('signal', 'N/A')}")
                print(f"    - Güven: {gram_data.get('confidence', 0):.2%}")
                print(f"    - Trend: {gram_data.get('trend', 'N/A')}")
            
            if global_a:
                global_data = json.loads(global_a)
                print(f"\n  Global Trend:")
                print(f"    - Yön: {global_data.get('trend_direction', 'N/A')}")
                print(f"    - Güç: {global_data.get('trend_strength', 'N/A')}")
            
            if currency:
                currency_data = json.loads(currency)
                print(f"\n  Kur Riski:")
                print(f"    - Seviye: {currency_data.get('risk_level', 'N/A')}")
                print(f"    - Pozisyon Çarpanı: {currency_data.get('position_size_multiplier', 0):.2f}")
        
        conn.close()
        
    except Exception as e:
        print(f"❌ Hata: {e}")

if __name__ == "__main__":
    check_analysis_values()