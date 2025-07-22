# Gold Analyzer - Simülasyon Sistemi Dokümantasyonu

## 🎯 Sistem Özeti

Altın bazlı otomatik trading simülasyon sistemi. 1000 gram sermaye ile başlayıp, 4 farklı timeframe'de paralel işlem yaparak performans ölçer.

## 📊 Temel Parametreler

```yaml
Sermaye: 1000 gram altın
Timeframe Dağılımı: Her birine 250 gram (15m, 1h, 4h, 1d)
İşlem Saatleri: 09:00-17:00 TR
Min Güven Skoru: %60
Max Risk: %2 (işlem ve günlük)
Spread: 15 TL (alış/satış)
Komisyon: %0.1 (giriş+çıkış)
```

## 🚀 Hızlı Başlangıç

```python
# Simülasyon başlat
sim = SimulationManager()
sim.create_simulation("Ana Strateji", strategy_type="MAIN")
sim.start()

# Durum kontrolü
status = sim.get_status()
print(f"Sermaye: {status['current_capital']} gram")
print(f"Açık Pozisyonlar: {status['open_positions']}")
```

## 📈 Çıkış Stratejileri

1. **Stop-Loss/Take-Profit**: 1.5xATR / 2:1 RR
2. **Günlük Limit**: %2 kayıpta durdur
3. **Ters Sinyal**: Yön değişince kapat
4. **Trailing Stop**: %70 kâr koru
5. **Zaman**: 4h-7gün (timeframe'e göre)
6. **Güven Düşüşü**: %40 altında kapat
7. **Volatilite**: %50 artışta kapat
8. **Saat Sonu**: 17:00'de yeni pozisyon yok

## 🔧 Simülasyon Tipleri

### 1. ANA (MAIN)
- Tüm sinyaller (%60+ güven)
- Normal risk yönetimi

### 2. CONSERVATIVE
- Sadece STRONG sinyaller
- %70+ güven, %1 risk

### 3. MOMENTUM
- Trend takibi
- RSI 30-70 dışında işlem

### 4. MEAN_REVERSION
- Bollinger Band stratejisi
- Aşırılarda ters işlem

### 5. CONSENSUS
- 3+ gösterge uyumu
- Pattern onaylı

### 6. RISK_ADJUSTED
- Volatiliteye göre pozisyon
- Extreme'de işlem yok

### 7. TIME_BASED
- 09-11: Momentum
- 11-14: Mean Reversion
- 14-17: Conservative

## 📝 Kullanım Örnekleri

### Yeni Simülasyon
```python
# Conservative strateji
sim.create_simulation("Güvenli", strategy_type="CONSERVATIVE")

# Özel parametreler
sim.create_simulation("Özel", 
    strategy_type="MAIN",
    min_confidence=0.65,
    max_risk=0.015
)
```

### Performans Kontrolü
```python
# Günlük rapor
report = sim.get_daily_report(date="2024-01-22")

# Timeframe karşılaştırma
comparison = sim.compare_timeframes()
print(f"En iyi: {comparison['best_timeframe']}")
```

### Pozisyon Takibi
```python
# Açık pozisyonlar
positions = sim.get_open_positions()

# İşlem geçmişi
history = sim.get_trade_history(timeframe="15m", limit=10)
```

## 🎯 Pozisyon Boyutu Formülü

```
Risk Miktarı = Timeframe Sermayesi × 0.02
Stop Mesafesi = Entry × (1.5 × ATR%)  
Pozisyon = Risk Miktarı / Stop Mesafesi
```

## 📊 Performans Metrikleri

- **Win Rate**: Kazanma oranı
- **Profit Factor**: Kar/Zarar oranı
- **Sharpe Ratio**: Risk-düzeltilmiş getiri
- **Max Drawdown**: Maksimum düşüş
- **Avg Win/Loss**: Ortalama kar/zarar

## 🔄 Otomatik İşlem Akışı

1. **Sinyal Kontrolü** (her timeframe için)
   - Güven > %60
   - Saat 09:00-17:00
   - Açık pozisyon yok

2. **Risk Hesaplama**
   - %2 risk limiti
   - Pozisyon boyutu
   - SL/TP seviyeleri

3. **Pozisyon Açma**
   - Spread uygula (-15 TL)
   - Komisyon hesapla
   - Veritabanına kaydet

4. **Pozisyon Takibi**
   - Çıkış koşulları kontrolü
   - Trailing stop güncelleme
   - PnL hesaplama

5. **Pozisyon Kapama**
   - Çıkış nedeni kaydet
   - Net kar/zarar hesapla
   - Raporları güncelle

## 💾 Veritabanı Tabloları

- `simulations`: Ana simülasyon bilgileri
- `sim_positions`: İşlem detayları  
- `sim_daily_performance`: Günlük özet

## 🚨 Önemli Notlar

1. **Spread Hesabı**: Hem alış hem satışta -15 TL
2. **Komisyon**: Toplam %0.1 (giriş+çıkış)
3. **Saat Dışı**: 17:00'den sonra sadece SL/TP aktif
4. **Risk Limiti**: Günlük %2 aşılınca yeni pozisyon yok
5. **Gerçek Değil**: Bu bir simülasyon, gerçek para kullanmıyor

## 🔍 Hata Ayıklama

```python
# Log kontrolü
sim.get_logs(level="ERROR", limit=50)

# Pozisyon detayı
sim.debug_position(position_id=123)

# Sinyal analizi
sim.analyze_missed_signals(date="2024-01-22")
```

## 📈 Gelecek Özellikler

- [ ] Multi-portfolio karşılaştırma
- [ ] ML bazlı sinyal filtreleme
- [ ] Otomatik parametre optimizasyonu
- [ ] Gerçek zamanlı web dashboard
- [ ] Telegram/Discord bildirimleri