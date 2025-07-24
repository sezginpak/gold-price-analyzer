# Dezy - Gold Price Analyzer 🏆

Kuyumcu işletmeleri için geliştirilmiş, altın ve döviz fiyatlarını gerçek zamanlı takip eden, teknik analiz yapan ve alım/satım sinyalleri üreten profesyonel sistem. Dezy kuyumcu uygulamasına entegre edilmek üzere tasarlanmıştır.

## 🚀 Özellikler

### Temel Özellikler
- ✅ Gerçek zamanlı fiyat takibi (HaremAltin API)
- ✅ Destek/Direnç seviyesi tespiti
- ✅ Otomatik alım/satım sinyalleri
- ✅ SQLite veritabanı ile veri saklama
- ✅ OHLC mum grafiği oluşturma
- ✅ Risk yönetimi ve güven skorlaması

### Gelişmiş Özellikler
- ✅ Web Dashboard (Real-time güncelleme)
- ✅ WebSocket ile canlı veri akışı
- ✅ Auto-restart ve hata yönetimi
- ✅ Log rotation ve istatistik takibi
- ✅ Docker desteği
- ✅ Systemd service entegrasyonu

## 📦 Kurulum

### 1. Repository'yi Klonlayın
```bash
git clone https://github.com/YOUR_USERNAME/dezy-gold-analyzer.git
cd dezy-gold-analyzer
```

### 2. Python Sanal Ortamı Oluşturun
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# veya
venv\Scripts\activate  # Windows
```

### 3. Bağımlılıkları Yükleyin
```bash
pip install -r requirements.txt
```

### 4. Konfigürasyon
```bash
cp .env.example .env
# .env dosyasını ihtiyaçlarınıza göre düzenleyin
```

## 🎯 Kullanım

### Ana Uygulamayı Çalıştırma

```bash
# Temel versiyon
python main.py

# Robust versiyon (auto-restart ile)
python main_robust.py

# Web Dashboard ile
python main_with_web.py
```

### Web Dashboard'a Erişim

```
http://localhost:8080
```

### Test Modu

```bash
# Temel analiz testi
python test_basic_analysis.py

# HaremAltin API testi
python test_harem_service.py
```

## ⚙️ Konfigürasyon

`.env` dosyasında ayarlayabileceğiniz parametreler:

- `COLLECTION_INTERVAL`: Veri toplama aralığı (saniye)
- `MIN_CONFIDENCE_SCORE`: Minimum güven skoru (0-1)
- `RISK_TOLERANCE`: Risk toleransı (low/medium/high)
- `SUPPORT_RESISTANCE_LOOKBACK`: Destek/Direnç analizi için bakılacak mum sayısı

## 📊 Sinyal Üretimi

Sistem şu kriterlere göre sinyal üretir:

1. **Alış Sinyali**: Fiyat güçlü destek seviyesine yaklaştığında
2. **Satış Sinyali**: Fiyat güçlü direnç seviyesine yaklaştığında

Her sinyal için:
- Güven skoru (0-100%)
- Risk seviyesi (LOW/MEDIUM/HIGH)
- Hedef fiyat
- Stop loss seviyesi

## 🗄️ Veri Saklama

- SQLite veritabanı kullanılır (`gold_prices.db`)
- Otomatik veri sıkıştırma (1 hafta sonra)
- OHLC mumları otomatik oluşturulur

## 🚀 VPS Deployment

### Otomatik Deployment

```bash
chmod +x deploy_to_vps.sh
./deploy_to_vps.sh
```

### Manuel Deployment

1. Dosyaları VPS'e kopyalayın
2. Systemd service'i kurun:
```bash
sudo cp gold-analyzer.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable gold-analyzer
sudo systemctl start gold-analyzer
```

3. Nginx reverse proxy ayarlayın:
```nginx
server {
    listen 80;
    server_name your-domain.com;
    
    location / {
        proxy_pass http://localhost:8080;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
    }
}
```

### Docker Deployment

```bash
# Build
docker build -t gold-analyzer .

# Run
docker run -d -p 8080:8080 --name gold-analyzer gold-analyzer

# veya Docker Compose ile
docker-compose up -d
```

## 🔧 Geliştirme

### Yeni Analiz Yöntemi Eklemek

1. `analyzers/` klasörüne yeni modül ekleyin
2. `SignalGenerator` sınıfına entegre edin
3. Güven skoru hesaplamasına dahil edin

### Yeni Veri Kaynağı Eklemek

1. `collectors/` klasörüne yeni collector ekleyin
2. `PriceCollector` interface'ini implement edin
3. `main.py`'de yeni collector'ı kullanın

## 📊 API Endpoints

### REST API

- `GET /api/prices` - Son fiyatları getir
- `GET /api/signals` - Son sinyalleri getir
- `GET /api/analysis` - Güncel analizi getir
- `GET /api/stats` - Sistem istatistiklerini getir

### WebSocket

- `ws://localhost:8080/ws` - Real-time veri akışı

## 🔒 Güvenlik

### Önemli Güvenlik Notları

⚠️ **UYARI**: Deploy scriptlerinde şifre kullanmayın! 

- **SSH Key Authentication kullanın** (önerilen)
- VPS bilgilerini `.env` dosyasında saklayın
- `.env` dosyasını asla Git'e eklemeyin
- Production'da güçlü şifreler kullanın

### Güvenlik Önlemleri

- API anahtarları `.env` dosyasında saklanır
- Hassas veriler loglanmaz
- WebSocket bağlantıları rate-limited
- Tüm deployment bilgileri environment variable'lardan okunur

### SSH Key Kurulumu

```bash
# SSH key oluştur (eğer yoksa)
ssh-keygen -t rsa -b 4096

# Public key'i VPS'e kopyala
ssh-copy-id user@your-vps-ip
```

## ⚠️ Uyarılar

- Bu sistem sadece analiz amaçlıdır
- Gerçek yatırım kararları için kullanmayın
- Sinyaller %100 doğru değildir
- Yatırım kararları almadan önce profesyonel danışmanlık alın

## 🤝 Katkıda Bulunma

1. Fork edin
2. Feature branch oluşturun (`git checkout -b feature/amazing-feature`)
3. Değişikliklerinizi commit edin (`git commit -m 'Add amazing feature'`)
4. Branch'inizi push edin (`git push origin feature/amazing-feature`)
5. Pull Request açın

## 📝 Lisans

MIT License - detaylar için [LICENSE](LICENSE) dosyasına bakın.