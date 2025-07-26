# CSS Modules Architecture

Bu proje CSS Modules mimarisi kullanmaktadır. Her CSS modülü kendi sorumluluğuna sahiptir ve bağımsız olarak yönetilebilir.

## Klasör Yapısı

```
static/css/
├── main.css                # Ana CSS dosyası - tüm modülleri import eder
├── modules/
│   ├── variables.css      # CSS değişkenleri ve design tokens
│   ├── base.css          # Global reset ve temel stiller
│   ├── layout.css        # Sayfa yapısı ve grid sistemleri
│   ├── glass-card.css    # Glass morphism kart bileşeni
│   ├── navigation.css    # Header ve navigasyon stilleri
│   ├── buttons.css       # Buton bileşenleri
│   ├── forms.css         # Form elemanları
│   ├── animations.css    # Animasyon ve geçişler
│   ├── utilities.css     # Yardımcı sınıflar
│   ├── dashboard.css     # Dashboard sayfası özel stilleri
│   ├── signals.css       # Trading sinyalleri stilleri
│   ├── charts.css        # Grafik bileşenleri
│   ├── mobile.css        # Mobil responsive stiller
│   └── scrollbar.css     # Özel scrollbar stilleri
```

## CSS Module Kullanımı

### 1. BEM Naming Convention

Tüm CSS sınıfları BEM (Block Element Modifier) metodolojisini takip eder:

```css
.block {}                  /* Block */
.block__element {}        /* Element */
.block--modifier {}       /* Modifier */
.block__element--modifier {} /* Element with modifier */
```

### 2. Component Örnekleri

#### Glass Card Component
```html
<div class="glass-card">
    <div class="glass-card__header">
        <h2 class="glass-card__title">Başlık</h2>
    </div>
    <div class="glass-card__body">
        İçerik
    </div>
    <div class="glass-card__footer">
        Footer
    </div>
</div>
```

#### Button Component
```html
<!-- Primary Button -->
<button class="btn btn--primary btn--lg">
    <i class="fas fa-save"></i>
    Kaydet
</button>

<!-- Ghost Button -->
<button class="btn btn--ghost btn--sm">İptal</button>

<!-- Icon Button -->
<button class="btn btn--icon">
    <i class="fas fa-times"></i>
</button>
```

#### Navigation Component
```html
<nav class="nav">
    <div class="nav__container">
        <div class="nav__logo">
            <i class="nav__logo-icon"></i>
            <span class="nav__logo-text">Logo</span>
        </div>
        <div class="nav__links">
            <a href="/" class="nav__item active">
                <div class="nav__link">
                    <i class="nav__icon"></i>
                    <span class="nav__text">Dashboard</span>
                </div>
                <div class="nav__underline"></div>
            </a>
        </div>
    </div>
</nav>
```

### 3. Utility Classes

Utility sınıfları hızlı stil değişiklikleri için kullanılır:

```html
<!-- Display -->
<div class="d-flex justify-center items-center">...</div>

<!-- Spacing -->
<div class="mt-lg mb-sm px-md">...</div>

<!-- Text -->
<p class="text-center text-muted text-sm">...</p>

<!-- Colors -->
<span class="text-success bg-glass">...</span>
```

### 4. Responsive Design

Mobile-first yaklaşım kullanılır:

```css
/* Mobile (default) */
.element { ... }

/* Tablet (768px+) */
@media (min-width: 768px) {
    .element { ... }
}

/* Desktop (1024px+) */
@media (min-width: 1024px) {
    .element { ... }
}
```

### 5. CSS Variables

Tüm renk, spacing ve diğer değerler CSS değişkenleri olarak tanımlanmıştır:

```css
/* Kullanım */
.element {
    color: var(--text-primary);
    padding: var(--spacing-md);
    border-radius: var(--radius-lg);
}
```

## Yeni Component Ekleme

1. `modules/` klasörüne yeni CSS dosyası oluştur
2. BEM naming convention'a uy
3. CSS variables kullan
4. `main.css` dosyasına import et

```css
/* modules/new-component.css */
.new-component {
    background: var(--bg-glass);
    padding: var(--spacing-md);
    border-radius: var(--radius-md);
}

.new-component__title {
    font-size: var(--text-lg);
    color: var(--text-primary);
}
```

## Best Practices

1. **Modülerlik**: Her component kendi CSS dosyasında
2. **Değişkenler**: Renk ve spacing için mutlaka CSS variables kullan
3. **BEM**: Tutarlı naming için BEM metodolojisini takip et
4. **Responsive**: Mobile-first yaklaşım
5. **Performance**: Gereksiz selector derinliğinden kaçın
6. **Accessibility**: Focus state'leri unutma

## Debugging

Browser DevTools'da CSS modüllerini debug etmek için:

1. Network sekmesinde `main.css` ve import edilen modülleri kontrol et
2. Elements sekmesinde computed styles'ı incele
3. CSS variables değerlerini `:root` elementinde gör