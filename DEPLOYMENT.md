# Gold Price Analyzer - Deployment Kılavuzu

## 🖥️ Lokal Bilgisayarda Sürekli Çalıştırma

### MacOS - LaunchAgent

1. LaunchAgent dosyası oluştur:
```bash
mkdir -p ~/Library/LaunchAgents
```

2. `~/Library/LaunchAgents/com.goldanalyzer.plist` dosyası:
```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.goldanalyzer</string>
    <key>ProgramArguments</key>
    <array>
        <string>/usr/local/bin/python3</string>
        <string>/Users/sezginpaksoy/Desktop/Dezy/gold_price_analyzer/main_robust.py</string>
    </array>
    <key>WorkingDirectory</key>
    <string>/Users/sezginpaksoy/Desktop/Dezy/gold_price_analyzer</string>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>/Users/sezginpaksoy/Desktop/Dezy/gold_price_analyzer/logs/launchd.log</string>
    <key>StandardErrorPath</key>
    <string>/Users/sezginpaksoy/Desktop/Dezy/gold_price_analyzer/logs/launchd_error.log</string>
</dict>
</plist>
```

3. Servisi başlat:
```bash
launchctl load ~/Library/LaunchAgents/com.goldanalyzer.plist
launchctl start com.goldanalyzer
```

### Windows - Task Scheduler

1. `run_analyzer.bat` dosyası oluştur:
```batch
@echo off
cd /d "C:\path\to\gold_price_analyzer"
python main_robust.py
```

2. Task Scheduler'da yeni task oluştur:
   - Trigger: At startup
   - Action: Start program -> run_analyzer.bat
   - Settings: Run whether user is logged on or not

## 🌐 VPS'de Çalıştırma (Önerilen)

### 1. Ucuz VPS Seçenekleri

- **Hetzner Cloud**: €4.51/ay (2GB RAM, 20GB SSD)
- **DigitalOcean**: $6/ay (1GB RAM, 25GB SSD)
- **Vultr**: $6/ay (1GB RAM, 25GB SSD)
- **Oracle Cloud**: Free tier (1GB RAM, selamın aleyküm)

### 2. VPS Kurulum

```bash
# 1. Sistemi güncelle
sudo apt update && sudo apt upgrade -y

# 2. Python ve gerekli paketleri kur
sudo apt install python3 python3-pip python3-venv git -y

# 3. Projeyi klonla
git clone <your-repo-url> /home/ubuntu/gold_price_analyzer
cd /home/ubuntu/gold_price_analyzer

# 4. Virtual environment oluştur
python3 -m venv venv
source venv/bin/activate

# 5. Bağımlılıkları yükle
pip install -r requirements.txt

# 6. Systemd service kur
sudo cp gold-analyzer.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable gold-analyzer
sudo systemctl start gold-analyzer

# 7. Durumu kontrol et
sudo systemctl status gold-analyzer
```

### 3. Docker ile Kurulum (Alternatif)

```bash
# Docker kurulumu
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Docker Compose kurulumu
sudo apt install docker-compose -y

# Projeyi çalıştır
cd /home/ubuntu/gold_price_analyzer
sudo docker-compose up -d

# Logları izle
sudo docker-compose logs -f
```

## 📊 Monitoring ve Log Takibi

### 1. Canlı Log İzleme

```bash
# Ana loglar
tail -f logs/gold_analyzer.log

# Sadece hatalar
tail -f logs/gold_analyzer_errors.log

# Sinyaller
tail -f signals/signals_$(date +%Y%m%d).log
```

### 2. Systemd Logs

```bash
# Service logları
sudo journalctl -u gold-analyzer -f

# Son 100 satır
sudo journalctl -u gold-analyzer -n 100
```

### 3. Docker Logs

```bash
# Container logları
docker logs -f gold_price_analyzer

# Son 1 saatlik loglar
docker logs --since 1h gold_price_analyzer
```

## 🔧 Hata Ayıklama

### 1. Servis yeniden başlatma

```bash
# Systemd
sudo systemctl restart gold-analyzer

# Docker
docker-compose restart

# LaunchAgent (MacOS)
launchctl stop com.goldanalyzer
launchctl start com.goldanalyzer
```

### 2. Debug mode

```bash
# Çevre değişkeni ile
export LOG_LEVEL=DEBUG
python main_robust.py

# Veya .env dosyasında
LOG_LEVEL=DEBUG
```

### 3. Veritabanı kontrol

```bash
# SQLite veritabanını kontrol et
sqlite3 gold_prices.db
.tables
SELECT COUNT(*) FROM price_data;
SELECT * FROM price_data ORDER BY timestamp DESC LIMIT 10;
.quit
```

## 📱 Bildirimler (Opsiyonel)

### Telegram Bot Entegrasyonu

1. BotFather'dan bot oluştur
2. Token'ı .env dosyasına ekle:
```
TELEGRAM_BOT_TOKEN=your_token
TELEGRAM_CHAT_ID=your_chat_id
```

### Email Bildirimleri

1. SMTP ayarlarını .env'ye ekle:
```
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your_email
SMTP_PASS=your_app_password
ALERT_EMAIL=recipient@example.com
```

## 🛡️ Güvenlik

1. **Firewall**: Sadece gerekli portları aç
2. **SSL**: Eğer web interface eklerseniz
3. **Backup**: Düzenli veritabanı yedekleme
4. **Monitoring**: Uptime monitoring servisi kullan

## 💰 Maliyet Optimizasyonu

1. **Log Rotation**: Disk dolmasını önle
2. **Data Cleanup**: Eski verileri düzenli temizle
3. **Resource Limits**: CPU/Memory limitleri koy
4. **Monitoring**: Kaynak kullanımını izle

## 📞 Destek

Hatalar için logs/gold_analyzer_errors.log dosyasını kontrol edin.
Kritik hatalar logs/gold_analyzer_critical.log dosyasında.