"""
Pozisyon yönetimi modülü
"""
import logging
from decimal import Decimal
from typing import Optional, Dict
import json

from utils.timezone import utc_now, parse_timestamp
from models.simulation import (
    SimulationPosition, 
    PositionStatus,
    ExitReason,
    SimulationConfig
)
from storage.sqlite_storage import SQLiteStorage

logger = logging.getLogger("gold_analyzer")


class PositionManager:
    """Pozisyon açma, kapatma ve yönetim işlemleri"""
    
    def __init__(self, storage: SQLiteStorage):
        self.storage = storage
    
    async def save_position(self, position: SimulationPosition) -> int:
        """Pozisyonu veritabanına kaydet"""
        try:
            with self.storage.get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    INSERT INTO sim_positions (
                        simulation_id, timeframe, position_type, status,
                        entry_signal_id, entry_time, entry_price, entry_spread, entry_commission,
                        position_size, allocated_capital, risk_amount,
                        stop_loss, take_profit, trailing_stop,
                        entry_confidence, entry_indicators
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    position.simulation_id,
                    position.timeframe,
                    position.position_type,
                    position.status.value,
                    position.entry_signal_id,
                    position.entry_time,
                    float(position.entry_price),
                    float(position.entry_spread),
                    float(position.entry_commission),
                    float(position.position_size),
                    float(position.allocated_capital),
                    float(position.risk_amount),
                    float(position.stop_loss),
                    float(position.take_profit),
                    float(position.trailing_stop) if position.trailing_stop else None,
                    position.entry_confidence,
                    json.dumps(position.entry_indicators) if position.entry_indicators else None
                ))
                
                conn.commit()
                return cursor.lastrowid
        
        except Exception as e:
            logger.error(f"Pozisyon kaydetme hatası: {str(e)}")
            raise
    
    async def get_position(self, position_id: int) -> Optional[SimulationPosition]:
        """Pozisyon bilgilerini al"""
        with self.storage.get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT * FROM sim_positions WHERE id = ?
            """, (position_id,))
            
            row = cursor.fetchone()
            if row:
                # SQLite Row nesnesini dictionary'e çevir
                col_names = [desc[0] for desc in cursor.description]
                data = dict(zip(col_names, row))
                
                position = SimulationPosition(
                    id=data['id'],
                    simulation_id=data['simulation_id'],
                    timeframe=data['timeframe'],
                    position_type=data['position_type'],
                    status=PositionStatus(data['status']),
                    entry_time=parse_timestamp(data['entry_time']),
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
    
    async def update_position_trailing_stop(self, position_id: int, trailing_stop: Decimal):
        """Trailing stop güncelle"""
        with self.storage.get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                UPDATE sim_positions
                SET trailing_stop = ?, updated_at = ?
                WHERE id = ?
            """, (float(trailing_stop), utc_now(), position_id))
            
            conn.commit()
    
    async def update_position_close(self, position: SimulationPosition):
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
                float(position.profit_loss_pct),
                position.holding_period_minutes,
                json.dumps(position.exit_indicators) if position.exit_indicators else None,
                utc_now(),
                position.id
            ))
            
            conn.commit()
    
    def calculate_position_size(
        self, 
        config: SimulationConfig,
        available_capital: Decimal,
        current_price: Decimal,
        atr: Dict
    ) -> Decimal:
        """Pozisyon büyüklüğünü hesapla"""
        try:
            # ATR bazlı risk hesaplama
            atr_value = Decimal(str(atr.get('atr', 0)))
            if atr_value <= 0:
                logger.warning("ATR değeri 0 veya negatif, varsayılan risk kullanılıyor")
                atr_value = current_price * Decimal("0.01")  # %1
            
            # Risk miktarını hesapla (gram cinsinden)
            risk_amount_gram = available_capital * Decimal(str(config.max_risk))
            
            # ATR bazlı stop distance (fiyatın yüzdesi olarak)
            stop_distance_ratio = (atr_value * Decimal(str(config.atr_multiplier_sl))) / current_price
            
            # Pozisyon büyüklüğü = Risk miktarı / Stop yüzdesi
            # Örnek: 5 gram risk / 0.015 (%1.5 stop) = 333 gram pozisyon
            position_size = risk_amount_gram / stop_distance_ratio
            
            # Maksimum pozisyon kontrolü (sermayenin %20'si) - daha konservatif
            max_position = available_capital * Decimal("0.2")
            position_size = min(position_size, max_position)
            
            logger.debug(f"Position size calculation: capital={available_capital}, risk={risk_amount_gram}g, "
                        f"stop_ratio={stop_distance_ratio:.4f}, raw_size={risk_amount_gram/stop_distance_ratio:.2f}g, "
                        f"final_size={position_size:.2f}g")
            
            return position_size
            
        except Exception as e:
            logger.error(f"Pozisyon büyüklüğü hesaplama hatası: {str(e)}")
            # Güvenli bir varsayılan değer (gram cinsinden)
            return available_capital * Decimal("0.02")  # Sermayenin %2'si kadar gram
    
    def calculate_stop_loss(
        self,
        position_type: str,
        entry_price: Decimal,
        atr: Dict,
        config: SimulationConfig
    ) -> Decimal:
        """Stop loss hesapla"""
        atr_value = Decimal(str(atr.get('atr', 0)))
        if atr_value <= 0:
            atr_value = entry_price * Decimal("0.01")
        
        stop_distance = atr_value * Decimal(str(config.atr_multiplier_sl))
        
        if position_type == "LONG":
            return entry_price - stop_distance
        else:
            return entry_price + stop_distance
    
    def calculate_take_profit(
        self,
        position_type: str,
        entry_price: Decimal,
        stop_loss: Decimal,
        config: SimulationConfig
    ) -> Decimal:
        """Take profit hesapla"""
        risk = abs(entry_price - stop_loss)
        reward = risk * Decimal(str(config.risk_reward_ratio))
        
        if position_type == "LONG":
            return entry_price + reward
        else:
            return entry_price - reward
    
    async def get_open_positions_by_simulation(self, simulation_id: int) -> list:
        """Simülasyonun açık pozisyonlarını getir"""
        with self.storage.get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT id, timeframe FROM sim_positions
                WHERE simulation_id = ? AND status = 'OPEN'
            """, (simulation_id,))
            
            return cursor.fetchall()