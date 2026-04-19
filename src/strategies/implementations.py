"""
Concrete strategy implementations for crypto scalping.
"""

from typing import Dict, Optional
import pandas as pd
from .base import BaseStrategy, Signal


class EMAcrossoverStrategy(BaseStrategy):
    """
    EMA Crossover Strategy: Buy on golden cross, Sell on death cross.
    Fast EMA (9) crosses above Slow EMA (26) = BUY
    Fast EMA (9) crosses below Slow EMA (26) = SELL
    """
    
    def __init__(self, symbol: str, params: Dict = None):
        super().__init__(symbol, params)
        self.fast_period = self.params.get('fast_period', 9)
        self.slow_period = self.params.get('slow_period', 26)
        self.min_volume = self.params.get('min_volume', 100000)
    
    def analyze(self, ohlcv_data: pd.DataFrame, ticker_data: Dict) -> Signal:
        """Analyze using EMA crossover."""
        if len(ohlcv_data) < self.slow_period:
            return Signal(action='HOLD', confidence=0.0, reason='Insufficient data')
        
        close = ohlcv_data['close']
        volume = ohlcv_data['volume']
        
        # Calculate EMAs
        fast_ema = self.calculate_ema(close, self.fast_period)
        slow_ema = self.calculate_ema(close, self.slow_period)
        
        # Check volume
        if volume.iloc[-1] < self.min_volume:
            return Signal(action='HOLD', confidence=0.0, reason='Low volume')
        
        current_price = close.iloc[-1]
        
        # Check for crossover
        if self.is_golden_cross(fast_ema, slow_ema):
            stop_loss = self.get_stop_loss(current_price, 'BUY', 2.0)
            take_profit = self.get_take_profit(current_price, 'BUY', 1.5)
            
            signal = Signal(
                action='BUY',
                confidence=0.8,
                entry_price=current_price,
                stop_loss=stop_loss,
                take_profit=take_profit,
                reason=f'Golden Cross: EMA({self.fast_period}) > EMA({self.slow_period})',
            )
        elif self.is_death_cross(fast_ema, slow_ema):
            stop_loss = self.get_stop_loss(current_price, 'SELL', 2.0)
            take_profit = self.get_take_profit(current_price, 'SELL', 1.5)
            
            signal = Signal(
                action='SELL',
                confidence=0.8,
                entry_price=current_price,
                stop_loss=stop_loss,
                take_profit=take_profit,
                reason=f'Death Cross: EMA({self.fast_period}) < EMA({self.slow_period})',
            )
        else:
            signal = Signal(action='HOLD', confidence=0.0, reason='No crossover detected')
        
        self.record_signal(signal)
        return signal


class RSIOversoldStrategy(BaseStrategy):
    """
    RSI Oversold/Overbought Strategy.
    Buy when RSI < 30 (oversold), Sell when RSI > 70 (overbought).
    """
    
    def __init__(self, symbol: str, params: Dict = None):
        super().__init__(symbol, params)
        self.period = self.params.get('period', 14)
        self.oversold_threshold = self.params.get('oversold_threshold', 30)
        self.overbought_threshold = self.params.get('overbought_threshold', 70)
    
    def analyze(self, ohlcv_data: pd.DataFrame, ticker_data: Dict) -> Signal:
        """Analyze using RSI."""
        if len(ohlcv_data) < self.period:
            return Signal(action='HOLD', confidence=0.0, reason='Insufficient data')
        
        close = ohlcv_data['close']
        rsi = self.calculate_rsi(close, self.period)
        
        current_price = close.iloc[-1]
        current_rsi = rsi.iloc[-1]
        
        if self.is_oversold(current_rsi, self.oversold_threshold):
            stop_loss = self.get_stop_loss(current_price, 'BUY', 2.0)
            take_profit = self.get_take_profit(current_price, 'BUY', 1.5)
            
            signal = Signal(
                action='BUY',
                confidence=0.7,
                entry_price=current_price,
                stop_loss=stop_loss,
                take_profit=take_profit,
                reason=f'RSI Oversold: {current_rsi:.2f} < {self.oversold_threshold}',
            )
        elif self.is_overbought(current_rsi, self.overbought_threshold):
            stop_loss = self.get_stop_loss(current_price, 'SELL', 2.0)
            take_profit = self.get_take_profit(current_price, 'SELL', 1.5)
            
            signal = Signal(
                action='SELL',
                confidence=0.7,
                entry_price=current_price,
                stop_loss=stop_loss,
                take_profit=take_profit,
                reason=f'RSI Overbought: {current_rsi:.2f} > {self.overbought_threshold}',
            )
        else:
            signal = Signal(
                action='HOLD',
                confidence=0.0,
                reason=f'RSI neutral: {current_rsi:.2f}',
            )
        
        self.record_signal(signal)
        return signal


