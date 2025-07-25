#!/usr/bin/env python3
"""
Strateji optimizasyon scripti - En iyi parametreleri bul
"""
import sys
sys.path.insert(0, '.')

from strategies.hybrid.signal_combiner import SignalCombiner
from strategies.hybrid.confluence_manager import ConfluenceManager
from strategies.hybrid.divergence_manager import DivergenceManager
from strategies.hybrid.structure_manager import StructureManager
from strategies.hybrid.momentum_manager import MomentumManager
from strategies.hybrid.smart_money_manager import SmartMoneyManager
from datetime import datetime, timedelta
import json

class StrategyOptimizer:
    def __init__(self):
        self.test_configs = []
        self.results = []
        
    def create_test_configs(self):
        """Test edilecek konfigürasyonları oluştur"""
        
        # Config 1: Mevcut (Original)
        self.test_configs.append({
            'name': 'Original',
            'min_confidence': {'15m': 0.50, '1h': 0.55, '4h': 0.60, '1d': 0.55},
            'bearish_filter': True,
            'rsi_boost': False,
            'divergence_required': False
        })
        
        # Config 2: Akıllı Dip Yakalama
        self.test_configs.append({
            'name': 'Smart Dip',
            'min_confidence': {'15m': 0.45, '1h': 0.50, '4h': 0.55, '1d': 0.50},
            'bearish_filter': False,
            'rsi_boost': True,
            'divergence_required': False,
            'bearish_dip_rules': {
                'rsi_threshold': 35,
                'divergence_boost': 0.15,
                'momentum_exhaustion_boost': 0.10,
                'bb_lower_boost': 0.10
            }
        })
        
        # Config 3: Balanced 
        self.test_configs.append({
            'name': 'Balanced',
            'min_confidence': {'15m': 0.48, '1h': 0.52, '4h': 0.57, '1d': 0.52},
            'bearish_filter': 'partial',  # Sadece RSI > 50 ise engelle
            'rsi_boost': True,
            'divergence_required': False
        })
        
        # Config 4: High Quality
        self.test_configs.append({
            'name': 'High Quality',
            'min_confidence': {'15m': 0.55, '1h': 0.60, '4h': 0.65, '1d': 0.60},
            'bearish_filter': False,
            'rsi_boost': True,
            'divergence_required': True,  # Divergence zorunlu
            'min_divergence_score': 5
        })
        
        # Config 5: Jeweler Special (Kuyumcu Özel)
        self.test_configs.append({
            'name': 'Jeweler Special',
            'min_confidence': {'15m': 0.52, '1h': 0.56, '4h': 0.60, '1d': 0.55},
            'bearish_filter': False,
            'rsi_boost': True,
            'divergence_required': False,
            'jeweler_mode': True,
            'daily_signal_target': 3,  # Günde 3 sinyal hedefi
            'min_profit_target': 0.6  # %0.6 minimum kar hedefi
        })
        
    def simulate_config(self, config):
        """Bir konfigürasyonu simüle et"""
        print(f"\n📊 Testing: {config['name']}")
        print("-" * 50)
        
        # Simülasyon parametreleri
        buy_signals = 0
        sell_signals = 0
        successful_buys = 0
        successful_sells = 0
        
        # Örnek senaryolar (gerçek veriden alınabilir)
        scenarios = [
            # (trend, rsi, divergence, price_action, expected_success)
            ('BEARISH', 28, 'BULLISH', 'support_bounce', True),  # İyi dip
            ('BEARISH', 45, None, 'downtrend', False),  # Kötü giriş
            ('BULLISH', 35, 'BULLISH', 'pullback', True),  # İyi alım
            ('NEUTRAL', 72, 'BEARISH', 'resistance', True),  # İyi satım
            ('BEARISH', 25, None, 'freefall', False),  # Riskli dip
        ]
        
        for trend, rsi, divergence, price_action, expected in scenarios:
            # Config'e göre sinyal üret
            signal = self.generate_signal(config, trend, rsi, divergence, price_action)
            
            if signal == 'BUY':
                buy_signals += 1
                if expected:
                    successful_buys += 1
            elif signal == 'SELL':
                sell_signals += 1
                if expected:
                    successful_sells += 1
        
        # Sonuçları hesapla
        total_signals = buy_signals + sell_signals
        successful_total = successful_buys + successful_sells
        
        result = {
            'name': config['name'],
            'total_signals': total_signals,
            'buy_signals': buy_signals,
            'sell_signals': sell_signals,
            'success_rate': (successful_total / total_signals * 100) if total_signals > 0 else 0,
            'buy_success': (successful_buys / buy_signals * 100) if buy_signals > 0 else 0,
            'sell_success': (successful_sells / sell_signals * 100) if sell_signals > 0 else 0
        }
        
        self.results.append(result)
        
        # Sonuçları yazdır
        print(f"Total Signals: {total_signals}")
        print(f"BUY: {buy_signals} (Success: {result['buy_success']:.1f}%)")
        print(f"SELL: {sell_signals} (Success: {result['sell_success']:.1f}%)")
        print(f"Overall Success: {result['success_rate']:.1f}%")
        
    def generate_signal(self, config, trend, rsi, divergence, price_action):
        """Config'e göre sinyal üret"""
        confidence = 0.5
        
        # RSI boost
        if config.get('rsi_boost'):
            if rsi < 30:
                confidence += 0.20
            elif rsi < 40:
                confidence += 0.10
            elif rsi > 70:
                confidence += 0.15
        
        # Divergence
        if divergence:
            if divergence == 'BULLISH':
                confidence += 0.15
            elif divergence == 'BEARISH':
                confidence += 0.10
        
        # BEARISH filter
        if config.get('bearish_filter'):
            if trend == 'BEARISH' and rsi < 50:
                if config['bearish_filter'] == True:
                    return 'HOLD'
                elif config['bearish_filter'] == 'partial':
                    confidence -= 0.10
        
        # Smart dip rules
        if config.get('bearish_dip_rules') and trend == 'BEARISH':
            if rsi < config['bearish_dip_rules']['rsi_threshold']:
                confidence += 0.15
                if divergence == 'BULLISH':
                    confidence += config['bearish_dip_rules']['divergence_boost']
        
        # Sinyal kararı
        min_conf = config['min_confidence'].get('15m', 0.5)
        
        if rsi < 40 and confidence >= min_conf:
            return 'BUY'
        elif rsi > 65 and confidence >= min_conf:
            return 'SELL'
        else:
            return 'HOLD'
    
    def find_best_config(self):
        """En iyi konfigürasyonu bul"""
        print("\n" + "="*60)
        print("ÖZET SONUÇLAR")
        print("="*60)
        
        # Sonuçları sırala
        sorted_results = sorted(self.results, key=lambda x: x['success_rate'], reverse=True)
        
        for i, result in enumerate(sorted_results):
            print(f"\n{i+1}. {result['name']}")
            print(f"   Başarı Oranı: {result['success_rate']:.1f}%")
            print(f"   BUY Başarısı: {result['buy_success']:.1f}%")
            print(f"   Toplam Sinyal: {result['total_signals']}")
        
        # En iyi config
        best = sorted_results[0]
        print(f"\n🏆 EN İYİ KONFİGÜRASYON: {best['name']}")
        
        # Öneriler
        print("\n💡 UYGULAMA ÖNERİLERİ:")
        if best['name'] == 'Smart Dip':
            print("1. BEARISH trend filtresini kaldır")
            print("2. RSI < 35 durumunda confidence boost ekle")
            print("3. Bullish divergence'a ekstra ağırlık ver")
            print("4. Minimum confidence'ı %45-50 aralığında tut")
        elif best['name'] == 'Jeweler Special':
            print("1. Günlük sinyal hedefi için confidence'ı optimize et")
            print("2. Volatilite düşük dönemlerde eşikleri gevşet")
            print("3. Destek/direnç seviyelerine yakın sinyallere öncelik ver")
        
        return best

def main():
    print("🎯 Gold Price Analyzer - Strateji Optimizasyonu")
    print("="*60)
    
    optimizer = StrategyOptimizer()
    
    # Test konfigürasyonlarını oluştur
    optimizer.create_test_configs()
    
    # Her konfigürasyonu test et
    for config in optimizer.test_configs:
        optimizer.simulate_config(config)
    
    # En iyi konfigürasyonu bul
    best_config = optimizer.find_best_config()
    
    # Uygulama kodu öner
    print("\n📝 UYGULANACAK KOD DEĞİŞİKLİKLERİ:")
    print("signal_combiner.py dosyasında:")
    print("""
    # BEARISH dip yakalama mantığı
    if gram_trend == 'BEARISH' and gram_data['indicators'].get('rsi', 50) < 35:
        # Dip yakalama fırsatı
        if divergence_signal == 'BULLISH' and divergence_data.get('total_score', 0) > 4:
            final_confidence += 0.15  # Divergence boost
            
        if momentum_data.get('exhaustion_detected'):
            final_confidence += 0.10  # Momentum exhaustion boost
            
        # RSI extreme oversold
        if gram_data['indicators'].get('rsi', 50) < 30:
            final_confidence += 0.10
    """)

if __name__ == "__main__":
    main()