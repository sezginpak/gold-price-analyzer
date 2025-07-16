"""
Sistem durumunu kontrol eden basit monitoring scripti
"""
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path
import sqlite3


def check_logs():
    """Log dosyalarını kontrol et"""
    print("\n📁 LOG DOSYALARI:")
    print("-" * 40)
    
    log_dir = Path("logs")
    if not log_dir.exists():
        print("❌ Log dizini bulunamadı!")
        return
    
    for log_file in log_dir.glob("*.log"):
        size = log_file.stat().st_size / 1024 / 1024  # MB
        modified = datetime.fromtimestamp(log_file.stat().st_mtime)
        age = datetime.now() - modified
        
        status = "✅" if age < timedelta(minutes=10) else "⚠️"
        print(f"{status} {log_file.name}: {size:.2f} MB, Son güncelleme: {age}")


def check_database():
    """Veritabanı durumunu kontrol et"""
    print("\n💾 VERİTABANI:")
    print("-" * 40)
    
    db_path = "gold_prices.db"
    if not os.path.exists(db_path):
        print("❌ Veritabanı bulunamadı!")
        return
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Toplam kayıt
        cursor.execute("SELECT COUNT(*) FROM price_data")
        total = cursor.fetchone()[0]
        
        # Son kayıt
        cursor.execute("SELECT timestamp FROM price_data ORDER BY timestamp DESC LIMIT 1")
        last_record = cursor.fetchone()
        
        if last_record:
            last_time = datetime.fromisoformat(last_record[0])
            age = datetime.now() - last_time
            
            status = "✅" if age < timedelta(minutes=5) else "❌"
            print(f"{status} Son kayıt: {age} önce")
        
        print(f"📊 Toplam kayıt: {total:,}")
        
        # Bugünkü kayıtlar
        today = datetime.now().date()
        cursor.execute(
            "SELECT COUNT(*) FROM price_data WHERE DATE(timestamp) = ?",
            (today.isoformat(),)
        )
        today_count = cursor.fetchone()[0]
        print(f"📅 Bugünkü kayıt: {today_count:,}")
        
        conn.close()
        
    except Exception as e:
        print(f"❌ Veritabanı hatası: {e}")


def check_signals():
    """Sinyal dosyalarını kontrol et"""
    print("\n🚨 SİNYALLER:")
    print("-" * 40)
    
    signal_dir = Path("signals")
    if not signal_dir.exists():
        print("📁 Sinyal dizini yok (henüz sinyal üretilmemiş)")
        return
    
    today_file = signal_dir / f"signals_{datetime.now().strftime('%Y%m%d')}.log"
    if today_file.exists():
        with open(today_file, 'r', encoding='utf-8') as f:
            content = f.read()
            signal_count = content.count("Type:")
            print(f"✅ Bugün {signal_count} sinyal üretildi")
            
            # Son sinyali göster
            if signal_count > 0:
                lines = content.strip().split('\n')
                last_signal_start = -1
                for i in range(len(lines)-1, -1, -1):
                    if lines[i].startswith("Type:"):
                        last_signal_start = i - 1
                        break
                
                if last_signal_start >= 0:
                    print("\n📍 Son Sinyal:")
                    for i in range(last_signal_start, min(last_signal_start + 8, len(lines))):
                        if i < len(lines):
                            print(f"   {lines[i]}")
    else:
        print("⚪ Bugün henüz sinyal yok")


def check_process():
    """Python process'ini kontrol et"""
    print("\n⚙️  PROCESS DURUMU:")
    print("-" * 40)
    
    try:
        import psutil
        
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            if 'python' in proc.info['name'].lower():
                cmdline = ' '.join(proc.info['cmdline'] or [])
                if 'main_robust.py' in cmdline or 'main.py' in cmdline:
                    print(f"✅ Process çalışıyor (PID: {proc.info['pid']})")
                    
                    # Memory ve CPU kullanımı
                    proc_info = psutil.Process(proc.info['pid'])
                    print(f"   💾 Memory: {proc_info.memory_info().rss / 1024 / 1024:.1f} MB")
                    print(f"   🖥️  CPU: {proc_info.cpu_percent(interval=1)}%")
                    return
        
        print("❌ Process bulunamadı!")
        
    except ImportError:
        print("⚠️  psutil kurulu değil (pip install psutil)")
    except Exception as e:
        print(f"❌ Process kontrol hatası: {e}")


def main():
    """Ana monitoring fonksiyonu"""
    print("\n" + "="*50)
    print("🔍 GOLD PRICE ANALYZER - SYSTEM MONITOR")
    print("="*50)
    print(f"⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    check_process()
    check_database()
    check_logs()
    check_signals()
    
    print("\n" + "="*50)
    print("✅ Kontrol tamamlandı")


if __name__ == "__main__":
    main()