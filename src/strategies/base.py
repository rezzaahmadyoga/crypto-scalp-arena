"""
Base strategy class for all scalping strategies.
Defines interface and common functionality for strategy implementations.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Optional
import pandas as pd
import numpy as np


@dataclass
class Signal:
    """Trading signal from a strategy."""
    action: str  # 'BUY', 'SELL', 'HOLD'
    confidence: float  # 0.0 to 1.0
    entry_price: Optional[float] = None
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    reason: str = ""
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()


class BaseStrategy(ABC):
    """
    Abstract base class for all trading strategies.
    Each strategy must implement the analyze() method.
    """
    
    def __init__(self, symbol: str, params: Dict = None):
        """
        Initialize strategy.
        
        Args:
            symbol: Trading symbol (e.g., 'BTC/USDT')
            params: Strategy parameters dictionary
        """
        self.symbol = symbol
        self.params = params or {}
        self.state = {}
        self.last_signal: Optional[Signal] = None
        self.signal_history = []
        self.trades_count = 0
        self.wins = 0
        self.losses = 0
    
    @abstractmethod
    def analyze(
        self,
        ohlcv_data: pd.DataFrame,
        ticker_data: Dict,
    ) -> Signal:
        """
        Analyze market data and generate trading signal.
        
        Args:
            ohlcv_data: DataFrame with columns [timestamp, open, high, low, close, volume]
            ticker_data: Dict with current market data {bid, ask, last, volume}
        
        Returns:
            Signal object with action and confidence
        """
        pass
    
    def get_position_size(
        self,
        portfolio_value: float,
        risk_percent: float = 2.0,
        entry_price: float = 0.0,
        stop_loss: float = 0.0,
    ) -> float:
        """
        Calculate position size based on risk management.
        
        Args:
            portfolio_value: Current portfolio value
            risk_percent: Risk percentage per trade (default 2%)
            entry_price: Entry price for the trade
            stop_loss: Stop loss price
        
        Returns:
            Position size (quantity)
        """
        if entry_price == 0 or stop_loss == 0:
            # Default: risk 2% of portfolio
            return (portfolio_value * risk_percent / 100) / entry_price if entry_price > 0 else 0
        
        # Risk-based position sizing
        risk_amount = portfolio_value * risk_percent / 100
        price_risk = abs(entry_price - stop_loss)
        
        if price_risk == 0:
            return 0
        
        quantity = risk_amount / price_risk
        return quantity
    
    def get_stop_loss(
        self,
        entry_price: float,
        side: str = 'BUY',
        stop_loss_percent: float = 2.0,
    ) -> float:
        """
        Calculate stop loss price.
        
        Args:
            entry_price: Entry price
            side: 'BUY' or 'SELL'
            stop_loss_percent: Stop loss percentage
        
        Returns:
            Stop loss price
        """
        if side == 'BUY':
            return entry_price * (1 - stop_loss_percent / 100)
        else:  # SELL
            return entry_price * (1 + stop_loss_percent / 100)
    
    def get_take_profit(
        self,
        entry_price: float,
        side: str = 'BUY',
        take_profit_percent: float = 1.0,
    ) -> float:
        """
        Calculate take profit price.
        
        Args:
            entry_price: Entry price
            side: 'BUY' or 'SELL'
            take_profit_percent: Take profit percentage
        
        Returns:
            Take profit price
        """
        if side == 'BUY':
            return entry_price * (1 + take_profit_percent / 100)
        else:  # SELL
            return entry_price * (1 - take_profit_percent / 100)
    
    def record_signal(self, signal: Signal):
        """Record signal for analysis."""
        self.last_signal = signal
        self.signal_history.append(signal)
    
    def record_trade_result(self, is_winning: bool):
        """Record trade result for statistics."""
        self.trades_count += 1
        if is_winning:
            self.wins += 1
        else:
            self.losses += 1
    
    def get_winrate(self) -> float:
        """Get win rate percentage."""
        if self.trades_count == 0:
            return 0.0
        return (self.wins / self.trades_count) * 100
    
    def get_stats(self) -> Dict:
        """Get strategy statistics."""
        return {
            'symbol': self.symbol,
            'trades_count': self.trades_count,
            'wins': self.wins,
            'losses': self.losses,
            'winrate': self.get_winrate(),
            'last_signal': self.last_signal,
        }
    
    # Common technical indicator helpers
    
    @staticmethod
    def calculate_sma(data: pd.Series, period: int) -> pd.Series:
        """Calculate Simple Moving Average."""
        return data.rolling(window=period).mean()
    
    @staticmethod
    def calculate_ema(data: pd.Series, period: int) -> pd.Series:
        """Calculate Exponential Moving Average."""
        return data.ewm(span=period, adjust=False).mean()
    
    @staticmethod
    def calculate_rsi(data: pd.Series, period: int = 14) -> pd.Series:
        """Calculate Relative Strength Index."""
        delta = data.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi
    
    @staticmethod
    def calculate_macd(
        data: pd.Series,
        fast: int = 12,
        slow: int = 26,
        signal: int = 9,
    ) -> tuple:
        """Calculate MACD."""
        ema_fast = data.ewm(span=fast, adjust=False).mean()
        ema_slow = data.ewm(span=slow, adjust=False).mean()
        
        macd_line = ema_fast - ema_slow
        signal_line = macd_line.ewm(span=signal, adjust=False).mean()
        histogram = macd_line - signal_line
        
        return macd_line, signal_line, histogram
    
    @staticmethod
    def calculate_bollinger_bands(
        data: pd.Series,
        period: int = 20,
        std_dev: float = 2.0,
    ) -> tuple:
        """Calculate Bollinger Bands."""
        sma = data.rolling(window=period).mean()
        std = data.rolling(window=period).std()
        
        upper_band = sma + (std * std_dev)
        lower_band = sma - (std * std_dev)
        
        return upper_band, sma, lower_band
    
    @staticmethod
    def calculate_atr(
        high: pd.Series,
        low: pd.Series,
        close: pd.Series,
        period: int = 14,
    ) -> pd.Series:
        """Calculate Average True Range."""
        tr1 = high - low
        tr2 = abs(high - close.shift())
        tr3 = abs(low - close.shift())
        
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = tr.rolling(window=period).mean()
        
        return atr
    
    @staticmethod
    def calculate_stochastic(
        high: pd.Series,
        low: pd.Series,
        close: pd.Series,
        period: int = 14,
        smooth_k: int = 3,
        smooth_d: int = 3,
    ) -> tuple:
        """Calculate Stochastic Oscillator."""
        lowest_low = low.rolling(window=period).min()
        highest_high = high.rolling(window=period).max()
        
        k_percent = 100 * (close - lowest_low) / (highest_high - lowest_low)
        k_percent_smooth = k_percent.rolling(window=smooth_k).mean()
        d_percent = k_percent_smooth.rolling(window=smooth_d).mean()
        
        return k_percent_smooth, d_percent
    
    @staticmethod
    def is_overbought(rsi: float, threshold: float = 70.0) -> bool:
        """Check if RSI indicates overbought condition."""
        return rsi > threshold
    
    @staticmethod
    def is_oversold(rsi: float, threshold: float = 30.0) -> bool:
        """Check if RSI indicates oversold condition."""
        return rsi < threshold
    
    @staticmethod
    def is_golden_cross(fast_ma: pd.Series, slow_ma: pd.Series) -> bool:
        """Check if fast MA crossed above slow MA (bullish)."""
        if len(fast_ma) < 2 or len(slow_ma) < 2:
            return False
        
        prev_fast = fast_ma.iloc[-2]
        prev_slow = slow_ma.iloc[-2]
        curr_fast = fast_ma.iloc[-1]
        curr_slow = slow_ma.iloc[-1]
        
        return prev_fast <= prev_slow and curr_fast > curr_slow
    
    @staticmethod
    def is_death_cross(fast_ma: pd.Series, slow_ma: pd.Series) -> bool:
        """Check if fast MA crossed below slow MA (bearish)."""
        if len(fast_ma) < 2 or len(slow_ma) < 2:
            return False
        
        prev_fast = fast_ma.iloc[-2]
        prev_slow = slow_ma.iloc[-2]
        curr_fast = fast_ma.iloc[-1]
        curr_slow = slow_ma.iloc[-1]
        
        return prev_fast >= prev_slow and curr_fast < curr_slow
