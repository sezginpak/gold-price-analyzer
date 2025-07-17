# Yeni Mimari Tasarım - Gram Altın Odaklı Hibrit Sistem

## Proje Yapısı

```
gold_price_analyzer/
├── analyzers/
│   ├── gram_altin_analyzer.py    # Ana analiz motoru
│   ├── global_trend_analyzer.py   # ONS/USD trend analizi
│   └── currency_risk_analyzer.py  # USD/TRY risk değerlendirme
├── models/
│   ├── market_data.py            # Yeni birleşik veri modeli
│   ├── analysis_result.py        # Güncellenen analiz sonuçları
│   └── trading_signal.py         # Gram altın bazlı sinyaller
├── strategies/
│   ├── hybrid_strategy.py        # Ana strateji
│   ├── signal_combiner.py        # Sinyal birleştirici
│   └── risk_manager.py           # Risk yönetimi
├── collectors/
│   └── harem_collector.py        # Veri toplama (mevcut)
├── storage/
│   └── sqlite_storage.py         # Yeni şema ile
└── web/
    ├── dashboard.py              # Yeni dashboard
    └── api.py                    # API endpoints

## Veri Akışı

1. **Veri Toplama**
   - HaremAltin API → gram_altin, ons_usd, usd_try

2. **Analiz Katmanı**
   - GramAltinAnalyzer: RSI, MACD, Bollinger vb. (gram altın üzerinden)
   - GlobalTrendAnalyzer: ONS/USD majör trend (günlük/haftalık)
   - CurrencyRiskAnalyzer: USD/TRY volatilite ve risk

3. **Karar Katmanı**
   - HybridStrategy: Tüm analizleri birleştir
   - SignalCombiner: Nihai sinyal üret (AL/SAT/BEKLE)
   - RiskManager: Pozisyon büyüklüğü öner

4. **Çıktı**
   - Gram altın fiyat hedefi
   - Stop-loss (gram altın)
   - Pozisyon büyüklüğü (risk bazlı)

## Örnek Sinyal Mantığı

```python
# Global trend yükselişte + Gram altın düşük RSI
if global_trend == "BULLISH" and gram_rsi < 30:
    signal = "STRONG_BUY"
    confidence = 0.85

# Global trend düşüşte ama gram altın güçlü destek
elif global_trend == "BEARISH" and gram_at_support:
    signal = "CAUTIOUS_BUY"  
    confidence = 0.60
    
# USD/TRY yüksek volatilite
if usd_try_volatility > threshold:
    position_size *= 0.5  # Pozisyon küçült
```

## Veritabanı Şeması

```sql
-- Ana piyasa verileri
CREATE TABLE market_data (
    id INTEGER PRIMARY KEY,
    timestamp DATETIME,
    gram_altin REAL,      -- Ana fiyat
    ons_usd REAL,         -- Global trend için
    usd_try REAL,         -- Risk hesaplama için
    ons_try REAL          -- Kayıt amaçlı
);

-- Gram altın bazlı analizler
CREATE TABLE gram_analysis (
    id INTEGER PRIMARY KEY,
    timestamp DATETIME,
    price REAL,           -- Gram altın fiyatı
    rsi REAL,
    macd_signal TEXT,
    bollinger_position TEXT,
    support_level REAL,
    resistance_level REAL,
    signal TEXT,          -- AL/SAT/BEKLE
    confidence REAL
);

-- Global trend analizi
CREATE TABLE global_trends (
    id INTEGER PRIMARY KEY,
    timestamp DATETIME,
    ons_usd_price REAL,
    trend_direction TEXT,  -- BULLISH/BEARISH/SIDEWAYS
    trend_strength TEXT,   -- STRONG/MODERATE/WEAK
    ma50 REAL,
    ma200 REAL
);

-- Risk metrikleri
CREATE TABLE risk_metrics (
    id INTEGER PRIMARY KEY,
    timestamp DATETIME,
    usd_try_volatility REAL,
    risk_level TEXT,      -- LOW/MEDIUM/HIGH
    suggested_position_size REAL
);
```

## Dashboard Görünümü

1. **Ana Panel**
   - Gram altın anlık fiyat (büyük)
   - Alım/Satım sinyali
   - Güven skoru

2. **Analiz Panelleri**
   - Gram altın teknik göstergeler
   - ONS/USD global trend
   - USD/TRY risk seviyesi

3. **Pozisyon Önerisi**
   - Hedef fiyat (gram altın)
   - Stop-loss (gram altın)
   - Pozisyon büyüklüğü