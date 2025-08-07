/**
 * Optimized Dashboard Manager
 * Tek API endpoint ile tüm dashboard verilerini yönetir
 * Memory leaks ve performans sorunlarını çözer
 */

class OptimizedDashboardManager {
    constructor() {
        this.isLoading = false;
        this.lastUpdate = null;
        this.updateInterval = null;
        this.websocket = null;
        this.retryCount = 0;
        this.maxRetries = 3;
        
        this.init();
    }

    init() {
        console.log('OptimizedDashboardManager başlatılıyor...');
        
        // DOM yüklendiğinde başlat
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', () => {
                this.loadDashboardData();
                this.initWebSocket();
                this.startAutoUpdate();
            });
        } else {
            this.loadDashboardData();
            this.initWebSocket();
            this.startAutoUpdate();
        }

        // Sayfa kapatıldığında cleanup
        window.addEventListener('beforeunload', () => {
            this.cleanup();
        });
    }

    async loadDashboardData() {
        if (this.isLoading) return;
        
        this.isLoading = true;
        this.showLoadingStates();

        try {
            const response = await fetch('/api/dashboard', {
                method: 'GET',
                headers: {
                    'Accept': 'application/json',
                    'Cache-Control': 'no-cache'
                }
            });

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }

            const data = await response.json();
            
            if (data.error) {
                throw new Error(data.error);
            }

            this.updateDashboard(data);
            this.lastUpdate = new Date();
            this.retryCount = 0; // Reset retry count on success
            
        } catch (error) {
            console.error('Dashboard veri yükleme hatası:', error);
            this.handleLoadError(error);
        } finally {
            this.isLoading = false;
            this.hideLoadingStates();
        }
    }

    updateDashboard(data) {
        try {
            // Current prices
            if (data.current_prices) {
                this.updateCurrentPrices(data.current_prices);
            }

            // Performance metrics
            if (data.performance) {
                this.updatePerformanceMetrics(data.performance);
            }

            // Market overview
            if (data.market_overview) {
                this.updateMarketOverview(data.market_overview);
            }

            // Signals
            if (data.signals) {
                this.updateSignals(data.signals);
            }

            // Technical indicators
            if (data.indicators) {
                this.updateTechnicalIndicators(data.indicators);
            }

            // Advanced modules
            if (data.fibonacci) {
                this.updateFibonacci(data.fibonacci);
            }
            
            if (data.smc) {
                this.updateSMC(data.smc);
            }
            
            if (data.divergence) {
                this.updateDivergence(data.divergence);
            }
            
            if (data.market_regime) {
                this.updateMarketRegime(data.market_regime);
            }

            // Update last update time
            this.updateLastUpdateTime();
            
        } catch (error) {
            console.error('Dashboard güncelleme hatası:', error);
        }
    }

    updateCurrentPrices(prices) {
        // Gram altın fiyatı
        const gramElement = document.getElementById('gram-altin');
        if (gramElement && prices.gram_altin) {
            gramElement.textContent = `₺${parseFloat(prices.gram_altin).toFixed(2)}`;
        }

        // ONS USD fiyatı
        const onsElement = document.getElementById('ons-usd');
        if (onsElement && prices.ons_usd) {
            onsElement.textContent = `$${parseFloat(prices.ons_usd).toFixed(2)}`;
        }

        // USD TRY kuru
        const usdElement = document.getElementById('usd-try');
        if (usdElement && prices.usd_try) {
            usdElement.textContent = `₺${parseFloat(prices.usd_try).toFixed(4)}`;
        }

        // Değişim yüzdeleri
        if (prices.changes) {
            this.updatePriceChanges(prices.changes);
        }
    }

    updatePriceChanges(changes) {
        // Gram altın değişimi
        if (changes.gram_altin) {
            const changeElement = document.getElementById('gram-change-pct');
            const changeValueElement = document.getElementById('gram-change-value');
            
            if (changeElement) {
                const pct = changes.gram_altin.change_pct;
                changeElement.textContent = `${pct > 0 ? '+' : ''}${pct.toFixed(2)}%`;
                changeElement.className = pct >= 0 ? 'text-green-400' : 'text-red-400';
            }
            
            if (changeValueElement) {
                const val = changes.gram_altin.change;
                changeValueElement.textContent = `${val > 0 ? '+' : ''}₺${val.toFixed(2)}`;
                changeValueElement.className = val >= 0 ? 'text-green-400' : 'text-red-400';
            }
        }
    }

    updatePerformanceMetrics(performance) {
        // Günlük performans
        if (performance.daily) {
            const dailyPnlElement = document.getElementById('daily-pnl');
            const dailyWinRateElement = document.getElementById('daily-winrate');
            
            if (dailyPnlElement) {
                const pnl = performance.daily.pnl || 0;
                dailyPnlElement.textContent = `${pnl > 0 ? '+' : ''}${pnl.toFixed(2)} gram`;
                dailyPnlElement.className = pnl >= 0 ? 'text-green-400' : 'text-red-400';
            }
            
            if (dailyWinRateElement) {
                const winRate = performance.daily.win_rate || 0;
                dailyWinRateElement.textContent = `${winRate.toFixed(1)}%`;
            }
        }

        // Haftalık performans
        if (performance.weekly) {
            const weeklyPnlElement = document.getElementById('weekly-pnl');
            if (weeklyPnlElement) {
                const pnl = performance.weekly.pnl || 0;
                weeklyPnlElement.textContent = `${pnl > 0 ? '+' : ''}${pnl.toFixed(2)} gram`;
                weeklyPnlElement.className = pnl >= 0 ? 'text-green-400' : 'text-red-400';
            }
        }

        // Overview stats
        if (performance.overview) {
            const currentPriceElement = document.getElementById('current-price-overview');
            const openPositionsElement = document.getElementById('open-positions');
            const lockedCapitalElement = document.getElementById('locked-capital');
            
            if (currentPriceElement && performance.overview.current_price) {
                currentPriceElement.textContent = `₺${performance.overview.current_price.toFixed(2)}`;
            }
            
            if (openPositionsElement) {
                openPositionsElement.textContent = performance.overview.open_positions || 0;
            }
            
            if (lockedCapitalElement) {
                lockedCapitalElement.textContent = `${(performance.overview.locked_capital || 0).toFixed(1)} gram`;
            }
        }
    }

    updateMarketOverview(overview) {
        // Günlük high/low
        const dailyHighElement = document.getElementById('daily-high');
        const dailyLowElement = document.getElementById('daily-low');
        
        if (dailyHighElement && overview.daily_high) {
            dailyHighElement.textContent = `₺${overview.daily_high.toFixed(2)}`;
        }
        
        if (dailyLowElement && overview.daily_low) {
            dailyLowElement.textContent = `₺${overview.daily_low.toFixed(2)}`;
        }

        // Market volatility
        const volatilityElement = document.getElementById('market-volatility');
        if (volatilityElement && overview.volatility) {
            volatilityElement.textContent = overview.volatility;
            volatilityElement.className = this.getVolatilityColor(overview.volatility);
        }

        // Market overview
        const marketOverviewElement = document.getElementById('market-overview');
        if (marketOverviewElement && overview.trend) {
            marketOverviewElement.textContent = overview.trend;
            marketOverviewElement.className = this.getTrendColor(overview.trend);
        }
    }

    updateTechnicalIndicators(indicators) {
        // RSI
        const rsiElement = document.getElementById('rsi-value');
        if (rsiElement && indicators.rsi) {
            rsiElement.textContent = indicators.rsi.value.toFixed(1);
            rsiElement.className = this.getRSIColor(indicators.rsi.value);
        }

        // MACD
        const macdElement = document.getElementById('macd-signal');
        if (macdElement && indicators.macd) {
            macdElement.textContent = indicators.macd.signal;
            macdElement.className = this.getSignalColor(indicators.macd.signal);
        }

        // Bollinger Bands
        const bbElement = document.getElementById('bb-position');
        if (bbElement && indicators.bollinger) {
            bbElement.textContent = indicators.bollinger.position;
            bbElement.className = this.getBBColor(indicators.bollinger.position);
        }
    }

    updateSignals(signals) {
        const signalElement = document.getElementById('current-signal');
        const signalStrengthElement = document.getElementById('signal-strength');
        
        if (signalElement && signals.current) {
            signalElement.textContent = signals.current.signal || 'WAIT';
            signalElement.className = this.getSignalColor(signals.current.signal);
        }
        
        if (signalStrengthElement && signals.current) {
            signalStrengthElement.textContent = `${(signals.current.confidence || 0).toFixed(1)}%`;
        }
    }

    updateFibonacci(fibonacci) {
        const fibStatusElement = document.getElementById('fibonacci-status');
        const fibLevelElement = document.getElementById('fibonacci-nearest-level');
        
        if (fibStatusElement) {
            if (fibonacci.status === 'success' && fibonacci.nearest_level) {
                fibStatusElement.textContent = 'Aktif';
                fibStatusElement.className = 'text-green-400';
            } else {
                fibStatusElement.textContent = fibonacci.message || 'Veri yok';
                fibStatusElement.className = 'text-yellow-400';
            }
        }
        
        if (fibLevelElement && fibonacci.nearest_level) {
            fibLevelElement.textContent = `${fibonacci.nearest_level.description} (₺${fibonacci.nearest_level.price.toFixed(2)})`;
        }
    }

    updateSMC(smc) {
        const smcSignalElement = document.getElementById('smc-signal');
        const smcStrengthElement = document.getElementById('smc-strength');
        
        if (smcSignalElement && smc.signals) {
            smcSignalElement.textContent = smc.signals.action;
            smcSignalElement.className = this.getSignalColor(smc.signals.action);
        }
        
        if (smcStrengthElement && smc.signals) {
            smcStrengthElement.textContent = `${smc.signals.strength.toFixed(1)}%`;
        }
    }

    updateDivergence(divergence) {
        const divSignalElement = document.getElementById('divergence-signal');
        const divStrengthElement = document.getElementById('divergence-strength');
        
        if (divSignalElement) {
            divSignalElement.textContent = divergence.overall_signal;
            divSignalElement.className = this.getSignalColor(divergence.overall_signal);
        }
        
        if (divStrengthElement) {
            divStrengthElement.textContent = `${divergence.signal_strength.toFixed(1)}%`;
        }
    }

    updateMarketRegime(regime) {
        const regimeElement = document.getElementById('market-regime');
        const volatilityRegimeElement = document.getElementById('volatility-regime');
        
        if (regimeElement && regime.trend_regime) {
            regimeElement.textContent = regime.trend_regime.type;
            regimeElement.className = this.getRegimeColor(regime.trend_regime.type);
        }
        
        if (volatilityRegimeElement && regime.volatility_regime) {
            volatilityRegimeElement.textContent = regime.volatility_regime.level;
            volatilityRegimeElement.className = this.getVolatilityColor(regime.volatility_regime.level);
        }
    }

    // WebSocket connection
    initWebSocket() {
        try {
            const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
            const wsUrl = `${protocol}//${window.location.host}/ws`;
            
            this.websocket = new WebSocket(wsUrl);
            
            this.websocket.onopen = () => {
                console.log('WebSocket bağlantısı kuruldu');
            };
            
            this.websocket.onmessage = (event) => {
                try {
                    const data = JSON.parse(event.data);
                    this.handleWebSocketMessage(data);
                } catch (error) {
                    console.error('WebSocket mesaj parse hatası:', error);
                }
            };
            
            this.websocket.onerror = (error) => {
                console.error('WebSocket hatası:', error);
            };
            
            this.websocket.onclose = () => {
                console.log('WebSocket bağlantısı kapandı, yeniden bağlanmaya çalışılıyor...');
                setTimeout(() => this.initWebSocket(), 5000);
            };
            
        } catch (error) {
            console.error('WebSocket başlatma hatası:', error);
        }
    }

    handleWebSocketMessage(data) {
        switch (data.type) {
            case 'price_update':
                if (data.data) {
                    this.updateCurrentPrices(data.data);
                }
                break;
            case 'performance_update':
                if (data.data) {
                    this.updatePerformanceMetrics(data.data);
                }
                break;
            case 'signal_update':
                if (data.data) {
                    this.updateSignals(data.data);
                }
                break;
        }
    }

    startAutoUpdate() {
        // 30 saniyede bir tam güncelleme
        this.updateInterval = setInterval(() => {
            this.loadDashboardData();
        }, 30000);
    }

    showLoadingStates() {
        const loadingElements = document.querySelectorAll('.loading-placeholder');
        loadingElements.forEach(el => {
            el.style.display = 'inline-block';
        });
    }

    hideLoadingStates() {
        const loadingElements = document.querySelectorAll('.loading-placeholder');
        loadingElements.forEach(el => {
            el.style.display = 'none';
        });
    }

    handleLoadError(error) {
        this.retryCount++;
        
        if (this.retryCount >= this.maxRetries) {
            console.error('Maksimum deneme sayısına ulaşıldı, hata durumu gösteriliyor');
            this.showErrorState(error.message);
        } else {
            console.log(`Yeniden deneme ${this.retryCount}/${this.maxRetries}`);
            setTimeout(() => this.loadDashboardData(), 5000);
        }
    }

    showErrorState(message) {
        const errorElements = document.querySelectorAll('[id$="-value"], [id$="-price"], [id$="-signal"]');
        errorElements.forEach(el => {
            el.textContent = 'Hata';
            el.className = 'text-red-400';
            el.title = message;
        });
    }

    updateLastUpdateTime() {
        const lastUpdateElement = document.getElementById('last-update');
        if (lastUpdateElement) {
            lastUpdateElement.textContent = new Date().toLocaleTimeString('tr-TR');
        }
    }

    // Utility methods for styling
    getSignalColor(signal) {
        switch(signal?.toUpperCase()) {
            case 'BUY': return 'text-green-400 font-semibold';
            case 'SELL': return 'text-red-400 font-semibold';
            case 'BULLISH': return 'text-green-400';
            case 'BEARISH': return 'text-red-400';
            case 'NEUTRAL': return 'text-gray-400';
            default: return 'text-gray-300';
        }
    }

    getRSIColor(value) {
        if (value >= 70) return 'text-red-400';
        if (value <= 30) return 'text-green-400';
        return 'text-yellow-400';
    }

    getVolatilityColor(level) {
        switch(level?.toLowerCase()) {
            case 'very_low': case 'düşük': return 'text-blue-400';
            case 'low': case 'orta': return 'text-green-400';
            case 'medium': case 'yüksek': return 'text-yellow-400';
            case 'high': case 'çok yüksek': return 'text-red-400';
            default: return 'text-gray-300';
        }
    }

    getTrendColor(trend) {
        switch(trend?.toLowerCase()) {
            case 'bullish': case 'yükseliş': return 'text-green-400';
            case 'bearish': case 'düşüş': return 'text-red-400';
            case 'ranging': case 'yatay': return 'text-yellow-400';
            default: return 'text-gray-300';
        }
    }

    getBBColor(position) {
        switch(position?.toLowerCase()) {
            case 'overbought': return 'text-red-400';
            case 'oversold': return 'text-green-400';
            case 'middle': return 'text-yellow-400';
            default: return 'text-gray-300';
        }
    }

    getRegimeColor(regime) {
        switch(regime?.toLowerCase()) {
            case 'trending': return 'text-green-400';
            case 'ranging': return 'text-yellow-400';
            case 'volatile': return 'text-red-400';
            default: return 'text-gray-300';
        }
    }

    cleanup() {
        if (this.updateInterval) {
            clearInterval(this.updateInterval);
        }
        
        if (this.websocket) {
            this.websocket.close();
        }
        
        console.log('OptimizedDashboardManager cleanup tamamlandı');
    }
}

// Global instance
window.optimizedDashboard = new OptimizedDashboardManager();