# Gold Price Analyzer 🏆

Altın ve döviz fiyatlarını gerçek zamanlı takip eden, teknik analiz yapan ve alım/satım sinyalleri üreten sistem.

## 🚀 Özellikler

- ✅ Gerçek zamanlı fiyat takibi (HaremAltin API)
- ✅ Destek/Direnç seviyesi tespiti
- ✅ Otomatik alım/satım sinyalleri
- ✅ SQLite veritabanı ile veri saklama
- ✅ OHLC mum grafiği oluşturma
- ✅ Risk yönetimi ve güven skorlaması

## 📦 Kurulum

1. Bağımlılıkları yükleyin:
```bash
pip install -r requirements.txt
```

2. `.env` dosyası oluşturun:
```bash
cp .env.example .env
```

3. Ayarları düzenleyin (opsiyonel)

## 🎯 Kullanım

### Ana Uygulamayı Çalıştırma

```bash
python main.py
```

### Test Modu

```bash
python test_basic_analysis.py
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

## 🔧 Geliştirme

Yeni analiz yöntemi eklemek için:

1. `analyzers/` klasörüne yeni modül ekleyin
2. `SignalGenerator` sınıfına entegre edin
3. Güven skoru hesaplamasına dahil edin

## ⚠️ Uyarılar

- Bu sistem sadece analiz amaçlıdır
- Gerçek yatırım kararları için kullanmayın
- Sinyaller %100 doğru değildir

## 📝 Lisans

MIT