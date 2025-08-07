/**
 * Market Regime Detection JavaScript Functions
 * Volatilite, trend ve momentum göstergelerini yönetir
 */

class MarketRegimeManager {
    constructor() {
        this.currentRegime = null;
        this.updateInterval = null;
        this.historyChart = null;
        this.gaugeCharts = {};
        this.lastAlertCount = 0;
        
        // Element selectors
        this.elements = {
            widget: document.getElementById('market-regime-widget'),
            volatilityLevel: document.getElementById('volatility-level'),
            volatilityGauge: document.getElementById('volatility-gauge'),
            trendType: document.getElementById('trend-type'),
            trendGauge: document.getElementById('trend-gauge'),
            momentumState: document.getElementById('momentum-state'),
            momentumGauge: document.getElementById('momentum-gauge'),
            adaptiveParams: document.getElementById('adaptive-params'),
            regimeAlerts: document.getElementById('regime-alerts'),
            historyContainer: document.getElementById('regime-history-container'),
            transitionAlert: document.getElementById('transition-alert')
        };
    }
    
    /**
     * Market regime manager'ı başlat
     */
    async init() {
        try {
            // İlk yükleme
            await this.loadMarketRegime();
            
            // Periyodik güncelleme başlat (2 dakikada bir)
            this.startPeriodicUpdate();
            
            // Event listener'lar ekle
            this.setupEventListeners();
            
            console.log('Market Regime Manager başlatıldı');
        } catch (error) {
            console.error('Market regime manager başlatma hatası:', error);
        }
    }
    
    /**
     * Market regime verilerini yükle
     */
    async loadMarketRegime() {
        try {
            const response = await fetch('/api/market-regime');
            const data = await response.json();
            
            if (data.status === 'success') {
                this.currentRegime = data;
                this.updateRegimeDisplay(data);
                await this.loadRegimeAlerts();
            } else {
                this.handleError(data.message || 'Market regime verisi alınamadı');
            }
        } catch (error) {
            console.error('Market regime yükleme hatası:', error);
            this.handleError('Bağlantı hatası');
        }
    }
    
    /**
     * Market regime gösterimini güncelle
     */
    updateRegimeDisplay(data) {
        if (!this.elements.widget) return;
        
        // Widget'ın görünür olduğundan emin ol
        this.elements.widget.style.display = 'block';
        
        // Volatilite göstergesi
        this.updateVolatilityIndicator(data.volatility_regime);
        
        // Trend göstergesi
        this.updateTrendIndicator(data.trend_regime);
        
        // Momentum göstergesi
        this.updateMomentumIndicator(data.momentum_regime);
        
        // Adaptive parametreler
        this.updateAdaptiveParameters(data.adaptive_parameters);
        
        // Transition alert
        this.updateTransitionAlert(data.regime_transition);
        
        // Overall status güncelleme
        this.updateOverallStatus(data.overall_assessment);
        
        // Animation effect
        this.elements.widget.classList.add('regime-change-animation');
        setTimeout(() => {
            this.elements.widget.classList.remove('regime-change-animation');
        }, 500);
    }
    
    /**
     * Volatilite göstergesini güncelle
     */
    updateVolatilityIndicator(volatilityData) {
        const container = document.getElementById('volatility-indicator');
        if (!container) return;
        
        const level = volatilityData.level;
        const atrValue = volatilityData.atr_value;
        const percentile = volatilityData.atr_percentile;
        const expanding = volatilityData.expanding;
        const contracting = volatilityData.contracting;
        const squeezePotential = volatilityData.squeeze_potential;
        
        // Level gösterimi
        const levelElement = container.querySelector('.regime-indicator-value');
        if (levelElement) {
            levelElement.textContent = this.translateVolatilityLevel(level);
            levelElement.className = `regime-indicator-value volatility-${level}`;
        }
        
        // Açıklama
        const descElement = container.querySelector('.regime-indicator-desc');
        if (descElement) {
            let description = `ATR: ${atrValue.toFixed(2)} (%${percentile.toFixed(0)} persentil)`;
            
            if (squeezePotential) {
                description += ' - Sıkışma!';
            } else if (expanding) {
                description += ' - Genişliyor';
            } else if (contracting) {
                description += ' - Daralan';
            }
            
            descElement.textContent = description;
        }
        
        // Gauge chart güncelle
        this.updateGaugeChart('volatility-gauge', percentile, this.getVolatilityColor(level));
    }
    