class BollingerBandsStrategy(BaseStrategy):
    """
    Bollinger Bands Strategy.
    Buy when price touches lower band, Sell when price touches upper band.
    """
    
    def __init__(self, symbol: str, params: Dict = None):
        super().__init__(symbol, params)
        self.period = self.params.get('period', 20)
        self.std_dev = self.params.get('std_dev', 2.0)
    
    def analyze(self, ohlcv_data: pd.DataFrame, ticker_data: Dict) -> Signal:
        """Analyze using Bollinger Bands."""
        if len(ohlcv_data) < self.period:
            return Signal(action='HOLD', confidence=0.0, reason='Insufficient data')
        
        close = ohlcv_data['close']
        upper_band, middle_band, lower_band = self.calculate_bollinger_bands(
            close, self.period, self.std_dev
        )
        
        current_price = close.iloc[-1]
        current_upper = upper_band.iloc[-1]
        current_lower = lower_band.iloc[-1]
        current_middle = middle_band.iloc[-1]
        
        if current_price <= current_lower:
            stop_loss = self.get_stop_loss(current_price, 'BUY', 2.0)
            take_profit = current_middle
            
            signal = Signal(
                action='BUY',
                confidence=0.75,
                entry_price=current_price,
                stop_loss=stop_loss,
                take_profit=take_profit,
                reason=f'Price at lower band: {current_price:.2f} <= {current_lower:.2f}',
            )
        elif current_price >= current_upper:
            stop_loss = self.get_stop_loss(current_price, 'SELL', 2.0)
            take_profit = current_middle
            
            signal = Signal(
                action='SELL',
                confidence=0.75,
                entry_price=current_price,
                stop_loss=stop_loss,
                take_profit=take_profit,
                reason=f'Price at upper band: {current_price:.2f} >= {current_upper:.2f}',
            )
        else:
            signal = Signal(
                action='HOLD',
                confidence=0.0,
                reason='Price within bands',
            )
        
        self.record_signal(signal)
        return signal


class MACDStrategy(BaseStrategy):
    """
    MACD Strategy: Buy on bullish crossover, Sell on bearish crossover.
    """
    
    def __init__(self, symbol: str, params: Dict = None):
        super().__init__(symbol, params)
        self.fast = self.params.get('fast', 12)
        self.slow = self.params.get('slow', 26)
        self.signal = self.params.get('signal', 9)
    
    def analyze(self, ohlcv_data: pd.DataFrame, ticker_data: Dict) -> Signal:
        """Analyze using MACD."""
        if len(ohlcv_data) < self.slow:
            return Signal(action='HOLD', confidence=0.0, reason='Insufficient data')
        
        close = ohlcv_data['close']
        macd_line, signal_line, histogram = self.calculate_macd(
            close, self.fast, self.slow, self.signal
        )
        
        current_price = close.iloc[-1]
        
        if len(macd_line) < 2:
            return Signal(action='HOLD', confidence=0.0, reason='Insufficient data')
        
        # Check for crossover
        prev_histogram = histogram.iloc[-2]
        curr_histogram = histogram.iloc[-1]
        
        if prev_histogram < 0 and curr_histogram > 0:
            # Bullish crossover
            stop_loss = self.get_stop_loss(current_price, 'BUY', 2.0)
            take_profit = self.get_take_profit(current_price, 'BUY', 1.5)
            
            signal = Signal(
                action='BUY',
                confidence=0.75,
                entry_price=current_price,
                stop_loss=stop_loss,
                take_profit=take_profit,
                reason='MACD bullish crossover',
            )
        elif prev_histogram > 0 and curr_histogram < 0:
            # Bearish crossover
            stop_loss = self.get_stop_loss(current_price, 'SELL', 2.0)
            take_profit = self.get_take_profit(current_price, 'SELL', 1.5)
            
            signal = Signal(
                action='SELL',
                confidence=0.75,
                entry_price=current_price,
                stop_loss=stop_loss,
                take_profit=take_profit,
                reason='MACD bearish crossover',
            )
        else:
            signal = Signal(action='HOLD', confidence=0.0, reason='No MACD crossover')
        
        self.record_signal(signal)
        return signal


