# Web Modülleri

Bu klasör, Gold Price Analyzer web arayüzünün modüler yapısını içerir.

## Klasör Yapısı

```
web/
├── routes/          # API ve sayfa route'ları
│   ├── api.py      # Genel API endpoint'leri
│   ├── analysis.py # Analiz API endpoint'leri
│   ├── dashboard.py # HTML sayfa route'ları
│   ├── simulation.py # Simülasyon API endpoint'leri
│   └── static.py   # Static dosya ayarları
├── handlers/        # WebSocket ve diğer handler'lar
│   └── websocket.py # WebSocket bağlantı yönetimi
├── utils/          # Yardımcı fonksiyonlar
│   ├── cache.py    # Cache yönetimi
│   ├── stats.py    # İstatistik yönetimi
│   └── formatters.py # Veri formatlama fonksiyonları
└── middleware/     # Middleware'ler (henüz kullanılmıyor)
```

## Özellikler

### Route Modülleri

#### `routes/api.py`
- `/api/stats` - Sistem istatistikleri
- `/api/prices/*` - Fiyat verileri
- `/api/candles/*` - OHLC mum verileri
- `/api/signals/*` - Trading sinyalleri
- `/api/logs/*` - Log yönetimi
- `/api/market/overview` - Piyasa genel görünümü
- `/api/alerts/active` - Aktif uyarılar
- `/api/performance/metrics` - Performans metrikleri

#### `routes/analysis.py`
- `/api/analysis/config` - Analiz konfigürasyonu
- `/api/analysis/trigger/{timeframe}` - Manuel analiz tetikleme
- `/api/analysis/history` - Analiz geçmişi
- `/api/analysis/details` - Detaylı analiz bilgileri
- `/api/analysis/levels` - Destek/Direnç seviyeleri
- `/api/analysis/indicators/{timeframe}` - Teknik göstergeler
- `/api/analysis/performance/summary` - Performans özeti
- `/api/analysis/patterns/active` - Aktif chart pattern'leri

#### `routes/simulation.py`
- `/api/simulations/list` - Simülasyon listesi
- `/api/simulations/{sim_id}/positions` - Pozisyon detayları
- `/api/simulations/{sim_id}/performance` - Performans grafiği
- `/api/simulations/{sim_id}/summary` - Simülasyon özeti
- `/api/simulations/{sim_id}/trades/recent` - Son işlemler
- `/api/simulations/{sim_id}/statistics` - Detaylı istatistikler

#### `routes/dashboard.py`
- `/` - Ana dashboard
- `/analysis` - Analiz sayfası
- `/signals` - Sinyaller sayfası
- `/logs` - Log görüntüleme sayfası
- `/simulations` - Simülasyon sayfası
- `/menu` - Menu component'i

### Utility Modülleri

#### `utils/cache.py`
- Basit TTL tabanlı cache sistemi
- Varsayılan 30 saniye cache süresi
- API yanıtlarını hızlandırır

#### `utils/stats.py`
- Global sistem istatistikleri
- Uptime, bağlantı sayısı, hata sayısı vb.
- Periyodik güncelleme desteği

#### `utils/formatters.py`
- Analiz özetlerini formatlar
- Log satırlarını parse eder
- Timezone dönüşümleri yapar

### Handler Modülleri

#### `handlers/websocket.py`
- WebSocket bağlantılarını yönetir
- Real-time fiyat güncellemeleri gönderir
- Otomatik bağlantı yönetimi

## Kullanım

Web server başlatıldığında tüm modüller otomatik olarak yüklenir:

```python
from web import (
    dashboard_router,
    api_router,
    analysis_router,
    simulation_router,
    WebSocketManager,
    cache,
    stats
)

# Route'ları ekle
app.include_router(dashboard_router)
app.include_router(api_router)
app.include_router(analysis_router)
app.include_router(simulation_router)
```

## Yeni Endpoint Ekleme

1. İlgili route modülüne fonksiyon ekleyin
2. Uygun decorator kullanın (`@router.get`, `@router.post` vb.)
3. Gerekirse cache kullanın
4. Hata yönetimi ekleyin

Örnek:
```python
@router.get("/yeni-endpoint")
async def yeni_endpoint():
    cached = cache.get("yeni_endpoint")
    if cached:
        return cached
    
    try:
        # İşlemler...
        result = {"data": "..."}
        cache.set("yeni_endpoint", result)
        return result
    except Exception as e:
        logger.error(f"Hata: {e}")
        return {"error": str(e)}
```

## Notlar

- Tüm route'lar prefix ile tanımlanır (`/api`, `/api/analysis` vb.)
- WebSocket endpoint'i ana web_server.py'de tanımlıdır
- Cache sistemi thread-safe değildir, production'da Redis kullanılmalı
- Tüm timestamp'ler Türkiye saatine çevrilir