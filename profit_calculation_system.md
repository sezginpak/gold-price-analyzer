# Profit Calculation System - Modüler Kar Hesaplama Sistemi

## 📋 Genel Bakış

Bu doküman, kuyumcu API'sinde kullanılan modüler kar hesaplama sistemini açıklar. Sistem, farklı kar kaynaklarını bağımsız olarak yönetmek ve hesaplamak için tasarlanmıştır.

## 🏗️ Sistem Mimarisi

### 1. Temel Yapı

```
app/services/
├── profit_service.py                    # Ana kar yönetim servisi
├── enhanced_profit_service.py           # Yardımcı kar hesaplama servisi
└── profit_calculators/                  # Modüler kar hesaplayıcılar
    ├── __init__.py
    ├── base.py                         # Base calculator ve result sınıfı
    ├── sales_profit_calculator.py      # Satış karları
    ├── consolidated_asset_profit_calculator.py  # Asset karları
    ├── position_profit_calculator.py   # Position dönüşüm karları
    └── scrap_gold_profit_calculator.py # Hurda altın karları
```

### 2. İkili Kar Hesaplama Sistemi

Tüm kar hesaplamaları iki boyutta yapılır:

1. **TL Bazlı Kar (Muhasebe Karı)**
   - Klasik muhasebe yaklaşımı
   - TL gelir - TL maliyet = TL kar
   - Vergi ve raporlama için kullanılır

2. **Altın Bazlı Kar (Gerçek Zenginlik Artışı)**
   - Altın gram cinsinden kar/zarar
   - Enflasyondan arındırılmış gerçek kar
   - İş performansının gerçek göstergesi

## 💰 Altın Fiyat Kullanımı

Sistem, HaremAltin API'sinden gerçek zamanlı has altın (1000 milyem) fiyatlarını kullanır:

1. **Alış Fiyatı (Buy Price)**:
   - Varlık değerleme için kullanılır
   - Eldeki altının güncel değerini hesaplamak için
   - `get_current_gold_price("buy")`

2. **Satış Fiyatı (Sell Price)**:
   - Kar hesaplamaları için kullanılır
   - Satış geliri ve kar marjı hesaplamalarında
   - `get_current_gold_price("sell")` (varsayılan)

**Kaynak**: `app.core.get_prices.HaremAltinPriceService`

## 📊 Kar Kaynakları

### 1. Sales Profit (Satış Karları)

**Kaynak:** `SalesProfitCalculator`

**Kar Hesaplama:**
- Satış geliri - Ürün maliyeti = Satış karı
- İşçilik karları dahil
- Hurda satış karları dahil

**Örnek Hesaplama:**
```python
# Bilezik satışı
Satış fiyatı: 5,000 TL
Altın maliyeti: 4,000 TL
İşçilik maliyeti: 500 TL
Kar: 5,000 - (4,000 + 500) = 500 TL

# Altın bazlı
Satılan gram: 1.00g
Alış gram değeri: 0.95g
Altın karı: -0.05g (altın kaybı)
```

### 2. Consolidated Asset Profit (Ham Altın Karları)

**Kaynak:** `ConsolidatedAssetProfitCalculator`

**Kar Türleri:**

#### a) Milyem Farkı Karı
- 900 milyem olarak alınan altın, 916 milyem çıkarsa
- Kar = (916-900) / 1000 * ağırlık * altın fiyatı

**Örnek:**
```python
Alış: 10g, 900 milyem
Gerçek: 10g, 916 milyem
Has altın kazancı: 10 * (916-900)/1000 = 0.16g
TL karşılığı: 0.16g * 4,300 TL = 688 TL
```

#### b) Arbitraj Karı
- Tam çeyrek (1.75g) alıp 1.80g olarak satmak
- Fiyat farklarından yararlanma

### 3. Position Profit (Pozisyon Dönüşüm Karları)

**Kaynak:** `PositionProfitCalculator`

**Kar Türleri:**

#### a) TL → Altın Dönüşüm Karı
- TL'nin ortalama altın maliyeti ile güncel kur farkı
- Düşük maliyetli TL ile altın almak

**Örnek:**
```python
TL pozisyonu: 10,000 TL (ort. maliyet: 4,200 TL/g)
Güncel kur: 4,300 TL/g
Alınan altın: 10,000 / 4,300 = 2.326g
Maliyet farkı: (4,300 - 4,200) * 2.326 = 232.6 TL kar
```

#### b) Altın → TL Realizasyon Karı
- Altını TL'ye çevirirken oluşan kar/zarar
- Alış ve satış fiyatı farkı

### 4. Scrap Gold Profit (Hurda Altın Karları)

**Kaynak:** `ScrapGoldProfitCalculator`

**Kar Türleri:**

#### a) Hurda Alış Spread'i
```python
Has değer: 1g * 4,300 TL = 4,300 TL
Ödenen: 1g * 4,100 TL = 4,100 TL
Spread karı: 200 TL
```

#### b) Hurda Satış Spread'i
```python
Satış fiyatı: 1g * 4,250 TL = 4,250 TL
Has değer: 1g * 4,300 TL = 4,300 TL
Spread karı: -50 TL (zarar)
```

## 🔧 Implementasyon Detayları

### BaseProfitCalculator Sınıfı

```python
class BaseProfitCalculator(ABC):
    """Tüm calculator'lar için base class"""
    
    @abstractmethod
    async def calculate(
        self,
        branch_id: PyObjectId,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        **kwargs
    ) -> List[ProfitCalculationResult]:
        """Kar hesaplama metodu"""
        pass
        
    @abstractmethod
    async def calculate_for_transaction(
        self,
        transaction_id: PyObjectId,
        **kwargs
    ) -> Optional[ProfitCalculationResult]:
        """Tek işlem için kar hesaplama"""
        pass
```

