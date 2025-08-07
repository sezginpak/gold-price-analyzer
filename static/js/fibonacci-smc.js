/**
 * Fibonacci Retracement & Smart Money Concepts Integration
 * Dashboard ve Analysis sayfalarında kullanılır
 */

class FibonacciSMCManager {
    constructor() {
        this.fibonacciData = null;
        this.smcData = null;
        this.charts = {
            fibonacci: null,
            smc: null
        };
        this.updateInterval = null;
        
        this.init();
    }

    init() {
        console.log('FibonacciSMCManager başlatılıyor...');
        
        // DOM yüklendiğinde verileri al
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', () => {
                this.loadData();
                this.bindEvents();
                this.initializeWebSocketHandlers();
            });
        } else {
            this.loadData();
            this.bindEvents();
            this.initializeWebSocketHandlers();
        }

        // 2 dakikada bir güncelle
        this.updateInterval = setInterval(() => {
            this.loadData();
        }, 120000);
    }

    initializeWebSocketHandlers() {
        // WebSocket mesaj dinleyicilerini ekle
        if (typeof window.websocketManager !== 'undefined' && window.websocketManager) {
            // WebSocket'ten gelen mesajları dinle
            const originalOnMessage = window.websocketManager.onmessage;
            
            window.websocketManager.onmessage = (event) => {
                // Orjinal handler'ı çalıştır
                if (originalOnMessage && typeof originalOnMessage === 'function') {
                    originalOnMessage(event);
                }
                
                // Fibonacci ve SMC mesajlarını işle
                try {
                    const data = JSON.parse(event.data);
                    this.handleWebSocketMessage(data);
                } catch (error) {
                    console.error('WebSocket mesaj parse hatası:', error);
                }
            };
        } else {
            // WebSocket manager henüz hazır değilse biraz bekle
            setTimeout(() => {
                this.initializeWebSocketHandlers();
            }, 1000);
        }
    }

    handleWebSocketMessage(data) {
        switch (data.type) {
            case 'fibonacci_update':
                if (data.data) {
                    this.handleFibonacciWebSocketUpdate(data.data);
                }
                break;
            case 'smc_update':
                if (data.data) {
                    this.handleSMCWebSocketUpdate(data.data);
                }
                break;
        }
    }

    handleFibonacciWebSocketUpdate(fibonacciData) {
        // WebSocket'ten gelen Fibonacci verisini işle
        const processedData = {
            status: 'success',
            current_price: fibonacciData.current_price,
            trend: fibonacciData.trend,
            swing_range: fibonacciData.swing_range,
            bounce_potential: fibonacciData.bounce_potential,
            nearest_level: fibonacciData.nearest_level,
            levels: fibonacciData.levels || [],
            signals: fibonacciData.signals || {}
        };

        this.fibonacciData = processedData;
        this.updateFibonacciWidgets();
        this.updateFibonacciAnalysis();
        
        console.log('Fibonacci WebSocket güncellemesi alındı');
    }

    handleSMCWebSocketUpdate(smcData) {
        // WebSocket'ten gelen SMC verisini işle
        const processedData = {
            status: 'success',
            current_price: smcData.current_price,
            market_structure: smcData.market_structure || {},
            order_blocks: smcData.order_blocks || [],
            fair_value_gaps: smcData.fair_value_gaps || [],
            liquidity_zones: smcData.liquidity_zones || [],
            signals: smcData.signals || {}
        };

        // İstatistikleri ekle
        if (smcData.statistics) {
            this.smcData = {
                ...processedData,
                orderBlocks: {
                    status: 'success',
                    order_blocks: smcData.order_blocks || [],
                    statistics: smcData.statistics.order_blocks || {}
                },
                fvgs: {
                    status: 'success',
                    fair_value_gaps: smcData.fair_value_gaps || [],
                    statistics: smcData.statistics.fair_value_gaps || {}
                },
                structure: {
                    status: 'success',
                    market_structure: smcData.market_structure || {}
                }
            };
        }

        this.updateSMCWidgets();
        this.updateSMCAnalysis();
        
        console.log('SMC WebSocket güncellemesi alındı');
    }

    bindEvents() {
        // Dashboard refresh butonları
        const refreshFibBtn = document.getElementById('refresh-fibonacci');
        if (refreshFibBtn) {
            refreshFibBtn.addEventListener('click', () => this.refreshFibonacci());
        }

        const refreshSMCBtn = document.getElementById('refresh-smc');
        if (refreshSMCBtn) {
            refreshSMCBtn.addEventListener('click', () => this.refreshSMC());
        }

        // Analysis sayfası refresh butonları
        const refreshDetailedFibBtn = document.getElementById('refresh-detailed-fibonacci');
        if (refreshDetailedFibBtn) {
            refreshDetailedFibBtn.addEventListener('click', () => this.refreshFibonacci());
        }

        const refreshDetailedSMCBtn = document.getElementById('refresh-detailed-smc');
        if (refreshDetailedSMCBtn) {
            refreshDetailedSMCBtn.addEventListener('click', () => this.refreshSMC());
        }
    }

    async loadData() {
        try {
            await Promise.all([
                this.loadFibonacciData(),
                this.loadSMCData()
            ]);
        } catch (error) {
            console.error('Fibonacci/SMC veri yükleme hatası:', error);
        }
    }

    async loadFibonacciData() {
        try {
            const response = await fetch('/api/fibonacci/levels');
            const data = await response.json();

            if (data.status === 'success') {
                this.fibonacciData = data;
                this.updateFibonacciWidgets();
                this.updateFibonacciAnalysis();
            } else {
                console.warn('Fibonacci veri hatası:', data.message);
                this.showFibonacciError(data.message);
            }
        } catch (error) {
            console.error('Fibonacci API hatası:', error);
            this.showFibonacciError('Fibonacci verisi yüklenemedi');
        }
    }

    async loadSMCData() {
        try {
            const [smcResponse, orderBlocksResponse, fvgResponse, structureResponse] = await Promise.all([
                fetch('/api/smc'),
                fetch('/api/smc/order-blocks'),
                fetch('/api/smc/fair-value-gaps'),
                fetch('/api/smc/market-structure')
            ]);

            const [smcData, orderBlocksData, fvgData, structureData] = await Promise.all([
                smcResponse.json(),
                orderBlocksResponse.json(),
                fvgResponse.json(),
                structureResponse.json()
            ]);

            if (smcData.status === 'success') {
                this.smcData = {
                    ...smcData,
                    orderBlocks: orderBlocksData.status === 'success' ? orderBlocksData : null,
                    fvgs: fvgData.status === 'success' ? fvgData : null,
                    structure: structureData.status === 'success' ? structureData : null
                };
                
                this.updateSMCWidgets();
                this.updateSMCAnalysis();
            } else {
                console.warn('SMC veri hatası:', smcData.message);
                this.showSMCError(smcData.message);
            }
        } catch (error) {
            console.error('SMC API hatası:', error);
            this.showSMCError('SMC verisi yüklenemedi');
        }
    }

    // Dashboard Widget Updates
    updateFibonacciWidgets() {
        if (!this.fibonacciData) return;

        // Status güncelle
        const fibStatus = document.getElementById('fibonacci-status');
        if (fibStatus) {
            fibStatus.textContent = 'Aktif';
            fibStatus.className = 'fibonacci-status active';
        }

        // Bounce potential
        const bouncePotential = document.getElementById('fibonacci-bounce-potential');
        if (bouncePotential && this.fibonacciData.bounce_potential !== undefined) {
            bouncePotential.textContent = `${Math.round(this.fibonacciData.bounce_potential)}%`;
        }

        // Trend direction
        const trendDir = document.getElementById('fibonacci-trend');
        if (trendDir && this.fibonacciData.trend) {
            const trendText = this.fibonacciData.trend === 'up' ? '↗ Yükseliş' :
                             this.fibonacciData.trend === 'down' ? '↘ Düşüş' : '→ Sideways';
            trendDir.textContent = trendText;
            trendDir.className = `text-lg font-bold ${
                this.fibonacciData.trend === 'up' ? 'text-green-400' :
                this.fibonacciData.trend === 'down' ? 'text-red-400' : 'text-yellow-400'
            }`;
        }

        // Nearest level
        this.updateNearestFibonacciLevel();

        // Top fibonacci levels
        this.updateTopFibonacciLevels();
    }

    updateNearestFibonacciLevel() {
        const container = document.getElementById('nearest-fibonacci-level');
        if (!container || !this.fibonacciData?.nearest_level) {
            if (container) {
                container.innerHTML = '<div class="text-gray-400 text-sm">Yakın seviye bulunamadı</div>';
            }
            return;
        }

        const nearest = this.fibonacciData.nearest_level;
        const levelType = nearest.level > 1.0 ? 'extension' : 'retracement';
        const isGoldenRatio = [0.382, 0.618, 1.618].includes(nearest.level);

        container.innerHTML = `
            <div class="fib-level current ${nearest.strength}">
                <div class="fib-level-info">
                    <div class="fib-level-ratio">
                        ${(nearest.level * 100).toFixed(1)}%
                        ${isGoldenRatio ? '<span class="fib-badge golden-ratio ml-1">Altın Oran</span>' : ''}
                    </div>
                    <div class="fib-level-description">${nearest.description}</div>
                </div>
                <div class="fib-level-price">
                    ₺${nearest.price.toFixed(2)}
                    <div class="fib-level-distance">
                        ${((Math.abs(this.fibonacciData.current_price - nearest.price) / this.fibonacciData.current_price) * 100).toFixed(2)}% uzak
                    </div>
                </div>
            </div>
        `;
    }

    updateTopFibonacciLevels() {
        const container = document.getElementById('top-fibonacci-levels');
        if (!container || !this.fibonacciData?.levels) {
            if (container) {
                container.innerHTML = '<div class="fib-smc-loading"><div class="fib-smc-spinner"></div></div>';
            }
            return;
        }

        // En yakın 3 seviyeyi al
        const topLevels = this.fibonacciData.levels.slice(0, 3);

        const levelsHtml = topLevels.map(level => {
            const isNearest = level.is_nearest;
            const levelTypeClass = level.level_type;
            const strengthClass = level.strength;

            return `
                <div class="fib-level ${strengthClass} ${isNearest ? 'current' : ''}">
                    <div class="fib-level-info">
                        <div class="fib-level-ratio">
                            ${(level.ratio * 100).toFixed(1)}%
                            ${level.is_golden_ratio ? '<span class="fib-badge golden-ratio ml-1">AR</span>' : ''}
                            <span class="fib-badge ${levelTypeClass} ml-1">${levelTypeClass === 'extension' ? 'EXT' : 'RET'}</span>
                        </div>
                        <div class="fib-level-description">${level.description}</div>
                    </div>
                    <div class="fib-level-price">
                        ₺${level.price.toFixed(2)}
                        <div class="fib-level-distance">${level.distance_pct.toFixed(2)}% uzak</div>
                    </div>
                </div>
            `;
        }).join('');

        container.innerHTML = levelsHtml || '<div class="text-gray-400 text-sm text-center py-4">Seviye bulunamadı</div>';
    }

    updateSMCWidgets() {
        if (!this.smcData) return;

        // Status güncelle
        const smcStatus = document.getElementById('smc-status');
        if (smcStatus) {
            smcStatus.textContent = 'Aktif';
            smcStatus.className = 'fibonacci-status active';
        }

        // Order blocks count
        const orderBlocksCount = document.getElementById('smc-order-blocks-count');
        if (orderBlocksCount && this.smcData.orderBlocks?.statistics) {
            orderBlocksCount.textContent = this.smcData.orderBlocks.statistics.total_count || 0;
        }

        // FVG count
        const fvgCount = document.getElementById('smc-fvg-count');
        if (fvgCount && this.smcData.fvgs?.statistics) {
            fvgCount.textContent = this.smcData.fvgs.statistics.total_count || 0;
        }

        // Market Structure
        this.updateSMCMarketStructure();

        // Recent Order Blocks
        this.updateRecentOrderBlocks();
    }

    updateSMCMarketStructure() {
        const trendElement = document.getElementById('smc-market-trend');
        const bosLevelElement = document.getElementById('smc-bos-level');
        const chochLevelElement = document.getElementById('smc-choch-level');

        if (this.smcData?.structure?.market_structure) {
            const structure = this.smcData.structure.market_structure;

            if (trendElement) {
                const trendClass = structure.trend === 'bullish' ? 'bullish' :
                                 structure.trend === 'bearish' ? 'bearish' : 'ranging';
                trendElement.textContent = structure.trend.toUpperCase();
                trendElement.className = `text-xl font-bold structure-trend-value ${trendClass}`;
            }

            if (bosLevelElement && structure.bos_level) {
                bosLevelElement.textContent = `₺${structure.bos_level.toFixed(2)}`;
            }

            if (chochLevelElement && structure.choch_level) {
                chochLevelElement.textContent = `₺${structure.choch_level.toFixed(2)}`;
            }
        }
    }

    updateRecentOrderBlocks() {
        const container = document.getElementById('recent-order-blocks');
        if (!container || !this.smcData?.orderBlocks?.order_blocks) {
            if (container) {
                container.innerHTML = '<div class="fib-smc-loading"><div class="fib-smc-spinner"></div></div>';
            }
            return;
        }

        // En yakın 3 order block'u al
        const recentBlocks = this.smcData.orderBlocks.order_blocks.slice(0, 3);

        const blocksHtml = recentBlocks.map(block => {
            const typeClass = block.type;
            const touchedClass = block.touched ? 'touched' : '';

            return `
                <div class="order-block ${typeClass} ${touchedClass}">
                    <div class="order-block-info">
                        <div class="order-block-type ${typeClass}">${block.type}</div>
                        <div class="order-block-range">
                            ₺${block.low.toFixed(2)} - ₺${block.high.toFixed(2)}
                        </div>
                    </div>
                    <div class="order-block-strength">
                        ${block.strength.toFixed(0)}%
                        ${block.touched ? '<div class="text-xs text-orange-400">Dokunuldu</div>' : ''}
                    </div>
                </div>
            `;
        }).join('');

        container.innerHTML = blocksHtml || '<div class="text-gray-400 text-sm text-center py-4">Order block bulunamadı</div>';
    }

    // Analysis Page Updates
    updateFibonacciAnalysis() {
        // Analysis sayfası elemanları sadece analysis sayfasında mevcut
        if (!document.getElementById('analysis-fibonacci-bounce')) return;

        this.updateAnalysisFibonacciOverview();
        this.updateFibonacciLevelsTable();
        this.updateFibonacciSignals();
    }

    updateAnalysisFibonacciOverview() {
        if (!this.fibonacciData) return;

        const bounceElement = document.getElementById('analysis-fibonacci-bounce');
        if (bounceElement) {
            bounceElement.textContent = `${Math.round(this.fibonacciData.bounce_potential)}%`;
        }

        const trendElement = document.getElementById('analysis-fibonacci-trend');
        if (trendElement) {
            const trendText = this.fibonacciData.trend === 'up' ? '↗ Yükseliş' :
                             this.fibonacciData.trend === 'down' ? '↘ Düşüş' : '→ Sideways';
            trendElement.textContent = trendText;
            trendElement.className = `text-xl font-bold ${
                this.fibonacciData.trend === 'up' ? 'text-green-400' :
                this.fibonacciData.trend === 'down' ? 'text-red-400' : 'text-yellow-400'
            }`;
        }

        const rangeElement = document.getElementById('analysis-swing-range');
        if (rangeElement && this.fibonacciData.swing_range) {
            rangeElement.textContent = `₺${this.fibonacciData.swing_range.toFixed(2)}`;
        }

        // Current position update
        this.updateCurrentFibonacciPosition();
    }

    updateCurrentFibonacciPosition() {
        const container = document.getElementById('current-fibonacci-position');
        if (!container || !this.fibonacciData?.nearest_level) return;

        const nearest = this.fibonacciData.nearest_level;
        const current = this.fibonacciData.current_price;

        container.innerHTML = `
            <div class="grid grid-cols-1 lg:grid-cols-3 gap-4">
                <div class="text-center">
                    <div class="text-lg font-bold text-yellow-400 mb-1">₺${current.toFixed(2)}</div>
                    <div class="text-sm text-gray-400">Mevcut Fiyat</div>
                </div>
                <div class="text-center">
                    <div class="text-lg font-bold text-blue-400 mb-1">${(nearest.level * 100).toFixed(1)}%</div>
                    <div class="text-sm text-gray-400">En Yakın Seviye</div>
                </div>
                <div class="text-center">
                    <div class="text-lg font-bold ${this.fibonacciData.bounce_potential > 60 ? 'text-green-400' : 'text-yellow-400'} mb-1">
                        ${Math.round(this.fibonacciData.bounce_potential)}%
                    </div>
                    <div class="text-sm text-gray-400">Bounce Potansiyeli</div>
                </div>
            </div>
            <div class="mt-4 p-3 bg-slate-800/50 rounded-lg">
                <div class="text-sm text-gray-300">
                    <strong>${nearest.description}</strong> seviyesine 
                    <span class="text-yellow-400">₺${Math.abs(current - nearest.price).toFixed(2)}</span> mesafede.
                    Bounce potansiyeli ${this.fibonacciData.bounce_potential > 60 ? 'yüksek' : 'orta'} seviyede.
                </div>
            </div>
        `;
    }

    updateFibonacciLevelsTable() {
        const tableBody = document.getElementById('fibonacci-levels-table');
        if (!tableBody || !this.fibonacciData?.levels) return;

        const rowsHtml = this.fibonacciData.levels.map(level => {
            const strengthColor = {
                'very_strong': 'text-red-400',
                'strong': 'text-orange-400',
                'medium': 'text-blue-400',
                'weak': 'text-gray-400'
            }[level.strength] || 'text-gray-400';

            const statusBadge = level.is_nearest ? 
                '<span class="fib-badge golden-ratio">Yakın</span>' : '';
            const typeBadge = `<span class="fib-badge ${level.level_type}">${level.level_type === 'extension' ? 'EXT' : 'RET'}</span>`;
            const goldenBadge = level.is_golden_ratio ? 
                '<span class="fib-badge golden-ratio">AR</span>' : '';

            return `
                <tr class="${level.is_nearest ? 'bg-yellow-400/10' : ''}">
                    <td class="py-2">${(level.ratio * 100).toFixed(1)}%</td>
                    <td class="py-2 font-semibold text-yellow-400">₺${level.price.toFixed(2)}</td>
                    <td class="py-2">${level.distance_pct.toFixed(2)}%</td>
                    <td class="py-2 ${strengthColor}">${level.strength}</td>
                    <td class="py-2 text-sm">${level.description}</td>
                    <td class="py-2">${statusBadge} ${typeBadge} ${goldenBadge}</td>
                </tr>
            `;
        }).join('');

        tableBody.innerHTML = rowsHtml;
    }

    updateFibonacciSignals() {
        const container = document.getElementById('fibonacci-signals');
        if (!container || !this.fibonacciData) return;

        // Fibonacci sinyalleri için API'dan signals verisi gerekiyor
        // Şimdilik basit bir gösterim yapıyoruz
        const bounce = this.fibonacciData.bounce_potential;
        const trend = this.fibonacciData.trend;

        let signalHtml = '';

        if (bounce > 70) {
            signalHtml = `
                <div class="bg-green-600/20 border border-green-600/30 rounded-lg p-4">
                    <div class="flex items-center mb-2">
                        <i class="fas fa-arrow-up text-green-400 mr-2"></i>
                        <span class="font-semibold text-green-400">Güçlü Alım Sinyali</span>
                    </div>
                    <div class="text-sm text-gray-300">
                        Yüksek bounce potansiyeli (%${Math.round(bounce)}) ve ${trend} trend yapısı güçlü alım fırsatı sunuyor.
                    </div>
                </div>
            `;
        } else if (bounce > 50) {
            signalHtml = `
                <div class="bg-yellow-600/20 border border-yellow-600/30 rounded-lg p-4">
                    <div class="flex items-center mb-2">
                        <i class="fas fa-eye text-yellow-400 mr-2"></i>
                        <span class="font-semibold text-yellow-400">İzleme Sinyali</span>
                    </div>
                    <div class="text-sm text-gray-300">
                        Orta seviye bounce potansiyeli (%${Math.round(bounce)}). Diğer göstergelerle birlikte değerlendirin.
                    </div>
                </div>
            `;
        } else {
            signalHtml = `
                <div class="bg-gray-600/20 border border-gray-600/30 rounded-lg p-4">
                    <div class="flex items-center mb-2">
                        <i class="fas fa-pause text-gray-400 mr-2"></i>
                        <span class="font-semibold text-gray-400">Bekleme Sinyali</span>
                    </div>
                    <div class="text-sm text-gray-300">
                        Düşük bounce potansiyeli (%${Math.round(bounce)}). Daha iyi giriş noktası bekleyin.
                    </div>
                </div>
            `;
        }

        container.innerHTML = signalHtml;
    }

    updateSMCAnalysis() {
        // Analysis sayfası elemanları sadece analysis sayfasında mevcut
        if (!document.getElementById('analysis-smc-order-blocks')) return;

        this.updateAnalysisSMCOverview();
        this.updateAnalysisMarketStructure();
        this.updateAnalysisOrderBlocks();
        this.updateAnalysisFairValueGaps();
        this.updateAnalysisLiquidityZones();
        this.updateSMCSignals();
    }

    updateAnalysisSMCOverview() {
        if (!this.smcData) return;

        const orderBlocksElement = document.getElementById('analysis-smc-order-blocks');
        if (orderBlocksElement && this.smcData.orderBlocks?.statistics) {
            orderBlocksElement.textContent = this.smcData.orderBlocks.statistics.total_count || 0;
        }

        const fvgsElement = document.getElementById('analysis-smc-fvgs');
        if (fvgsElement && this.smcData.fvgs?.statistics) {
            fvgsElement.textContent = this.smcData.fvgs.statistics.total_count || 0;
        }

        const structureElement = document.getElementById('analysis-smc-structure');
        if (structureElement && this.smcData.structure?.market_structure) {
            const structure = this.smcData.structure.market_structure;
            structureElement.textContent = structure.trend.toUpperCase();
            structureElement.className = `text-xl font-bold ${
                structure.trend === 'bullish' ? 'text-green-400' :
                structure.trend === 'bearish' ? 'text-red-400' : 'text-yellow-400'
            }`;
        }

        const liquidityElement = document.getElementById('analysis-smc-liquidity');
        if (liquidityElement && this.smcData.liquidity_zones) {
            liquidityElement.textContent = this.smcData.liquidity_zones.length || 0;
        }
    }

    updateAnalysisMarketStructure() {
        if (!this.smcData?.structure?.market_structure) return;

        const structure = this.smcData.structure.market_structure;

        // Trend
        const trendElement = document.getElementById('analysis-market-structure-trend');
        if (trendElement) {
            trendElement.textContent = structure.trend.toUpperCase();
            trendElement.className = `structure-trend-value ${structure.trend}`;
        }

        // Structure metrics
        const metrics = ['higher_highs', 'higher_lows', 'lower_highs', 'lower_lows'];
        metrics.forEach(metric => {
            const element = document.getElementById(`analysis-${metric.replace('_', '-')}`);
            if (element) {
                element.textContent = structure[metric] || 0;
            }
        });

        // BOS & CHoCH levels and status
        const levels = this.smcData.structure.levels;
        if (levels) {
            const bosLevelElement = document.getElementById('analysis-bos-level');
            const bosStatusElement = document.getElementById('analysis-bos-status');
            const chochLevelElement = document.getElementById('analysis-choch-level');
            const chochStatusElement = document.getElementById('analysis-choch-status');

            if (bosLevelElement && levels.bos_level) {
                bosLevelElement.textContent = `₺${levels.bos_level.toFixed(2)}`;
            }

            if (bosStatusElement && levels.bos_status) {
                const statusClass = levels.bos_status === 'safe' ? 'text-green-400' :
                                   levels.bos_status === 'risk' ? 'text-red-400' : 'text-yellow-400';
                bosStatusElement.textContent = levels.bos_status.toUpperCase();
                bosStatusElement.className = `font-semibold ${statusClass}`;
            }

            if (chochLevelElement && levels.choch_level) {
                chochLevelElement.textContent = `₺${levels.choch_level.toFixed(2)}`;
            }

            if (chochStatusElement && levels.choch_status) {
                const statusClass = levels.choch_status === 'near' ? 'text-red-400' :
                                   levels.choch_status === 'approaching' ? 'text-yellow-400' : 'text-green-400';
                chochStatusElement.textContent = levels.choch_status.toUpperCase();
                chochStatusElement.className = `font-semibold ${statusClass}`;
            }
        }
    }

    updateAnalysisOrderBlocks() {
        const container = document.getElementById('analysis-order-blocks');
        if (!container || !this.smcData?.orderBlocks?.order_blocks) {
            if (container) {
                container.innerHTML = '<div class="fib-smc-loading"><div class="fib-smc-spinner"></div></div>';
            }
            return;
        }

        const blocks = this.smcData.orderBlocks.order_blocks;

        const blocksHtml = blocks.map(block => {
            const typeClass = block.type;
            const touchedClass = block.touched ? 'touched' : '';
            const nearClass = block.is_near ? 'bg-yellow-400/10 border-yellow-400/30' : '';

            return `
                <div class="order-block ${typeClass} ${touchedClass} ${nearClass}">
                    <div class="order-block-info">
                        <div class="order-block-type ${typeClass}">${block.type.toUpperCase()}</div>
                        <div class="order-block-range">
                            ₺${block.low.toFixed(2)} - ₺${block.high.toFixed(2)}
                            ${block.is_near ? '<span class="text-yellow-400 text-xs ml-2">YAKIN</span>' : ''}
                        </div>
                    </div>
                    <div class="order-block-strength">
                        ${block.strength.toFixed(0)}%
                        ${block.touched ? '<div class="text-xs text-orange-400 mt-1">Dokunuldu</div>' : ''}
                        <div class="text-xs text-gray-400 mt-1">${block.distance_from_price.toFixed(2)}% uzak</div>
                    </div>
                </div>
            `;
        }).join('');

        container.innerHTML = blocksHtml || '<div class="text-gray-400 text-sm text-center py-4">Order block bulunamadı</div>';
    }

    updateAnalysisFairValueGaps() {
        const container = document.getElementById('analysis-fair-value-gaps');
        if (!container || !this.smcData?.fvgs?.fair_value_gaps) {
            if (container) {
                container.innerHTML = '<div class="fib-smc-loading"><div class="fib-smc-spinner"></div></div>';
            }
            return;
        }

        const fvgs = this.smcData.fvgs.fair_value_gaps;

        const fvgsHtml = fvgs.map(fvg => {
            const typeClass = fvg.type;
            const filledClass = fvg.filled ? 'filled' : '';
            const inGapClass = fvg.price_in_gap ? 'bg-purple-400/10 border-purple-400/30' : '';

            return `
                <div class="fvg-item ${typeClass} ${filledClass} ${inGapClass}">
                    <div class="fvg-info">
                        <div class="fvg-type ${typeClass}">${fvg.type.toUpperCase()} FVG</div>
                        <div class="fvg-range">
                            ₺${fvg.low.toFixed(2)} - ₺${fvg.high.toFixed(2)}
                            ${fvg.price_in_gap ? '<span class="text-purple-400 text-xs ml-2">İÇİNDE</span>' : ''}
                        </div>
                    </div>
                    <div class="fvg-size">
                        ${fvg.size_pct.toFixed(2)}%
                        ${fvg.filled ? '<div class="text-xs text-gray-500 mt-1">Doldu</div>' : ''}
                        <div class="text-xs text-gray-400 mt-1">${fvg.distance_from_price.toFixed(2)}% uzak</div>
                    </div>
                </div>
            `;
        }).join('');

        container.innerHTML = fvgsHtml || '<div class="text-gray-400 text-sm text-center py-4">FVG bulunamadı</div>';
    }

    updateAnalysisLiquidityZones() {
        const container = document.getElementById('analysis-liquidity-zones');
        if (!container || !this.smcData?.liquidity_zones) {
            if (container) {
                container.innerHTML = '<div class="fib-smc-loading"><div class="fib-smc-spinner"></div></div>';
            }
            return;
        }

        const zones = this.smcData.liquidity_zones;

        const zonesHtml = zones.map(zone => {
            const typeText = zone.type.replace('_', ' ').toUpperCase();

            return `
                <div class="liquidity-zone">
                    <div class="liquidity-info">
                        <div class="liquidity-type">${typeText}</div>
                        <div class="liquidity-description">${zone.description}</div>
                    </div>
                    <div class="liquidity-strength">
                        ${zone.strength}%
                        <div class="text-xs text-gray-400 mt-1">₺${zone.level.toFixed(2)}</div>
                    </div>
                </div>
            `;
        }).join('');

        container.innerHTML = zonesHtml || '<div class="text-gray-400 text-sm text-center py-4">Likidite bölgesi bulunamadı</div>';
    }

    updateSMCSignals() {
        const container = document.getElementById('smc-signals');
        if (!container || !this.smcData?.signals) return;

        const signals = this.smcData.signals;
        let signalHtml = '';

        if (signals.action === 'BUY') {
            signalHtml = `
                <div class="bg-green-600/20 border border-green-600/30 rounded-lg p-4">
                    <div class="flex items-center mb-2">
                        <i class="fas fa-arrow-up text-green-400 mr-2"></i>
                        <span class="font-semibold text-green-400">ALIŞ SİNYALİ</span>
                        <span class="ml-2 text-sm text-gray-300">(Güç: ${signals.strength}%)</span>
                    </div>
                    <div class="text-sm text-gray-300 mb-3">
                        ${signals.reasons.join(', ')}
                    </div>
                    <div class="grid grid-cols-1 lg:grid-cols-3 gap-3">
                        ${signals.target ? `<div><span class="text-gray-400 text-xs">Hedef:</span><br><span class="text-green-400 font-semibold">₺${signals.target.toFixed(2)}</span></div>` : ''}
                        ${signals.stop ? `<div><span class="text-gray-400 text-xs">Stop:</span><br><span class="text-red-400 font-semibold">₺${signals.stop.toFixed(2)}</span></div>` : ''}
                        ${signals.risk_reward ? `<div><span class="text-gray-400 text-xs">R/R:</span><br><span class="text-yellow-400 font-semibold">1:${signals.risk_reward.toFixed(1)}</span></div>` : ''}
                    </div>
                </div>
            `;
        } else if (signals.action === 'SELL') {
            signalHtml = `
                <div class="bg-red-600/20 border border-red-600/30 rounded-lg p-4">
                    <div class="flex items-center mb-2">
                        <i class="fas fa-arrow-down text-red-400 mr-2"></i>
                        <span class="font-semibold text-red-400">SATIŞ SİNYALİ</span>
                        <span class="ml-2 text-sm text-gray-300">(Güç: ${signals.strength}%)</span>
                    </div>
                    <div class="text-sm text-gray-300 mb-3">
                        ${signals.reasons.join(', ')}
                    </div>
                    <div class="grid grid-cols-1 lg:grid-cols-3 gap-3">
                        ${signals.target ? `<div><span class="text-gray-400 text-xs">Hedef:</span><br><span class="text-green-400 font-semibold">₺${signals.target.toFixed(2)}</span></div>` : ''}
                        ${signals.stop ? `<div><span class="text-gray-400 text-xs">Stop:</span><br><span class="text-red-400 font-semibold">₺${signals.stop.toFixed(2)}</span></div>` : ''}
                        ${signals.risk_reward ? `<div><span class="text-gray-400 text-xs">R/R:</span><br><span class="text-yellow-400 font-semibold">1:${signals.risk_reward.toFixed(1)}</span></div>` : ''}
                    </div>
                </div>
            `;
        } else if (signals.action === 'WATCH') {
            signalHtml = `
                <div class="bg-yellow-600/20 border border-yellow-600/30 rounded-lg p-4">
                    <div class="flex items-center mb-2">
                        <i class="fas fa-eye text-yellow-400 mr-2"></i>
                        <span class="font-semibold text-yellow-400">İZLEME SİNYALİ</span>
                        <span class="ml-2 text-sm text-gray-300">(Güç: ${signals.strength}%)</span>
                    </div>
                    <div class="text-sm text-gray-300">
                        ${signals.reasons.join(', ')}
                    </div>
                </div>
            `;
        } else {
            signalHtml = `
                <div class="bg-gray-600/20 border border-gray-600/30 rounded-lg p-4">
                    <div class="flex items-center mb-2">
                        <i class="fas fa-pause text-gray-400 mr-2"></i>
                        <span class="font-semibold text-gray-400">BEKLEME SİNYALİ</span>
                    </div>
                    <div class="text-sm text-gray-300">
                        Şu anda net bir SMC sinyali bulunmuyor.
                    </div>
                </div>
            `;
        }

        container.innerHTML = signalHtml;
    }

    // Error handling
    showFibonacciError(message) {
        const status = document.getElementById('fibonacci-status');
        if (status) {
            status.textContent = 'Hata';
            status.className = 'fibonacci-status inactive';
        }

        const containers = [
            'nearest-fibonacci-level',
            'top-fibonacci-levels',
            'current-fibonacci-position',
            'fibonacci-levels-table',
            'fibonacci-signals'
        ];

        containers.forEach(id => {
            const element = document.getElementById(id);
            if (element) {
                element.innerHTML = `<div class="text-red-400 text-sm text-center py-4">${message}</div>`;
            }
        });
    }

    showSMCError(message) {
        const status = document.getElementById('smc-status');
        if (status) {
            status.textContent = 'Hata';
            status.className = 'fibonacci-status inactive';
        }

        const containers = [
            'recent-order-blocks',
            'analysis-order-blocks',
            'analysis-fair-value-gaps',
            'analysis-liquidity-zones',
            'smc-signals'
        ];

        containers.forEach(id => {
            const element = document.getElementById(id);
            if (element) {
                element.innerHTML = `<div class="text-red-400 text-sm text-center py-4">${message}</div>`;
            }
        });
    }

    // Refresh methods
    async refreshFibonacci() {
        const button = event?.target;
        if (button) {
            button.disabled = true;
            const originalText = button.innerHTML;
            button.innerHTML = '<i class="fas fa-spin fa-sync-alt mr-1"></i> Yenileniyor...';

            try {
                await this.loadFibonacciData();
            } finally {
                button.disabled = false;
                button.innerHTML = originalText;
            }
        } else {
            await this.loadFibonacciData();
        }
    }

    async refreshSMC() {
        const button = event?.target;
        if (button) {
            button.disabled = true;
            const originalText = button.innerHTML;
            button.innerHTML = '<i class="fas fa-spin fa-sync-alt mr-1"></i> Yenileniyor...';

            try {
                await this.loadSMCData();
            } finally {
                button.disabled = false;
                button.innerHTML = originalText;
            }
        } else {
            await this.loadSMCData();
        }
    }

    destroy() {
        if (this.updateInterval) {
            clearInterval(this.updateInterval);
        }

        // Chart cleanup
        Object.values(this.charts).forEach(chart => {
            if (chart && typeof chart.destroy === 'function') {
                chart.destroy();
            }
        });
    }
}

// Global instance
let fibonacciSMCManager = null;

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    fibonacciSMCManager = new FibonacciSMCManager();
});

// Cleanup on page unload
window.addEventListener('beforeunload', function() {
    if (fibonacciSMCManager) {
        fibonacciSMCManager.destroy();
    }
});

// Export for global access
window.FibonacciSMCManager = FibonacciSMCManager;