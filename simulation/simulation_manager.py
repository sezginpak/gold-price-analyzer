"""
Simülasyon yönetim sistemi
Gerçek zamanlı sinyal takibi ve otomatik trading simülasyonu
"""
import asyncio
import logging
import json
from datetime import datetime, timedelta, time
from decimal import Decimal
from typing import Dict, List, Optional, Tuple, Any
from collections import defaultdict

from models.simulation import (
    SimulationConfig, SimulationPosition, SimulationStatus,
    StrategyType, PositionStatus, ExitReason, TimeframeCapital,
    SimulationSummary
)
from models.trading_signal import SignalType
from storage.sqlite_storage import SQLiteStorage
from utils.risk_management import KellyRiskManager

logger = logging.getLogger(__name__)


class SimulationManager:
    """Ana simülasyon yönetici sınıfı"""
    
    def __init__(self, storage: SQLiteStorage):
        self.storage = storage
        self.risk_manager = KellyRiskManager()
        self.active_simulations: Dict[int, SimulationConfig] = {}
        self.timeframe_capitals: Dict[int, Dict[str, TimeframeCapital]] = {}
        self.is_running = False
        
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
                    datetime.now(),
                    datetime.now(),
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
        if self.is_running:
            logger.warning("Simülasyon zaten çalışıyor")
            return
        
        self.is_running = True
        logger.info("Simülasyon sistemi başlatıldı")
        
        # Aktif simülasyonları yükle
        await self._load_active_simulations()
        
        # Ana döngü
        while self.is_running:
            try:
                await self._process_simulations()
                await asyncio.sleep(60)  # 1 dakika bekle
            except Exception as e:
                logger.error(f"Simülasyon döngü hatası: {str(e)}")
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
                    self.timeframe_capitals[simulation_id][timeframe] = TimeframeCapital(
                        timeframe=timeframe,
                        allocated_capital=Decimal(str(allocated)),
                        current_capital=Decimal(str(current)),
                        in_position=bool(in_position)
                    )
                
        except Exception as e:
            logger.error(f"Timeframe sermaye yükleme hatası: {str(e)}")
    
    async def _process_simulations(self):
        """Tüm aktif simülasyonları işle"""
        current_time = datetime.now()
        
        # Türkiye saatine çevir (UTC+3)
        tr_time = current_time.replace(hour=(current_time.hour + 3) % 24)
        
        # İşlem saatleri kontrolü
        if not self._is_trading_hours(tr_time):
            # Sadece açık pozisyonları kontrol et
            await self._check_open_positions()
            return
        
        # Her simülasyon için
        for sim_id, config in self.active_simulations.items():
            try:
                await self._process_single_simulation(sim_id, config, current_time)
            except Exception as e:
                logger.error(f"Simülasyon {sim_id} işleme hatası: {str(e)}")
    
    def _is_trading_hours(self, current_time: datetime) -> bool:
        """İşlem saatleri içinde mi?"""
        current_hour = current_time.hour
        # Varsayılan 09:00-17:00
        return 9 <= current_hour < 17
    
    async def _process_single_simulation(
        self,
        sim_id: int,
        config: SimulationConfig,
        current_time: datetime
    ):
        """Tek bir simülasyonu işle"""
        # Son sinyalleri al
        signals = await self._get_latest_signals()
        
        # Her timeframe için
        for timeframe, signal_data in signals.items():
            if timeframe not in self.timeframe_capitals[sim_id]:
                continue
            
            tf_capital = self.timeframe_capitals[sim_id][timeframe]
            
            # Açık pozisyon varsa kontrol et
            if tf_capital.in_position and tf_capital.open_position_id:
                await self._check_position_exit(
                    sim_id, tf_capital.open_position_id, signal_data
                )
            else:
                # Yeni pozisyon açma kontrolü
                if self._should_open_position(config, signal_data, timeframe):
                    await self._open_position(
                        sim_id, config, timeframe, signal_data, tf_capital
                    )
        
        # Günlük performansı güncelle
        await self._update_daily_performance(sim_id)
    
    async def _get_latest_signals(self) -> Dict[str, Dict]:
        """Son sinyalleri al"""
        try:
            signals = {}
            timeframes = ['15m', '1h', '4h', '1d']
            
            for timeframe in timeframes:
                # Son hybrid analizi al
                analysis = self.storage.get_latest_hybrid_analysis(timeframe)
                if analysis:
                    signals[timeframe] = {
                        'signal': analysis.get('signal'),
                        'confidence': analysis.get('confidence', 0),
                        'price': analysis.get('gram_price'),
                        'indicators': {
                            'rsi': analysis.get('gram_analysis', {}).get('rsi'),
                            'macd': analysis.get('gram_analysis', {}).get('macd'),
                            'bb': analysis.get('gram_analysis', {}).get('bollinger_bands'),
                            'atr': analysis.get('gram_analysis', {}).get('atr'),
                            'patterns': analysis.get('pattern_analysis', {})
                        },
                        'stop_loss': analysis.get('stop_loss'),
                        'take_profit': analysis.get('take_profit'),
                        'position_size': analysis.get('position_size')
                    }
            
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
        if not signal_data or not signal_data.get('signal'):
            return False
        
        # Sadece BUY/SELL sinyalleri
        if signal_data['signal'] not in ['BUY', 'SELL']:
            return False
        
        # Güven skoru kontrolü
        confidence = signal_data.get('confidence', 0)
        if confidence < config.min_confidence:
            return False
        
        # Strateji tipine göre ek filtreler
        if not self._apply_strategy_filter(config, signal_data, timeframe):
            return False
        
        return True
    
    def _apply_strategy_filter(
        self,
        config: SimulationConfig,
        signal_data: Dict,
        timeframe: str
    ) -> bool:
        """Strateji tipine göre sinyal filtrele"""
        strategy = config.strategy_type
        indicators = signal_data.get('indicators', {})
        
        if strategy == StrategyType.MAIN:
            # Ana strateji - ek filtre yok
            return True
        
        elif strategy == StrategyType.CONSERVATIVE:
            # Sadece yüksek güvenli sinyaller
            return signal_data.get('confidence', 0) >= 0.7
        
        elif strategy == StrategyType.MOMENTUM:
            # RSI 30-70 dışında
            rsi = indicators.get('rsi')
            if rsi:
                return rsi < 30 or rsi > 70
            return False
        
        elif strategy == StrategyType.MEAN_REVERSION:
            # Bollinger band dışında
            bb = indicators.get('bb', {})
            if bb and signal_data.get('price'):
                upper = bb.get('upper')
                lower = bb.get('lower')
                price = signal_data['price']
                if upper and lower:
                    return price > upper or price < lower
            return False
        
        elif strategy == StrategyType.CONSENSUS:
            # TODO: 3+ gösterge uyumu kontrolü
            return True
        
        elif strategy == StrategyType.RISK_ADJUSTED:
            # TODO: Volatilite bazlı filtreleme
            return True
        
        elif strategy == StrategyType.TIME_BASED:
            # Saate göre strateji değiştir
            hour = datetime.now().hour
            if 9 <= hour < 11:  # Momentum
                rsi = indicators.get('rsi')
                return rsi and (rsi < 30 or rsi > 70)
            elif 11 <= hour < 14:  # Mean reversion
                return True
            else:  # Conservative
                return signal_data.get('confidence', 0) >= 0.7
        
        return True
    
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
                today = datetime.now().date()
                
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
            if not atr or not atr.get('value'):
                logger.warning(f"ATR değeri bulunamadı {timeframe} için, pozisyon açılamıyor")
                return
            
            # Stop loss hesapla (1.5 x ATR)
            atr_value = Decimal(str(atr['value']))
            atr_pct = atr_value / current_price
            stop_distance = atr_pct * config.atr_multiplier_sl
            
            if signal_data['signal'] == 'BUY':
                stop_loss = current_price * (1 - stop_distance)
                take_profit = current_price * (1 + stop_distance * config.risk_reward_ratio)
            else:
                stop_loss = current_price * (1 + stop_distance)
                take_profit = current_price * (1 - stop_distance * config.risk_reward_ratio)
            
            # Pozisyon boyutu hesapla
            risk_amount = tf_capital.current_capital * Decimal(str(config.max_risk))
            position_value = risk_amount / stop_distance
            position_size = position_value / current_price  # gram cinsinden
            
            # Spread ve komisyon
            spread_cost = config.spread
            commission = position_value * Decimal(str(config.commission_rate))
            
            # Pozisyon oluştur
            position = SimulationPosition(
                simulation_id=sim_id,
                timeframe=timeframe,
                position_type="LONG" if signal_data['signal'] == 'BUY' else "SHORT",
                status=PositionStatus.OPEN,
                entry_time=datetime.now(),
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
            tf_capital.last_trade_time = datetime.now()
            
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
                return
            
            current_price = Decimal(str(current_signal['price']))
            exit_reason = None
            exit_price = current_price
            
            # 1. Stop loss kontrolü
            if position.position_type == "LONG":
                if current_price <= position.stop_loss:
                    exit_reason = ExitReason.STOP_LOSS
                    exit_price = position.stop_loss
            else:
                if current_price >= position.stop_loss:
                    exit_reason = ExitReason.STOP_LOSS
                    exit_price = position.stop_loss
            
            # 2. Take profit kontrolü
            if not exit_reason:
                if position.position_type == "LONG":
                    if current_price >= position.take_profit:
                        exit_reason = ExitReason.TAKE_PROFIT
                        exit_price = position.take_profit
                else:
                    if current_price <= position.take_profit:
                        exit_reason = ExitReason.TAKE_PROFIT
                        exit_price = position.take_profit
            
            # 3. Trailing stop kontrolü
            if not exit_reason and position.trailing_stop:
                if position.position_type == "LONG":
                    if current_price <= position.trailing_stop:
                        exit_reason = ExitReason.TRAILING_STOP
                        exit_price = position.trailing_stop
                else:
                    if current_price >= position.trailing_stop:
                        exit_reason = ExitReason.TRAILING_STOP
                        exit_price = position.trailing_stop
            
            # 4. Trailing stop aktivasyonu
            if not exit_reason:
                config = self.active_simulations[sim_id]
                if position.should_activate_trailing_stop(
                    current_price,
                    config.trailing_stop_activation
                ):
                    new_trailing = position.calculate_trailing_stop(
                        current_price,
                        config.trailing_stop_distance
                    )
                    
                    # Mevcut trailing stop'tan daha iyi mi?
                    if not position.trailing_stop or (
                        position.position_type == "LONG" and new_trailing > position.trailing_stop
                    ) or (
                        position.position_type == "SHORT" and new_trailing < position.trailing_stop
                    ):
                        position.trailing_stop = new_trailing
                        await self._update_position_trailing_stop(position_id, new_trailing)
                        logger.info(f"Trailing stop güncellendi: {new_trailing}")
            
            # 5. Ters sinyal kontrolü
            if not exit_reason:
                new_signal = current_signal.get('signal')
                if new_signal:
                    if (position.position_type == "LONG" and new_signal == "SELL") or \
                       (position.position_type == "SHORT" and new_signal == "BUY"):
                        exit_reason = ExitReason.REVERSE_SIGNAL
            
            # 6. Güven düşüşü kontrolü
            if not exit_reason:
                if current_signal.get('confidence', 1) < 0.4:
                    exit_reason = ExitReason.CONFIDENCE_DROP
            
            # 7. Zaman limiti kontrolü
            if not exit_reason:
                config = self.active_simulations[sim_id]
                time_limit = config.time_limits.get(position.timeframe, 168)
                holding_hours = (datetime.now() - position.entry_time).total_seconds() / 3600
                if holding_hours >= time_limit:
                    exit_reason = ExitReason.TIME_LIMIT
            
            # Pozisyonu kapat
            if exit_reason:
                await self._close_position(
                    sim_id,
                    position,
                    exit_price,
                    exit_reason,
                    current_signal.get('indicators')
                )
                
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
            
            # PnL hesapla
            if position.position_type == "LONG":
                gross_pnl = (exit_price - position.entry_price) * position.position_size
            else:
                gross_pnl = (position.entry_price - exit_price) * position.position_size
            
            # Net PnL (tüm maliyetler dahil)
            total_costs = (position.entry_spread + position.entry_commission + 
                          exit_spread + exit_commission)
            net_pnl = gross_pnl - total_costs
            pnl_pct = (net_pnl / position.allocated_capital) * 100
            
            # Pozisyonu güncelle
            position.status = PositionStatus.CLOSED
            position.exit_time = datetime.now()
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
            
            # Timeframe sermayesini güncelle
            tf_capital = self.timeframe_capitals[sim_id][position.timeframe]
            tf_capital.update_capital(net_pnl)
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
            latest = self.storage.get_latest_price_data()
            if latest:
                return Decimal(str(latest['gram_altin_satis']))
            return None
        except Exception as e:
            logger.error(f"Fiyat alma hatası: {str(e)}")
            return None
    
    # Veritabanı işlemleri
    async def _save_position(self, position: SimulationPosition) -> int:
        """Pozisyonu veritabanına kaydet"""
        with self.storage.get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO sim_positions (
                    simulation_id, timeframe, position_type, status,
                    entry_time, entry_price, entry_spread, entry_commission,
                    position_size, allocated_capital, risk_amount,
                    stop_loss, take_profit, entry_confidence, entry_indicators
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                position.simulation_id,
                position.timeframe,
                position.position_type,
                position.status.value,
                position.entry_time,
                float(position.entry_price),
                float(position.entry_spread),
                float(position.entry_commission),
                float(position.position_size),
                float(position.allocated_capital),
                float(position.risk_amount),
                float(position.stop_loss),
                float(position.take_profit),
                position.entry_confidence,
                json.dumps(position.entry_indicators)
            ))
            
            conn.commit()
            return cursor.lastrowid
    
    async def _get_position(self, position_id: int) -> Optional[SimulationPosition]:
        """Pozisyonu veritabanından al"""
        with self.storage.get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("SELECT * FROM sim_positions WHERE id = ?", (position_id,))
            row = cursor.fetchone()
        
        if row:
            # Row'dan SimulationPosition oluştur
            col_names = [desc[0] for desc in cursor.description]
            data = dict(zip(col_names, row))
            
            position = SimulationPosition(
                id=data['id'],
                simulation_id=data['simulation_id'],
                timeframe=data['timeframe'],
                position_type=data['position_type'],
                status=PositionStatus(data['status']),
                entry_time=datetime.fromisoformat(data['entry_time']),
                entry_price=Decimal(str(data['entry_price'])),
                entry_spread=Decimal(str(data['entry_spread'])),
                entry_commission=Decimal(str(data['entry_commission'])),
                position_size=Decimal(str(data['position_size'])),
                allocated_capital=Decimal(str(data['allocated_capital'])),
                risk_amount=Decimal(str(data['risk_amount'])),
                stop_loss=Decimal(str(data['stop_loss'])),
                take_profit=Decimal(str(data['take_profit'])),
                entry_confidence=data['entry_confidence']
            )
            
            # Opsiyonel alanlar
            if data.get('trailing_stop'):
                position.trailing_stop = Decimal(str(data['trailing_stop']))
            if data.get('max_profit'):
                position.max_profit = Decimal(str(data['max_profit']))
            if data.get('entry_indicators'):
                position.entry_indicators = json.loads(data['entry_indicators'])
            
            return position
        
        return None
    
    async def _update_position_trailing_stop(self, position_id: int, trailing_stop: Decimal):
        """Trailing stop güncelle"""
        with self.storage.get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                UPDATE sim_positions
                SET trailing_stop = ?, updated_at = ?
                WHERE id = ?
            """, (float(trailing_stop), datetime.now(), position_id))
            
            conn.commit()
    
    async def _update_position_close(self, position: SimulationPosition):
        """Pozisyon kapanışını güncelle"""
        with self.storage.get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                UPDATE sim_positions
                SET status = ?, exit_time = ?, exit_price = ?,
                    exit_spread = ?, exit_commission = ?, exit_reason = ?,
                    gross_profit_loss = ?, net_profit_loss = ?,
                    profit_loss_pct = ?, holding_period_minutes = ?,
                    exit_indicators = ?, updated_at = ?
                WHERE id = ?
            """, (
            position.status.value,
            position.exit_time,
            float(position.exit_price),
            float(position.exit_spread),
            float(position.exit_commission),
            position.exit_reason.value,
            float(position.gross_profit_loss),
            float(position.net_profit_loss),
            position.profit_loss_pct,
            position.holding_period_minutes,
            json.dumps(position.exit_indicators) if position.exit_indicators else None,
            datetime.now(),
            position.id
        ))
        
        conn.commit()
    
    async def _update_timeframe_capital(
        self,
        sim_id: int,
        timeframe: str,
        tf_capital: TimeframeCapital
    ):
        """Timeframe sermayesini güncelle"""
        with self.storage.get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                UPDATE sim_timeframe_capital
                SET current_capital = ?, in_position = ?, last_update = ?
                WHERE simulation_id = ? AND timeframe = ?
            """, (
                float(tf_capital.current_capital),
                int(tf_capital.in_position),
                datetime.now(),
                sim_id,
                timeframe
            ))
            
            conn.commit()
    
    async def _update_simulation_stats(self, sim_id: int):
        """Simülasyon istatistiklerini güncelle"""
        with self.storage.get_connection() as conn:
            cursor = conn.cursor()
            
            # Toplam sermayeyi hesapla
        total_capital = sum(
            tf.current_capital 
            for tf in self.timeframe_capitals[sim_id].values()
        )
        
        # İşlem istatistikleri
        cursor.execute("""
            SELECT 
                COUNT(*) as total_trades,
                SUM(CASE WHEN net_profit_loss > 0 THEN 1 ELSE 0 END) as winning_trades,
                SUM(CASE WHEN net_profit_loss < 0 THEN 1 ELSE 0 END) as losing_trades,
                AVG(CASE WHEN net_profit_loss > 0 THEN net_profit_loss ELSE NULL END) as avg_win,
                AVG(CASE WHEN net_profit_loss < 0 THEN ABS(net_profit_loss) ELSE NULL END) as avg_loss,
                SUM(net_profit_loss) as total_pnl
            FROM sim_positions
            WHERE simulation_id = ? AND status = 'CLOSED'
        """, (sim_id,))
        
        stats = cursor.fetchone()
        
        # Metrikleri hesapla
        total_trades = stats[0] or 0
        winning_trades = stats[1] or 0
        losing_trades = stats[2] or 0
        avg_win = stats[3] or 0
        avg_loss = stats[4] or 0
        total_pnl = stats[5] or 0
        
        win_rate = winning_trades / total_trades if total_trades > 0 else 0
        profit_factor = (winning_trades * avg_win) / (losing_trades * avg_loss) if losing_trades > 0 and avg_loss > 0 else 0
        
        # Simülasyonu güncelle
        cursor.execute("""
            UPDATE simulations
            SET current_capital = ?, total_trades = ?, winning_trades = ?,
                losing_trades = ?, total_profit_loss = ?, total_profit_loss_pct = ?,
                win_rate = ?, profit_factor = ?, avg_win = ?, avg_loss = ?,
                last_update = ?
            WHERE id = ?
        """, (
            float(total_capital),
            total_trades,
            winning_trades,
            losing_trades,
            float(total_pnl),
            float((total_capital - 1000) / 10),  # %
            win_rate,
            profit_factor,
            float(avg_win),
            float(avg_loss),
            datetime.now(),
            sim_id
        ))
        
        conn.commit()
    
    async def _update_daily_performance(self, sim_id: int):
        """Günlük performansı güncelle"""
        try:
            today = datetime.now().date()
            
            with self.storage.get_connection() as conn:
                cursor = conn.cursor()
                
                # Toplam sermayeyi hesapla
                tf_capitals = self.timeframe_capitals.get(sim_id, {})
                if not tf_capitals:
                    # Eğer timeframe capitals yoksa, varsayılan dağıtımı kullan
                    self._init_timeframe_capitals(sim_id, self.active_simulations[sim_id])
                    tf_capitals = self.timeframe_capitals.get(sim_id, {})
                
                total_capital = sum(
                    float(tf.current_capital) 
                    for tf in tf_capitals.values()
                ) or 1000.0  # Varsayılan sermaye
                
                # Günün başlangıç sermayesini al (veya varsayılan)
                cursor.execute("""
                    SELECT ending_capital FROM sim_daily_performance
                    WHERE simulation_id = ? AND date < ?
                    ORDER BY date DESC LIMIT 1
                """, (sim_id, today))
                
                row = cursor.fetchone()
                starting_capital = row[0] if row else 1000.0
                
                # Bugünkü işlemleri al - timeframe bazlı
                cursor.execute("""
                    SELECT 
                        COUNT(*) as total,
                        SUM(CASE WHEN net_profit_loss > 0 THEN 1 ELSE 0 END) as wins,
                        SUM(CASE WHEN net_profit_loss < 0 THEN 1 ELSE 0 END) as losses,
                        SUM(net_profit_loss) as total_pnl,
                        SUM(CASE WHEN timeframe = '15m' THEN 1 ELSE 0 END) as trades_15m,
                        SUM(CASE WHEN timeframe = '1h' THEN 1 ELSE 0 END) as trades_1h,
                        SUM(CASE WHEN timeframe = '4h' THEN 1 ELSE 0 END) as trades_4h,
                        SUM(CASE WHEN timeframe = '1d' THEN 1 ELSE 0 END) as trades_1d,
                        SUM(CASE WHEN timeframe = '15m' THEN net_profit_loss ELSE 0 END) as pnl_15m,
                        SUM(CASE WHEN timeframe = '1h' THEN net_profit_loss ELSE 0 END) as pnl_1h,
                        SUM(CASE WHEN timeframe = '4h' THEN net_profit_loss ELSE 0 END) as pnl_4h,
                        SUM(CASE WHEN timeframe = '1d' THEN net_profit_loss ELSE 0 END) as pnl_1d
                    FROM sim_positions
                    WHERE simulation_id = ? 
                    AND DATE(exit_time) = ?
                    AND status = 'CLOSED'
                """, (sim_id, today))
                
                stats = cursor.fetchone()
                
                # Değerleri al
                total_trades = stats[0] or 0
                winning_trades = stats[1] or 0
                losing_trades = stats[2] or 0
                daily_pnl = stats[3] or 0.0
                
                # Mevcut kaydı kontrol et
                cursor.execute("""
                    SELECT id FROM sim_daily_performance
                    WHERE simulation_id = ? AND date = ?
                """, (sim_id, today))
                
                if cursor.fetchone():
                    # Güncelle
                    cursor.execute("""
                        UPDATE sim_daily_performance
                        SET ending_capital = ?, daily_pnl = ?, daily_pnl_pct = ?,
                            total_trades = ?, winning_trades = ?, losing_trades = ?,
                            trades_15m = ?, trades_1h = ?, trades_4h = ?, trades_1d = ?,
                            pnl_15m = ?, pnl_1h = ?, pnl_4h = ?, pnl_1d = ?
                        WHERE simulation_id = ? AND date = ?
                    """, (
                        float(total_capital), float(daily_pnl), 
                        float(daily_pnl / starting_capital * 100) if starting_capital > 0 else 0,
                        total_trades, winning_trades, losing_trades,
                        stats[4], stats[5], stats[6], stats[7],
                        float(stats[8] or 0), float(stats[9] or 0), float(stats[10] or 0), float(stats[11] or 0),
                        sim_id, today
                    ))
                else:
                    # Yeni kayıt
                    cursor.execute("""
                        INSERT INTO sim_daily_performance (
                            simulation_id, date, starting_capital, ending_capital,
                            daily_pnl, daily_pnl_pct, total_trades, winning_trades, losing_trades,
                            trades_15m, trades_1h, trades_4h, trades_1d,
                            pnl_15m, pnl_1h, pnl_4h, pnl_1d
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        sim_id, today, float(starting_capital), float(total_capital),
                        float(daily_pnl), float(daily_pnl / starting_capital * 100) if starting_capital > 0 else 0,
                        total_trades, winning_trades, losing_trades,
                        stats[4], stats[5], stats[6], stats[7],
                        float(stats[8]), float(stats[9]), float(stats[10]), float(stats[11])
                    ))
                
                conn.commit()
                
        except Exception as e:
            logger.error(f"Günlük performans güncelleme hatası: {str(e)}")
    
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
                today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
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
                running_days=(datetime.now() - datetime.fromisoformat(sim_data['start_date'])).days,
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