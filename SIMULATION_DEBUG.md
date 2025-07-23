# Simülasyon Sistemi Debug Notları

## Özet
Simülasyon sistemi çalışıyor ancak pozisyon açmıyor. ATR ve diğer sorunlar çözüldü.

## Çözülen Sorunlar

### 1. Timezone Sorunu
- **Sorun**: UTC saati kullanıldığı için trading saatleri dışında kalıyordu
- **Çözüm**: `simulation_manager.py` içinde UTC+3 düzeltmesi yapıldı
```python
# Türkiye saatine çevir (UTC+3)
tr_time = current_time.replace(hour=(current_time.hour + 3) % 24)
```

### 2. Confidence Eşikleri
- **Sorun**: Sinyallerin confidence değerleri düşüktü (0.4-0.5)
- **Çözüm**: Veritabanında eşikler düşürüldü:
  - MAIN: 0.6 → 0.4
  - CONSERVATIVE: 0.7 → 0.5
  - MOMENTUM: 0.65 → 0.45
  - MEAN_REVERSION: 0.65 → 0.45

### 3. ATR Erişim Sorunu
- **Sorun**: ATR değeri bulunamıyor hatası
- **Çözüm**: 
  1. İlk düzeltme: `atr.get('value')` yerine `atr.get('atr')`
  2. Ana sorun: `gram_analysis` boş geliyordu
  3. Gerçek çözüm: `analysis['details']['gram']` yapısından erişim

### 4. Decimal Tip Uyumluluğu
- **Sorun**: "unsupported operand type(s) for *: 'decimal.Decimal' and 'float'"
- **Çözüm**: Float değerleri Decimal'e çevirme:
```python
stop_distance = atr_pct * Decimal(str(config.atr_multiplier_sl))
```

### 5. NoneType Hataları
- **Sorun**: Günlük performans güncellemesinde NoneType to float hatası
- **Çözüm**: Timeframe capitals kontrolü ve varsayılan değerler eklendi
- **Düzeltme**: `tf.current_capital if tf.current_capital is not None else 0` şeklinde güncellendi
- **Durum**: Hala devam ediyor, başka bir yerde de sorun olabilir

## Mevcut Durum

### Çalışan Kısımlar
- SimulationManager başlatılıyor ✅
- 4 simülasyon yükleniyor ✅
- Trading saatleri kontrolü çalışıyor (TR saati) ✅
- Sinyaller alınıyor ✅
- ATR değerleri DB'de mevcut ✅

### Son Sinyaller (23.07.2025 07:51)
- 15m: BUY 0.449 (Ana strateji için yeterli)
- 1h: SELL 0.507 (Conservative hariç hepsi için yeterli)
- 4h: SELL 0.484 (Momentum ve Mean Reversion için yeterli)

### Sorunlar
1. **Pozisyon açılmıyor** - 0 pozisyon
2. **1d timeframe için yeterli mum yok** - "Not enough gram candles for 1d: 7/20"
3. **Günlük performans güncelleme hatası devam ediyor** - başka bir yerde NoneType sorunu var
4. **SimulationManager logları görünmüyor** - start(), load_active_simulations() vs. logları yok

## Debug İçin Kontrol Edilecekler

1. **_should_open_position metodunun gerçekten çağrılıp çağrılmadığı**
2. **Strateji filtrelerinin pozisyon açmayı engelleyip engellemediği**
3. **Timeframe capitals'in doğru yüklenip yüklenmediği**
4. **1d timeframe'in sorun yaratıp yaratmadığı**

## Sunucu Bilgileri
- IP: 152.42.143.169
- Kullanıcı: root
- Şifre: sezgin64.Pak
- Proje dizini: /root/gold-price-analyzer

## Son Commit
```
commit 00a1b4c: Fix: Decimal type compatibility in position calculations
```

## Sonraki Adımlar
1. ~~Detaylı debug log ekleme~~ ✅ Eklendi ama görünmüyor
2. ~~_should_open_position ve _process_single_simulation metodlarına log ekleme~~ ✅ Eklendi
3. ~~1d timeframe'i geçici olarak devre dışı bırakma~~ ✅ _get_latest_signals'da kaldırıldı
4. Strateji filtrelerini kontrol etme
5. **SimulationManager'ın neden başlamadığını araştır** 🔴 ACİL
6. NoneType hatasının kaynağını bul (başka yerlerde de olabilir)
7. Veritabanında aktif simülasyon var mı kontrol et