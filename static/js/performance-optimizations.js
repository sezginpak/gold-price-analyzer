// Performance Optimizations for Dashboard
// Gold Price Analyzer - Dashboard Performans İyileştirmeleri

// ========================
// 1. Unified Data Manager
// ========================
class DashboardDataManager {
    constructor() {
        this.cache = new Map();
        this.cacheExpiry = 5000; // 5 seconds
        this.pendingRequests = new Map();
        this.updateCallbacks = new Set();
        this.pollingIntervals = new Map();
    }

    // Cache management
    getCached(key) {
        const cached = this.cache.get(key);
        if (cached && Date.now() - cached.timestamp < this.cacheExpiry) {
            return cached.data;
        }
        return null;
    }

    setCache(key, data) {
        this.cache.set(key, {
            data,
            timestamp: Date.now()
        });
    }

    // Deduplicated API calls
    async fetchData(url, key) {
        // Check cache first
        const cached = this.getCached(key);
        if (cached) return cached;

        // Check if request is already pending
        if (this.pendingRequests.has(key)) {
            return this.pendingRequests.get(key);
        }

        // Make new request
        const promise = fetch(url)
            .then(res => res.json())
            .then(data => {
                this.setCache(key, data);
                this.pendingRequests.delete(key);
                return data;
            })
            .catch(err => {
                this.pendingRequests.delete(key);
                throw err;
            });

        this.pendingRequests.set(key, promise);
        return promise;
    }

    // Subscribe to updates
    subscribe(callback) {
        this.updateCallbacks.add(callback);
        return () => this.updateCallbacks.delete(callback);
    }

    notifySubscribers(type, data) {
        this.updateCallbacks.forEach(callback => {
            try {
                callback(type, data);
            } catch (err) {
                console.error('Subscriber callback error:', err);
            }
        });
    }
}

// ========================
// 2. Optimized Polling Manager
// ========================
class PollingManager {
    constructor(dataManager) {
        this.dataManager = dataManager;
        this.tasks = new Map();
        this.masterInterval = null;
        this.wsConnected = false;
    }

    // Register a polling task
    register(name, fn, interval, wsDependent = false) {
        this.tasks.set(name, {
            fn,
            interval,
            lastRun: 0,
            wsDependent // Skip if WebSocket is connected
        });
    }

    // Start master polling loop
    start() {
        if (this.masterInterval) return;

        // Use single interval for all polling
        this.masterInterval = setInterval(() => {
            const now = Date.now();
            
            this.tasks.forEach((task, name) => {
                // Skip WebSocket dependent tasks if connected
                if (task.wsDependent && this.wsConnected) return;

                if (now - task.lastRun >= task.interval) {
                    task.lastRun = now;
                    try {
                        task.fn();
                    } catch (err) {
                        console.error(`Polling task ${name} error:`, err);
                    }
                }
            });
        }, 1000); // Check every second
    }

    stop() {
        if (this.masterInterval) {
            clearInterval(this.masterInterval);
            this.masterInterval = null;
        }
    }

    setWebSocketStatus(connected) {
        this.wsConnected = connected;
    }
}

// ========================
// 3. DOM Update Optimizer
// ========================
class DOMUpdateOptimizer {
    constructor() {
        this.pendingUpdates = new Map();
        this.rafId = null;
        this.updateCache = new Map();
    }

    // Batch DOM updates
    scheduleUpdate(elementId, value, formatter = null) {
        // Check if value actually changed
        const cached = this.updateCache.get(elementId);
        if (cached === value) return;

        this.pendingUpdates.set(elementId, { value, formatter });
        
        if (!this.rafId) {
            this.rafId = requestAnimationFrame(() => {
                this.flushUpdates();
            });
        }
    }

    flushUpdates() {
        this.pendingUpdates.forEach(({ value, formatter }, elementId) => {
            const element = document.getElementById(elementId);
            if (element) {
                const formattedValue = formatter ? formatter(value) : value;
                
                // Use textContent for text-only updates (faster)
                if (typeof formattedValue === 'string' && !formattedValue.includes('<')) {
                    element.textContent = formattedValue;
                } else {
                    element.innerHTML = formattedValue;
                }
                
                this.updateCache.set(elementId, value);
            }
        });

        this.pendingUpdates.clear();
        this.rafId = null;
    }
}

