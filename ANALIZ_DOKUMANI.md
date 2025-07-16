# Gold Price Analyzer - Analiz Sistemi Dokümantasyonu

## Genel Bakış

Sistem her 60 saniyede bir detaylı teknik analiz yapar ve sonuçları veritabanına kaydeder. Analiz için minimum 50 adet 15 dakikalık mum (candle) gerekir.

## Analiz Bileşenleri

### 1. Destek/Direnç Analizi

**Nasıl Çalışır:**
- Son 100 mumda yerel minimum ve maksimum noktaları (pivot points) bulur
- Birbirine yakın seviyeleri gruplar (%0.2 tolerans)
- En az 2 kez test edilmiş seviyeleri filtreler
- Dokunma sayısına göre güç hesaplar (5 dokunmada maksimum güç)

**Kullanım:**
- Fiyat desteğe yaklaştığında (%0.5 mesafe) → Potansiyel ALIŞ sinyali
- Fiyat dirence yaklaştığında (%0.5 mesafe) → Potansiyel SATIŞ sinyali

### 2. Trend Analizi

**Hesaplama:**
- Son 10 mumun ortalaması vs önceki 10 mumun ortalaması karşılaştırılır
- Değişim yüzdesi hesaplanır

**Trend Tipleri:**
- BULLISH (Yükseliş): Değişim > %1
- BEARISH (Düşüş): Değişim < -%1  
- NEUTRAL (Yatay): Değişim -%1 ile %1 arası

**Trend Gücü:**
- STRONG (Güçlü): |Değişim| > %3
- MODERATE (Orta): |Değişim| > %1.5
- WEAK (Zayıf): |Değişim| <= %1.5

### 3. Teknik Göstergeler

#### RSI (Relative Strength Index)
- 14 periyotluk klasik RSI hesaplaması
- RSI > 70 → Aşırı alım (Overbought)
- RSI < 30 → Aşırı satım (Oversold)
- RSI 30-70 → Nötr

#### Moving Averages (Hareketli Ortalamalar)
- MA 20 (Kısa dönem): Son 20 mumun ortalaması
- MA 50 (Uzun dönem): Son 50 mumun ortalaması

#### MA Cross (Hareketli Ortalama Kesişimi)
- Golden Cross: MA20 > MA50 (ve önceden MA20 <= MA50 idi) → Yükseliş sinyali
- Death Cross: MA20 < MA50 (ve önceden MA20 >= MA50 idi) → Düşüş sinyali

### 4. Sinyal Üretimi

**ALIŞ Sinyali Kriterleri:**
1. Fiyat güçlü bir destek seviyesine yakın (%0.5 mesafe)
2. Destek seviyesinin gücü minimum güven skorunu geçmeli (varsayılan %70)

**SATIŞ Sinyali Kriterleri:**
1. Fiyat güçlü bir direnç seviyesine yakın (%0.5 mesafe)
2. Direnç seviyesinin gücü minimum güven skorunu geçmeli (varsayılan %70)

**Risk Yönetimi:**
- Stop Loss: Desteğin %1 altı (ALIŞ) veya direncin %1 üstü (SATIŞ)
- Take Profit: %2 kar veya en yakın direnç/destek seviyesi

### 5. Risk Seviyeleri

Risk toleransına göre güven skorları değerlendirilir:

**Düşük Risk Toleransı:**
- LOW risk: Güven >= %90
- MEDIUM risk: Güven >= %80
- HIGH risk: Güven < %80

**Orta Risk Toleransı:**
- LOW risk: Güven >= %80
- MEDIUM risk: Güven >= %70
- HIGH risk: Güven < %70

**Yüksek Risk Toleransı:**
- LOW risk: Güven >= %70
- MEDIUM risk: Güven >= %60
- HIGH risk: Güven < %60

## Veri Akışı

1. **Fiyat Güncellemesi** (her 5 saniye)
   - HaremAltin API'den fiyat alınır
   - SQLite veritabanına kaydedilir

2. **Mum Oluşturma** (15 dakikalık)
   - Raw fiyat verilerinden OHLC mumları oluşturulur
   - Her mumda: Open, High, Low, Close değerleri

3. **Analiz** (her 60 saniye)
   - 50+ mum varsa analiz başlar
   - Tüm göstergeler hesaplanır
   - Sinyal üretilir (varsa)
   - Sonuçlar veritabanına kaydedilir

4. **Web Dashboard**
   - Gerçek zamanlı fiyat güncellemeleri (WebSocket)
   - Analiz sonuçları gösterimi
   - Sinyal geçmişi

## Konfigürasyon (config.py)

```python
# Analiz parametreleri
support_resistance_lookback = 100  # Destek/Direnç için bakılan mum sayısı
rsi_period = 14                    # RSI periyodu
ma_short_period = 20               # Kısa MA periyodu
ma_long_period = 50                # Uzun MA periyodu
min_confidence_score = 0.7         # Minimum güven skoru (%70)
risk_tolerance = "medium"          # Risk toleransı

# Zamanlama
collection_interval = 1            # Dakika cinsinden analiz sıklığı
```

## Gelecek Geliştirmeler

1. **Ek Göstergeler**
   - MACD
   - Bollinger Bands
   - Fibonacci Retracement

2. **Makine Öğrenmesi**
   - Geçmiş sinyallerin başarı oranı analizi
   - Pattern recognition (baş-omuz, üçgen formasyonları vb.)

3. **Bildirimler**
   - Telegram/Discord entegrasyonu
   - Email uyarıları

4. **Backtesting**
   - Geçmiş veri üzerinde strateji testi
   - Performans metrikleri