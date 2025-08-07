/**
 * Advanced Divergence Detection JavaScript Module
 * Real-time divergence visualization and management
 */

class DivergenceManager {
    constructor() {
        this.currentData = null;
        this.alertsContainer = document.getElementById('divergence-alerts');
        this.charts = {};
        this.notifications = [];
        this.lastClassACount = 0;
        
        // Chart.js default config
        Chart.defaults.color = '#e2e8f0';
        Chart.defaults.borderColor = '#475569';
        Chart.defaults.backgroundColor = 'rgba(75, 85, 99, 0.3)';
        
        this.initializeEventListeners();
    }

    /**
     * Initialize event listeners and UI components
     */
    initializeEventListeners() {
        // WebSocket message handler için global listener
        if (typeof window.handleDivergenceUpdate === 'undefined') {
            window.handleDivergenceUpdate = (data) => this.handleWebSocketUpdate(data);
        }
        
        // Dashboard refresh button
        const refreshBtn = document.getElementById('refresh-divergence');
        if (refreshBtn) {
            refreshBtn.addEventListener('click', () => this.refreshDivergenceData());
        }
        
        // Alert dismiss buttons
        document.addEventListener('click', (e) => {
            if (e.target.classList.contains('dismiss-alert')) {
                this.dismissAlert(e.target.closest('.divergence-alert'));
            }
        });
        
        // Auto-refresh için interval setup
        setInterval(() => this.autoRefresh(), 180000); // 3 dakikada bir
    }

    /**
     * Handle WebSocket divergence updates
     * @param {Object} data - Divergence data from WebSocket
     */
    handleWebSocketUpdate(data) {
        if (!data || data.type !== 'divergence_update') return;
        
        this.currentData = data.data;
        this.updateDivergenceWidgets();
        this.checkForNewAlerts();
        
        console.log('Divergence data updated:', this.currentData);
    }

    /**
     * Update all divergence widgets with new data
     */
    updateDivergenceWidgets() {
        if (!this.currentData) return;
        
        // Dashboard widget update
        this.updateDashboardWidget();
        
        // Analysis page update  
        this.updateAnalysisPage();
        
        // Update navigation badge
        this.updateNavigationBadge();
    }

    /**
     * Update dashboard divergence widget
     */
    updateDashboardWidget() {
        const widget = document.getElementById('divergence-widget');
        if (!widget) return;
        
        const data = this.currentData;
        
        // Update status
        const status = document.getElementById('divergence-status');
        if (status) {
            const isActive = data.active_count > 0;
            status.className = `divergence-status ${isActive ? 'active' : 'inactive'}`;
            status.textContent = isActive ? 'Aktif' : 'Pasif';
        }
        
        // Update active count
        const activeCount = document.getElementById('divergence-active-count');
        if (activeCount) {
            activeCount.textContent = data.active_count || 0;
        }
        
        // Update class badges
        this.updateClassBadges(data.class_counts || {});
        
        // Update confluence score
        this.updateConfluenceScore(data.confluence_score || 0);
        
        // Update mini divergence list
        this.updateMiniDivergenceList(data.active_divergences || []);
        
        // Update dominant divergence
        this.updateDominantDivergence(data.dominant_divergence);
    }

    /**
     * Update class badges with counts
     * @param {Object} classCounts - Class counts {A: 0, B: 0, C: 0}
     */
    updateClassBadges(classCounts) {
        ['A', 'B', 'C'].forEach(className => {
            const badge = document.getElementById(`class-${className.toLowerCase()}-count`);
            if (badge) {
                const count = classCounts[className] || 0;
                badge.textContent = count;
                
                // Add pulse animation for Class A
                if (className === 'A' && count > 0) {
                    badge.parentElement.classList.add('pulse-gold');
                } else {
                    badge.parentElement.classList.remove('pulse-gold');
                }
            }
        });
    }

    /**
     * Update confluence score gauge
     * @param {number} score - Confluence score (0-100)
     */
    updateConfluenceScore(score) {
        const scoreElement = document.getElementById('confluence-score');
        const gaugeElement = document.getElementById('confluence-gauge');
        
        if (scoreElement) {
            scoreElement.textContent = Math.round(score);
        }
        
        if (gaugeElement) {
            this.renderConfluenceGauge(gaugeElement, score);
        }
    }

