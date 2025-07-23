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

### 6. Logger Sorunu ✅ ÇÖZÜLDÜ!
- **Sorun**: simulation.simulation_manager logları görünmüyordu
- **Sebep**: `logger = logging.getLogger(__name__)` kullanımı "simulation.simulation_manager" adında bağımsız logger oluşturuyordu
- **Çözüm**: `logger = logging.getLogger("gold_analyzer")` olarak değiştirildi
- **Sonuç**: Tüm SimulationManager logları artık görünüyor

### 7. Simülasyon Tabloları Eksik
- **Sorun**: "no such table: simulations" hatası
- **Sebep**: Simülasyon tabloları henüz oluşturulmamış
- **Çözüm**: `python storage/create_simulation_tables.py` çalıştırılmalı

## Mevcut Durum

### Çalışan Kısımlar
- SimulationManager başlatılıyor ✅
- 4 simülasyon yükleniyor ✅
- Trading saatleri kontrolü çalışıyor (TR saati) ✅
- Sinyaller alınıyor ✅
- ATR değerleri DB'de mevcut ✅
- **POZİSYONLAR AÇILIYOR!** ✅
  - Ana Strateji: 2 pozisyon
  - Momentum: 11 pozisyon
  - Toplam: 13 açık pozisyon

### Son Sinyaller (23.07.2025 07:51)
- 15m: BUY 0.449 (Ana strateji için yeterli)
- 1h: SELL 0.507 (Conservative hariç hepsi için yeterli)
- 4h: SELL 0.484 (Momentum ve Mean Reversion için yeterli)

### Sorunlar
1. ~~**Pozisyon açılmıyor**~~ ✅ ÇÖZÜLDÜ - 13 pozisyon açık!
2. **1d timeframe için yeterli mum yok** - "Not enough gram candles for 1d: 7/20"
3. **Günlük performans güncelleme hatası devam ediyor** - başka bir yerde NoneType sorunu var
4. ~~**SimulationManager logları görünmüyor**~~ ✅ ÇÖZÜLDÜ - Logger ismi düzeltildi
5. ~~**Simülasyon tabloları eksik**~~ ✅ ÇÖZÜLDÜ - Tablolar oluşturuldu

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
commit da9a87e: Fix logger issue in SimulationManager
```

## Yeni Bulgular (23.07.2025 Update)

### 🎉 SİSTEM ÇALIŞIYOR!
- **13 pozisyon açık**: Ana Strateji (2), Momentum (11)
- **Timeframe dağılımı**: 15m (2), 1h (6), 4h (5)
- **Conservative ve Mean Reversion**: Market koşulları uygun olmadığı için pozisyon yok

### Logger Sorunu Çözüldü ✅
- **Sorun**: `logger = logging.getLogger(__name__)` kullanımı
- **Çözüm**: `logger = logging.getLogger("gold_analyzer")` olarak değiştirildi
- **Sonuç**: Artık tüm debug logları görünüyor

### Confidence Değerleri Sorunu ✅ ÇÖZÜLDÜ
- **Bulgu**: Confidence değerleri hala yüksek (0.6-0.7)
- **Sinyaller**: 0.4 civarında
- **Çözüm**: `init_simulations.py` scripti oluşturuldu:
  - Ana Strateji: 0.35
  - Konservatif: 0.45  
  - Momentum: 0.40
  - Mean Reversion: 0.38
- **Sonuç**: Confidence eşikleri düşürüldü, sinyaller artık eşiği geçiyor

### Strategy Filter Sorunu ✅ ÇÖZÜLDÜ
- **Bulgu**: Basic checks passed ama strategy filter'lar fail oluyor
- **Momentum**: RSI 30-70 dışında olmalı - Şu an pozisyonlar açılıyor
- **Mean Reversion**: Bollinger band dışında olmalı - BB key sorunu çözüldü
- **Conservative**: Sabit 0.7 yerine config'den değer alınıyor
- **Sonuç**: Stratejiler artık doğru çalışıyor!

## Çözüm Önerisi

SimulationManager çalışıyor ve her dakika günlük performans güncellemeye çalışıyor. Bu da _process_simulations'ın çalıştığını gösteriyor. Ancak:

1. "SimulationManager initialized" logu görünmüyor - logger problemi olabilir
2. "Loading active simulations..." logu görünmüyor
3. NoneType hatası hala devam ediyor

**Muhtemel Sebepler:**
- Logger __name__ kullanıyor ("simulation.simulation_manager") ama main logger "gold_analyzer"
- Farklı logger instance'ları olabilir
- NoneType hatası başka bir yerde olabilir (total_capital hesaplaması değil)

## Sonraki Adımlar
1. ~~Detaylı debug log ekleme~~ ✅ Eklendi ve çalışıyor
2. ~~_should_open_position ve _process_single_simulation metodlarına log ekleme~~ ✅ Eklendi
3. ~~1d timeframe'i geçici olarak devre dışı bırakma~~ ✅ _get_latest_signals'da kaldırıldı
4. ~~Strateji filtrelerini kontrol etme~~ ✅ Düzeltildi
5. ~~**SimulationManager'ın neden başlamadığını araştır**~~ ✅ Başladı ve çalışıyor
6. ~~Veritabanında aktif simülasyon var mı kontrol et~~ ✅ 4 simülasyon aktif
7. **NoneType hatasının kaynağını bul** 🔴 Hala devam ediyor
8. Web dashboard'da simülasyon sonuçlarını görüntüle
9. Pozisyon kapatma mantığını test et