class AlphaSignalsStrategy(BaseStrategy):
    """
    Alpha Signals Strategy: Composite indicator combining EMA, RSI, and Bollinger Bands.
    Generates stronger signals when multiple indicators align.
    """
    
    def __init__(self, symbol: str, params: Dict = None):
        super().__init__(symbol, params)
        self.ema_fast = self.params.get('ema_fast', 9)
        self.ema_slow = self.params.get('ema_slow', 26)
        self.rsi_period = self.params.get('rsi_period', 14)
        self.bb_period = self.params.get('bb_period', 20)
        self.bb_std = self.params.get('bb_std', 2.0)
    
    def analyze(self, ohlcv_data: pd.DataFrame, ticker_data: Dict) -> Signal:
        """Analyze using composite alpha signals."""
        if len(ohlcv_data) < max(self.ema_slow, self.bb_period):
            return Signal(action='HOLD', confidence=0.0, reason='Insufficient data')
        
        close = ohlcv_data['close']
        current_price = close.iloc[-1]
        
        # Signal 1: EMA Crossover
        fast_ema = self.calculate_ema(close, self.ema_fast)
        slow_ema = self.calculate_ema(close, self.ema_slow)
        ema_signal = 1 if self.is_golden_cross(fast_ema, slow_ema) else (-1 if self.is_death_cross(fast_ema, slow_ema) else 0)
        
        # Signal 2: RSI
        rsi = self.calculate_rsi(close, self.rsi_period)
        current_rsi = rsi.iloc[-1]
        rsi_signal = 1 if self.is_oversold(current_rsi, 30) else (-1 if self.is_overbought(current_rsi, 70) else 0)
        
        # Signal 3: Bollinger Bands
        upper_band, middle_band, lower_band = self.calculate_bollinger_bands(
            close, self.bb_period, self.bb_std
        )
        current_upper = upper_band.iloc[-1]
        current_lower = lower_band.iloc[-1]
        bb_signal = 1 if current_price <= current_lower else (-1 if current_price >= current_upper else 0)
        
        # Combine signals
        total_signal = ema_signal + rsi_signal + bb_signal
        
        if total_signal >= 2:
            # Strong BUY signal
            stop_loss = self.get_stop_loss(current_price, 'BUY', 2.0)
            take_profit = self.get_take_profit(current_price, 'BUY', 1.5)
            
            signal = Signal(
                action='BUY',
                confidence=min(0.95, 0.7 + (total_signal * 0.1)),
                entry_price=current_price,
                stop_loss=stop_loss,
                take_profit=take_profit,
                reason=f'Alpha BUY: EMA={ema_signal}, RSI={rsi_signal}, BB={bb_signal}',
            )
        elif total_signal <= -2:
            # Strong SELL signal
            stop_loss = self.get_stop_loss(current_price, 'SELL', 2.0)
            take_profit = self.get_take_profit(current_price, 'SELL', 1.5)
            
            signal = Signal(
                action='SELL',
                confidence=min(0.95, 0.7 + (abs(total_signal) * 0.1)),
                entry_price=current_price,
                stop_loss=stop_loss,
                take_profit=take_profit,
                reason=f'Alpha SELL: EMA={ema_signal}, RSI={rsi_signal}, BB={bb_signal}',
            )
        else:
            signal = Signal(
                action='HOLD',
                confidence=0.0,
                reason=f'Weak signals: {total_signal}',
            )
        
        self.record_signal(signal)
        return signal


class PriceActionStrategy(BaseStrategy):
    """
    Price Action Strategy: Trade based on support/resistance levels and breakouts.
    """
    
    def __init__(self, symbol: str, params: Dict = None):
        super().__init__(symbol, params)
        self.lookback = self.params.get('lookback', 20)
        self.breakout_threshold = self.params.get('breakout_threshold', 1.02)  # 2% above resistance
    
    def analyze(self, ohlcv_data: pd.DataFrame, ticker_data: Dict) -> Signal:
        """Analyze using price action."""
        if len(ohlcv_data) < self.lookback:
            return Signal(action='HOLD', confidence=0.0, reason='Insufficient data')
        
        close = ohlcv_data['close']
        high = ohlcv_data['high']
        low = ohlcv_data['low']
        
        current_price = close.iloc[-1]
        
        # Find support and resistance
        resistance = high.iloc[-self.lookback:].max()
        support = low.iloc[-self.lookback:].min()
        
        # Check for breakout
        if current_price > resistance * self.breakout_threshold:
            stop_loss = support
            take_profit = self.get_take_profit(current_price, 'BUY', 1.5)
            
            signal = Signal(
                action='BUY',
                confidence=0.7,
                entry_price=current_price,
                stop_loss=stop_loss,
                take_profit=take_profit,
                reason=f'Breakout above resistance: {resistance:.2f}',
            )
        elif current_price < support * (2 - self.breakout_threshold):
            stop_loss = resistance
            take_profit = self.get_take_profit(current_price, 'SELL', 1.5)
            
            signal = Signal(
                action='SELL',
                confidence=0.7,
                entry_price=current_price,
                stop_loss=stop_loss,
                take_profit=take_profit,
                reason=f'Breakdown below support: {support:.2f}',
            )
        else:
            signal = Signal(
                action='HOLD',
                confidence=0.0,
                reason=f'Price between support ({support:.2f}) and resistance ({resistance:.2f})',
            )
        
        self.record_signal(signal)
        return signal
