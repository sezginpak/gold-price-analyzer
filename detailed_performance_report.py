#!/usr/bin/env python3
"""Detailed performance report with actionable insights"""

import sqlite3
import pandas as pd
from datetime import datetime, timedelta
import numpy as np
import json
from collections import defaultdict
import warnings
warnings.filterwarnings('ignore')

def generate_detailed_report():
    """Generate comprehensive performance report"""
    
    # Connect to database
    conn = sqlite3.connect('gold_prices_server.db')
    
    # Get all data
    df = pd.read_sql_query("""
        SELECT * FROM hybrid_analysis 
        ORDER BY timestamp DESC
    """, conn)
    
    # Get price data for simulation
    price_df = pd.read_sql_query("""
        SELECT timestamp, gram_altin 
        FROM price_data 
        WHERE gram_altin IS NOT NULL
        ORDER BY timestamp
    """, conn)
    
    conn.close()
    
    # Convert timestamps
    df['timestamp'] = pd.to_datetime(df['timestamp'], format='ISO8601')
    price_df['timestamp'] = pd.to_datetime(price_df['timestamp'], format='ISO8601')
    
    print("📊 DETAYLI PERFORMANS ANALİZ RAPORU")
    print("=" * 50)
    print(f"Analiz Dönemi: {df['timestamp'].min().strftime('%Y-%m-%d')} - {df['timestamp'].max().strftime('%Y-%m-%d')}")
    print(f"Toplam Gün: {(df['timestamp'].max() - df['timestamp'].min()).days}")
    print(f"Toplam Sinyal: {len(df)}")
    print(f"Toplam Fiyat Verisi: {len(price_df)}")
    
    # Simulate trading performance
    print("\n📈 SİMÜLE EDİLMİŞ TRADING PERFORMANSI")
    print("-" * 50)
    
    results = simulate_trading(df, price_df)
    
    # Overall performance
    print(f"\n💰 GENEL PERFORMANS METRİKLERİ:")
    print(f"- Başlangıç Sermaye: 1000 gram altın")
    print(f"- Final Sermaye: {results['final_capital']:.2f} gram")
    print(f"- Toplam Kar/Zarar: {results['total_pnl']:.2f} gram ({results['total_pnl_pct']:.2%})")
    print(f"- Toplam İşlem: {results['total_trades']}")
    print(f"- Kazançlı İşlem: {results['winning_trades']} ({results['win_rate']:.1%})")
    print(f"- Zararlı İşlem: {results['losing_trades']}")
    print(f"- Ortalama Kazanç: {results['avg_win']:.2f} gram")
    print(f"- Ortalama Zarar: {results['avg_loss']:.2f} gram")
    print(f"- Profit Factor: {results['profit_factor']:.2f}")
    print(f"- Max Drawdown: {results['max_drawdown']:.2%}")
    print(f"- Sharpe Ratio: {results['sharpe_ratio']:.2f}")
    
    # Timeframe breakdown
    print("\n⏰ TIMEFRAME BAZINDA PERFORMANS:")
    for tf, metrics in results['timeframe_metrics'].items():
        print(f"\n{tf}:")
        print(f"  - İşlem Sayısı: {metrics['trades']}")
        print(f"  - Başarı Oranı: {metrics['win_rate']:.1%}")
        print(f"  - Toplam Kar/Zarar: {metrics['pnl']:.2f} gram")
        print(f"  - Ortalama Kar/İşlem: {metrics['avg_pnl']:.2f} gram")
    
    # Signal quality analysis
    print("\n🎯 SİNYAL KALİTESİ ANALİZİ:")
    analyze_signal_quality(df, results)
    
    # Best and worst periods
    print("\n📊 EN İYİ/KÖTÜ DÖNEMLER:")
    analyze_periods(df, results)
    
    # Pattern analysis
    print("\n🔍 PATTERN ANALİZİ:")
    analyze_patterns(df)
    
    # Specific recommendations
    print("\n💡 SOMUT İYİLEŞTİRME ÖNERİLERİ:")
    generate_recommendations(df, results)
    
    # Create summary report
    create_summary_report(df, results)

