// Dashboard Fixes and Improvements
// Gold Price Analyzer - Dashboard Veri Gösterim Düzeltmeleri

// ========================
// 1. Timezone Helper Functions
// ========================
function parseServerTime(isoString) {
    // Server'dan UTC olarak gelen zamanı Türkiye saatine çevir
    const utcDate = new Date(isoString);
    return new Date(utcDate.getTime() + (3 * 60 * 60 * 1000)); // UTC+3
}

function formatDisplayTime(dateObj, includeSeconds = false) {
    const format = includeSeconds ? 
        { hour: '2-digit', minute: '2-digit', second: '2-digit' } :
        { hour: '2-digit', minute: '2-digit' };
    
    return dateObj.toLocaleTimeString('tr-TR', {
        ...format,
        timeZone: 'Europe/Istanbul'
    });
}

function formatDisplayDate(dateObj) {
    return dateObj.toLocaleDateString('tr-TR', {
        day: '2-digit',
        month: '2-digit', 
        year: 'numeric',
        timeZone: 'Europe/Istanbul'
    });
}

// ========================
// 2. Error Handling Utilities
// ========================
async function fetchWithRetry(url, options = {}, retries = 3) {
    for (let i = 0; i < retries; i++) {
        try {
            const response = await fetch(url, options);
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            return await response.json();
        } catch (error) {
            console.warn(`API call failed (attempt ${i + 1}/${retries}):`, error.message);
            if (i === retries - 1) throw error;
            await new Promise(resolve => setTimeout(resolve, 1000 * (i + 1))); // Exponential backoff
        }
    }
}

function showLoadingState(...elementIds) {
    elementIds.forEach(id => {
        const element = document.getElementById(id);
        if (element) {
            element.innerHTML = '<i class="fas fa-spinner fa-spin text-gray-400"></i>';
        }
    });
}

function showErrorState(message, ...elementIds) {
    const ids = elementIds.length > 0 ? elementIds : ['gram-altin', 'ons-usd', 'usd-try', 'ons-try'];
    ids.forEach(id => {
        const element = document.getElementById(id);
        if (element) {
            element.innerHTML = `<span class="text-red-400" title="${message}">Hata</span>`;
        }
    });
}

function hideLoadingState() {
    // Loading state'i kaldır
}

