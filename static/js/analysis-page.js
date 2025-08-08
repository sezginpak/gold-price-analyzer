/**
 * Analysis Page Manager
 * Analiz sayfasındaki tüm bileşenleri yönetir
 */

class AnalysisPageManager {
    constructor() {
        this.regimeData = null;
        this.divergenceData = null;
        this.fibonacciData = null;
        this.smcData = null;
        this.updateInterval = null;
        this.charts = {};
        
        this.init();
    }

    init() {
        console.log('AnalysisPageManager başlatılıyor...');
        
        // DOM hazır olduğunda başlat
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', () => {
                this.loadAllData();
                this.startPeriodicUpdate();
            });
        } else {
            this.loadAllData();
            this.startPeriodicUpdate();
        }

        // Page visibility change detection
        document.addEventListener('visibilitychange', () => {
            if (!document.hidden) {
                this.loadAllData(); // Sayfa aktif olduğunda yenile
            }
        });
    }

    async loadAllData() {
        console.log('Analiz verilerini yüklüyor...');
        
        // Paralel olarak tüm verileri yükle
        const promises = [
            this.loadMarketRegime(),
            this.loadDivergenceAnalysis(),
            this.loadFibonacciAnalysis(),
            this.loadSMCAnalysis()
        ];

        try {
            await Promise.allSettled(promises);
            this.updateLastRefreshTime();
        } catch (error) {
            console.error('Veri yükleme hatası:', error);
        }
    }

    async loadMarketRegime() {
        try {
            const response = await fetch('/api/market-regime', {
                headers: { 'Cache-Control': 'no-cache' }
            });
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }

            const data = await response.json();
            
            if (data.status === 'success') {
                this.regimeData = data;
                this.updateMarketRegimeDisplay(data);
            } else {
                this.showMarketRegimeError(data.message || 'Veri alınamadı');
            }
        } catch (error) {
            console.error('Market regime yükleme hatası:', error);
            this.showMarketRegimeError('Bağlantı hatası');
        }
    }

    updateMarketRegimeDisplay(data) {
        try {
            // Status güncelle
            const statusElement = document.getElementById('analysis-regime-status');
            if (statusElement) {
                statusElement.textContent = 'Aktif';
                statusElement.className = 'regime-status active';
            }

            // Volatilite rejimi
            if (data.volatility_regime) {
                this.updateElement('analysis-volatility-level', data.volatility_regime.level || 'N/A');
                this.updateElement('analysis-volatility-desc', this.getVolatilityDescription(data.volatility_regime));
                this.updateVolatilityGauge(data.volatility_regime);
            }

            // Trend rejimi
            if (data.trend_regime) {
                this.updateElement('analysis-trend-type', data.trend_regime.type || 'N/A');
                this.updateElement('analysis-trend-desc', this.getTrendDescription(data.trend_regime));
                this.updateTrendGauge(data.trend_regime);
            }

            // Momentum rejimi
            if (data.momentum_regime) {
                this.updateElement('analysis-momentum-state', data.momentum_regime.state || 'N/A');
                this.updateElement('analysis-momentum-desc', this.getMomentumDescription(data.momentum_regime));
                this.updateMomentumGauge(data.momentum_regime);
            }

            // Adaptive parametreler
            if (data.adaptive_parameters) {
                this.updateAdaptiveParameters(data.adaptive_parameters);
            }

            // Öneriler
            if (data.recommendations) {
                this.updateRecommendations(data.recommendations);
            }

            // Uyarılar ve fırsatlar
            this.updateWarningsOpportunities(data);

            console.log('Market regime display güncellendi');
        } catch (error) {
            console.error('Market regime display güncelleme hatası:', error);
        }
    }

    updateAdaptiveParameters(params) {
        // RSI parametreleri
        this.updateElement('analysis-rsi-overbought', params.rsi_overbought?.toFixed(1) || '-');
        this.updateElement('analysis-rsi-oversold', params.rsi_oversold?.toFixed(1) || '-');

        // Risk yönetimi parametreleri
        this.updateElement('analysis-stop-multiplier', params.stop_loss_multiplier?.toFixed(1) || '-');
        this.updateElement('analysis-tp-multiplier', params.take_profit_multiplier?.toFixed(1) || '-');
        this.updateElement('analysis-position-adjustment', params.position_size_adjustment?.toFixed(2) || '-');
        this.updateElement('analysis-signal-threshold', params.signal_threshold?.toFixed(2) || '-');
    }

    updateRecommendations(recommendations) {
        this.updateElement('analysis-strategy-recommendation', recommendations.strategy || 'N/A');
        this.updateElement('analysis-position-recommendation', recommendations.position_sizing || 'N/A');
        this.updateElement('analysis-timeframe-recommendation', recommendations.time_horizon || 'N/A');
        
        // Market fazı - overall_assessment'dan al
        if (this.regimeData?.overall_assessment?.market_phase) {
            this.updateElement('analysis-phase-recommendation', this.regimeData.overall_assessment.market_phase);
        }
    }

    updateWarningsOpportunities(data) {
        const element = document.getElementById('analysis-warnings-opportunities');
        if (!element) return;

        let content = [];

        // Uyarılar ekle
        if (data.recommendations?.warnings?.length > 0) {
            content.push(`⚠️ ${data.recommendations.warnings.join(', ')}`);
        }

        // Fırsatlar ekle
        if (data.recommendations?.opportunities?.length > 0) {
            content.push(`💡 ${data.recommendations.opportunities.join(', ')}`);
        }

        // Genel değerlendirme
        if (data.overall_assessment) {
            const assessment = data.overall_assessment;
            content.push(`📊 Risk: ${assessment.risk_level || 'N/A'} | Fırsat: ${assessment.opportunity_level || 'N/A'}`);
        }

        element.textContent = content.length > 0 ? content.join(' • ') : 'Aktif uyarı veya fırsat bulunmuyor.';
    }

    updateVolatilityGauge(volatilityData) {
        // SVG gauge güncelleme (basitleştirilmiş)
        const gaugeElement = document.getElementById('analysis-volatility-gauge');
        if (gaugeElement && volatilityData.atr_percentile) {
            this.createSimpleGauge(gaugeElement, volatilityData.atr_percentile, 100, 'cyan');
        }
    }

    updateTrendGauge(trendData) {
        const gaugeElement = document.getElementById('analysis-trend-gauge');
        if (gaugeElement && trendData.trend_strength) {
            this.createSimpleGauge(gaugeElement, trendData.trend_strength, 100, 'green');
        }
    }

    updateMomentumGauge(momentumData) {
        const gaugeElement = document.getElementById('analysis-momentum-gauge');
        if (gaugeElement && momentumData.reversal_potential !== undefined) {
            this.createSimpleGauge(gaugeElement, momentumData.reversal_potential, 100, 'orange');
        }
    }

    createSimpleGauge(svgElement, value, max, color) {
        if (!svgElement) return;

        // SVG temizle
        svgElement.innerHTML = '';

        const percentage = Math.min((value / max) * 100, 100);
        const angle = (percentage / 100) * 180; // Yarı çember için 180 derece

        // SVG namespace
        const svgNS = 'http://www.w3.org/2000/svg';

        // Background circle
        const bgCircle = document.createElementNS(svgNS, 'path');
        bgCircle.setAttribute('d', 'M 20 60 A 40 40 0 0 1 100 60');
        bgCircle.setAttribute('stroke', '#374151');
        bgCircle.setAttribute('stroke-width', '8');
        bgCircle.setAttribute('fill', 'none');
        svgElement.appendChild(bgCircle);

        // Progress arc
        if (percentage > 0) {
            const endAngle = (angle * Math.PI) / 180;
            const x = 60 + 40 * Math.cos(Math.PI - endAngle);
            const y = 60 - 40 * Math.sin(Math.PI - endAngle);
            const largeArc = percentage > 50 ? 1 : 0;

            const progressPath = document.createElementNS(svgNS, 'path');
            progressPath.setAttribute('d', `M 20 60 A 40 40 0 ${largeArc} 1 ${x} ${y}`);
            progressPath.setAttribute('stroke', this.getColorByName(color));
            progressPath.setAttribute('stroke-width', '8');
            progressPath.setAttribute('fill', 'none');
            progressPath.setAttribute('stroke-linecap', 'round');
            svgElement.appendChild(progressPath);
        }

        // Value text
        const text = document.createElementNS(svgNS, 'text');
        text.setAttribute('x', '60');
        text.setAttribute('y', '80');
        text.setAttribute('text-anchor', 'middle');
        text.setAttribute('fill', 'white');
        text.setAttribute('font-size', '14');
        text.setAttribute('font-weight', 'bold');
        text.textContent = `${value.toFixed(1)}`;
        svgElement.appendChild(text);
    }

    getColorByName(colorName) {
        const colors = {
            'cyan': '#06b6d4',
            'green': '#10b981',
            'orange': '#f97316',
            'purple': '#8b5cf6',
            'blue': '#3b82f6'
        };
        return colors[colorName] || '#6b7280';
    }

    async loadDivergenceAnalysis() {
        try {
            const response = await fetch('/api/divergence');
            const data = await response.json();
            
            if (data.status === 'success') {
                this.divergenceData = data;
                this.updateDivergenceDisplay(data);
                console.log('Divergence verisi yüklendi:', data.overall_signal);
            } else {
                this.showDivergenceError(data.message || 'Veri alınamadı');
            }
        } catch (error) {
            console.error('Divergence yükleme hatası:', error);
            this.showDivergenceError('Bağlantı hatası');
        }
    }

    updateDivergenceDisplay(data) {
        try {
            // Divergence status
            const statusElement = document.getElementById('analysis-divergence-status');
            if (statusElement) {
                if (data.overall_signal && data.overall_signal !== 'NEUTRAL') {
                    statusElement.textContent = `${data.overall_signal} Sinyal`;
                    statusElement.className = `divergence-status active ${data.overall_signal.toLowerCase()}`;
                } else {
                    statusElement.textContent = 'Nötr';
                    statusElement.className = 'divergence-status inactive';
                }
            }

            // Divergence table
            this.updateDivergenceTable(data);
            
        } catch (error) {
            console.error('Divergence display güncelleme hatası:', error);
        }
    }

    updateDivergenceTable(data) {
        const table = document.getElementById('detailed-divergence-table');
        if (!table) return;

        let html = `
            <thead>
                <tr class="border-b border-gray-600">
                    <th class="text-left px-3 py-2 text-sm">Tip</th>
                    <th class="text-left px-3 py-2 text-sm">Gösterge</th>
                    <th class="text-left px-3 py-2 text-sm">Güç</th>
                    <th class="text-left px-3 py-2 text-sm">Sınıf</th>
                    <th class="text-left px-3 py-2 text-sm">Başarı %</th>
                </tr>
            </thead>
            <tbody>
        `;

        // Regular Divergences
        if (data.regular_divergences && data.regular_divergences.length > 0) {
            data.regular_divergences.forEach(div => {
                const typeClass = div.type.includes('bullish') ? 'text-green-400' : 'text-red-400';
                const classColor = this.getDivergenceClassColor(div.class_rating);
                
                html += `
                    <tr class="border-b border-gray-700">
                        <td class="px-3 py-2 text-xs ${typeClass}">${div.type.replace('_', ' ').toUpperCase()}</td>
                        <td class="px-3 py-2 text-xs">${div.indicator}</td>
                        <td class="px-3 py-2 text-xs">${div.strength.toFixed(1)}</td>
                        <td class="px-3 py-2 text-xs ${classColor}">${div.class_rating}</td>
                        <td class="px-3 py-2 text-xs">${(div.success_probability * 100).toFixed(0)}%</td>
                    </tr>
                `;
            });
        }

        // Hidden Divergences
        if (data.hidden_divergences && data.hidden_divergences.length > 0) {
            data.hidden_divergences.forEach(div => {
                const typeClass = div.type.includes('bullish') ? 'text-green-400' : 'text-red-400';
                const classColor = this.getDivergenceClassColor(div.class_rating);
                
                html += `
                    <tr class="border-b border-gray-700">
                        <td class="px-3 py-2 text-xs ${typeClass}">${div.type.replace('_', ' ').toUpperCase()}</td>
                        <td class="px-3 py-2 text-xs">${div.indicator}</td>
                        <td class="px-3 py-2 text-xs">${div.strength.toFixed(1)}</td>
                        <td class="px-3 py-2 text-xs ${classColor}">${div.class_rating}</td>
                        <td class="px-3 py-2 text-xs">${(div.success_probability * 100).toFixed(0)}%</td>
                    </tr>
                `;
            });
        }

        // Eğer hiç divergence yoksa
        if ((!data.regular_divergences || data.regular_divergences.length === 0) && 
            (!data.hidden_divergences || data.hidden_divergences.length === 0)) {
            html += `
                <tr>
                    <td colspan="5" class="px-3 py-4 text-center text-gray-400 text-sm">
                        Aktif divergence tespit edilmedi
                    </td>
                </tr>
            `;
        }

        html += '</tbody>';
        table.innerHTML = html;
    }

    getDivergenceClassColor(classRating) {
        switch (classRating) {
            case 'A': return 'text-green-400';
            case 'B': return 'text-yellow-400';
            case 'C': return 'text-gray-400';
            default: return 'text-gray-300';
        }
    }

    showDivergenceError(message) {
        const statusElement = document.getElementById('analysis-divergence-status');
        if (statusElement) {
            statusElement.textContent = 'Hata';
            statusElement.className = 'divergence-status error';
        }

        const table = document.getElementById('detailed-divergence-table');
        if (table) {
            table.innerHTML = `
                <tbody>
                    <tr>
                        <td colspan="5" class="px-3 py-4 text-center text-red-400 text-sm">${message}</td>
                    </tr>
                </tbody>
            `;
        }
    }

    async loadFibonacciAnalysis() {
        try {
            const response = await fetch('/api/fibonacci');
            const data = await response.json();
            
            this.fibonacciData = data;
            this.updateFibonacciDisplay(data);
            console.log('Fibonacci verisi yüklendi:', data.status);
        } catch (error) {
            console.error('Fibonacci yükleme hatası:', error);
            this.showFibonacciError('Bağlantı hatası');
        }
    }

    updateFibonacciDisplay(data) {
        try {
            if (data.status === 'success') {
                // Bounce potential
                this.updateElement('analysis-fibonacci-bounce', `${(data.bounce_potential || 0).toFixed(1)}%`);
                
                // Trend
                this.updateElement('analysis-fibonacci-trend', data.trend || 'N/A');
                
                // Fibonacci levels table
                this.updateFibonacciLevels(data.fibonacci_levels);
                
                // Signals
                this.updateFibonacciSignals(data.signals);
                
            } else {
                this.showFibonacciError(data.message || 'Veri yok');
            }
        } catch (error) {
            console.error('Fibonacci display güncelleme hatası:', error);
        }
    }

    updateFibonacciLevels(levels) {
        const tableBody = document.getElementById('fibonacci-levels-table');
        if (!tableBody || !levels) return;

        let html = '';
        Object.entries(levels).forEach(([ratio, level]) => {
            const distance = level.distance_pct || 0;
            const rowClass = distance < 1 ? 'bg-yellow-900/30' : '';
            
            html += `
                <tr class="${rowClass}">
                    <td class="px-3 py-2 text-sm">${(parseFloat(ratio) * 100).toFixed(1)}%</td>
                    <td class="px-3 py-2 text-sm font-semibold">₺${level.price?.toFixed(2) || 'N/A'}</td>
                    <td class="px-3 py-2 text-sm">${level.strength || 'N/A'}</td>
                    <td class="px-3 py-2 text-sm">${distance.toFixed(2)}%</td>
                </tr>
            `;
        });
        
        tableBody.innerHTML = html;
    }

    updateFibonacciSignals(signals) {
        const signalsDiv = document.getElementById('fibonacci-signals');
        if (!signalsDiv || !signals) return;

        let html = '';
        if (signals.action && signals.action !== 'WAIT') {
            const colorClass = signals.action === 'BUY' ? 'border-green-500 bg-green-900/20' : 'border-red-500 bg-red-900/20';
            
            html = `
                <div class="border-l-4 ${colorClass} p-3 rounded">
                    <div class="font-semibold text-sm mb-1">${signals.action} Sinyali</div>
                    <div class="text-xs text-gray-300 mb-2">Güç: ${(signals.strength || 0).toFixed(1)}%</div>
                    <div class="text-xs text-gray-400">${signals.reason?.join(', ') || ''}</div>
                </div>
            `;
        } else {
            html = '<div class="text-center text-gray-400 text-sm py-4">Aktif Fibonacci sinyali yok</div>';
        }
        
        signalsDiv.innerHTML = html;
    }

    showFibonacciError(message) {
        this.updateElement('analysis-fibonacci-bounce', 'Hata', 'text-red-400');
        this.updateElement('analysis-fibonacci-trend', 'Hata', 'text-red-400');
        
        const signalsDiv = document.getElementById('fibonacci-signals');
        if (signalsDiv) {
            signalsDiv.innerHTML = `<div class="text-center text-red-400 text-sm py-4">${message}</div>`;
        }
    }

    async loadSMCAnalysis() {
        try {
            const response = await fetch('/api/smc');
            const data = await response.json();
            
            if (data.status === 'success') {
                this.smcData = data;
                this.updateSMCDisplay(data);
                console.log('SMC verisi yüklendi:', data.signals?.action);
            } else {
                this.showSMCError(data.message || 'Veri alınamadı');
            }
        } catch (error) {
            console.error('SMC yükleme hatası:', error);
            this.showSMCError('Bağlantı hatası');
        }
    }

    updateSMCDisplay(data) {
        try {
            // Order Blocks
            const orderBlocks = data.order_blocks || [];
            this.updateElement('analysis-smc-order-blocks', orderBlocks.length.toString());
            
            // Fair Value Gaps
            const fvgs = data.fair_value_gaps || [];
            this.updateElement('analysis-smc-fvgs', fvgs.length.toString());
            
            // Market Structure
            if (data.market_structure) {
                this.updateElement('analysis-smc-structure', data.market_structure.trend || 'N/A');
            }
            
            // Liquidity Zones
            const liquidityZones = data.liquidity_zones || [];
            this.updateElement('analysis-smc-liquidity', liquidityZones.length.toString());
            
            // SMC Signals
            this.updateSMCSignals(data.signals);
            
        } catch (error) {
            console.error('SMC display güncelleme hatası:', error);
        }
    }

    updateSMCSignals(signals) {
        const signalsDiv = document.getElementById('smc-signals');
        if (!signalsDiv || !signals) return;

        if (signals.action && signals.action !== 'WAIT') {
            const colorClass = signals.action === 'BUY' ? 'text-green-400' : 'text-red-400';
            
            signalsDiv.innerHTML = `
                <div class="border-l-4 border-purple-500 bg-purple-900/20 p-3 rounded">
                    <div class="font-semibold text-sm mb-1">SMC ${signals.action} Sinyali</div>
                    <div class="text-xs text-gray-300 mb-2">Güç: ${(signals.strength || 0).toFixed(1)}%</div>
                    <div class="text-xs text-gray-400">${signals.reasons?.slice(0, 3).join(', ') || ''}</div>
                    ${signals.risk_reward ? `<div class="text-xs text-yellow-400 mt-1">Risk/Reward: ${signals.risk_reward.toFixed(2)}</div>` : ''}
                </div>
            `;
        } else {
            signalsDiv.innerHTML = '<div class="text-center text-gray-400 text-sm py-4">Aktif SMC sinyali yok</div>';
        }
    }

    showSMCError(message) {
        this.updateElement('analysis-smc-order-blocks', 'Hata', 'text-red-400');
        this.updateElement('analysis-smc-fvgs', 'Hata', 'text-red-400');
        this.updateElement('analysis-smc-structure', 'Hata', 'text-red-400');
        this.updateElement('analysis-smc-liquidity', 'Hata', 'text-red-400');
        
        const signalsDiv = document.getElementById('smc-signals');
        if (signalsDiv) {
            signalsDiv.innerHTML = `<div class="text-center text-red-400 text-sm py-4">${message}</div>`;
        }
    }

    showMarketRegimeError(message) {
        const statusElement = document.getElementById('analysis-regime-status');
        if (statusElement) {
            statusElement.textContent = 'Hata';
            statusElement.className = 'regime-status error';
            statusElement.title = message;
        }

        // Error state için tüm değerleri "Hata" yap
        const errorElements = [
            'analysis-volatility-level',
            'analysis-trend-type',
            'analysis-momentum-state',
            'analysis-volatility-desc',
            'analysis-trend-desc', 
            'analysis-momentum-desc'
        ];

        errorElements.forEach(id => {
            this.updateElement(id, 'Hata', 'text-red-400');
        });
    }

    getVolatilityDescription(volatilityData) {
        const level = volatilityData.level?.toLowerCase();
        const atr = volatilityData.atr_value?.toFixed(2);
        
        const descriptions = {
            'very_low': `Çok düşük volatilite (ATR: ${atr})`,
            'low': `Düşük volatilite (ATR: ${atr})`,
            'medium': `Orta volatilite (ATR: ${atr})`,
            'high': `Yüksek volatilite (ATR: ${atr})`,
            'very_high': `Çok yüksek volatilite (ATR: ${atr})`
        };

        return descriptions[level] || `Volatilite: ${level} (ATR: ${atr})`;
    }

    getTrendDescription(trendData) {
        const type = trendData.type;
        const strength = trendData.trend_strength?.toFixed(1);
        const direction = trendData.direction;

        return `${type} trend, ${direction} yönlü (Güç: ${strength}%)`;
    }

    getMomentumDescription(momentumData) {
        const state = momentumData.state;
        const rsi = momentumData.rsi_momentum;
        const macd = momentumData.macd_momentum;

        return `${state} momentum (RSI: ${rsi}, MACD: ${macd})`;
    }

    updateElement(id, value, className = '') {
        const element = document.getElementById(id);
        if (element) {
            element.textContent = value;
            if (className) {
                element.className = className;
            }
        }
    }

    updateLastRefreshTime() {
        const timeElement = document.getElementById('last-analysis-update');
        if (timeElement) {
            timeElement.textContent = new Date().toLocaleTimeString('tr-TR');
        }
    }

    startPeriodicUpdate() {
        // 2 dakikada bir güncelle
        this.updateInterval = setInterval(() => {
            if (!document.hidden) { // Sadece sayfa görünürse güncelle
                this.loadAllData();
            }
        }, 120000);
    }

    cleanup() {
        if (this.updateInterval) {
            clearInterval(this.updateInterval);
        }
        
        // Chart cleanup
        Object.values(this.charts).forEach(chart => {
            if (chart && typeof chart.destroy === 'function') {
                chart.destroy();
            }
        });
        
        console.log('AnalysisPageManager cleanup tamamlandı');
    }
}

// Global instance oluştur
window.analysisPageManager = new AnalysisPageManager();

// Sayfa kapatıldığında cleanup
window.addEventListener('beforeunload', () => {
    if (window.analysisPageManager) {
        window.analysisPageManager.cleanup();
    }
});