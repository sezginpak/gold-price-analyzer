"""
Yüksek İşlem Maliyeti Stratejisi Test Scripti
%0.45 toplam maliyet ile kar etme potansiyelini test eder
"""
import asyncio
import logging
import sqlite3
from datetime import datetime, timedelta
from typing import Dict, List

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class HighCostStrategyTester:
    """Yüksek maliyet stratejisi test edilir"""
    
    def __init__(self):
        self.db_path = "gold_prices.db"
        self.total_cost_percentage = 0.0045  # %0.45 toplam maliyet
        
    def run_tests(self):
        """Ana test fonksiyonu"""
        logger.info("=== YÜKSEK MALİYET STRATEJİSİ TESTİ BAŞLADI ===")
        logger.info(f"Toplam işlem maliyeti: {self.total_cost_percentage:.2%}")
        
        # 1. Simülasyon konfigürasyonlarını kontrol et
        self.check_simulation_configs()
        
        # 2. Minimum kar eşiklerini hesapla
        self.calculate_profit_thresholds()
        
        # 3. Teorik senaryoları test et
        self.test_theoretical_scenarios()
        
        logger.info("=== TEST TAMAMLANDI ===")
    
    def check_simulation_configs(self):
        """Simülasyon konfigürasyonlarını kontrol et"""
        logger.info("\n📊 SİMÜLASYON KONFİGÜRASYONLARI:")
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT name, min_confidence, max_risk, spread, commission_rate 
                FROM simulations 
                WHERE name LIKE 'Yüksek Maliyet%'
            """)
            
            for row in cursor.fetchall():
                name, min_conf, max_risk, spread, commission = row
                logger.info(f"  {name}:")
                logger.info(f"    Min Confidence: {min_conf:.1%}")
                logger.info(f"    Max Risk: {max_risk:.1%}")
                logger.info(f"    Spread: {spread} TL")
                logger.info(f"    Commission: {commission:.2%}")
                
                # Toplam maliyet hesapla (yaklaşık)
                # Spread %0.11 + Commission %0.10 = %0.21 tek yön x2 = %0.42 gidiş-dönüş
                estimated_cost = 0.0042  # %0.42
                logger.info(f"    Estimated Total Cost: {estimated_cost:.2%}")
                logger.info("")
            
            conn.close()
            
        except Exception as e:
            logger.error(f"Config kontrol hatası: {str(e)}")
    
    def calculate_profit_thresholds(self):
        """Kar eşiklerini hesapla"""
        logger.info("\n💰 KAR EŞİKLERİ ANALİZİ:")
        
        # Temel hesaplamalar
        spread_cost = 0.0011  # %0.11 spread
        commission_cost = 0.001  # %0.10 commission
        total_one_way = spread_cost + commission_cost  # %0.21
        total_round_trip = total_one_way * 2  # %0.42 gidiş-dönüş
        
        logger.info(f"  Spread maliyeti: {spread_cost:.2%}")
        logger.info(f"  Komisyon maliyeti: {commission_cost:.2%}")
        logger.info(f"  Tek yön toplam: {total_one_way:.2%}")
        logger.info(f"  Gidiş-dönüş toplam: {total_round_trip:.2%}")
        
        # Breakeven ve kar eşikleri
        breakeven = total_round_trip
        min_profit_target = breakeven * 1.5  # %50 üstü
        good_profit_target = breakeven * 2.0  # %100 üstü
        excellent_profit_target = breakeven * 3.0  # %200 üstü
        
        logger.info(f"\n  🎯 HEDEF EŞIKLER:")
        logger.info(f"    Breakeven: {breakeven:.2%}")
        logger.info(f"    Minimum Kar: {min_profit_target:.2%}")
        logger.info(f"    İyi Kar: {good_profit_target:.2%}")
        logger.info(f"    Mükemmel Kar: {excellent_profit_target:.2%}")
        
        # Risk/Reward oranları
        logger.info(f"\n  📈 GEREKLİ RİSK/REWARD ORANLARI:")
        for risk_pct in [0.5, 1.0, 1.5, 2.0]:
            rr_ratio = min_profit_target / (risk_pct / 100)
            logger.info(f"    {risk_pct}% risk için: {rr_ratio:.1f}:1 RR gerekli")
    
    def test_theoretical_scenarios(self):
        """Teorik senaryoları test et"""
        logger.info("\n🧪 TEORİK SENARYO TESTİ:")
        
        scenarios = [
            {
                "name": "Konservatif Strateji",
                "confidence": 0.85,
                "risk_per_trade": 0.012,  # %1.2
                "avg_rr_ratio": 5.0,
                "win_rate": 0.65,
                "trades_per_month": 8
            },
            {
                "name": "Trend Takip Stratejisi", 
                "confidence": 0.80,
                "risk_per_trade": 0.015,  # %1.5
                "avg_rr_ratio": 4.0,
                "win_rate": 0.60,
                "trades_per_month": 12
            },
            {
                "name": "Dip Yakalama Stratejisi",
                "confidence": 0.75,
                "risk_per_trade": 0.018,  # %1.8
                "avg_rr_ratio": 4.5,
                "win_rate": 0.55,
                "trades_per_month": 6
            }
        ]
        
        total_cost = 0.0042  # %0.42
        
        for scenario in scenarios:
            logger.info(f"\n  📊 {scenario['name']}:")
            
            # Hesaplamalar
            avg_win = scenario['risk_per_trade'] * scenario['avg_rr_ratio']
            avg_loss = scenario['risk_per_trade']
            win_rate = scenario['win_rate']
            
            # Beklenen getiri
            expected_return = (win_rate * avg_win) - ((1 - win_rate) * avg_loss)
            
            # Maliyet düşüldükten sonra net getiri
            net_return = expected_return - total_cost
            
            # Aylık beklenen getiri
            monthly_return = net_return * scenario['trades_per_month']
            
            logger.info(f"    Win Rate: {win_rate:.1%}")
            logger.info(f"    Avg Win: {avg_win:.2%}")
            logger.info(f"    Avg Loss: {avg_loss:.2%}")
            logger.info(f"    Gross Expected Return/Trade: {expected_return:.2%}")
            logger.info(f"    Net Return After Costs: {net_return:.2%}")
            logger.info(f"    Monthly Trades: {scenario['trades_per_month']}")
            logger.info(f"    Monthly Expected Return: {monthly_return:.2%}")
            
            # Karlılık değerlendirmesi
            if net_return > 0:
                logger.info(f"    ✅ Karlı strateji! Net getiri: {net_return:.2%}")
            else:
                logger.info(f"    ❌ Zararlı strateji! Net kayıp: {net_return:.2%}")
                
            # Minimum win rate hesapla
            min_win_rate = (avg_loss + total_cost) / (avg_win + avg_loss + total_cost)
            logger.info(f"    Minimum Win Rate for Profit: {min_win_rate:.1%}")
    
    def analyze_current_market_conditions(self):
        """Mevcut piyasa koşullarını analiz et"""
        logger.info("\n📈 PİYASA KOŞULLARI ANALİZİ:")
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Son fiyat verilerini al
            cursor.execute("""
                SELECT price, timestamp 
                FROM price_data 
                ORDER BY timestamp DESC 
                LIMIT 100
            """)
            
            prices = [row[0] for row in cursor.fetchall()]
            
            if len(prices) >= 20:
                # Volatilite hesapla
                import statistics
                recent_returns = []
                for i in range(1, min(20, len(prices))):
                    ret = (prices[i-1] - prices[i]) / prices[i]
                    recent_returns.append(ret)
                
                volatility = statistics.stdev(recent_returns) if recent_returns else 0
                avg_return = statistics.mean(recent_returns) if recent_returns else 0
                
                logger.info(f"  Günlük Volatilite: {volatility:.2%}")
                logger.info(f"  Ortalama Günlük Getiri: {avg_return:.2%}")
                
                # Yüksek maliyet için uygunluk
                min_required_volatility = 0.008  # %0.8
                if volatility >= min_required_volatility:
                    logger.info(f"  ✅ Volatilite yeterli ({volatility:.2%} >= {min_required_volatility:.2%})")
                else:
                    logger.info(f"  ⚠️  Volatilite düşük ({volatility:.2%} < {min_required_volatility:.2%})")
            
            conn.close()
            
        except Exception as e:
            logger.error(f"Piyasa analizi hatası: {str(e)}")


def main():
    """Ana fonksiyon"""
    tester = HighCostStrategyTester()
    tester.run_tests()
    
    # Sonuç özeti
    logger.info("\n" + "="*60)
    logger.info("SONUÇ ÖZETİ:")
    logger.info("="*60)
    logger.info("✅ Yüksek maliyet stratejisi şu koşullarda karlı olabilir:")
    logger.info("   • Minimum %75-85 güven skorlu sinyaller")
    logger.info("   • 4:1 veya daha yüksek Risk/Reward oranı")
    logger.info("   • %60+ win rate")
    logger.info("   • Yeterli piyasa volatilitesi (%0.8+)")
    logger.info("   • Sıkı pozisyon boyutu kontrolü")
    logger.info("   • Güçlü trend uyumu")
    logger.info("")
    logger.info("⚠️  Kritik başarı faktörleri:")
    logger.info("   • Çok seçici sinyal filtresi")
    logger.info("   • Mükemmel giriş/çıkış timing'i")
    logger.info("   • Disiplinli risk yönetimi")
    logger.info("   • Piyasa koşullarına adaptasyon")


if __name__ == "__main__":
    main()