// ========================
// 3. Fixed Technical Indicators Update
// ========================
function updateTechnicalIndicatorsFixed(details) {
    if (!details || !details.gram) {
        // Tüm göstergeleri "Veri yok" olarak işaretle
        ['rsi-value', 'macd-signal', 'bb-position', 'stoch-value', 'cci-value', 'williams-value'].forEach(id => {
            const element = document.getElementById(id);
            if (element) element.innerHTML = '<span class="text-gray-400">-</span>';
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
        const rsiElement = document.getElementById('rsi-value');
        if (rsiElement) {
            rsiElement.innerHTML = `<span class="${rsiClass}">${rsiValue} (${rsiText})</span>`;
        }
    }

    // MACD - Hem değer hem signal göster
    if (gram.macd && gram.macd.histogram !== undefined) {
        const macdClass = gram.macd.histogram > 0 ? 'text-green-400' : 'text-red-400';
        const macdText = gram.macd.histogram > 0 ? 'Boğa' : 'Ayı';
        const macdElement = document.getElementById('macd-signal');
        if (macdElement) {
            macdElement.innerHTML = `<span class="${macdClass}">${gram.macd.histogram.toFixed(3)} (${macdText})</span>`;
        }
    } else if (gram.signal) {
        // Fallback to simple signal if MACD data not available
        const signalClass = gram.signal === 'BUY' ? 'text-green-400' : 
                          gram.signal === 'SELL' ? 'text-red-400' : 'text-yellow-400';
        const macdElement = document.getElementById('macd-signal');
        if (macdElement) {
            macdElement.innerHTML = `<span class="${signalClass}">${gram.signal || 'NEUTRAL'}</span>`;
        }
    }

    // Bollinger Bands pozisyonu
    if (gram.bollinger && gram.bollinger.position) {
        let bbClass = '';
        let bbText = gram.bollinger.position;
        if (bbText.includes('Upper') || bbText.includes('ABOVE')) {
            bbClass = 'text-red-400';
            bbText = 'Üst Band';
        } else if (bbText.includes('Lower') || bbText.includes('BELOW')) {
            bbClass = 'text-green-400';
            bbText = 'Alt Band';
        } else {
            bbClass = 'text-yellow-400';
            bbText = 'Orta';
        }
        const bbElement = document.getElementById('bb-position');
        if (bbElement) {
            bbElement.innerHTML = `<span class="${bbClass}">${bbText}</span>`;
        }
    } else if (gram.indicators && gram.indicators.bollinger) {
        // Alternative bollinger data structure
        const bb = gram.indicators.bollinger;
        let bbPosition = 'Orta';
        let bbClass = 'text-yellow-400';
        if (gram.price && bb.upper && gram.price > bb.upper) {
            bbPosition = 'Üst Band';
            bbClass = 'text-red-400';
        } else if (gram.price && bb.lower && gram.price < bb.lower) {
            bbPosition = 'Alt Band';
            bbClass = 'text-green-400';
        }
        const bbElement = document.getElementById('bb-position');
        if (bbElement) {
            bbElement.innerHTML = `<span class="${bbClass}">${bbPosition}</span>`;
        }
    }

    // Stochastic
    if (gram.stochastic !== undefined && gram.stochastic !== null) {
        const stochValue = gram.stochastic.toFixed(1);
        let stochClass = '';
        if (gram.stochastic < 20) stochClass = 'text-green-400';
        else if (gram.stochastic > 80) stochClass = 'text-red-400';
        else stochClass = 'text-yellow-400';
        
        const stochElement = document.getElementById('stoch-value');
        if (stochElement) {
            stochElement.innerHTML = `<span class="${stochClass}">${stochValue}</span>`;
        }
    }

    // CCI değeri
    if (gram.cci !== undefined && gram.cci !== null) {
        const cciValue = gram.cci.toFixed(1);
        let cciClass = '';
        if (gram.cci < -100) cciClass = 'text-green-400';
        else if (gram.cci > 100) cciClass = 'text-red-400';
        else cciClass = 'text-yellow-400';
        
        const cciElement = document.getElementById('cci-value');
        if (cciElement) {
            cciElement.innerHTML = `<span class="${cciClass}">${cciValue}</span>`;
        }
    }

    // Williams %R
    if (gram.williams_r !== undefined && gram.williams_r !== null) {
        const williamsValue = gram.williams_r.toFixed(1);
        let williamsClass = '';
        if (gram.williams_r < -80) williamsClass = 'text-green-400';
        else if (gram.williams_r > -20) williamsClass = 'text-red-400';
        else williamsClass = 'text-yellow-400';
        
        const williamsElement = document.getElementById('williams-value');
        if (williamsElement) {
            williamsElement.innerHTML = `<span class="${williamsClass}">${williamsValue}</span>`;
        }
    }
}

// ========================
// 4. Market Overview Widget Fix
// ========================
async function loadMarketOverviewFixed() {
    try {
        const data = await fetchWithRetry('/api/market/overview');
        
        if (data.prices) {
            // Fiyat güncelle
            const gramElement = document.getElementById('mo-gram-price');
            const onsElement = document.getElementById('mo-ons-price');
            const usdElement = document.getElementById('mo-usd-price');
            
            if (gramElement) gramElement.textContent = `₺${data.prices.gram_altin.toFixed(2)}`;
            if (onsElement) onsElement.textContent = `$${data.prices.ons_usd.toFixed(2)}`;
            if (usdElement) usdElement.textContent = data.prices.usd_try.toFixed(4);
            
            // Değişim yüzdelerini güncelle
            if (data.changes) {
                updateWidgetChange('mo-gram-change', data.changes.gram_altin);
                updateWidgetChange('mo-ons-change', data.changes.ons_usd);
                updateWidgetChange('mo-usd-change', data.changes.usd_try);
            }
            
            // Trend ve risk güncelle
            if (data.analysis) {
                const trendElement = document.getElementById('mo-trend');
                const riskElement = document.getElementById('mo-risk');
                if (trendElement) trendElement.textContent = data.analysis.trend || '-';
                if (riskElement) riskElement.textContent = data.analysis.currency_risk || '-';
            }
        }
        
        // Günlük range güncelle
        if (data.daily_range) {
            const highElement = document.getElementById('daily-high');
            const lowElement = document.getElementById('daily-low');
            if (highElement) highElement.textContent = `₺${data.daily_range.high.toFixed(2)}`;
            if (lowElement) lowElement.textContent = `₺${data.daily_range.low.toFixed(2)}`;
        }
        
    } catch (error) {
        console.error('Piyasa özeti yüklenemedi:', error);
        // Error state göster
        ['mo-gram-price', 'mo-ons-price', 'mo-usd-price'].forEach(id => {
            const el = document.getElementById(id);
            if (el) el.textContent = 'Hata';
        });
    }
}

function updateWidgetChange(elementId, changeData) {
    const element = document.getElementById(elementId);
    if (!element) return;
    
    const change = changeData?.change_pct || changeData || 0;
    const changeText = change >= 0 ? `+${change.toFixed(2)}%` : `${change.toFixed(2)}%`;
    const colorClass = change >= 0 ? 'text-emerald-400' : 'text-rose-400';
    
    element.innerHTML = `<span class="${colorClass}">${changeText}</span>`;
}

// ========================
// 5. Price Update with All Currencies
// ========================
function updateAllPriceChanges(data) {
    // Gram Altın değişimi
    if (data.gram_altin && data.daily_change_pct !== undefined) {
        updatePriceChange('gram-change', data.daily_change_pct);
    }
    
    // ONS/USD değişimi (calculate if not provided)
    if (data.ons_usd) {
        const onsChange = data.ons_change_pct || calculateDailyChange('ons_usd', data.ons_usd);
        updatePriceChange('ons-change', onsChange);
    }
    
    // USD/TRY değişimi
    if (data.usd_try) {
        const usdChange = data.usd_change_pct || calculateDailyChange('usd_try', data.usd_try);
        updatePriceChange('usd-change', usdChange);
    }
    
    // ONS/TRY değişimi
    if (data.ons_usd && data.usd_try) {
        const onsTry = parseFloat(data.ons_usd) * parseFloat(data.usd_try);
        const onsTryChange = calculateDailyChange('ons_try', onsTry);
        updatePriceChange('ons-try-change', onsTryChange);
    }
}

function updatePriceChange(elementId, changePercent) {
    const element = document.getElementById(elementId);
    if (!element) return;
    
    const change = parseFloat(changePercent) || 0;
    const arrow = change >= 0 ? '↑' : '↓';
    const colorClass = change >= 0 ? 'text-emerald-400' : 'text-rose-400';
    const changeText = `${arrow} ${Math.abs(change).toFixed(2)}%`;
    
    element.innerHTML = `<span class="${colorClass}">${changeText}</span>`;
}

// Store for daily price tracking (for change calculation)
const dailyPriceStore = {
    ons_usd: { open: null, current: null },
    usd_try: { open: null, current: null },
    ons_try: { open: null, current: null }
};

function calculateDailyChange(currency, currentPrice) {
    if (!dailyPriceStore[currency].open) {
        // Initialize with current price if no open price
        dailyPriceStore[currency].open = currentPrice;
        dailyPriceStore[currency].current = currentPrice;
        return 0;
    }
    
    dailyPriceStore[currency].current = currentPrice;
    const change = ((currentPrice - dailyPriceStore[currency].open) / dailyPriceStore[currency].open) * 100;
    return change;
}

// ========================
// 6. WebSocket Reconnection Logic
// ========================
let reconnectAttempts = 0;
const maxReconnectAttempts = 5;
let wsConnectionStatus = 'disconnected';

function connectWebSocketFixed(existingWs) {
    if (existingWs && existingWs.readyState === WebSocket.OPEN) {
        return existingWs; // Already connected
    }
    
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const ws = new WebSocket(`${protocol}//${window.location.host}/ws`);
    
    ws.onopen = () => {
        console.log('WebSocket bağlantısı açıldı');
        wsConnectionStatus = 'connected';
        updateConnectionStatus('Bağlı', 'bg-success');
        reconnectAttempts = 0;
    };
    
    ws.onclose = (event) => {
        console.log('WebSocket bağlantısı kapandı:', event.code, event.reason);
        wsConnectionStatus = 'disconnected';
        updateConnectionStatus('Bağlantı koptu', 'bg-error');
        
        // Otomatik yeniden bağlanma
        if (reconnectAttempts < maxReconnectAttempts) {
            const delay = Math.min(1000 * Math.pow(2, reconnectAttempts), 30000);
            reconnectAttempts++;
            
            updateConnectionStatus(`Yeniden bağlanıyor... (${delay/1000}s)`, 'bg-warning');
            setTimeout(() => connectWebSocketFixed(null), delay);
        } else {
            updateConnectionStatus('Bağlantı başarısız', 'bg-error');
            showReconnectButton();
        }
    };
    
    ws.onerror = (error) => {
        console.error('WebSocket hatası:', error);
        wsConnectionStatus = 'error';
    };
    
    ws.onmessage = (event) => {
        try {
            const data = JSON.parse(event.data);
            handleWebSocketMessageFixed(data);
        } catch (error) {
            console.error('WebSocket mesaj parse hatası:', error);
        }
    };
    
    return ws;
}

function updateConnectionStatus(text, colorClass) {
    const statusText = document.getElementById('status-text');
    const statusDot = document.getElementById('ws-status');
    
    if (statusText) statusText.textContent = text;
    if (statusDot) {
        statusDot.className = `nav__status-dot ${colorClass}`;
    }
}

function showReconnectButton() {
    const statusText = document.getElementById('status-text');
    if (!statusText) return;
    
    const statusContainer = statusText.parentNode;
    let reconnectBtn = document.getElementById('reconnect-btn');
    
    if (!reconnectBtn) {
        reconnectBtn = document.createElement('button');
        reconnectBtn.id = 'reconnect-btn';
        reconnectBtn.textContent = 'Yeniden Bağlan';
        reconnectBtn.className = 'ml-2 px-2 py-1 bg-blue-600 text-white rounded text-xs hover:bg-blue-700';
        reconnectBtn.onclick = () => {
            reconnectAttempts = 0;
            reconnectBtn.remove();
            connectWebSocketFixed(null);
        };
        statusContainer.appendChild(reconnectBtn);
    }
}

function handleWebSocketMessageFixed(data) {
    switch (data.type) {
        case 'price_update':
            if (data.data) {
                // Update prices
                if (typeof updateCurrentPrice === 'function') {
                    updateCurrentPrice(data.data);
                }
                // Update all currency changes
                updateAllPriceChanges(data.data);
                // Update chart
                if (typeof addPriceToChart === 'function') {
                    addPriceToChart(data.data);
                }
            }
            break;
        case 'performance_update':
            if (data.data && typeof handlePerformanceUpdate === 'function') {
                handlePerformanceUpdate(data.data);
            }
            break;
        case 'new_signal':
            if (data.data && typeof handleNewSignal === 'function') {
                handleNewSignal(data.data);
            }
            break;
        case 'analysis_update':
            if (data.data?.details) {
                updateTechnicalIndicatorsFixed(data.data.details);
            }
            break;
        default:
            console.warn('Bilinmeyen WebSocket mesaj tipi:', data.type);
    }
}

// ========================
// 7. Initialize Fixes on Page Load
// ========================
document.addEventListener('DOMContentLoaded', function() {
    console.log('Dashboard fixes loaded');
    
    // Override existing functions with fixed versions
    if (typeof updateTechnicalIndicators !== 'undefined') {
        window.updateTechnicalIndicators = updateTechnicalIndicatorsFixed;
    }
    
    // Fix WebSocket connection if needed
    if (typeof ws !== 'undefined') {
        window.ws = connectWebSocketFixed(ws);
    }
    
    // Load market overview with fixes
    if (typeof loadMarketOverview !== 'undefined') {
        window.loadMarketOverview = loadMarketOverviewFixed;
        loadMarketOverviewFixed();
    }
    
    // Set up periodic refresh for daily price opens (at midnight)
    const now = new Date();
    const tomorrow = new Date(now);
    tomorrow.setDate(tomorrow.getDate() + 1);
    tomorrow.setHours(0, 0, 0, 0);
    const msUntilMidnight = tomorrow - now;
    
    setTimeout(() => {
        // Reset daily price store at midnight
        Object.keys(dailyPriceStore).forEach(key => {
            dailyPriceStore[key].open = dailyPriceStore[key].current;
        });
        // Then set up daily interval
        setInterval(() => {
            Object.keys(dailyPriceStore).forEach(key => {
                dailyPriceStore[key].open = dailyPriceStore[key].current;
            });
        }, 24 * 60 * 60 * 1000);
    }, msUntilMidnight);
});

// Export for debugging
window.dashboardFixes = {
    updateTechnicalIndicatorsFixed,
    loadMarketOverviewFixed,
    connectWebSocketFixed,
    updateAllPriceChanges,
    fetchWithRetry,
    wsConnectionStatus
};