def simulate_trading(df, price_df):
    """Simulate trading based on signals"""
    
    initial_capital = 1000  # gram altın
    capital_per_timeframe = initial_capital / 4  # 4 timeframe'e eşit dağıt
    
    results = {
        'trades': [],
        'capital_history': [initial_capital],
        'timeframe_metrics': defaultdict(lambda: {
            'trades': 0, 'wins': 0, 'losses': 0, 'pnl': 0
        })
    }
    
    # Sort by timestamp
    df = df.sort_values('timestamp')
    
    active_positions = {}
    capital = initial_capital
    
    for idx, signal in df.iterrows():
        if signal['signal'] in ['BUY', 'STRONG_BUY']:
            # Open long position
            entry_price = signal['gram_price']
            position_size = min(signal['position_size'], capital * 0.1)  # Max 10% per trade
            
            if capital >= position_size * entry_price:
                position_id = f"{signal['timeframe']}_{signal['timestamp']}"
                active_positions[position_id] = {
                    'entry_price': entry_price,
                    'size': position_size,
                    'stop_loss': signal['stop_loss'],
                    'take_profit': signal['take_profit'],
                    'timeframe': signal['timeframe'],
                    'entry_time': signal['timestamp'],
                    'confidence': signal['confidence']
                }
                capital -= position_size * entry_price
        
        elif signal['signal'] in ['SELL', 'STRONG_SELL'] and len(active_positions) > 0:
            # Close positions
            current_price = signal['gram_price']
            
            for pos_id in list(active_positions.keys()):
                pos = active_positions[pos_id]
                
                # Check exit conditions
                if (current_price <= pos['stop_loss'] or 
                    current_price >= pos['take_profit'] or
                    signal['timeframe'] == pos['timeframe']):
                    
                    # Calculate P&L
                    pnl = (current_price - pos['entry_price']) * pos['size']
                    capital += (pos['entry_price'] + pnl) * pos['size']
                    
                    # Record trade
                    trade_result = {
                        'entry_price': pos['entry_price'],
                        'exit_price': current_price,
                        'size': pos['size'],
                        'pnl': pnl,
                        'pnl_pct': pnl / (pos['entry_price'] * pos['size']),
                        'timeframe': pos['timeframe'],
                        'duration': (signal['timestamp'] - pos['entry_time']).total_seconds() / 3600,
                        'confidence': pos['confidence']
                    }
                    
                    results['trades'].append(trade_result)
                    
                    # Update timeframe metrics
                    tf_metrics = results['timeframe_metrics'][pos['timeframe']]
                    tf_metrics['trades'] += 1
                    tf_metrics['pnl'] += pnl
                    if pnl > 0:
                        tf_metrics['wins'] += 1
                    else:
                        tf_metrics['losses'] += 1
                    
                    # Remove position
                    del active_positions[pos_id]
        
        results['capital_history'].append(capital)
    
    # Calculate final metrics
    trades_df = pd.DataFrame(results['trades'])
    
    if len(trades_df) > 0:
        winning_trades = trades_df[trades_df['pnl'] > 0]
        losing_trades = trades_df[trades_df['pnl'] < 0]
        
        results['final_capital'] = capital
        results['total_pnl'] = capital - initial_capital
        results['total_pnl_pct'] = (capital - initial_capital) / initial_capital
        results['total_trades'] = len(trades_df)
        results['winning_trades'] = len(winning_trades)
        results['losing_trades'] = len(losing_trades)
        results['win_rate'] = len(winning_trades) / len(trades_df) if len(trades_df) > 0 else 0
        
        results['avg_win'] = winning_trades['pnl'].mean() if len(winning_trades) > 0 else 0
        results['avg_loss'] = losing_trades['pnl'].mean() if len(losing_trades) > 0 else 0
        
        total_wins = winning_trades['pnl'].sum() if len(winning_trades) > 0 else 0
        total_losses = abs(losing_trades['pnl'].sum()) if len(losing_trades) > 0 else 1
        results['profit_factor'] = total_wins / total_losses if total_losses > 0 else 0
        
        # Calculate drawdown
        capital_series = pd.Series(results['capital_history'])
        rolling_max = capital_series.expanding().max()
        drawdown = (capital_series - rolling_max) / rolling_max
        results['max_drawdown'] = drawdown.min()
        
        # Calculate Sharpe ratio (simplified)
        returns = trades_df['pnl_pct']
        results['sharpe_ratio'] = (returns.mean() / returns.std() * np.sqrt(252)) if returns.std() > 0 else 0
        
        # Calculate timeframe metrics
        for tf, metrics in results['timeframe_metrics'].items():
            if metrics['trades'] > 0:
                metrics['win_rate'] = metrics['wins'] / metrics['trades']
                metrics['avg_pnl'] = metrics['pnl'] / metrics['trades']
    else:
        # No trades
        results.update({
            'final_capital': initial_capital,
            'total_pnl': 0,
            'total_pnl_pct': 0,
            'total_trades': 0,
            'winning_trades': 0,
            'losing_trades': 0,
            'win_rate': 0,
            'avg_win': 0,
            'avg_loss': 0,
            'profit_factor': 0,
            'max_drawdown': 0,
            'sharpe_ratio': 0
        })
    
    return results