// ========================
// 4. Chart Update Throttler
// ========================
class ChartUpdateThrottler {
    constructor(chart, delay = 500) {
        this.chart = chart;
        this.delay = delay;
        this.pendingData = [];
        this.timeoutId = null;
    }

    addData(label, value) {
        this.pendingData.push({ label, value });
        
        if (!this.timeoutId) {
            this.timeoutId = setTimeout(() => {
                this.flush();
            }, this.delay);
        }
    }

    flush() {
        if (this.pendingData.length === 0) return;

        // Batch update chart
        const chart = this.chart;
        if (!chart || !chart.data) return;

        // Add all pending data at once
        this.pendingData.forEach(({ label, value }) => {
            // Limit data points
            if (chart.data.labels.length >= 360) {
                chart.data.labels.shift();
                chart.data.datasets[0].data.shift();
            }
            
            chart.data.labels.push(label);
            chart.data.datasets[0].data.push(value);
        });

        // Single update call
        chart.update('none'); // No animation for performance

        this.pendingData = [];
        this.timeoutId = null;
    }
}

// ========================
// 5. WebSocket Message Buffer
// ========================
class WebSocketMessageBuffer {
    constructor(flushInterval = 100) {
        this.buffer = [];
        this.flushInterval = flushInterval;
        this.flushTimer = null;
        this.handlers = new Map();
    }

    registerHandler(type, handler) {
        this.handlers.set(type, handler);
    }

    addMessage(message) {
        this.buffer.push(message);
        
        if (!this.flushTimer) {
            this.flushTimer = setTimeout(() => {
                this.flush();
            }, this.flushInterval);
        }
    }

    flush() {
        if (this.buffer.length === 0) return;

        // Group messages by type
        const grouped = this.buffer.reduce((acc, msg) => {
            if (!acc[msg.type]) acc[msg.type] = [];
            acc[msg.type].push(msg);
            return acc;
        }, {});

        // Process each type with latest data only
        Object.entries(grouped).forEach(([type, messages]) => {
            const handler = this.handlers.get(type);
            if (handler) {
                // For most types, only process the latest
                if (type === 'price_update' || type === 'analysis_update') {
                    handler(messages[messages.length - 1]);
                } else {
                    // For signals etc, process all
                    messages.forEach(handler);
                }
            }
        });

        this.buffer = [];
        this.flushTimer = null;
    }
}

// ========================
// 6. Initialize Optimizations
// ========================
let dashboardOptimizations = null;

