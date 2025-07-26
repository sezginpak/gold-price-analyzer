#!/usr/bin/env python3
"""Trading signal performance analyzer - Comprehensive analysis"""

import sqlite3
import pandas as pd
from datetime import datetime, timedelta
import numpy as np
import json
from collections import Counter, defaultdict
import warnings
warnings.filterwarnings('ignore')

def analyze_trading_signals():
    """Analyze trading signal performance from hybrid_analysis table"""
    
    # Farklı veritabanı dosyalarını dene
    db_files = ['gold_prices_server.db', 'gold_analyzer.db', 'data/gold_analyzer.db', 'gold_prices.db', 'data/gold_prices.db']
    
    for db_file in db_files:
        try:
            print(f"\n{'='*50}")
            print(f"Trying database: {db_file}")
            print(f"{'='*50}")
            
            # Connect to database
            conn = sqlite3.connect(db_file)
            
            # Check if hybrid_analysis table exists
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='hybrid_analysis';")
            if not cursor.fetchone():
                print(f"❌ hybrid_analysis tablosu bulunamadı")
                conn.close()
                continue
            
            # Try to read hybrid_analysis table
            query = """
            SELECT * FROM hybrid_analysis 
            ORDER BY timestamp DESC
            LIMIT 10000
            """
            
            df = pd.read_sql_query(query, conn)
            
            if len(df) > 0:
                print(f"\n✅ Başarılı! Toplam kayıt sayısı: {len(df)}")
                analyze_signals(df)
                conn.close()
                return
            else:
                print(f"❌ Tablo boş veya veri yok")
                conn.close()
                continue
                
        except sqlite3.DatabaseError as e:
            print(f"❌ Veritabanı hatası: {e}")
            
            # Try to get table schema
            try:
                conn2 = sqlite3.connect(db_file)
                cursor = conn2.cursor()
                
                # Get table names
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
                tables = cursor.fetchall()
                print("\nMevcut tablolar:")
                for table in tables:
                    print(f"- {table[0]}")
                
                conn2.close()
                
            except Exception as e2:
                print(f"Schema okuma hatası: {e2}")
    
    print("\n❌ Hiçbir veritabanından veri okunamadı!")

