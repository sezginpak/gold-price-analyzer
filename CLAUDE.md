# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Proje Hakkında

Dezy - Gold Price Analyzer - Kuyumcu işletmeleri için geliştirilmiş, altın ve döviz fiyatlarını gerçek zamanlı takip eden, teknik analiz yapan ve alım/satım sinyalleri üreten Python tabanlı profesyonel bir sistemdir. Dezy kuyumcu uygulamasına entegre edilmek üzere tasarlanmıştır.

## Geliştirme Komutları

### Temel Komutlar

```bash
# Ana analiz servisini başlat
python main.py

# Web dashboard'u başlat (port 8080)
python web_server.py

# Hızlı deployment (commit, push, pull, restart)
./quick_deploy.sh
```

### Systemd Servisleri

```bash
# Servis durumlarını kontrol et
sudo systemctl status gold-analyzer
sudo systemctl status gold-web
sudo systemctl status gold-updater

# Log'ları görüntüle
sudo journalctl -u gold-analyzer -f
sudo journalctl -u gold-web -f
```

## Mimari Yapı

### Katmanlar ve Sorumluluklar

1. **collectors/** - Veri Toplama Katmanı
   - `harem_price_collector.py`: HaremAltin API'den altın fiyatları toplar
   - AsyncIO tabanlı, rate limiting destekli

2. **analyzers/** - Analiz Motoru
   - `gram_altin_analyzer.py`: Ana gram altın analizi
   - `currency_risk_analyzer.py`: USD/TRY risk değerlendirmesi
   - `global_trend_analyzer.py`: ONS/USD global trend takibi
   - `timeframe_analyzer.py`: Çoklu zaman dilimi analizi (15m, 1h, 4h, günlük)

3. **indicators/** - Teknik Göstergeler
   - RSI, MACD, Bollinger Bands, ATR, Stochastic
   - `pattern_recognition.py`: Destek/direnç ve pattern tanıma

4. **strategies/** - Trading Stratejileri
   - `hybrid_strategy.py`: Tüm analizleri birleştiren hibrit strateji
   - Gram altın odaklı, global trend destekli

5. **storage/** - Veri Depolama
   - `sqlite_storage.py`: SQLite veritabanı yönetimi
   - OHLC mum verisi, analiz sonuçları, sinyaller

6. **services/** - API Servisleri
   - `harem_altin_service.py`: HaremAltin API wrapper

7. **web_server.py** - Web Dashboard
   - FastAPI tabanlı
   - WebSocket ile real-time veri akışı
   - Jinja2 template engine

### Veri Akışı

1. **Veri Toplama**: HaremAltin API → SQLite
2. **Analiz**: SQLite → Analyzers → Indicators → Strategies
3. **Sinyal Üretimi**: Strategies → Trading Signals
4. **Görüntüleme**: WebSocket → Dashboard

## Kritik Dosyalar ve Yapılandırma

### config.py
- Tüm sistem ayarları burada
- `.env` dosyasından environment variables okur
- MongoDB ve Redis config'leri var ama aktif kullanılmıyor

### utils/logger.py
- Merkezi log sistemi
- Log rotation desteği
- WebSocket üzerinden canlı log akışı

### utils/timezone.py
- Timezone yönetimi için merkezi modül
- Türkiye (Europe/Istanbul) timezone'u için özel fonksiyonlar
- UTC ve Turkey time dönüşümleri
- Tarih/saat formatlama fonksiyonları

### models/
- Pydantic tabanlı veri modelleri
- `price_data.py`: Fiyat verisi
- `trading_signal.py`: Alım/satım sinyalleri
- `analysis_result.py`: Analiz sonuçları

## Önemli Detaylar

### Hibrit Analiz Sistemi
- Gram altın fiyatı ana odak noktası
- ONS/USD trendleri global görünüm sağlar
- USD/TRY volatilitesi risk değerlendirmesi için kullanılır
- Tüm analizler `hybrid_strategy.py`'de birleştirilir

### Veri Toplama Döngüsü
- HaremAltin API'den 1 dakikalık veriler
- SQLite'da OHLC formatında saklanır
- Otomatik veri sıkıştırma (eski veriler için)
- Rate limiting ve hata yönetimi

### Web Dashboard Özellikleri
- `/` - Ana dashboard (real-time fiyatlar)
- `/signals` - Trading sinyalleri
- `/analysis` - Detaylı analiz sonuçları
- `/logs` - Sistem logları
- WebSocket endpoint: `/ws` (canlı veri akışı)

### Deployment Notları
- Ubuntu/Debian için systemd servisleri hazır
- Production'da port 8080 kullanılıyor
- **Hızlı Deployment**: `./quick_deploy.sh` komutu ile tek seferde:
  - Git commit (otomatik veya custom mesaj)
  - GitHub'a push
  - VPS'e SSH bağlantı
  - Git pull (stash ile)
  - Servisleri restart (gold-analyzer ve gold-web)
  - Durum kontrolü

## Eksikler ve Dikkat Edilmesi Gerekenler

1. **Test Altyapısı Yok**: Birim testler veya entegrasyon testleri bulunmuyor
2. **Docker Desteği Eksik**: README'de bahsediliyor ama Dockerfile yok
3. **CI/CD Pipeline Yok**: Otomatik test ve deployment pipeline'ı kurulmamış
4. **MongoDB/Redis**: Config'de tanımlı ama kullanılmıyor, sadece SQLite aktif

## Aktif Geliştirmeler

### 🎯 Simülasyon Sistemi
- **Amaç**: Sinyal performansını ölçmek için otomatik trading simülasyonu
- **Sermaye**: 1000 gram altın (4 timeframe'e eşit dağıtılmış)
- **Özellikler**: 
  - 8 farklı çıkış stratejisi
  - 7 simülasyon senaryosu
  - Gram bazlı kar/zarar takibi
  - Detaylı raporlama

## Geliştirme İpuçları

- Yeni bir analyzer eklerken `analyzers/` klasörüne ekle ve `hybrid_strategy.py`'de entegre et
- Yeni indicator'ler için `indicators/` klasörünü kullan
- Web dashboard'a yeni sayfa eklerken `templates/` ve `web_server.py`'i güncelle
- Tüm async fonksiyonlar için proper error handling kullan
- Log mesajları için `utils.logger` kullan, print() kullanma

## Timezone Yönetimi

### Önemli: Tüm datetime işlemleri için utils.timezone modülünü kullan!

```python
# YANLIŞ
from datetime import datetime
now = datetime.now()

# DOĞRU
from utils.timezone import now
current_time = now()  # Türkiye saatinde timezone-aware datetime
```

### Kullanım Örnekleri:

```python
from utils.timezone import now, utc_now, to_turkey_time, format_for_display

# Şu anki Türkiye saati
turkey_time = now()

# UTC saati
utc_time = utc_now()

# UTC'den Türkiye saatine dönüşüm
turkey_time = to_turkey_time(utc_datetime)

# Görüntüleme için formatlama
formatted = format_for_display(datetime_obj, "%d.%m.%Y %H:%M")
```

### Veritabanı Kayıtları:
- Analiz ve strateji timestamp'leri UTC olarak saklanır
- Web arayüzünde gösterim için Türkiye saatine çevrilir
- Log kayıtları Türkiye saatinde tutulur