    /**
     * Trend göstergesini güncelle
     */
    updateTrendIndicator(trendData) {
        const container = document.getElementById('trend-indicator');
        if (!container) return;
        
        const type = trendData.type;
        const direction = trendData.direction;
        const adxValue = trendData.adx_value;
        const trendStrength = trendData.trend_strength;
        const breakoutPotential = trendData.breakout_potential;
        
        // Type gösterimi
        const typeElement = container.querySelector('.regime-indicator-value');
        if (typeElement) {
            const displayText = this.translateTrendType(type, direction);
            typeElement.textContent = displayText;
            typeElement.className = `regime-indicator-value trend-${type}`;
        }
        
        // Açıklama
        const descElement = container.querySelector('.regime-indicator-desc');
        if (descElement) {
            let description = `ADX: ${adxValue.toFixed(1)} - Güç: %${trendStrength.toFixed(0)}`;
            
            if (breakoutPotential) {
                description += ' - Breakout!';
            }
            
            descElement.textContent = description;
        }
        
        // Gauge chart güncelle
        this.updateGaugeChart('trend-gauge', trendStrength, this.getTrendColor(type));
    }
    
    /**
     * Momentum göstergesini güncelle
     */
    updateMomentumIndicator(momentumData) {
        const container = document.getElementById('momentum-indicator');
        if (!container) return;
        
        const state = momentumData.state;
        const rsiMomentum = momentumData.rsi_momentum;
        const macdMomentum = momentumData.macd_momentum;
        const alignment = momentumData.momentum_alignment;
        const reversalPotential = momentumData.reversal_potential;
        
        // State gösterimi
        const stateElement = container.querySelector('.regime-indicator-value');
        if (stateElement) {
            stateElement.textContent = this.translateMomentumState(state);
            stateElement.className = `regime-indicator-value momentum-${state}`;
        }
        
        // Açıklama
        const descElement = container.querySelector('.regime-indicator-desc');
        if (descElement) {
            let description = `RSI: ${rsiMomentum}, MACD: ${macdMomentum}`;
            
            if (state === 'exhausted') {
                description += ' - Tükenme!';
            } else if (reversalPotential > 70) {
                description += ' - Reversal!';
            } else if (!alignment) {
                description += ' - Uyumsuz';
            }
            
            descElement.textContent = description;
        }
        
        // Gauge chart güncelle
        const momentumScore = this.calculateMomentumScore(momentumData);
        this.updateGaugeChart('momentum-gauge', momentumScore, this.getMomentumColor(state));
    }
    
    /**
     * Adaptive parametreleri güncelle
     */
    updateAdaptiveParameters(params) {
        const container = document.getElementById('adaptive-params-grid');
        if (!container) return;
        
        const parameters = [
            { label: 'RSI Aşırı Alım', value: params.rsi_overbought.toFixed(0) },
            { label: 'RSI Aşırı Satım', value: params.rsi_oversold.toFixed(0) },
            { label: 'Sinyal Eşiği', value: (params.signal_threshold * 100).toFixed(0) + '%' },
            { label: 'Stop Loss Çarpan', value: params.stop_loss_multiplier.toFixed(1) + 'x' },
            { label: 'Take Profit Çarpan', value: params.take_profit_multiplier.toFixed(1) + 'x' },
            { label: 'Pozisyon Ayar', value: (params.position_size_adjustment * 100).toFixed(0) + '%' }
        ];
        
        container.innerHTML = parameters.map(param => `
            <div class="param-item">
                <span class="param-label">${param.label}</span>
                <span class="param-value">${param.value}</span>
            </div>
        `).join('');
    }
    