def analyze_signal_quality(df, results):
    """Analyze signal quality metrics"""
    
    # Confidence vs Success Rate
    high_conf_signals = df[df['confidence'] > 0.7]
    med_conf_signals = df[(df['confidence'] > 0.5) & (df['confidence'] <= 0.7)]
    low_conf_signals = df[df['confidence'] <= 0.5]
    
    print(f"- Yüksek Güvenli Sinyaller (>70%): {len(high_conf_signals)} ({len(high_conf_signals)/len(df)*100:.1f}%)")
    print(f"- Orta Güvenli Sinyaller (50-70%): {len(med_conf_signals)} ({len(med_conf_signals)/len(df)*100:.1f}%)")
    print(f"- Düşük Güvenli Sinyaller (<50%): {len(low_conf_signals)} ({len(low_conf_signals)/len(df)*100:.1f}%)")
    
    # Signal strength distribution
    print(f"\nSinyal Gücü Dağılımı:")
    for strength in ['STRONG', 'MODERATE', 'WEAK']:
        count = len(df[df['signal_strength'] == strength])
        print(f"- {strength}: {count} ({count/len(df)*100:.1f}%)")
    
    # R/R ratio analysis
    valid_rr = df[df['risk_reward_ratio'].notna() & (df['risk_reward_ratio'] > 0)]
    print(f"\nRisk/Reward Analizi:")
    print(f"- R/R > 3: {len(valid_rr[valid_rr['risk_reward_ratio'] > 3])} sinyaller")
    print(f"- R/R 2-3: {len(valid_rr[(valid_rr['risk_reward_ratio'] >= 2) & (valid_rr['risk_reward_ratio'] <= 3)])} sinyaller")
    print(f"- R/R < 2: {len(valid_rr[valid_rr['risk_reward_ratio'] < 2])} sinyaller")

def analyze_periods(df, results):
    """Analyze best and worst performing periods"""
    
    # Group by date
    df['date'] = df['timestamp'].dt.date
    daily_signals = df.groupby('date').agg({
        'signal': 'count',
        'confidence': 'mean',
        'risk_reward_ratio': 'mean'
    }).rename(columns={'signal': 'count'})
    
    # Best days
    best_days = daily_signals.nlargest(3, 'confidence')
    print("\nEn Yüksek Güvenli Günler:")
    for date, row in best_days.iterrows():
        print(f"- {date}: {row['count']} sinyal, Ortalama güven: {row['confidence']:.2%}")
    
    # Most active days
    most_active = daily_signals.nlargest(3, 'count')
    print("\nEn Aktif Günler:")
    for date, row in most_active.iterrows():
        print(f"- {date}: {row['count']} sinyal")

def analyze_patterns(df):
    """Analyze pattern recognition performance"""
    
    pattern_count = 0
    pattern_types = defaultdict(int)
    
    for idx, row in df.iterrows():
        if pd.notna(row.get('pattern_analysis')):
            try:
                patterns = json.loads(row['pattern_analysis'])
                if patterns:
                    pattern_count += 1
                    for pattern_type, detected in patterns.items():
                        if detected:
                            pattern_types[pattern_type] += 1
            except:
                pass
    
    print(f"- Pattern tespit edilen sinyal sayısı: {pattern_count} ({pattern_count/len(df)*100:.1f}%)")
    
    if pattern_types:
        print("- Tespit edilen pattern türleri:")
        for pattern, count in sorted(pattern_types.items(), key=lambda x: x[1], reverse=True):
            print(f"  - {pattern}: {count} kez")
    else:
        print("- Hiç pattern tespit edilmemiş!")

