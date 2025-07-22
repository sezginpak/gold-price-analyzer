"""
Kelly Criterion Tabanlı Risk Yönetimi
Optimal pozisyon boyutlandırma ve risk kontrolü
Altın ticareti için özelleştirilmiş güvenli Kelly yaklaşımı
"""

import pandas as pd
import numpy as np
from typing import Dict, Tuple, Optional, List
from decimal import Decimal
import logging
from collections import deque

logger = logging.getLogger(__name__)


class KellyRiskManager:
    """
    Kelly Criterion ile pozisyon boyutlandırma ve risk yönetimi
    Fractional Kelly yaklaşımı ile güvenli ticaret
    """
    
    def __init__(self, 
                 kelly_fraction: float = 0.25,
                 max_risk_per_trade: float = 0.02,
                 max_portfolio_risk: float = 0.06,
                 min_trades_for_kelly: int = 30):
        """
        Risk yönetimi parametreleri
        
        Args:
            kelly_fraction: Kelly oranının kullanılacak kısmı (0.25 = %25 Kelly)
            max_risk_per_trade: Tek işlem için maksimum risk (0.02 = %2)
            max_portfolio_risk: Toplam portföy riski limiti (0.06 = %6)
            min_trades_for_kelly: Kelly hesaplaması için minimum işlem sayısı
        """
        self.kelly_fraction = kelly_fraction
        self.max_risk_per_trade = max_risk_per_trade
        self.max_portfolio_risk = max_portfolio_risk
        self.min_trades_for_kelly = min_trades_for_kelly
        
        # İşlem geçmişi (Kelly hesaplaması için)
        self.trade_history = deque(maxlen=100)
        
        # Risk metrikleri
        self.current_drawdown = 0.0
        self.max_drawdown = 0.0
        self.peak_capital = 0.0
        
    def calculate_kelly_percentage(self, 
                                 win_rate: float, 
                                 avg_win_loss_ratio: float) -> float:
        """
        Kelly yüzdesini hesapla
        
        Formula: f = (p * b - q) / b
        f: Optimal yatırım oranı
        p: Kazanma olasılığı
        q: Kaybetme olasılığı (1-p)
        b: Kazanç/kayıp oranı
        
        Args:
            win_rate: Kazanma oranı (0-1 arası)
            avg_win_loss_ratio: Ortalama kazanç/kayıp oranı
            
        Returns:
            Kelly yüzdesi (0-1 arası)
        """
        try:
            if win_rate <= 0 or win_rate >= 1:
                logger.warning(f"Geçersiz win_rate: {win_rate}")
                return 0.0
                
            if avg_win_loss_ratio <= 0:
                logger.warning(f"Geçersiz win/loss ratio: {avg_win_loss_ratio}")
                return 0.0
            
            # Kelly formülü
            q = 1 - win_rate
            kelly_percentage = (win_rate * avg_win_loss_ratio - q) / avg_win_loss_ratio
            
            # Negatif Kelly = ticaret yapma
            if kelly_percentage < 0:
                return 0.0
            
            # Fractional Kelly uygula (güvenlik için)
            safe_kelly = kelly_percentage * self.kelly_fraction
            
            # Maksimum limiti uygula
            return min(safe_kelly, self.max_risk_per_trade)
            
        except Exception as e:
            logger.error(f"Kelly hesaplama hatası: {str(e)}")
            return self.max_risk_per_trade * 0.5  # Güvenli varsayılan
    
    def calculate_position_size(self,
                              capital: float,
                              entry_price: float,
                              stop_loss_price: float,
                              confidence: float = 0.7) -> Dict:
        """
        Pozisyon boyutunu hesapla
        
        Args:
            capital: Mevcut sermaye
            entry_price: Giriş fiyatı
            stop_loss_price: Stop loss fiyatı
            confidence: Sinyal güven skoru (0-1)
            
        Returns:
            Pozisyon detayları dictionary
        """
        try:
            # Risk miktarını hesapla
            price_risk = abs(entry_price - stop_loss_price) / entry_price
            
            # İşlem geçmişinden istatistikleri al
            stats = self.calculate_trading_stats()
            
            # Kelly yüzdesini hesapla
            if stats['total_trades'] >= self.min_trades_for_kelly:
                kelly_pct = self.calculate_kelly_percentage(
                    stats['win_rate'],
                    stats['avg_win_loss_ratio']
                )
            else:
                # Yeterli veri yok, konservatif yaklaş
                kelly_pct = self.max_risk_per_trade * 0.3
            
            # Güven skoruna göre ayarla
            adjusted_risk = kelly_pct * confidence
            
            # Maksimum risk limitini uygula
            final_risk = min(adjusted_risk, self.max_risk_per_trade)
            
            # Risk miktarı (para birimi)
            risk_amount = capital * final_risk
            
            # Pozisyon boyutu
            position_size = risk_amount / price_risk
            
            # Lot hesaplama (gram altın için)
            lots = position_size / entry_price
            
            return {
                'position_size': round(position_size, 2),
                'lots': round(lots, 3),
                'risk_amount': round(risk_amount, 2),
                'risk_percentage': round(final_risk * 100, 2),
                'kelly_percentage': round(kelly_pct * 100, 2),
                'confidence_adjusted': round(adjusted_risk * 100, 2),
                'price_risk': round(price_risk * 100, 2),
                'max_loss': round(risk_amount, 2),
                'position_value': round(lots * entry_price, 2)
            }
            
        except Exception as e:
            logger.error(f"Pozisyon boyutu hesaplama hatası: {str(e)}")
            # Güvenli varsayılan
            safe_risk = capital * self.max_risk_per_trade * 0.5
            safe_lots = safe_risk / (price_risk * entry_price)
            
            return {
                'position_size': round(safe_risk / price_risk, 2),
                'lots': round(safe_lots, 3),
                'risk_amount': round(safe_risk, 2),
                'risk_percentage': round(self.max_risk_per_trade * 50, 2),
                'error': str(e)
            }
    
    def add_trade_result(self, 
                        entry_price: float,
                        exit_price: float,
                        position_size: float,
                        trade_type: str):
        """
        İşlem sonucunu geçmişe ekle
        
        Args:
            entry_price: Giriş fiyatı
            exit_price: Çıkış fiyatı
            position_size: Pozisyon büyüklüğü
            trade_type: 'BUY' veya 'SELL'
        """
        try:
            if trade_type == 'BUY':
                profit_loss = (exit_price - entry_price) / entry_price
            else:  # SELL
                profit_loss = (entry_price - exit_price) / entry_price
            
            self.trade_history.append({
                'profit_loss': profit_loss,
                'position_size': position_size,
                'trade_type': trade_type,
                'entry': entry_price,
                'exit': exit_price
            })
            
        except Exception as e:
            logger.error(f"İşlem kaydı hatası: {str(e)}")
    
    def calculate_trading_stats(self) -> Dict:
        """
        İşlem istatistiklerini hesapla
        
        Returns:
            İstatistikler dictionary
        """
        try:
            if not self.trade_history:
                return {
                    'total_trades': 0,
                    'win_rate': 0.5,
                    'avg_win_loss_ratio': 1.5,
                    'profit_factor': 1.0,
                    'sharpe_ratio': 0.0
                }
            
            trades = list(self.trade_history)
            profits = [t['profit_loss'] for t in trades]
            
            wins = [p for p in profits if p > 0]
            losses = [p for p in profits if p < 0]
            
            win_rate = len(wins) / len(trades) if trades else 0.5
            
            avg_win = np.mean(wins) if wins else 0
            avg_loss = abs(np.mean(losses)) if losses else 1
            
            avg_win_loss_ratio = avg_win / avg_loss if avg_loss > 0 else 1.5
            
            # Profit factor
            total_wins = sum(wins) if wins else 0
            total_losses = abs(sum(losses)) if losses else 1
            profit_factor = total_wins / total_losses if total_losses > 0 else 1.0
            
            # Sharpe ratio (basitleştirilmiş)
            if len(profits) > 1:
                returns_std = np.std(profits)
                sharpe_ratio = (np.mean(profits) / returns_std) * np.sqrt(252) if returns_std > 0 else 0
            else:
                sharpe_ratio = 0.0
            
            return {
                'total_trades': len(trades),
                'win_rate': round(win_rate, 3),
                'avg_win_loss_ratio': round(avg_win_loss_ratio, 2),
                'profit_factor': round(profit_factor, 2),
                'sharpe_ratio': round(sharpe_ratio, 2),
                'avg_win': round(avg_win * 100, 2),
                'avg_loss': round(avg_loss * 100, 2)
            }
            
        except Exception as e:
            logger.error(f"İstatistik hesaplama hatası: {str(e)}")
            return {
                'total_trades': 0,
                'win_rate': 0.5,
                'avg_win_loss_ratio': 1.5,
                'profit_factor': 1.0,
                'sharpe_ratio': 0.0
            }
    
    def update_drawdown(self, current_capital: float):
        """
        Drawdown metriklerini güncelle
        
        Args:
            current_capital: Mevcut sermaye
        """
        try:
            # Peak capital güncelle
            if current_capital > self.peak_capital:
                self.peak_capital = current_capital
                self.current_drawdown = 0.0
            else:
                # Drawdown hesapla
                self.current_drawdown = (self.peak_capital - current_capital) / self.peak_capital
                
                # Maximum drawdown güncelle
                if self.current_drawdown > self.max_drawdown:
                    self.max_drawdown = self.current_drawdown
                    
        except Exception as e:
            logger.error(f"Drawdown güncelleme hatası: {str(e)}")
    
    def check_risk_limits(self, 
                         open_positions: List[Dict],
                         capital: float) -> Dict:
        """
        Risk limitlerini kontrol et
        
        Args:
            open_positions: Açık pozisyonlar listesi
            capital: Mevcut sermaye
            
        Returns:
            Risk durumu dictionary
        """
        try:
            total_risk = 0.0
            position_count = len(open_positions)
            
            for pos in open_positions:
                # Her pozisyonun risk miktarını topla
                position_risk = pos.get('risk_amount', 0) / capital
                total_risk += position_risk
            
            # Risk limitleri kontrolü
            can_open_new = total_risk < self.max_portfolio_risk
            remaining_risk = max(0, self.max_portfolio_risk - total_risk)
            
            # Drawdown kontrolü
            drawdown_limit_reached = self.current_drawdown > 0.15  # %15 drawdown limiti
            
            return {
                'total_risk_percentage': round(total_risk * 100, 2),
                'position_count': position_count,
                'can_open_new_position': can_open_new and not drawdown_limit_reached,
                'remaining_risk_percentage': round(remaining_risk * 100, 2),
                'current_drawdown': round(self.current_drawdown * 100, 2),
                'max_drawdown': round(self.max_drawdown * 100, 2),
                'drawdown_limit_reached': drawdown_limit_reached,
                'risk_status': 'SAFE' if total_risk < 0.04 else 'CAUTION' if total_risk < 0.06 else 'HIGH'
            }
            
        except Exception as e:
            logger.error(f"Risk limit kontrolü hatası: {str(e)}")
            return {
                'total_risk_percentage': 0.0,
                'can_open_new_position': False,
                'error': str(e)
            }
    
    def get_risk_adjusted_confidence(self,
                                   base_confidence: float,
                                   market_volatility: float,
                                   pattern_strength: float = 0.5) -> float:
        """
        Piyasa koşullarına göre güven skorunu ayarla
        
        Args:
            base_confidence: Temel güven skoru
            market_volatility: Piyasa volatilitesi (ATR bazlı)
            pattern_strength: Pattern gücü (0-1)
            
        Returns:
            Ayarlanmış güven skoru
        """
        try:
            # Volatilite ayarlaması
            if market_volatility > 2.0:  # Yüksek volatilite
                volatility_factor = 0.8
            elif market_volatility > 1.5:
                volatility_factor = 0.9
            else:
                volatility_factor = 1.0
            
            # Pattern gücü bonusu
            pattern_bonus = pattern_strength * 0.2
            
            # Drawdown penaltisi
            drawdown_penalty = min(self.current_drawdown * 2, 0.3)
            
            # Final güven skoru
            adjusted_confidence = base_confidence * volatility_factor + pattern_bonus - drawdown_penalty
            
            return max(0.1, min(0.95, adjusted_confidence))
            
        except Exception as e:
            logger.error(f"Güven skoru ayarlama hatası: {str(e)}")
            return base_confidence * 0.8