    /**
     * Transition alert güncelle
     */
    updateTransitionAlert(transitionData) {
        const container = document.getElementById('transition-alert');
        if (!container) return;
        
        if (transitionData.early_warning && transitionData.transition_probability > 50) {
            container.style.display = 'block';
            container.innerHTML = `
                <div class="transition-content">
                    <i class="fas fa-exchange-alt transition-icon"></i>
                    <div class="transition-text">
                        <div class="transition-title">Regime Değişimi Uyarısı</div>
                        <div class="transition-desc">
                            ${transitionData.current_regime} → ${transitionData.next_regime} 
                            (${transitionData.transition_probability.toFixed(0)}% olasılık)
                        </div>
                    </div>
                </div>
            `;
            
            // Pulse animation
            container.classList.add('regime-alert-pulse');
        } else {
            container.style.display = 'none';
            container.classList.remove('regime-alert-pulse');
        }
    }
    
    /**
     * Overall status güncelle
     */
    updateOverallStatus(assessment) {
        const statusElement = document.getElementById('regime-status');
        if (!statusElement) return;
        
        const riskLevel = assessment.risk_level;
        const opportunityLevel = assessment.opportunity_level;
        const overallScore = assessment.overall_score;
        
        let statusClass = 'active';
        let statusText = 'Normal';
        
        if (riskLevel === 'high') {
            statusClass = 'alert';
            statusText = 'Yüksek Risk';
        } else if (opportunityLevel === 'high') {
            statusClass = 'active';
            statusText = 'Fırsat';
        } else if (riskLevel === 'medium') {
            statusClass = 'warning';
            statusText = 'Dikkat';
        }
        
        statusElement.className = `regime-status ${statusClass}`;
        statusElement.textContent = statusText;
    }
    
    /**
     * Gauge chart güncelle
     */
    updateGaugeChart(elementId, value, color) {
        const svg = document.getElementById(elementId);
        if (!svg) return;
        
        const circumference = 2 * Math.PI * 45; // radius = 45
        const fillValue = Math.max(0, Math.min(100, value));
        const fillLength = (fillValue / 100) * circumference;
        
        // SVG oluştur eğer yoksa
        if (!svg.innerHTML) {
            svg.innerHTML = `
                <circle cx="60" cy="60" r="45" class="gauge-bg"></circle>
                <circle cx="60" cy="60" r="45" class="gauge-fill"
                    stroke-dasharray="0 ${circumference}"
                    transform="rotate(-90 60 60)"></circle>
                <text x="60" y="60" class="gauge-text">${fillValue.toFixed(0)}</text>
            `;
        }
        
        // Gauge'ı güncelle
        const fillCircle = svg.querySelector('.gauge-fill');
        const text = svg.querySelector('.gauge-text');
        
        if (fillCircle) {
            fillCircle.style.stroke = color;
            fillCircle.setAttribute('stroke-dasharray', `${fillLength} ${circumference}`);
        }
        
        if (text) {
            text.textContent = fillValue.toFixed(0);
            text.style.fill = color;
        }
    }
    
    /**
     * Regime alerts yükle
     */
    async loadRegimeAlerts() {
        try {
            const response = await fetch('/api/market-regime/alerts');
            const data = await response.json();
            
            if (data.status === 'success' && data.alerts) {
                this.updateRegimeAlerts(data.alerts);
            }
        } catch (error) {
            console.error('Regime alerts yükleme hatası:', error);
        }
    }
    