def analyze_signals(df):
    """Sinyal performansını analiz et"""
    
    print(f"\n📊 PERFORMANS ANALİZ RAPORU")
    print(f"========================\n")
    
    # Tarih formatını düzelt
    df['timestamp'] = pd.to_datetime(df['timestamp'], format='ISO8601')
    
    # Genel istatistikler
    print(f"🎯 GENEL PERFORMANS")
    print(f"- Toplam Sinyal Sayısı: {len(df)}")
    print(f"- Tarih Aralığı: {df['timestamp'].min()} - {df['timestamp'].max()}")
    print(f"- Ortalama Güven Seviyesi: {df['confidence'].mean():.2%}")
    
    # Sinyal dağılımı
    signal_counts = df['signal'].value_counts()
    print(f"\n📈 Sinyal Dağılımı:")
    for signal, count in signal_counts.items():
        print(f"- {signal}: {count} ({count/len(df)*100:.1f}%)")
    
    # Timeframe bazlı analiz
    print(f"\n📊 TIMEFRAME BAZLI ANALİZ")
    timeframe_stats = {}
    
    for timeframe in df['timeframe'].unique():
        tf_df = df[df['timeframe'] == timeframe]
        
        # Bu timeframe için başarı metrikleri hesapla
        buy_signals = tf_df[tf_df['signal'] == 'BUY']
        sell_signals = tf_df[tf_df['signal'] == 'SELL']
        
        # Simülasyon mantığı ile başarı oranı tahminini yap
        # Yüksek güven + iyi R/R = başarılı sinyal
        successful_buys = buy_signals[
            (buy_signals['confidence'] > 0.65) & 
            (buy_signals['risk_reward_ratio'].notna()) & 
            (buy_signals['risk_reward_ratio'] > 1.5)
        ]
        
        successful_sells = sell_signals[
            (sell_signals['confidence'] > 0.65) & 
            (sell_signals['risk_reward_ratio'].notna()) & 
            (sell_signals['risk_reward_ratio'] > 1.5)
        ]
        
        buy_success_rate = len(successful_buys) / len(buy_signals) if len(buy_signals) > 0 else 0
        sell_success_rate = len(successful_sells) / len(sell_signals) if len(sell_signals) > 0 else 0
        
        timeframe_stats[timeframe] = {
            'total': len(tf_df),
            'confidence': tf_df['confidence'].mean(),
            'buy_count': len(buy_signals),
            'sell_count': len(sell_signals),
            'buy_success_rate': buy_success_rate,
            'sell_success_rate': sell_success_rate,
            'avg_rr': tf_df['risk_reward_ratio'].mean() if tf_df['risk_reward_ratio'].notna().any() else 0
        }
        
        print(f"\n{timeframe} Timeframe:")
        print(f"- Toplam Sinyal: {len(tf_df)}")
        print(f"- Ortalama Güven: {tf_df['confidence'].mean():.2%}")
        print(f"- BUY Sinyalleri: {len(buy_signals)} (Tahmini Başarı: {buy_success_rate:.1%})")
        print(f"- SELL Sinyalleri: {len(sell_signals)} (Tahmini Başarı: {sell_success_rate:.1%})")
        print(f"- Ortalama R/R: {timeframe_stats[timeframe]['avg_rr']:.2f}")
    
    # En iyi performans gösteren timeframe
    best_timeframe = max(timeframe_stats.items(), 
                        key=lambda x: x[1]['confidence'] * (x[1]['buy_success_rate'] + x[1]['sell_success_rate']) / 2)
    print(f"\n🏆 En İyi Performans: {best_timeframe[0]} timeframe")
    
    # Sinyal gücü analizi
    print(f"\n💪 Sinyal Gücü Dağılımı:")
    strength_counts = df['signal_strength'].value_counts()
    for strength, count in strength_counts.items():
        print(f"- {strength}: {count} ({count/len(df)*100:.1f}%)")
    
    # Risk/Reward analizi
    valid_rr = df[df['risk_reward_ratio'].notna() & (df['risk_reward_ratio'] > 0)]
    if len(valid_rr) > 0:
        print(f"\n💰 Risk/Reward Analizi:")
        print(f"- Ortalama R/R Oranı: {valid_rr['risk_reward_ratio'].mean():.2f}")
        print(f"- Medyan R/R Oranı: {valid_rr['risk_reward_ratio'].median():.2f}")
        print(f"- En İyi R/R Oranı: {valid_rr['risk_reward_ratio'].max():.2f}")
        print(f"- En Kötü R/R Oranı: {valid_rr['risk_reward_ratio'].min():.2f}")
        
        # R/R > 2 olan sinyallerin oranı
        good_rr = len(valid_rr[valid_rr['risk_reward_ratio'] > 2]) / len(valid_rr)
        print(f"- R/R > 2 olan sinyal oranı: {good_rr:.1%}")
    
    # Güven seviyesi ve sinyal ilişkisi
    print(f"\n🎯 Güven Seviyesi ve Sinyal İlişkisi:")
    for signal in ['BUY', 'SELL', 'HOLD']:
        signal_df = df[df['signal'] == signal]
        if len(signal_df) > 0:
            high_conf = len(signal_df[signal_df['confidence'] > 0.7]) / len(signal_df)
            print(f"- {signal} sinyalleri:")
            print(f"  - Ortalama güven: {signal_df['confidence'].mean():.2%}")
            print(f"  - Yüksek güvenli (>70%) oran: {high_conf:.1%}")
    
    # Pozisyon büyüklüğü analizi
    print(f"\n📏 Pozisyon Büyüklüğü Analizi:")
    avg_position = df['position_size'].mean()
    print(f"- Ortalama pozisyon: {avg_position:.2f} lot")
    print(f"- Max pozisyon: {df['position_size'].max():.2f} lot")
    print(f"- Min pozisyon: {df['position_size'].min():.2f} lot")
    
    # Global trend ve currency risk analizi
    print(f"\n🌍 Global Trend ve Currency Risk:")
    global_trends = df['global_trend'].value_counts()
    for trend, count in global_trends.items():
        print(f"- {trend}: {count} ({count/len(df)*100:.1f}%)")
    
    currency_risks = df['currency_risk_level'].value_counts()
    print(f"\nCurrency Risk Dağılımı:")
    for risk, count in currency_risks.items():
        print(f"- {risk}: {count} ({count/len(df)*100:.1f}%)")
    
    # Zayıf performans alanları
    print(f"\n⚠️ ZAYIF PERFORMANS ALANLARI")
    
    # 1. Düşük güvenli sinyaller
    low_confidence = df[df['confidence'] < 0.5]
    if len(low_confidence) > 0:
        print(f"\n1. Düşük Güvenli Sinyaller (%50'nin altı):")
        print(f"   - Sayı: {len(low_confidence)} ({len(low_confidence)/len(df)*100:.1f}%)")
        print(f"   - Ortalama Güven: {low_confidence['confidence'].mean():.2%}")
        
        # Hangi timeframe'lerde yoğunlaşıyor?
        lc_timeframes = low_confidence['timeframe'].value_counts()
        print(f"   - Timeframe dağılımı:")
        for tf, count in lc_timeframes.items():
            print(f"     - {tf}: {count}")
    
    # 2. Düşük R/R oranlı sinyaller
    low_rr = df[(df['risk_reward_ratio'].notna()) & (df['risk_reward_ratio'] < 1.5)]
    if len(low_rr) > 0:
        print(f"\n2. Düşük Risk/Reward Oranlı Sinyaller (1.5'in altı):")
        print(f"   - Sayı: {len(low_rr)} ({len(low_rr)/len(df)*100:.1f}%)")
        print(f"   - Ortalama R/R: {low_rr['risk_reward_ratio'].mean():.2f}")
    
    # 3. Hold sinyali fazlalığı
    hold_ratio = len(df[df['signal'] == 'HOLD']) / len(df)
    if hold_ratio > 0.6:
        print(f"\n3. Aşırı HOLD Sinyali:")
        print(f"   - HOLD oranı: {hold_ratio:.1%}")
        print(f"   - Piyasa durgun veya strateji çok tutucu olabilir")
    
    # 4. Sinyal kalitesi skoru
    df['quality_score'] = (
        df['confidence'] * 0.4 + 
        (df['risk_reward_ratio'].fillna(1) / 3).clip(0, 1) * 0.3 +
        (df['signal_strength'].map({'STRONG': 1, 'MODERATE': 0.6, 'WEAK': 0.3}).fillna(0.5)) * 0.3
    )
    
    low_quality = df[df['quality_score'] < 0.5]
    if len(low_quality) > 0:
        print(f"\n4. Düşük Kaliteli Sinyaller:")
        print(f"   - Sayı: {len(low_quality)} ({len(low_quality)/len(df)*100:.1f}%)")
        print(f"   - En kötü performans gösteren timeframe: {low_quality['timeframe'].value_counts().index[0]}")
    
    # İyileştirme önerileri
    print(f"\n💡 İYİLEŞTİRME ÖNERİLERİ")
    
    print(f"\n1. Güven Seviyesi İyileştirmeleri:")
    if df['confidence'].mean() < 0.6:
        print(f"   ✓ Ortalama güven seviyesi düşük ({df['confidence'].mean():.2%})")
        print(f"   ✓ Teknik göstergelerin ağırlıklarını yeniden değerlendirin")
        print(f"   ✓ Daha fazla onaylayıcı sinyal bekleyin")
        print(f"   ✓ Volatilite filtresi ekleyin")
    
    print(f"\n2. Risk/Reward Optimizasyonu:")
    if valid_rr['risk_reward_ratio'].mean() < 2:
        print(f"   ✓ Ortalama R/R oranı düşük ({valid_rr['risk_reward_ratio'].mean():.2f})")
        print(f"   ✓ Take profit seviyelerini genişletin")
        print(f"   ✓ Stop loss seviyelerini daraltin")
        print(f"   ✓ ATR bazlı dinamik TP/SL kullanın")
    
    print(f"\n3. Timeframe Bazlı İyileştirmeler:")
    for timeframe, stats in timeframe_stats.items():
        if stats['confidence'] < 0.55:
            print(f"   ✓ {timeframe}: Düşük güven ({stats['confidence']:.2%})")
            print(f"     - Bu timeframe için strateji parametrelerini gözden geçirin")
            print(f"     - Daha uzun periyotlu göstergeler kullanın")
    
    print(f"\n4. Sinyal Çeşitliliği:")
    buy_sell_ratio = len(df[df['signal'].isin(['BUY', 'SELL'])]) / len(df)
    if buy_sell_ratio < 0.3:
        print(f"   ✓ Aktif sinyal oranı düşük ({buy_sell_ratio:.1%})")
        print(f"   ✓ Strateji parametrelerini daha agresif hale getirin")
        print(f"   ✓ Sinyal eşik değerlerini düşürün")
        print(f"   ✓ Trend takip stratejilerini güçlendirin")
    
    print(f"\n5. En İyi Performans Gösteren Parametreler:")
    # En iyi sinyalleri bul
    best_signals = df[df['quality_score'] > 0.7].head(10)
    if len(best_signals) > 0:
        print(f"   ✓ En başarılı sinyaller genelde:")
        common_strength = best_signals['signal_strength'].mode()[0] if len(best_signals) > 0 else 'N/A'
        print(f"     - {common_strength} sinyal gücünde")
        print(f"     - Ortalama {best_signals['confidence'].mean():.2%} güven seviyesinde")
        print(f"     - {best_signals['risk_reward_ratio'].mean():.2f} R/R oranında")
    
    # Son öneriler
    print(f"\n📌 SOMUT ADIMLAR:")
    print(f"1. hybrid_strategy.py dosyasında confidence hesaplama ağırlıklarını ayarlayın")
    print(f"2. indicators/technical_indicators.py'de RSI periyotlarını optimize edin")
    print(f"3. Stop loss hesaplamasında ATR çarpanını 2.0'dan 1.5'e düşürün")
    print(f"4. MACD parametrelerini (12,26,9) yerine (8,21,5) olarak test edin")
    print(f"5. Pattern recognition hassasiyetini artırın")
    
    # Performans özeti
    print(f"\n📊 PERFORMANS ÖZETİ:")
    overall_score = df['quality_score'].mean()
    print(f"Genel Performans Skoru: {overall_score:.2f}/1.00")
    
    if overall_score > 0.7:
        print("✅ Strateji iyi performans gösteriyor")
    elif overall_score > 0.5:
        print("⚠️ Strateji orta seviyede, iyileştirme gerekli")
    else:
        print("❌ Strateji zayıf performans gösteriyor, acil iyileştirme gerekli")

if __name__ == "__main__":
    analyze_trading_signals()