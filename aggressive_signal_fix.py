#!/usr/bin/env python3
"""
Agresif sinyal üretimi için düzeltmeler
"""

print("=== AGRESİF SİNYAL ÜRETİMİ İÇİN DÜZELTMELER ===\n")

print("🔍 PROBLEM ANALİZİ:")
print("- BEARISH trend'de RSI 20-28 arası ama hala HOLD")
print("- Confidence %56 civarı ama eşik %30 olmasına rağmen sinyal yok")
print("- signal_combiner.py'de filtreler çok sıkı olabilir")

print("\n💡 ÇÖZÜM ÖNERİLERİ:\n")

print("1. gram_altin_analyzer.py - Daha agresif sinyal üretimi:")
with open('gram_altin_analyzer_fix.txt', 'w') as f:
    f.write("""
# analyzers/gram_altin_analyzer.py - Line 287 civarı
# Daha agresif sinyal üretimi
if buy_signals > sell_signals and buy_signals >= total_weight * 0.15:  # %20'den %15'e
    signal = "BUY"
    # RSI < 35 ise confidence boost
    if rsi_value and rsi_value < 35:
        base_confidence = min(base_confidence * 1.3, 1.0)
    confidence = base_confidence
    
elif sell_signals > buy_signals and sell_signals >= total_weight * 0.25:  # %30'dan %25'e
    signal = "SELL"
    # RSI > 65 ise confidence boost
    if rsi_value and rsi_value > 65:
        base_confidence = min(base_confidence * 1.3, 1.0)
    confidence = base_confidence
    
# Eşit sinyal durumunda trend yönünde karar ver
elif buy_signals == sell_signals and buy_signals > 0:
    if trend == TrendType.BULLISH and rsi_value and rsi_value < 50:
        signal = "BUY"
        confidence = base_confidence * 0.8
    elif trend == TrendType.BEARISH and rsi_value and rsi_value > 50:
        signal = "SELL"
        confidence = base_confidence * 0.8
    else:
        signal = "HOLD"
""")

print("2. signal_combiner.py - Filter kontrolünü gevşet:")
with open('signal_combiner_fix.txt', 'w') as f:
    f.write("""
# strategies/hybrid/signal_combiner.py - _apply_filters metodu
def _apply_filters(self, signal: str, confidence: float, 
                  volatility: float, timeframe: str,
                  global_dir: str, risk_level: str,
                  dip_score: float = 0) -> Tuple[str, str]:
    
    # Volatilite filtresini sadece extreme düşük durumda uygula
    if volatility < MIN_VOLATILITY_THRESHOLD * 0.5 and signal != "HOLD":  # 0.15 altında
        logger.debug(f"🔄 FILTER: Extreme low volatility, converting to HOLD")
        return "HOLD", "WEAK"
    
    # Timeframe güven eşiği - Dip detection varsa gevşet
    if signal != "HOLD":
        min_confidence = MIN_CONFIDENCE_THRESHOLDS.get(timeframe, 0.5)
        
        # Dip detection veya extreme RSI durumunda eşiği düşür
        if dip_score > 0.2 or (global_dir == "BEARISH" and signal == "BUY"):
            min_confidence *= 0.8  # %20 azalt
            
        if confidence < min_confidence:
            # Eğer çok yakınsa (5% fark) ve güçlü sinyaller varsa geçir
            if confidence >= min_confidence * 0.95:
                logger.debug(f"🔍 FILTER: Near threshold, allowing signal")
            else:
                logger.debug(f"🔄 FILTER: Low confidence, converting to HOLD")
                return "HOLD", "WEAK"
""")

print("\n3. Dip detection RSI kontrolü:")
with open('dip_detection_fix.txt', 'w') as f:
    f.write("""
# signal_combiner.py - _analyze_dip_opportunity içinde
# RSI Oversold kontrolü - daha geniş aralık
rsi_value = advanced_indicators.get('rsi')
if not rsi_value and hasattr(self, '_gram_indicators'):
    # Gram analizinden RSI'ı al
    rsi_value = self._gram_indicators.get('rsi')
    
if rsi_value:
    if rsi_value < 25:  # Extreme oversold
        dip_score += self.dip_detection_weights['oversold_rsi'] * 1.0
        dip_signals.append(f"EXTREME oversold RSI {rsi_value:.1f}")
    elif rsi_value < 35:  # Normal oversold
        dip_score += self.dip_detection_weights['oversold_rsi'] * 0.7
        dip_signals.append(f"Oversold RSI {rsi_value:.1f}")
    elif rsi_value < 40:  # Near oversold
        dip_score += self.dip_detection_weights['oversold_rsi'] * 0.4
        dip_signals.append(f"Near oversold RSI {rsi_value:.1f}")
""")

print("\n📋 UYGULAMA ADIMLARI:")
print("1. gram_altin_analyzer.py'de sinyal eşiklerini %15/%25'e düşür")
print("2. Eşit sinyal durumunda trend yönünde karar verme ekle")
print("3. signal_combiner.py'de filtreleri gevşet")
print("4. Dip detection'da RSI aralığını genişlet")
print("5. Near-threshold durumları için tolerans ekle")

print("\n⚡ HIZLI TEST:")
print("Deploy sonrası şu komutu çalıştırın:")
print("python3 test_dip_detection.py")
print("\nBEARISH + RSI<30 durumunda BUY sinyali görmelisiniz!")

# Dosyalar oluşturuldu
print("\n✅ Fix dosyaları oluşturuldu:")
print("- gram_altin_analyzer_fix.txt")
print("- signal_combiner_fix.txt") 
print("- dip_detection_fix.txt")