    /**
     * Render confluence score as circular gauge
     * @param {HTMLElement} element - Canvas element
     * @param {number} score - Score value (0-100)
     */
    renderConfluenceGauge(element, score) {
        const canvas = element.querySelector('canvas') || document.createElement('canvas');
        if (!element.querySelector('canvas')) {
            canvas.width = 120;
            canvas.height = 120;
            element.appendChild(canvas);
        }
        
        const ctx = canvas.getContext('2d');
        const centerX = 60;
        const centerY = 60;
        const radius = 45;
        
        // Clear canvas
        ctx.clearRect(0, 0, 120, 120);
        
        // Background circle
        ctx.beginPath();
        ctx.arc(centerX, centerY, radius, 0, 2 * Math.PI);
        ctx.strokeStyle = 'rgba(55, 65, 81, 0.8)';
        ctx.lineWidth = 8;
        ctx.stroke();
        
        // Progress arc
        const progress = (score / 100) * 2 * Math.PI;
        ctx.beginPath();
        ctx.arc(centerX, centerY, radius, -Math.PI / 2, -Math.PI / 2 + progress);
        
        // Color gradient based on score
        const gradient = ctx.createLinearGradient(0, 0, 120, 0);
        if (score < 30) {
            gradient.addColorStop(0, '#ef4444');
            gradient.addColorStop(1, '#f87171');
        } else if (score < 70) {
            gradient.addColorStop(0, '#f59e0b');
            gradient.addColorStop(1, '#fbbf24');
        } else {
            gradient.addColorStop(0, '#22c55e');
            gradient.addColorStop(1, '#4ade80');
        }
        
        ctx.strokeStyle = gradient;
        ctx.lineWidth = 8;
        ctx.lineCap = 'round';
        ctx.stroke();
        
        // Center text
        ctx.fillStyle = '#ffd700';
        ctx.font = 'bold 16px Inter';
        ctx.textAlign = 'center';
        ctx.fillText(Math.round(score), centerX, centerY + 5);
    }

    /**
     * Update mini divergence list
     * @param {Array} divergences - Top divergences list
     */
    updateMiniDivergenceList(divergences) {
        const container = document.getElementById('mini-divergence-list');
        if (!container) return;
        
        if (!divergences.length) {
            container.innerHTML = '<div class="divergence-empty">Aktif divergence yok</div>';
            return;
        }
        
        const html = divergences.slice(0, 3).map(div => `
            <div class="divergence-card">
                <div class="divergence-card-header">
                    <span class="divergence-type ${div.type.includes('bullish') ? 'bullish' : 'bearish'}">
                        ${div.type.includes('bullish') ? '📈' : '📉'} 
                        ${div.type.replace('_', ' ').toUpperCase()}
                    </span>
                    <span class="divergence-class class-${div.class_rating.toLowerCase()}">
                        ${div.class_rating}
                    </span>
                </div>
                <div class="divergence-indicator">${div.indicator}</div>
                <div class="divergence-strength">
                    <span class="strength-label">Güç:</span>
                    <div class="strength-bar">
                        <div class="strength-fill" style="width: ${div.strength}%"></div>
                    </div>
                    <span class="strength-value">${Math.round(div.strength)}</span>
                </div>
                <div class="success-rate success-rate-${this.getSuccessRateClass(div.success_probability)}">
                    <i class="fas fa-chart-line"></i>
                    Başarı: %${Math.round(div.success_probability * 100)}
                </div>
            </div>
        `).join('');
        
        container.innerHTML = html;
    }

    /**
     * Update dominant divergence display
     * @param {Object} dominant - Dominant divergence data
     */
    updateDominantDivergence(dominant) {
        const element = document.getElementById('dominant-divergence');
        if (!element) return;
        
        if (!dominant) {
            element.innerHTML = '<div class="text-gray-400 text-sm">Dominant divergence yok</div>';
            return;
        }
        
        const html = `
            <div class="font-semibold text-${dominant.type.includes('bullish') ? 'green' : 'red'}-400">
                ${dominant.type.replace('_', ' ').toUpperCase()}
            </div>
            <div class="text-sm text-gray-400">${dominant.indicator} - Sınıf ${dominant.class_rating}</div>
            <div class="text-xs text-gray-500">Güç: ${Math.round(dominant.strength)} | Başarı: %${Math.round(dominant.success_probability * 100)}</div>
        `;
        
        element.innerHTML = html;
    }