    /**
     * Regime alerts gösterimini güncelle
     */
    updateRegimeAlerts(alerts) {
        const container = document.getElementById('regime-alerts');
        if (!container) return;
        
        if (alerts.length === 0) {
            container.style.display = 'none';
            return;
        }
        
        container.style.display = 'block';
        container.innerHTML = alerts.map(alert => `
            <div class="regime-alert-badge ${alert.level.toLowerCase()}" title="${alert.recommendation}">
                <i class="fas fa-${this.getAlertIcon(alert.type)}"></i>
                <span>${alert.message}</span>
            </div>
        `).join('');
        
        // Yeni alert varsa sound effect (opsiyonel)
        if (alerts.length > this.lastAlertCount) {
            this.playAlertSound();
        }
        
        this.lastAlertCount = alerts.length;
    }
    
    /**
     * Periyodik güncelleme başlat
     */
    startPeriodicUpdate() {
        if (this.updateInterval) {
            clearInterval(this.updateInterval);
        }
        
        this.updateInterval = setInterval(async () => {
            await this.loadMarketRegime();
        }, 120000); // 2 dakika
    }
    
    /**
     * Event listeners kurulumu
     */
    setupEventListeners() {
        // History period buttons
        document.querySelectorAll('.regime-history-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const period = e.target.dataset.period;
                this.loadRegimeHistory(period);
                
                // Active button
                document.querySelectorAll('.regime-history-btn').forEach(b => 
                    b.classList.remove('active'));
                e.target.classList.add('active');
            });
        });
        
        // Refresh button
        const refreshBtn = document.getElementById('regime-refresh');
        if (refreshBtn) {
            refreshBtn.addEventListener('click', async () => {
                refreshBtn.classList.add('fa-spin');
                await this.loadMarketRegime();
                setTimeout(() => {
                    refreshBtn.classList.remove('fa-spin');
                }, 500);
            });
        }
    }
    
    /**
     * Regime history yükle ve chart'ı güncelle
     */
    async loadRegimeHistory(hours = 24) {
        try {
            const response = await fetch(`/api/market-regime/history?hours=${hours}`);
            const data = await response.json();
            
            if (data.status === 'success' && data.history) {
                this.updateHistoryChart(data.history);
            }
        } catch (error) {
            console.error('Regime history yükleme hatası:', error);
        }
    }
    
    /**
     * History chart güncelle
     */
    updateHistoryChart(historyData) {
        const container = document.getElementById('regime-history-chart');
        if (!container) return;
        
        // Chart data hazırla
        const chartData = {
            labels: historyData.map(item => new Date(item.timestamp).toLocaleTimeString('tr-TR', {
                hour: '2-digit',
                minute: '2-digit'
            })),
            datasets: [{
                label: 'Overall Score',
                data: historyData.map(item => item.overall_score),
                borderColor: 'rgb(255, 215, 0)',
                backgroundColor: 'rgba(255, 215, 0, 0.1)',
                tension: 0.4
            }]
        };
        
        // Chart oluştur veya güncelle
        if (this.historyChart) {
            this.historyChart.data = chartData;
            this.historyChart.update();
        } else {
            const ctx = container.getContext('2d');
            this.historyChart = new Chart(ctx, {
                type: 'line',
                data: chartData,
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    scales: {
                        y: {
                            beginAtZero: true,
                            max: 100,
                            grid: { color: 'rgba(75, 85, 99, 0.3)' },
                            ticks: { color: '#9ca3af' }
                        },
                        x: {
                            grid: { color: 'rgba(75, 85, 99, 0.3)' },
                            ticks: { color: '#9ca3af' }
                        }
                    },
                    plugins: {
                        legend: { display: false }
                    }
                }
            });
        }
    }
    
    // Utility functions
    translateVolatilityLevel(level) {
        const translations = {
            'very_low': 'Çok Düşük',
            'low': 'Düşük', 
            'medium': 'Orta',
            'high': 'Yüksek',
            'extreme': 'Ekstrem'
        };
        return translations[level] || level;
    }
    
    translateTrendType(type, direction) {
        const types = {
            'trending': 'Trendli',
            'ranging': 'Aralık',
            'transitioning': 'Geçiş'
        };
        
        const directions = {
            'bullish': '↗️',
            'bearish': '↘️',
            'neutral': '→'
        };
        
        return `${types[type] || type} ${directions[direction] || ''}`;
    }
    
    translateMomentumState(state) {
        const translations = {
            'accelerating': 'Hızlanıyor',
            'stable': 'Sabit',
            'decelerating': 'Yavaşlıyor',
            'exhausted': 'Tükenme'
        };
        return translations[state] || state;
    }
    
    getVolatilityColor(level) {
        const colors = {
            'very_low': '#06b6d4',
            'low': '#10b981',
            'medium': '#f59e0b', 
            'high': '#f97316',
            'extreme': '#ef4444'
        };
        return colors[level] || '#6b7280';
    }
    
    getTrendColor(type) {
        const colors = {
            'trending': '#10b981',
            'ranging': '#f59e0b',
            'transitioning': '#8b5cf6'
        };
        return colors[type] || '#6b7280';
    }
    
    getMomentumColor(state) {
        const colors = {
            'accelerating': '#10b981',
            'stable': '#06b6d4',
            'decelerating': '#f59e0b',
            'exhausted': '#ef4444'
        };
        return colors[state] || '#6b7280';
    }
    
    calculateMomentumScore(momentumData) {
        let score = 50; // Base score
        
        if (momentumData.momentum_alignment) score += 20;
        if (momentumData.state === 'accelerating') score += 30;
        else if (momentumData.state === 'exhausted') score -= 30;
        else if (momentumData.state === 'decelerating') score -= 15;
        
        if (momentumData.reversal_potential > 70) score -= 20;
        
        return Math.max(0, Math.min(100, score));
    }
    
    getAlertIcon(type) {
        const icons = {
            'VOLATILITY_SQUEEZE': 'compress',
            'EXTREME_VOLATILITY': 'exclamation-triangle',
            'BREAKOUT_POTENTIAL': 'arrow-up',
            'MOMENTUM_EXHAUSTION': 'battery-empty',
            'REVERSAL_WARNING': 'exchange-alt',
            'REGIME_TRANSITION': 'sync-alt'
        };
        return icons[type] || 'bell';
    }
    
    playAlertSound() {
        // Basit alert sesi (opsiyonel)
        if ('AudioContext' in window) {
            const audioContext = new AudioContext();
            const oscillator = audioContext.createOscillator();
            const gainNode = audioContext.createGain();
            
            oscillator.connect(gainNode);
            gainNode.connect(audioContext.destination);
            
            oscillator.frequency.setValueAtTime(800, audioContext.currentTime);
            gainNode.gain.setValueAtTime(0.1, audioContext.currentTime);
            gainNode.gain.exponentialRampToValueAtTime(0.01, audioContext.currentTime + 0.5);
            
            oscillator.start();
            oscillator.stop(audioContext.currentTime + 0.5);
        }
    }
    
    handleError(message) {
        console.error('Market regime hatası:', message);
        
        // Error state göster
        if (this.elements.widget) {
            this.elements.widget.innerHTML = `
                <div class="regime-error">
                    <i class="fas fa-exclamation-triangle text-yellow-400"></i>
                    <p class="text-sm text-gray-400 mt-2">Market regime verisi yüklenemedi</p>
                    <p class="text-xs text-gray-500">${message}</p>
                    <button onclick="window.marketRegime.loadMarketRegime()" 
                            class="mt-2 px-3 py-1 bg-blue-600 text-white text-xs rounded hover:bg-blue-700">
                        Tekrar Dene
                    </button>
                </div>
            `;
        }
    }
    
    destroy() {
        if (this.updateInterval) {
            clearInterval(this.updateInterval);
        }
        
        if (this.historyChart) {
            this.historyChart.destroy();
        }
    }
}

// Global instance
window.marketRegime = new MarketRegimeManager();

// Auto-initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    if (document.getElementById('market-regime-widget')) {
        window.marketRegime.init();
    }
});