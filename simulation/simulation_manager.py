"""
Simülasyon yönetim sistemi
Gerçek zamanlı sinyal takibi ve otomatik trading simülasyonu
"""
import asyncio
import logging
import json
from datetime import timedelta, time
from decimal import Decimal
from typing import Dict, List, Optional, Tuple, Any
from collections import defaultdict
from utils.timezone import now, utc_now, to_turkey_time, get_day_start

from models.simulation import (
    SimulationConfig, SimulationPosition, SimulationStatus,
    StrategyType, PositionStatus, ExitReason, TimeframeCapital,
    SimulationSummary
)
from models.trading_signal import SignalType
from storage.sqlite_storage import SQLiteStorage
from utils.risk_management import KellyRiskManager

# Yeni modülleri import et
from .position_manager import PositionManager
from .signal_analyzer import SignalAnalyzer
from .statistics_manager import StatisticsManager

logger = logging.getLogger("gold_analyzer")


class SimulationManager:
    """Ana simülasyon yönetici sınıfı"""
    
    def __init__(self, storage: SQLiteStorage):
        self.storage = storage
        self.risk_manager = KellyRiskManager()
        self.active_simulations: Dict[int, SimulationConfig] = {}
        self.timeframe_capitals: Dict[int, Dict[str, TimeframeCapital]] = {}
        self.is_running = False
        
        # Yeni modülleri başlat
        self.position_manager = PositionManager(storage)
        self.signal_analyzer = SignalAnalyzer()
        self.statistics_manager = StatisticsManager(storage)
        
        logger.info("SimulationManager initialized")
        
    async def create_simulation(
        self,
        name: str,
        strategy_type: StrategyType = StrategyType.MAIN,
        **kwargs
    ) -> int:
        """Yeni simülasyon oluştur"""
        try:
            # Config oluştur
            config = SimulationConfig(
                name=name,
                strategy_type=strategy_type,
                **kwargs
            )
            
            # Veritabanına kaydet
            with self.storage.get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    INSERT INTO simulations (
                        name, strategy_type, status, initial_capital,
                        min_confidence, max_risk, spread, commission_rate,
                        current_capital, start_date, last_update, config
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    config.name,
                    config.strategy_type.value,
                    SimulationStatus.ACTIVE.value,
                    float(config.initial_capital),
                    config.min_confidence,
                    config.max_risk,
                    float(config.spread),
                    config.commission_rate,
                    float(config.initial_capital),
                    now(),
                    now(),
                    json.dumps(config.to_dict())
                ))
                
                simulation_id = cursor.lastrowid
                
                # Timeframe sermayelerini oluştur
                for timeframe, capital in config.capital_distribution.items():
                    cursor.execute("""
                        INSERT INTO sim_timeframe_capital (
                            simulation_id, timeframe, allocated_capital, current_capital
                        ) VALUES (?, ?, ?, ?)
                    """, (simulation_id, timeframe, float(capital), float(capital)))
                
                conn.commit()
            
            # Memory'de sakla
            self.active_simulations[simulation_id] = config
            self._init_timeframe_capitals(simulation_id, config)
            
            logger.info(f"Simülasyon oluşturuldu: {name} (ID: {simulation_id})")
            return simulation_id
            
        except Exception as e:
            logger.error(f"Simülasyon oluşturma hatası: {str(e)}")
            raise
    
    def _init_timeframe_capitals(self, simulation_id: int, config: SimulationConfig):
        """Timeframe sermayelerini başlat"""
        self.timeframe_capitals[simulation_id] = {}
        for timeframe, capital in config.capital_distribution.items():
            self.timeframe_capitals[simulation_id][timeframe] = TimeframeCapital(
                timeframe=timeframe,
                allocated_capital=capital,
                current_capital=capital
            )
    
    async def start(self):
        """Simülasyon döngüsünü başlat"""
        logger.info("SimulationManager.start() called")
        
        if self.is_running:
            logger.warning("Simülasyon zaten çalışıyor")
            return
        
        self.is_running = True
        logger.info("Simülasyon sistemi başlatıldı")
        
        # Aktif simülasyonları yükle
        logger.info("Loading active simulations...")
        await self._load_active_simulations()
        
        logger.info(f"Starting simulation loop with {len(self.active_simulations)} simulations")
        
        # Ana döngü
        while self.is_running:
            try:
                logger.debug("Processing simulations cycle...")
                await self._process_simulations()
                await asyncio.sleep(60)  # 1 dakika bekle
            except Exception as e:
                logger.error(f"Simülasyon döngü hatası: {str(e)}", exc_info=True)
                await asyncio.sleep(5)
    
    async def _load_active_simulations(self):
        """Aktif simülasyonları veritabanından yükle"""
        try:
            with self.storage.get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    SELECT id, config FROM simulations
                    WHERE status = ?
                """, (SimulationStatus.ACTIVE.value,))
                
                for row in cursor.fetchall():
                    sim_id, config_json = row
                    config_dict = json.loads(config_json)
                    
                    # Config nesnesini oluştur
                    config = SimulationConfig(
                        name=config_dict['name'],
                        strategy_type=StrategyType(config_dict['strategy_type']),
                        initial_capital=Decimal(str(config_dict['initial_capital'])),
                        min_confidence=config_dict['min_confidence'],
                        max_risk=config_dict['max_risk'],
                        spread=Decimal(str(config_dict['spread'])),
                        commission_rate=config_dict['commission_rate']
                    )
                    
                    # Capital distribution
                    if 'capital_distribution' in config_dict:
                        config.capital_distribution = {
                            k: Decimal(str(v)) 
                            for k, v in config_dict['capital_distribution'].items()
                        }
                    
                    # Time limits
                    if 'time_limits' in config_dict:
                        config.time_limits = config_dict['time_limits']
                    
                    # Other config parameters
                    if 'trading_hours' in config_dict:
                        config.trading_hours = config_dict['trading_hours']
                    if 'atr_multiplier_sl' in config_dict:
                        config.atr_multiplier_sl = config_dict['atr_multiplier_sl']
                    if 'risk_reward_ratio' in config_dict:
                        config.risk_reward_ratio = config_dict['risk_reward_ratio']
                    
                    self.active_simulations[sim_id] = config
                    
                    # Timeframe sermayelerini yükle
                    await self._load_timeframe_capitals(sim_id)
                
                logger.info(f"{len(self.active_simulations)} aktif simülasyon yüklendi")
            
        except Exception as e:
            logger.error(f"Simülasyon yükleme hatası: {str(e)}")
    
    async def _load_timeframe_capitals(self, simulation_id: int):
        """Timeframe sermayelerini yükle"""
        try:
            with self.storage.get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    SELECT timeframe, allocated_capital, current_capital, in_position
                    FROM sim_timeframe_capital
                    WHERE simulation_id = ?
                """, (simulation_id,))
                
                self.timeframe_capitals[simulation_id] = {}
                
                for row in cursor.fetchall():
                    timeframe, allocated, current, in_position = row
                    tf_capital = TimeframeCapital(
                        timeframe=timeframe,
                        allocated_capital=Decimal(str(allocated)),
                        current_capital=Decimal(str(current)),
                        in_position=bool(in_position)
                    )
                    
                    # Eğer pozisyonda ise, açık pozisyon ID'sini bul
                    if tf_capital.in_position:
                        cursor2 = conn.cursor()
                        cursor2.execute("""
                            SELECT id FROM sim_positions
                            WHERE simulation_id = ? AND timeframe = ? AND status = 'OPEN'
                            ORDER BY entry_time DESC LIMIT 1
                        """, (simulation_id, timeframe))
                        pos_row = cursor2.fetchone()
                        if pos_row:
                            tf_capital.open_position_id = pos_row[0]
                            logger.debug(f"Found open position {pos_row[0]} for sim {simulation_id} - {timeframe}")
                    
                    self.timeframe_capitals[simulation_id][timeframe] = tf_capital
                
        except Exception as e:
            logger.error(f"Timeframe sermaye yükleme hatası: {str(e)}")
    
    async def _process_simulations(self):
        """Tüm aktif simülasyonları işle"""
        current_time = now()
        
        # Türkiye saatine çevir (UTC+3)
        tr_time = current_time
        
        logger.info(f"Processing simulations - Current time: {current_time}, TR time: {tr_time}, Trading hours: {self._is_trading_hours(tr_time)}")
        
        # İşlem saatleri kontrolü
        if not self._is_trading_hours(tr_time):
            # Sadece açık pozisyonları kontrol et
            logger.debug("Outside trading hours, checking open positions only")
            await self._check_open_positions()
            return
        
        logger.info(f"Processing {len(self.active_simulations)} active simulations")
        
        # Her simülasyon için
        for sim_id, config in self.active_simulations.items():
            try:
                await self._process_single_simulation(sim_id, config, current_time)
            except Exception as e:
                logger.error(f"Simülasyon {sim_id} işleme hatası: {str(e)}")
    
    def _is_trading_hours(self, current_time) -> bool:
        """İşlem saatleri içinde mi?"""
        # GEÇİCİ: Test için trading saatleri kontrolü devre dışı
        return True
        # current_hour = current_time.hour
        # # Varsayılan 09:00-17:00
        # return 9 <= current_hour < 17
    
    async def _process_single_simulation(
        self,
        sim_id: int,
        config: SimulationConfig,
        current_time
    ):
        """Tek bir simülasyonu işle"""
        logger.debug(f"Processing simulation {sim_id}: {config.name}")
        logger.debug(f"Config - Strategy: {config.strategy_type.value}, Min confidence: {config.min_confidence}")
        
        # Son sinyalleri al
        signals = await self._get_latest_signals()
        logger.debug(f"Got signals for timeframes: {list(signals.keys())}")
        
        # Her timeframe için
        for timeframe, signal_data in signals.items():
            if timeframe not in self.timeframe_capitals[sim_id]:
                logger.debug(f"Timeframe {timeframe} not in capitals for sim {sim_id}")
                continue
            
            tf_capital = self.timeframe_capitals[sim_id][timeframe]
            logger.debug(f"\n=== Sim {sim_id} - {timeframe} ===")
            logger.debug(f"In position: {tf_capital.in_position}, Capital: {tf_capital.current_capital}")
            logger.debug(f"Signal: {signal_data.get('signal')}, Confidence: {signal_data.get('confidence')}")
            
            # Açık pozisyon varsa kontrol et
            if tf_capital.in_position and tf_capital.open_position_id:
                logger.debug(f"Checking open position {tf_capital.open_position_id} for exit")
                await self._check_position_exit(
                    sim_id, tf_capital.open_position_id, signal_data
                )
            else:
                # Önce aynı timeframe için açık pozisyon olup olmadığını kontrol et
                has_open_position = await self._check_open_position_exists(sim_id, timeframe)
                if has_open_position:
                    logger.warning(f"Open position already exists for {sim_id}-{timeframe}, skipping")
                    # Timeframe capital'i güncelle
                    tf_capital.in_position = True
                    continue
                
                # Yeni pozisyon açma kontrolü
                logger.debug(f"Checking if should open position for {timeframe}")
                if self._should_open_position(config, signal_data, timeframe):
                    logger.info(f"✅ Opening position for sim {sim_id} - {timeframe}")
                    await self._open_position(
                        sim_id, config, timeframe, signal_data, tf_capital
                    )
                else:
                    logger.debug(f"❌ Not opening position for {timeframe} - conditions not met")
        
        # Günlük performansı güncelle
        await self._update_daily_performance(sim_id)
    
    async def _get_latest_signals(self) -> Dict[str, Dict]:
        """Son sinyalleri al"""
        try:
            signals = {}
            # Geçici olarak 1d'yi kaldır - yeterli veri yok
            timeframes = ['15m', '1h', '4h']  # '1d' removed temporarily
            
            for timeframe in timeframes:
                # Son hybrid analizi al
                analysis = self.storage.get_latest_hybrid_analysis(timeframe)
                if analysis:
                    logger.debug(f"Found analysis for {timeframe} - Signal: {analysis.get('signal')}, Confidence: {analysis.get('confidence')}")
                    
                    # gram_analysis details.gram içinde olabilir
                    gram_analysis = analysis.get('gram_analysis', {})
                    if not gram_analysis and 'details' in analysis:
                        gram_analysis = analysis['details'].get('gram', {})
                    
                    signals[timeframe] = {
                        'signal': analysis.get('signal'),
                        'confidence': analysis.get('confidence', 0),
                        'price': analysis.get('gram_price'),
                        'indicators': {
                            'rsi': gram_analysis.get('indicators', {}).get('rsi'),
                            'macd': gram_analysis.get('indicators', {}).get('macd'),
                            'bb': gram_analysis.get('indicators', {}).get('bollinger'),
                            'atr': gram_analysis.get('indicators', {}).get('atr'),
                            'patterns': gram_analysis.get('patterns', [])
                        },
                        'stop_loss': analysis.get('stop_loss'),
                        'take_profit': analysis.get('take_profit'),
                        'position_size': analysis.get('position_size')
                    }
                else:
                    logger.debug(f"No analysis found for {timeframe}")
            
            logger.info(f"Total signals found: {len(signals)} - Timeframes: {list(signals.keys())}")
            return signals
            
        except Exception as e:
            logger.error(f"Sinyal alma hatası: {str(e)}")
            return {}
    
    def _should_open_position(
        self,
        config: SimulationConfig,
        signal_data: Dict,
        timeframe: str
    ) -> bool:
        """Pozisyon açılmalı mı?"""
        return self.signal_analyzer.should_open_position(config, signal_data, timeframe)
    
    def _apply_strategy_filter(
        self,
        config: SimulationConfig,
        signal_data: Dict,
        timeframe: str
    ) -> bool:
        """Strateji tipine göre sinyal filtrele"""
        return self.signal_analyzer._apply_strategy_filter(config, signal_data, timeframe)
    
    async def _check_open_position_exists(self, sim_id: int, timeframe: str) -> bool:
        """Belirli bir timeframe için açık pozisyon var mı kontrol et"""
        with self.storage.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT COUNT(*) FROM sim_positions
                WHERE simulation_id = ? AND timeframe = ? AND status = 'OPEN'
            """, (sim_id, timeframe))
            count = cursor.fetchone()[0]
            return count > 0
    
    async def _open_position(
        self,
        sim_id: int,
        config: SimulationConfig,
        timeframe: str,
        signal_data: Dict,
        tf_capital: TimeframeCapital
    ):
        """Yeni pozisyon aç"""
        try:
            # Günlük risk kontrolü
            with self.storage.get_connection() as conn:
                cursor = conn.cursor()
                today = now().date()
                
                cursor.execute("""
                    SELECT daily_pnl_pct FROM sim_daily_performance
                    WHERE simulation_id = ? AND date = ?
                """, (sim_id, today))
                
                row = cursor.fetchone()
                if row and row[0] <= -2.0:  # %2 günlük kayıp
                    logger.warning(f"Günlük kayıp limiti aşıldı: {row[0]:.2f}%, yeni pozisyon açılamaz")
                    return
            
            current_price = Decimal(str(signal_data['price']))
            
            # Risk hesaplama
            atr = signal_data['indicators'].get('atr')
            if not atr:
                logger.warning(f"ATR değeri bulunamadı {timeframe} için, pozisyon açılamıyor")
                return
            
            # ATR değerini al - eğer dict ise 'atr' key'inden al, değilse direkt kullan
            if isinstance(atr, dict):
                atr_dict = atr
            else:
                atr_dict = {'atr': atr}
                
            # Pozisyon boyutu hesapla
            position_size = self.position_manager.calculate_position_size(
                config, tf_capital.current_capital, current_price, atr_dict
            )
            
            # Stop loss ve take profit hesapla
            position_type = "LONG" if signal_data['signal'] == 'BUY' else "SHORT"
            stop_loss = self.position_manager.calculate_stop_loss(
                position_type, current_price, atr_dict, config
            )
            take_profit = self.position_manager.calculate_take_profit(
                position_type, current_price, stop_loss, config
            )
            
            # Risk miktarını hesapla
            risk_amount = tf_capital.current_capital * Decimal(str(config.max_risk))
            position_value = position_size * current_price  # gram x fiyat
            
            # Spread ve komisyon
            spread_cost = config.spread
            commission = position_value * Decimal(str(config.commission_rate))
            
            # Pozisyon oluştur
            position = SimulationPosition(
                simulation_id=sim_id,
                timeframe=timeframe,
                position_type="LONG" if signal_data['signal'] == 'BUY' else "SHORT",
                status=PositionStatus.OPEN,
                entry_time=now(),
                entry_price=current_price,
                entry_spread=spread_cost,
                entry_commission=commission,
                position_size=position_size,
                allocated_capital=position_value,
                risk_amount=risk_amount,
                stop_loss=stop_loss,
                take_profit=take_profit,
                entry_confidence=signal_data['confidence'],
                entry_indicators=signal_data['indicators']
            )
            
            # Veritabanına kaydet
            position_id = await self._save_position(position)
            
            # Timeframe sermayesini güncelle
            tf_capital.in_position = True
            tf_capital.open_position_id = position_id
            tf_capital.last_trade_time = now()
            
            # Timeframe capital'i veritabanında güncelle
            await self._update_timeframe_capital(sim_id, timeframe, tf_capital)
            
            logger.info(
                f"Pozisyon açıldı: Sim#{sim_id} {timeframe} "
                f"{position.position_type} {position_size:.3f} gram @ {current_price}"
            )
            
        except Exception as e:
            logger.error(f"Pozisyon açma hatası: {str(e)}")
    
    async def _check_position_exit(
        self,
        sim_id: int,
        position_id: int,
        current_signal: Dict
    ):
        """Açık pozisyon çıkış kontrolü"""
        try:
            # Pozisyonu al
            position = await self._get_position(position_id)
            if not position or position.status != PositionStatus.OPEN:
                logger.debug(f"Position {position_id} not found or not open")
                return
            
            current_price = Decimal(str(current_signal['price']))
            config = self.active_simulations[sim_id]
            
            # Çıkış koşullarını kontrol et
            exit_reason_str = self.signal_analyzer.check_exit_conditions(
                position, current_price, current_signal, config
            )
            
            exit_reason = None
            exit_price = current_price
            
            if exit_reason_str:
                # String'i ExitReason enum'a çevir
                exit_reason = ExitReason[exit_reason_str]
                # Çıkış fiyatını belirle
                if exit_reason == ExitReason.STOP_LOSS:
                    exit_price = position.stop_loss
                elif exit_reason == ExitReason.TAKE_PROFIT:
                    exit_price = position.take_profit
                elif exit_reason == ExitReason.TRAILING_STOP:
                    exit_price = position.trailing_stop
            
            # Trailing stop güncellemesi kontrol et
            if not exit_reason:
                new_trailing = self.signal_analyzer.update_trailing_stop(
                    position, current_price, config
                )
                if new_trailing:
                    await self._update_position_trailing_stop(position_id, new_trailing)
                    logger.info(f"Trailing stop güncellendi: {new_trailing}")
            
            # Güven düşüşü kontrolü (signal_analyzer içinde yok, burada bırakalım)
            if not exit_reason:
                if current_signal.get('confidence', 1) < 0.4:
                    exit_reason = ExitReason.CONFIDENCE_DROP
            
            # Pozisyonu kapat
            if exit_reason:
                logger.info(f"🔴 Closing position {position_id}: Reason={exit_reason.value}, Exit price={exit_price}")
                await self._close_position(
                    sim_id,
                    position,
                    exit_price,
                    exit_reason,
                    current_signal.get('indicators')
                )
            else:
                logger.debug(f"Position {position_id} remains open - no exit conditions met")
                
        except Exception as e:
            logger.error(f"Pozisyon çıkış kontrolü hatası: {str(e)}")
    
    async def _close_position(
        self,
        sim_id: int,
        position: SimulationPosition,
        exit_price: Decimal,
        exit_reason: ExitReason,
        exit_indicators: Optional[Dict] = None
    ):
        """Pozisyonu kapat"""
        try:
            config = self.active_simulations[sim_id]
            
            # Çıkış maliyetleri
            exit_spread = config.spread
            exit_commission = exit_price * position.position_size * Decimal(str(config.commission_rate))
            
            # PnL hesapla (TL cinsinden)
            if position.position_type == "LONG":
                gross_pnl_tl = (exit_price - position.entry_price) * position.position_size
            else:
                gross_pnl_tl = (position.entry_price - exit_price) * position.position_size
            
            # Net PnL (TL cinsinden, tüm maliyetler dahil)
            total_costs = (position.entry_spread + position.entry_commission + 
                          exit_spread + exit_commission)
            net_pnl_tl = gross_pnl_tl - total_costs
            
            # PnL'yi gram cinsine çevir (sermaye güncellemesi için)
            net_pnl_gram = net_pnl_tl / exit_price
            gross_pnl = gross_pnl_tl  # Database için TL olarak sakla
            net_pnl = net_pnl_tl  # Database için TL olarak sakla
            pnl_pct = (net_pnl_tl / position.allocated_capital) * 100
            
            # Pozisyonu güncelle
            position.status = PositionStatus.CLOSED
            position.exit_time = now()
            position.exit_price = exit_price
            position.exit_spread = exit_spread
            position.exit_commission = exit_commission
            position.exit_reason = exit_reason
            position.gross_profit_loss = gross_pnl
            position.net_profit_loss = net_pnl
            position.profit_loss_pct = float(pnl_pct)
            position.holding_period_minutes = int(
                (position.exit_time - position.entry_time).total_seconds() / 60
            )
            position.exit_indicators = exit_indicators
            
            # Veritabanında güncelle
            await self._update_position_close(position)
            
            # Timeframe sermayesini güncelle (gram cinsinden)
            tf_capital = self.timeframe_capitals[sim_id][position.timeframe]
            tf_capital.update_capital(net_pnl_gram)  # Gram cinsinden güncelle
            tf_capital.in_position = False
            tf_capital.open_position_id = None
            await self._update_timeframe_capital(sim_id, position.timeframe, tf_capital)
            
            # Simülasyon istatistiklerini güncelle
            await self._update_simulation_stats(sim_id)
            
            # Risk manager'a işlem sonucunu ekle
            self.risk_manager.add_trade_result(
                float(position.entry_price),
                float(exit_price),
                float(position.position_size),
                position.position_type
            )
            
            logger.info(
                f"Pozisyon kapatıldı: Sim#{sim_id} {position.timeframe} "
                f"{exit_reason.value} PnL: {net_pnl:.2f} ({pnl_pct:.2f}%)"
            )
            
        except Exception as e:
            logger.error(f"Pozisyon kapatma hatası: {str(e)}")
    
    async def _check_open_positions(self):
        """İşlem saatleri dışında açık pozisyonları kontrol et"""
        # Sadece SL/TP kontrolü yapılacak
        for sim_id in self.active_simulations:
            for timeframe, tf_capital in self.timeframe_capitals[sim_id].items():
                if tf_capital.in_position and tf_capital.open_position_id:
                    # Güncel fiyatı al
                    current_price = await self._get_current_price()
                    if current_price:
                        await self._check_sl_tp_only(
                            sim_id,
                            tf_capital.open_position_id,
                            current_price
                        )
    
    async def _check_sl_tp_only(
        self,
        sim_id: int,
        position_id: int,
        current_price: Decimal
    ):
        """Sadece SL/TP kontrolü"""
        try:
            position = await self._get_position(position_id)
            if not position or position.status != PositionStatus.OPEN:
                return
            
            exit_reason = None
            exit_price = current_price
            
            # Stop loss kontrolü
            if position.position_type == "LONG":
                if current_price <= position.stop_loss:
                    exit_reason = ExitReason.STOP_LOSS
                    exit_price = position.stop_loss
                elif current_price >= position.take_profit:
                    exit_reason = ExitReason.TAKE_PROFIT
                    exit_price = position.take_profit
            else:
                if current_price >= position.stop_loss:
                    exit_reason = ExitReason.STOP_LOSS
                    exit_price = position.stop_loss
                elif current_price <= position.take_profit:
                    exit_reason = ExitReason.TAKE_PROFIT
                    exit_price = position.take_profit
            
            if exit_reason:
                await self._close_position(sim_id, position, exit_price, exit_reason)
                
        except Exception as e:
            logger.error(f"SL/TP kontrol hatası: {str(e)}")
    
    async def _get_current_price(self) -> Optional[Decimal]:
        """Güncel gram altın fiyatını al"""
        try:
            # Son fiyat verisini al
            latest = self.storage.get_latest_price()
            if latest and latest.gram_altin:
                return latest.gram_altin
            return None
        except Exception as e:
            logger.error(f"Fiyat alma hatası: {str(e)}")
            return None
    
    # Veritabanı işlemleri
    async def _save_position(self, position: SimulationPosition) -> int:
        """Pozisyonu veritabanına kaydet"""
        return await self.position_manager.save_position(position)
    
    async def _get_position(self, position_id: int) -> Optional[SimulationPosition]:
        """Pozisyonu veritabanından al"""
        return await self.position_manager.get_position(position_id)
    
    async def _update_position_trailing_stop(self, position_id: int, trailing_stop: Decimal):
        """Trailing stop güncelle"""
        await self.position_manager.update_position_trailing_stop(position_id, trailing_stop)
    
    async def _update_position_close(self, position: SimulationPosition):
        """Pozisyon kapanışını güncelle"""
        await self.position_manager.update_position_close(position)
    
    async def _update_timeframe_capital(
        self,
        sim_id: int,
        timeframe: str,
        tf_capital: TimeframeCapital
    ):
        """Timeframe sermayesini güncelle"""
        await self.statistics_manager.update_timeframe_capital(sim_id, timeframe, tf_capital)
    
    async def _update_simulation_stats(self, sim_id: int):
        """Simülasyon istatistiklerini güncelle"""
        await self.statistics_manager.update_simulation_stats(sim_id, self.timeframe_capitals)
    
    async def _update_daily_performance(self, sim_id: int):
        """Günlük performansı güncelle"""
        await self.statistics_manager.update_daily_performance(sim_id, self.timeframe_capitals, self.active_simulations)
    
    # Public metodlar
    async def get_simulation_status(self, sim_id: int) -> Optional[SimulationSummary]:
        """Simülasyon durumunu al"""
        try:
            with self.storage.get_connection() as conn:
                cursor = conn.cursor()
                
                # Simülasyon bilgilerini al
                cursor.execute("""
                    SELECT * FROM simulations WHERE id = ?
                """, (sim_id,))
                
                sim_row = cursor.fetchone()
                if not sim_row:
                    return None
                
                col_names = [desc[0] for desc in cursor.description]
                sim_data = dict(zip(col_names, sim_row))
                
                # Timeframe sermayelerini al
                tf_capitals = {}
                for tf, capital in self.timeframe_capitals.get(sim_id, {}).items():
                    tf_capitals[tf] = {
                        'allocated': float(capital.allocated_capital),
                        'current': float(capital.current_capital),
                        'in_position': capital.in_position
                    }
                
                # Açık pozisyonları say
                cursor.execute("""
                    SELECT COUNT(*) FROM sim_positions
                    WHERE simulation_id = ? AND status = 'OPEN'
                """, (sim_id,))
                open_positions = cursor.fetchone()[0]
                
                # Günlük performans
                today_start = get_day_start()
                cursor.execute("""
                    SELECT COUNT(*), SUM(net_profit_loss)
                    FROM sim_positions
                    WHERE simulation_id = ? AND exit_time >= ?
                """, (sim_id, today_start))
                daily_trades, daily_pnl = cursor.fetchone()
                
                return SimulationSummary(
                simulation_id=sim_id,
                name=sim_data['name'],
                strategy_type=sim_data['strategy_type'],
                status=SimulationStatus(sim_data['status']),
                initial_capital=Decimal(str(sim_data['initial_capital'])),
                current_capital=Decimal(str(sim_data['current_capital'])),
                total_pnl=Decimal(str(sim_data['total_profit_loss'])),
                total_pnl_pct=sim_data['total_profit_loss_pct'],
                timeframe_capitals=tf_capitals,
                total_trades=sim_data['total_trades'],
                open_positions=open_positions,
                winning_trades=sim_data['winning_trades'],
                losing_trades=sim_data['losing_trades'],
                win_rate=sim_data['win_rate'],
                profit_factor=sim_data['profit_factor'],
                sharpe_ratio=sim_data['sharpe_ratio'],
                max_drawdown=Decimal(str(sim_data['max_drawdown'])),
                max_drawdown_pct=sim_data['max_drawdown_pct'],
                avg_win=sim_data['avg_win'],
                avg_loss=sim_data['avg_loss'],
                avg_win_loss_ratio=sim_data['avg_win'] / sim_data['avg_loss'] if sim_data['avg_loss'] > 0 else 0,
                start_date=datetime.fromisoformat(sim_data['start_date']),
                last_update=datetime.fromisoformat(sim_data['last_update']),
                running_days=(now() - datetime.fromisoformat(sim_data['start_date'])).days,
                daily_pnl=Decimal(str(daily_pnl or 0)),
                daily_pnl_pct=float(daily_pnl or 0) / float(sim_data['current_capital']) * 100,
                daily_trades=daily_trades or 0,
                daily_risk_used=0.0  # TODO: Hesapla
            )
            
        except Exception as e:
            logger.error(f"Simülasyon durumu alma hatası: {str(e)}")
            return None
    
    async def stop(self):
        """Simülasyon sistemini durdur"""
        self.is_running = False
        logger.info("Simülasyon sistemi durduruldu")