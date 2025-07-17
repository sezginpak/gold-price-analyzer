# Yeni Mimariye Geçiş Planı

## 1. Veri Uyumluluğu ✅

**Mevcut veriler tamamen uyumlu!** Çünkü:
- Dün `gram_altin` kolonunu ekledik
- Tüm gerekli fiyat verileri zaten toplanıyor
- Yeni sistem aynı veri yapısını kullanabilir

## 2. Geçiş Adımları

### Aşama 1: Veri Katmanı (Mevcut veriyi koruyarak)
```python
# Mevcut PriceData modelini güncelle
class PriceData:
    # Mevcut alanlar korunacak
    ons_usd, usd_try, ons_try, gram_altin ✓
```

### Aşama 2: Analiz Katmanı (Yeni)
1. **GramAltinAnalyzer**: 
   - Mevcut `price_candles` tablosunu kullanacak
   - Sadece gram_altin fiyatından mumlar oluşturacak

2. **GlobalTrendAnalyzer**:
   - Mevcut `ons_usd` verilerini kullanacak
   - Günlük/haftalık trend belirleyecek

3. **CurrencyRiskAnalyzer**:
   - Mevcut `usd_try` verilerini kullanacak
   - Volatilite hesaplayacak

### Aşama 3: Yeni Tablolar (Opsiyonel)
```sql
-- Gram altın özel mumları (opsiyonel)
CREATE TABLE IF NOT EXISTS gram_candles (
    id INTEGER PRIMARY KEY,
    timestamp DATETIME,
    interval TEXT,
    open REAL,
    high REAL, 
    low REAL,
    close REAL
);

-- Hibrit analiz sonuçları
CREATE TABLE IF NOT EXISTS hybrid_analysis (
    id INTEGER PRIMARY KEY,
    timestamp DATETIME,
    gram_price REAL,
    signal TEXT,
    confidence REAL,
    position_size REAL,
    stop_loss REAL,
    take_profit REAL,
    global_trend TEXT,
    currency_risk TEXT
);
```

## 3. Kod Değişiklikleri

### A. HaremPriceCollector (Minimal değişiklik)
```python
# Mevcut veri toplama aynı kalacak
# Sadece analiz callback'i değişecek
```

### B. Main.py (Yeni analiz akışı)
```python
# Eski: TimeframeAnalyzer
# Yeni: HybridStrategy
```

### C. Web Server (API güncelleme)
```python
# Yeni endpoint'ler:
/api/analysis/gram      # Gram altın analizi
/api/analysis/global    # Global trend
/api/analysis/risk      # Kur riski
/api/analysis/hybrid    # Birleşik analiz
```

## 4. Avantajlar

1. **Veri Kaybı Yok**: Tüm geçmiş veriler kullanılabilir
2. **Geriye Dönük Uyumlu**: Eski analizler görüntülenebilir
3. **Kademeli Geçiş**: Sistemler paralel çalışabilir
4. **Test Edilebilir**: Yeni sistem eski veriyle test edilebilir

## 5. Dikkat Edilecekler

1. **Mum Oluşturma**: 
   - Eski: ONS/TRY üzerinden
   - Yeni: Gram altın üzerinden
   - Çözüm: Her ikisi için ayrı mumlar

2. **Analiz Geçmişi**:
   - Eski analizler `analysis_results` tablosunda
   - Yeni analizler `hybrid_analysis` tablosunda
   - Dashboard'da her ikisi gösterilebilir

3. **Sinyal Uyumu**:
   - Eski: ONS/TRY bazlı
   - Yeni: Gram altın bazlı
   - Çözüm: Sinyal tipini belirten alan ekle