function initializeOptimizations() {
    // Create instances
    const dataManager = new DashboardDataManager();
    const pollingManager = new PollingManager(dataManager);
    const domUpdater = new DOMUpdateOptimizer();
    const wsBuffer = new WebSocketMessageBuffer();
    
    // Chart throttlers
    const chartThrottlers = new Map();
    
    // Store for global access
    dashboardOptimizations = {
        dataManager,
        pollingManager,
        domUpdater,
        wsBuffer,
        chartThrottlers
    };

    // Replace multiple setIntervals with unified polling
    pollingManager.register('stats', async () => {
        const data = await dataManager.fetchData('/api/stats', 'stats');
        if (data) {
            domUpdater.scheduleUpdate('uptime', data.uptime || '-');
            domUpdater.scheduleUpdate('total-records', data.total_records || '-');
            domUpdater.scheduleUpdate('today-signals', data.today_signals || '-');
        }
    }, 10000); // Every 10 seconds

    pollingManager.register('prices', async () => {
        const data = await dataManager.fetchData('/api/prices/current', 'current_prices');
        if (data && !data.error) {
            updateCurrentPriceOptimized(data);
        }
    }, 5000, true); // Every 5 seconds, skip if WebSocket connected

    pollingManager.register('analysis', async () => {
        const data = await dataManager.fetchData('/api/analysis/latest', 'latest_analysis');
        if (data && data.details) {
            updateTechnicalIndicatorsOptimized(data.details);
        }
    }, 15000, true); // Every 15 seconds, skip if WebSocket connected

    // Start polling
    pollingManager.start();

    // Setup WebSocket message buffering
    if (typeof ws !== 'undefined' && ws) {
        const originalOnMessage = ws.onmessage;
        ws.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data);
                wsBuffer.addMessage(data);
            } catch (err) {
                console.error('WebSocket parse error:', err);
            }
        };

        // Register handlers
        wsBuffer.registerHandler('price_update', (msg) => {
            updateCurrentPriceOptimized(msg.data);
            if (msg.data) {
                updateAllPriceChanges(msg.data);
                addPriceToChartOptimized(msg.data);
            }
        });

        wsBuffer.registerHandler('analysis_update', (msg) => {
            if (msg.data?.details) {
                updateTechnicalIndicatorsOptimized(msg.data.details);
            }
        });

        wsBuffer.registerHandler('performance_update', (msg) => {
            if (msg.data && typeof handlePerformanceUpdate === 'function') {
                handlePerformanceUpdate(msg.data);
            }
        });
    }

    // Optimize chart updates
    if (typeof priceChart !== 'undefined' && priceChart) {
        const chartThrottler = new ChartUpdateThrottler(priceChart, 500);
        chartThrottlers.set('price', chartThrottler);
        
        // Override addPriceToChart
        window.addPriceToChartOptimized = function(price) {
            if (!price || !price.timestamp || !price.gram_altin) return;
            
            const time = new Date(price.timestamp);
            const timeStr = time.toLocaleTimeString('tr-TR', { 
                hour: '2-digit', 
                minute: '2-digit',
                timeZone: 'Europe/Istanbul'
            });
            
            chartThrottler.addData(timeStr, parseFloat(price.gram_altin));
        };
    }

    return dashboardOptimizations;
}

// Optimized update functions
function updateCurrentPriceOptimized(data) {
    const { domUpdater } = dashboardOptimizations;
    
    if (data.gram_altin) {
        domUpdater.scheduleUpdate('gram-altin', data.gram_altin, 
            v => `₺${parseFloat(v).toFixed(2)}`);
    }
    if (data.ons_usd) {
        domUpdater.scheduleUpdate('ons-usd', data.ons_usd, 
            v => `$${parseFloat(v).toFixed(2)}`);
    }
    if (data.usd_try) {
        domUpdater.scheduleUpdate('usd-try', data.usd_try, 
            v => parseFloat(v).toFixed(4));
    }
    if (data.ons_usd && data.usd_try) {
        const onsTry = parseFloat(data.ons_usd) * parseFloat(data.usd_try);
        domUpdater.scheduleUpdate('ons-try', onsTry, 
            v => `₺${v.toFixed(2)}`);
    }
}

function updateTechnicalIndicatorsOptimized(details) {
    const { domUpdater } = dashboardOptimizations;
    
    if (!details || !details.gram) {
        ['rsi-value', 'macd-signal', 'bb-position', 'stoch-value'].forEach(id => {
            domUpdater.scheduleUpdate(id, '-', () => '<span class="text-gray-400">-</span>');
        });
        return;
    }

    const gram = details.gram;
    
    // RSI
    if (gram.rsi !== undefined && gram.rsi !== null) {
        const rsiValue = gram.rsi.toFixed(1);
        let rsiClass = '';
        let rsiText = '';
        if (gram.rsi < 30) {
            rsiClass = 'text-green-400';
            rsiText = 'Aşırı Satım';
        } else if (gram.rsi > 70) {
            rsiClass = 'text-red-400';
            rsiText = 'Aşırı Alım';
        } else {
            rsiClass = 'text-yellow-400';
            rsiText = 'Normal';
        }
        domUpdater.scheduleUpdate('rsi-value', gram.rsi, 
            () => `<span class="${rsiClass}">${rsiValue} (${rsiText})</span>`);
    }
    
    // Other indicators...
}

// Auto-initialize on DOM ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initializeOptimizations);
} else {
    initializeOptimizations();
}

// Cleanup on page unload
window.addEventListener('beforeunload', () => {
    if (dashboardOptimizations) {
        dashboardOptimizations.pollingManager.stop();
    }
});

// Export for debugging
window.dashboardOptimizations = dashboardOptimizations;