    /**
     * Update analysis page components
     */
    updateAnalysisPage() {
        if (!window.location.pathname.includes('analysis')) return;
        
        // Update detailed divergence table
        this.updateDetailedTable();
        
        // Update strength gauges
        this.updateStrengthGauges();
        
        // Update historical chart
        this.updateHistoricalChart();
        
        // Update target and invalidation levels
        this.updatePriceLevels();
    }

    /**
     * Update detailed divergence table on analysis page
     */
    updateDetailedTable() {
        const table = document.getElementById('detailed-divergence-table');
        if (!table) return;
        
        const data = this.currentData;
        const tbody = table.querySelector('tbody');
        
        if (!data.active_divergences || !data.active_divergences.length) {
            tbody.innerHTML = '<tr><td colspan="8" class="text-center py-4 text-gray-400">Aktif divergence bulunamadı</td></tr>';
            return;
        }
        
        // Tüm aktif divergence'ları getir
        this.loadAllDivergences().then(allDivergences => {
            const html = allDivergences.map((div, index) => `
                <tr class="border-b border-gray-700 hover:bg-slate-800/30">
                    <td class="py-3 px-2">${index + 1}</td>
                    <td class="py-3 px-2">
                        <span class="divergence-type ${div.direction}">${div.type.replace('_', ' ')}</span>
                    </td>
                    <td class="py-3 px-2">
                        <span class="divergence-indicator">${div.indicator}</span>
                    </td>
                    <td class="py-3 px-2">
                        <span class="divergence-class class-${div.class_rating.toLowerCase()}">${div.class_rating}</span>
                    </td>
                    <td class="py-3 px-2">
                        <div class="flex items-center gap-2">
                            <div class="strength-bar" style="width: 60px; height: 6px;">
                                <div class="strength-fill" style="width: ${div.strength}%"></div>
                            </div>
                            <span class="text-xs">${Math.round(div.strength)}</span>
                        </div>
                    </td>
                    <td class="py-3 px-2">
                        <span class="maturity-score">
                            <span class="maturity-indicator ${this.getMaturityClass(div.maturity_score)}"></span>
                            ${Math.round(div.maturity_score)}
                        </span>
                    </td>
                    <td class="py-3 px-2">
                        <span class="success-rate-${this.getSuccessRateClass(div.success_probability)}">
                            %${Math.round(div.success_probability * 100)}
                        </span>
                    </td>
                    <td class="py-3 px-2 text-xs">
                        ${div.angle_difference.toFixed(1)}°
                    </td>
                </tr>
            `).join('');
            
            tbody.innerHTML = html;
        });
    }

    /**
     * Update strength gauge charts
     */
    updateStrengthGauges() {
        const data = this.currentData;
        if (!data) return;
        
        // Overall signal strength gauge
        this.renderGauge('overall-strength-gauge', data.signal_strength || 0, 'Genel Güç');
        
        // Confluence gauge
        this.renderGauge('confluence-strength-gauge', data.confluence_score || 0, 'Confluence');
    }

    /**
     * Render a circular gauge
     * @param {string} elementId - Canvas element ID
     * @param {number} value - Value (0-100)
     * @param {string} label - Label text
     */
    renderGauge(elementId, value, label) {
        const element = document.getElementById(elementId);
        if (!element) return;
        
        // Chart.js doughnut chart olarak render et
        if (this.charts[elementId]) {
            this.charts[elementId].destroy();
        }
        
        const canvas = element.querySelector('canvas') || document.createElement('canvas');
        if (!element.querySelector('canvas')) {
            element.appendChild(canvas);
        }
        
        this.charts[elementId] = new Chart(canvas, {
            type: 'doughnut',
            data: {
                datasets: [{
                    data: [value, 100 - value],
                    backgroundColor: [
                        this.getGaugeColor(value),
                        'rgba(55, 65, 81, 0.3)'
                    ],
                    borderWidth: 0,
                    cutout: '70%'
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false },
                    tooltip: { enabled: false }
                },
                animation: {
                    animateRotate: true,
                    duration: 1000
                }
            },
            plugins: [{
                id: 'centerText',
                beforeDraw: (chart) => {
                    const ctx = chart.ctx;
                    const centerX = chart.chartArea.left + (chart.chartArea.right - chart.chartArea.left) / 2;
                    const centerY = chart.chartArea.top + (chart.chartArea.bottom - chart.chartArea.top) / 2;
                    
                    ctx.save();
                    ctx.textAlign = 'center';
                    ctx.textBaseline = 'middle';
                    
                    // Value
                    ctx.fillStyle = '#ffd700';
                    ctx.font = 'bold 18px Inter';
                    ctx.fillText(Math.round(value), centerX, centerY - 8);
                    
                    // Label
                    ctx.fillStyle = '#94a3b8';
                    ctx.font = '10px Inter';
                    ctx.fillText(label, centerX, centerY + 12);
                    
                    ctx.restore();
                }
            }]
        });
    }