def generate_recommendations(df, results):
    """Generate specific improvement recommendations"""
    
    recommendations = []
    
    # 1. Confidence improvement
    avg_confidence = df['confidence'].mean()
    if avg_confidence < 0.6:
        recommendations.append({
            'priority': 'HIGH',
            'area': 'Güven Seviyesi',
            'issue': f'Ortalama güven çok düşük ({avg_confidence:.2%})',
            'solution': 'hybrid_strategy.py içinde confidence_weights değerlerini ayarlayın:\n'
                       '  - gram_weight: 0.5 -> 0.6\n'
                       '  - global_weight: 0.3 -> 0.25\n'
                       '  - currency_weight: 0.2 -> 0.15'
        })
    
    # 2. Win rate improvement
    if results['win_rate'] < 0.4:
        recommendations.append({
            'priority': 'HIGH',
            'area': 'Başarı Oranı',
            'issue': f'Düşük başarı oranı ({results["win_rate"]:.1%})',
            'solution': 'indicators/technical_indicators.py dosyasında:\n'
                       '  - RSI_PERIOD: 14 -> 21\n'
                       '  - MACD_FAST: 12 -> 8\n'
                       '  - BB_PERIOD: 20 -> 14'
        })
    
    # 3. Risk/Reward optimization
    avg_rr = df['risk_reward_ratio'].mean()
    if avg_rr < 2:
        recommendations.append({
            'priority': 'MEDIUM',
            'area': 'Risk/Reward',
            'issue': f'Düşük R/R oranı ({avg_rr:.2f})',
            'solution': 'strategies/hybrid_strategy.py içinde:\n'
                       '  - stop_loss_multiplier: 2.0 -> 1.5\n'
                       '  - take_profit_multiplier: 3.0 -> 4.0'
        })
    
    # 4. Signal diversity
    hold_ratio = len(df[df['signal'] == 'HOLD']) / len(df)
    if hold_ratio > 0.6:
        recommendations.append({
            'priority': 'HIGH',
            'area': 'Sinyal Çeşitliliği',
            'issue': f'Çok fazla HOLD sinyali ({hold_ratio:.1%})',
            'solution': 'analyzers/gram_altin_analyzer.py içinde:\n'
                       '  - SIGNAL_THRESHOLD: 0.6 -> 0.5\n'
                       '  - MIN_CONFIDENCE: 0.5 -> 0.4'
        })
    
    # 5. Timeframe specific
    for tf, metrics in results['timeframe_metrics'].items():
        if metrics['trades'] > 0 and metrics['win_rate'] < 0.3:
            recommendations.append({
                'priority': 'MEDIUM',
                'area': f'{tf} Timeframe',
                'issue': f'Düşük başarı oranı ({metrics["win_rate"]:.1%})',
                'solution': f'analyzers/timeframe_analyzer.py içinde {tf} için:\n'
                           f'  - Daha uzun periyotlu göstergeler kullanın\n'
                           f'  - Volatilite filtresini sıkılaştırın'
            })
    
    # Print recommendations
    for rec in sorted(recommendations, key=lambda x: x['priority']):
        print(f"\n[{rec['priority']}] {rec['area']}:")
        print(f"  Problem: {rec['issue']}")
        print(f"  Çözüm: {rec['solution']}")

def create_summary_report(df, results):
    """Create a summary report file"""
    
    report = f"""
📊 PERFORMANS ANALİZ RAPORU - ÖZET
=====================================
Tarih: {datetime.now().strftime('%Y-%m-%d %H:%M')}

🎯 GENEL PERFORMANS
- Toplam Sinyal Sayısı: {len(df)}
- Başarı Oranı: {results['win_rate']:.1%}
- Toplam Kar/Zarar: {results['total_pnl']:.2f} gram ({results['total_pnl_pct']:.2%})
- Sharpe Ratio: {results['sharpe_ratio']:.2f}
- Max Drawdown: {results['max_drawdown']:.2%}

📈 TIMEFRAME BAZLI ANALİZ
"""
    
    for tf, metrics in results['timeframe_metrics'].items():
        if metrics['trades'] > 0:
            report += f"\n{tf}:"
            report += f"\n- İşlem Sayısı: {metrics['trades']}"
            report += f"\n- Başarı Oranı: {metrics['win_rate']:.1%}"
            report += f"\n- Kar/Zarar: {metrics['pnl']:.2f} gram"
    
    report += f"""

⚠️ ZAYIF PERFORMANS ALANLARI
- Düşük güven seviyesi: {df['confidence'].mean():.2%}
- Düşük R/R oranı: {df['risk_reward_ratio'].mean():.2f}
- Yüksek HOLD oranı: {len(df[df['signal'] == 'HOLD']) / len(df) * 100:.1f}%

💡 İYİLEŞTİRME ÖNERİLERİ
1. Güven seviyesi hesaplama ağırlıklarını optimize edin
2. RSI ve MACD parametrelerini ayarlayın
3. Stop loss ve take profit çarpanlarını iyileştirin
4. Pattern recognition hassasiyetini artırın
5. Timeframe bazlı strateji optimizasyonu yapın

📌 SONUÇ
Strateji {'iyi performans gösteriyor' if results['win_rate'] > 0.5 else 'iyileştirme gerektiriyor'}.
Önerilen aksiyonları uyguladıktan sonra tekrar test edin.
"""
    
    with open('performance_report.txt', 'w', encoding='utf-8') as f:
        f.write(report)
    
    print(f"\n✅ Detaylı rapor 'performance_report.txt' dosyasına kaydedildi.")

if __name__ == "__main__":
    generate_detailed_report()