### ProfitCalculationResult Sınıfı

```python
class ProfitCalculationResult:
    """Kar hesaplama sonucu"""
    
    # TL bazlı
    tl_revenue: Decimal          # TL gelir
    tl_cost: Decimal            # TL maliyet
    tl_profit: Decimal          # TL kar
    
    # Altın bazlı
    gold_revenue_grams: Decimal  # Altın gelir (gram)
    gold_cost_grams: Decimal    # Altın maliyet (gram)
    gold_profit_grams: Decimal  # Altın kar (gram)
    
    # Metadata
    metadata: Dict[str, Any]    # Ek bilgiler
```

## 📈 API Kullanımı

### 1. Kapsamlı Kar Hesaplama

```python
# Tüm kaynaklardan kar hesapla
result = await profit_service.calculate_comprehensive_profit(
    branch_id=branch_id,
    start_date=datetime(2025, 1, 1),
    end_date=datetime(2025, 1, 31),
    profit_sources=["sales", "positions", "scrap_gold"]
)

# Sonuç formatı
{
    "branch_id": "xxx",
    "start_date": "2025-01-01",
    "end_date": "2025-01-31",
    "sources": {
        "sales": {
            "count": 150,
            "tl_profit": 25000.0,
            "gold_profit_grams": -2.5,
            "details": [...]
        },
        "positions": {
            "count": 10,
            "tl_profit": 5000.0,
            "gold_profit_grams": 0.0,
            "details": [...]
        }
    },
    "totals": {
        "tl_profit": 30000.0,
        "gold_profit_grams": -2.5,
        "is_real_profit": false
    }
}
```

### 2. Tek Kaynak Kar Hesaplama

```python
# Sadece satış karları
sales_profits = await profit_service.calculate_profit_for_source(
    source="sales",
    branch_id=branch_id,
    start_date=start_date,
    end_date=end_date
)
```

## 🚀 Yeni Kar Kaynağı Ekleme

Yeni bir kar kaynağı eklemek için:

1. **Calculator Oluştur:**
```python
# app/services/profit_calculators/new_source_calculator.py
from .base import BaseProfitCalculator, ProfitCalculationResult

class NewSourceProfitCalculator(BaseProfitCalculator):
    def get_source_name(self) -> str:
        return "new_source"
        
    async def calculate(self, **kwargs) -> List[ProfitCalculationResult]:
        # Implementasyon
        pass
```

2. **__init__.py'ye Ekle:**
```python
from .new_source_calculator import NewSourceProfitCalculator
```

3. **ProfitService'e Entegre Et:**
```python
self.new_source_calculator = NewSourceProfitCalculator(db)

# calculate_comprehensive_profit metoduna ekle
if "new_source" in profit_sources:
    new_profits = await self.new_source_calculator.calculate(...)
```

## 📊 Performans ve Optimizasyon

### 1. Paralel Hesaplama
```python
# Tüm calculator'ları paralel çalıştır
import asyncio

tasks = []
if "sales" in profit_sources:
    tasks.append(self.sales_calculator.calculate(...))
if "positions" in profit_sources:
    tasks.append(self.position_calculator.calculate(...))
    
results = await asyncio.gather(*tasks)
```

### 2. Cache Kullanımı
- Altın fiyatları cache'lenir
- Sık kullanılan hesaplamalar cache'lenebilir

### 3. Batch İşleme
- Büyük tarih aralıkları için batch processing
- Progress tracking eklenebilir

## 🔍 Kar Analizi Örnekleri

### 1. Günlük Kar Özeti
```python
# Bugünün kar özeti
today_profit = await profit_service.calculate_comprehensive_profit(
    branch_id=branch_id,
    start_date=datetime.now().replace(hour=0, minute=0),
    end_date=datetime.now()
)
```

### 2. Kar Kaynak Analizi
```python
# En karlı kaynak hangisi?
all_sources = await profit_service.calculate_comprehensive_profit(
    branch_id=branch_id,
    start_date=month_start,
    end_date=month_end
)

# Sıralama
sorted_sources = sorted(
    all_sources["sources"].items(),
    key=lambda x: x[1]["tl_profit"],
    reverse=True
)
```

### 3. Gerçek Kar Kontrolü
```python
# Altın bazında kar var mı?
if result["totals"]["gold_profit_grams"] > 0:
    print("Gerçek kar var! Altın artışı:", result["totals"]["gold_profit_grams"])
else:
    print("Sadece enflasyonist kar. Altın kaybı:", abs(result["totals"]["gold_profit_grams"]))
```

## 📝 Notlar ve İpuçları

1. **Kar Realizasyonu:**
   - PENDING: Henüz kesinleşmemiş kar (satış yapıldı, ödeme bekleniyor)
   - REALIZED: Kesinleşmiş kar (ödeme alındı)

2. **Kar Marjı Hesaplama:**
   - TL Marjı = (TL Kar / TL Gelir) * 100
   - Sektör ortalaması: %5-15 arası

3. **Altın Kar Yorumlama:**
   - Pozitif: Gerçek zenginlik artışı
   - Negatif: Altın kaybı (enflasyonist kar)
   - Sıfır: Başabaş

4. **Vergi Hususları:**
   - TL karı vergi matrahıdır
   - Altın karı vergilendirilmez (sadece analiz için)

## 🔗 İlgili Dosyalar

- `/app/models/profit.py` - Profit modelleri
- `/app/services/profit_service.py` - Ana profit servisi
- `/app/services/enhanced_profit_service.py` - Yardımcı hesaplamalar
- `/app/api/api_v1/endpoints/profits.py` - API endpoint'leri
- `/docs/position_management_plan.md` - Position yönetimi
- `/docs/portfolio_management_plan.md` - Portfolio yönetimi