    /**
     * Update historical success rate chart
     */
    updateHistoricalChart() {
        const chartElement = document.getElementById('divergence-history-chart');
        if (!chartElement) return;
        
        // Get historical data and render with Chart.js
        this.loadDivergenceHistory().then(historyData => {
            if (this.charts.historyChart) {
                this.charts.historyChart.destroy();
            }
            
            const canvas = chartElement.querySelector('canvas') || document.createElement('canvas');
            if (!chartElement.querySelector('canvas')) {
                chartElement.appendChild(canvas);
            }
            
            this.charts.historyChart = new Chart(canvas, {
                type: 'line',
                data: {
                    labels: historyData.labels,
                    datasets: [{
                        label: 'Signal Strength',
                        data: historyData.signalStrength,
                        borderColor: '#ffd700',
                        backgroundColor: 'rgba(255, 215, 0, 0.1)',
                        tension: 0.4,
                        fill: true
                    }, {
                        label: 'Confluence Score',
                        data: historyData.confluenceScore,
                        borderColor: '#3b82f6',
                        backgroundColor: 'rgba(59, 130, 246, 0.1)',
                        tension: 0.4,
                        fill: false
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: {
                            position: 'top',
                            labels: { color: '#e2e8f0', font: { size: 11 } }
                        }
                    },
                    scales: {
                        x: {
                            grid: { color: 'rgba(71, 85, 105, 0.3)' },
                            ticks: { color: '#94a3b8', font: { size: 10 } }
                        },
                        y: {
                            grid: { color: 'rgba(71, 85, 105, 0.3)' },
                            ticks: { color: '#94a3b8', font: { size: 10 } },
                            max: 100
                        }
                    }
                }
            });
        });
    }

    /**
     * Update price levels (targets and invalidations)
     */
    updatePriceLevels() {
        const data = this.currentData;
        if (!data) return;
        
        // Target levels
        const targetsContainer = document.getElementById('target-levels');
        if (targetsContainer && data.next_targets) {
            const html = data.next_targets.map((target, index) => `
                <div class="price-level">
                    <span class="price-value">₺${target.toFixed(2)}</span>
                    <span class="price-distance">T${index + 1}</span>
                </div>
            `).join('');
            targetsContainer.innerHTML = html || '<div class="text-gray-400 text-sm">Hedef seviye yok</div>';
        }
        
        // Invalidation levels
        const invalidationContainer = document.getElementById('invalidation-levels');
        if (invalidationContainer && data.invalidation_levels) {
            const html = data.invalidation_levels.map(level => `
                <div class="price-level">
                    <span class="price-value">₺${level.toFixed(2)}</span>
                    <span class="price-distance">INV</span>
                </div>
            `).join('');
            invalidationContainer.innerHTML = html || '<div class="text-gray-400 text-sm">Geçersizleştirici seviye yok</div>';
        }
    }

    /**
     * Check for new alerts and show notifications
     */
    checkForNewAlerts() {
        if (!this.currentData) return;
        
        // Class A divergence alert'leri kontrol et
        const currentClassA = this.currentData.class_counts?.A || 0;
        if (currentClassA > this.lastClassACount) {
            this.showNotification({
                type: 'CLASS_A_DIVERGENCE',
                message: `${currentClassA - this.lastClassACount} yeni Sınıf A divergence tespit edildi!`,
                level: 'HIGH'
            });
        }
        this.lastClassACount = currentClassA;
        
        // Confluence alert'leri
        const confluenceScore = this.currentData.confluence_score || 0;
        if (confluenceScore > 80) {
            this.showNotification({
                type: 'HIGH_CONFLUENCE',
                message: `Yüksek confluence skoru: ${Math.round(confluenceScore)}`,
                level: 'HIGH'
            });
        }
    }

    /**
     * Show notification
     * @param {Object} alert - Alert object
     */
    showNotification(alert) {
        // Browser notification
        if ('Notification' in window && Notification.permission === 'granted') {
            new Notification('Divergence Alert', {
                body: alert.message,
                icon: '/static/favicon.ico'
            });
        }
        
        // UI alert
        this.addUIAlert(alert);
    }

    /**
     * Add UI alert to page
     * @param {Object} alert - Alert object
     */
    addUIAlert(alert) {
        if (!this.alertsContainer) return;
        
        const alertElement = document.createElement('div');
        alertElement.className = `divergence-alert alert-${alert.level.toLowerCase()}`;
        alertElement.innerHTML = `
            <i class="fas fa-exclamation-triangle alert-icon"></i>
            <div>
                <div class="alert-message">${alert.message}</div>
                <div class="alert-time">${new Date().toLocaleTimeString('tr-TR')}</div>
            </div>
            <button class="dismiss-alert ml-auto text-gray-400 hover:text-white">
                <i class="fas fa-times"></i>
            </button>
        `;
        
        this.alertsContainer.insertBefore(alertElement, this.alertsContainer.firstChild);
        
        // Auto dismiss after 10 seconds
        setTimeout(() => {
            if (alertElement.parentNode) {
                this.dismissAlert(alertElement);
            }
        }, 10000);
    }

    /**
     * Dismiss alert
     * @param {HTMLElement} alertElement - Alert element to dismiss
     */
    dismissAlert(alertElement) {
        alertElement.style.transform = 'translateX(100%)';
        alertElement.style.opacity = '0';
        setTimeout(() => {
            if (alertElement.parentNode) {
                alertElement.parentNode.removeChild(alertElement);
            }
        }, 300);
    }

    /**
     * Update navigation badge
     */
    updateNavigationBadge() {
        const badge = document.querySelector('.nav-divergence-badge');
        if (!badge) return;
        
        const activeCount = this.currentData?.active_count || 0;
        const classACount = this.currentData?.class_counts?.A || 0;
        
        if (classACount > 0) {
            badge.textContent = classACount;
            badge.className = 'nav-divergence-badge badge-class-a';
        } else if (activeCount > 0) {
            badge.textContent = activeCount;
            badge.className = 'nav-divergence-badge badge-active';
        } else {
            badge.textContent = '';
            badge.className = 'nav-divergence-badge badge-inactive';
        }
    }

    /**
     * Helper methods
     */
    getSuccessRateClass(rate) {
        if (rate > 0.7) return 'high';
        if (rate > 0.5) return 'medium';
        return 'low';
    }

    getMaturityClass(score) {
        if (score < 30) return 'maturity-fresh';
        if (score < 60) return 'maturity-developing';
        return 'maturity-mature';
    }

    getGaugeColor(value) {
        if (value < 30) return '#ef4444';
        if (value < 70) return '#f59e0b';
        return '#22c55e';
    }

    /**
     * API calls
     */
    async refreshDivergenceData() {
        try {
            const response = await fetch('/api/divergence');
            const data = await response.json();
            
            if (data.status === 'success') {
                // WebSocket update simülasyonu
                this.handleWebSocketUpdate({
                    type: 'divergence_update',
                    data: data
                });
            }
        } catch (error) {
            console.error('Divergence data refresh error:', error);
        }
    }

    async loadAllDivergences() {
        try {
            const response = await fetch('/api/divergence/active');
            const data = await response.json();
            return data.status === 'success' ? data.active_divergences : [];
        } catch (error) {
            console.error('Load all divergences error:', error);
            return [];
        }
    }

    async loadDivergenceHistory() {
        try {
            const response = await fetch('/api/divergence/history?hours=24');
            const data = await response.json();
            
            if (data.status === 'success') {
                const history = data.history;
                return {
                    labels: history.map(h => new Date(h.timestamp).toLocaleTimeString('tr-TR', { hour: '2-digit', minute: '2-digit' })),
                    signalStrength: history.map(h => h.signal_strength),
                    confluenceScore: history.map(h => h.confluence_score)
                };
            }
            
            return { labels: [], signalStrength: [], confluenceScore: [] };
        } catch (error) {
            console.error('Load divergence history error:', error);
            return { labels: [], signalStrength: [], confluenceScore: [] };
        }
    }

    async autoRefresh() {
        await this.refreshDivergenceData();
    }
}

// Initialize divergence manager when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.divergenceManager = new DivergenceManager();
    
    // Request notification permission
    if ('Notification' in window && Notification.permission === 'default') {
        Notification.requestPermission();
    }
});