"""
Portfolio management model for paper trading.
Tracks cash, positions, trades, and P&L calculations.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional
from enum import Enum
import uuid


class TradeStatus(str, Enum):
    """Trade status enumeration."""
    OPEN = "OPEN"
    CLOSED = "CLOSED"
    CANCELLED = "CANCELLED"


class OrderSide(str, Enum):
    """Order side enumeration."""
    BUY = "BUY"
    SELL = "SELL"


@dataclass
class Position:
    """Represents an open position in a symbol."""
    symbol: str
    quantity: float
    entry_price: float
    entry_time: datetime
    cost_basis: float = field(init=False)
    
    def __post_init__(self):
        self.cost_basis = self.quantity * self.entry_price
    
    def get_unrealized_pnl(self, current_price: float) -> float:
        """Calculate unrealized P&L."""
        return (current_price - self.entry_price) * self.quantity
    
    def get_unrealized_pnl_percent(self, current_price: float) -> float:
        """Calculate unrealized P&L percentage."""
        if self.entry_price == 0:
            return 0.0
        return ((current_price - self.entry_price) / self.entry_price) * 100


@dataclass
class Trade:
    """Represents a completed or open trade."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    strategy_id: str = ""
    symbol: str = ""
    side: OrderSide = OrderSide.BUY
    entry_price: float = 0.0
    quantity: float = 0.0
    exit_price: Optional[float] = None
    entry_time: datetime = field(default_factory=datetime.now)
    exit_time: Optional[datetime] = None
    status: TradeStatus = TradeStatus.OPEN
    pnl: float = 0.0
    pnl_percent: float = 0.0
    fees: float = 0.0
    notes: str = ""
    
    def close(self, exit_price: float, exit_time: Optional[datetime] = None):
        """Close the trade and calculate P&L."""
        self.exit_price = exit_price
        self.exit_time = exit_time or datetime.now()
        self.status = TradeStatus.CLOSED
        
        if self.side == OrderSide.BUY:
            self.pnl = (exit_price - self.entry_price) * self.quantity - self.fees
        else:  # SELL
            self.pnl = (self.entry_price - exit_price) * self.quantity - self.fees
        
        if self.entry_price != 0:
            self.pnl_percent = (self.pnl / (self.entry_price * self.quantity)) * 100
    
    def get_duration(self) -> Optional[float]:
        """Get trade duration in seconds."""
        if self.exit_time:
            return (self.exit_time - self.entry_time).total_seconds()
        return None
    
    def is_winning(self) -> bool:
        """Check if trade is profitable."""
        return self.pnl > 0


@dataclass
class Portfolio:
    """Main portfolio class tracking all trading activity."""
    initial_cash: float = 1000.0
    cash: float = field(init=False)
    positions: Dict[str, Position] = field(default_factory=dict)
    trades: List[Trade] = field(default_factory=list)
    portfolio_snapshots: List['PortfolioSnapshot'] = field(default_factory=list)
    creation_time: datetime = field(default_factory=datetime.now)
    
    def __post_init__(self):
        self.cash = self.initial_cash
    
    def get_total_value(self, current_prices: Dict[str, float]) -> float:
        """Calculate total portfolio value (cash + positions)."""
        positions_value = sum(
            position.quantity * current_prices.get(symbol, 0)
            for symbol, position in self.positions.items()
        )
        return self.cash + positions_value
    
    def get_unrealized_pnl(self, current_prices: Dict[str, float]) -> float:
        """Calculate total unrealized P&L."""
        return sum(
            position.get_unrealized_pnl(current_prices.get(symbol, 0))
            for symbol, position in self.positions.items()
        )
    
    def get_realized_pnl(self) -> float:
        """Calculate total realized P&L from closed trades."""
        return sum(trade.pnl for trade in self.trades if trade.status == TradeStatus.CLOSED)
    
    def get_total_pnl(self, current_prices: Dict[str, float]) -> float:
        """Calculate total P&L (realized + unrealized)."""
        return self.get_realized_pnl() + self.get_unrealized_pnl(current_prices)
    
    def get_total_pnl_percent(self, current_prices: Dict[str, float]) -> float:
        """Calculate total P&L percentage."""
        total_value = self.get_total_value(current_prices)
        if self.initial_cash == 0:
            return 0.0
        return ((total_value - self.initial_cash) / self.initial_cash) * 100
    
    def buy(
        self,
        symbol: str,
        quantity: float,
        price: float,
        strategy_id: str = "",
        fees: float = 0.0,
    ) -> Optional[Trade]:
        """Execute a buy order."""
        cost = quantity * price + fees
        
        if cost > self.cash:
            return None  # Insufficient cash
        
        # Reduce cash
        self.cash -= cost
        
        # Create or update position
        if symbol in self.positions:
            # Add to existing position (average price)
            existing = self.positions[symbol]
            total_quantity = existing.quantity + quantity
            new_entry_price = (
                (existing.quantity * existing.entry_price + quantity * price) /
                total_quantity
            )
            existing.quantity = total_quantity
            existing.entry_price = new_entry_price
        else:
            # Create new position
            self.positions[symbol] = Position(
                symbol=symbol,
                quantity=quantity,
                entry_price=price,
                entry_time=datetime.now(),
            )
        
        # Record trade
        trade = Trade(
            strategy_id=strategy_id,
            symbol=symbol,
            side=OrderSide.BUY,
            entry_price=price,
            quantity=quantity,
            fees=fees,
        )
        self.trades.append(trade)
        
        return trade
    
    def sell(
        self,
        symbol: str,
        quantity: float,
        price: float,
        strategy_id: str = "",
        fees: float = 0.0,
    ) -> Optional[Trade]:
        """Execute a sell order."""
        if symbol not in self.positions:
            return None  # No position to sell
        
        position = self.positions[symbol]
        if quantity > position.quantity:
            return None  # Insufficient quantity
        
        # Calculate proceeds
        proceeds = quantity * price - fees
        self.cash += proceeds
        
        # Find corresponding buy trade to close
        buy_trade = None
        for trade in reversed(self.trades):
            if (trade.symbol == symbol and
                trade.side == OrderSide.BUY and
                trade.status == TradeStatus.OPEN):
                buy_trade = trade
                break
        
        # Close buy trade
        if buy_trade:
            buy_trade.close(price)
        
        # Update position
        position.quantity -= quantity
        if position.quantity == 0:
            del self.positions[symbol]
        else:
            position.cost_basis = position.quantity * position.entry_price
        
        # Record sell trade
        sell_trade = Trade(
            strategy_id=strategy_id,
            symbol=symbol,
            side=OrderSide.SELL,
            entry_price=price,
            quantity=quantity,
            status=TradeStatus.CLOSED,
            exit_time=datetime.now(),
            fees=fees,
        )
        
        if buy_trade:
            sell_trade.pnl = buy_trade.pnl
            sell_trade.pnl_percent = buy_trade.pnl_percent
        
        self.trades.append(sell_trade)
        
        return sell_trade
    
    def get_winning_trades(self) -> List[Trade]:
        """Get all winning trades."""
        return [t for t in self.trades if t.is_winning()]
    
    def get_losing_trades(self) -> List[Trade]:
        """Get all losing trades."""
        return [t for t in self.trades if not t.is_winning() and t.status == TradeStatus.CLOSED]
    
    def get_closed_trades(self) -> List[Trade]:
        """Get all closed trades."""
        return [t for t in self.trades if t.status == TradeStatus.CLOSED]
    
    def get_open_trades(self) -> List[Trade]:
        """Get all open trades."""
        return [t for t in self.trades if t.status == TradeStatus.OPEN]
    
    def take_snapshot(self, current_prices: Dict[str, float]) -> 'PortfolioSnapshot':
        """Take a portfolio snapshot."""
        snapshot = PortfolioSnapshot(
            timestamp=datetime.now(),
            cash=self.cash,
            total_value=self.get_total_value(current_prices),
            positions_value=self.get_total_value(current_prices) - self.cash,
            unrealized_pnl=self.get_unrealized_pnl(current_prices),
            realized_pnl=self.get_realized_pnl(),
            total_pnl=self.get_total_pnl(current_prices),
            positions_count=len(self.positions),
            open_trades_count=len(self.get_open_trades()),
            closed_trades_count=len(self.get_closed_trades()),
        )
        self.portfolio_snapshots.append(snapshot)
        return snapshot


@dataclass
class PortfolioSnapshot:
    """Snapshot of portfolio state at a point in time."""
    timestamp: datetime
    cash: float
    total_value: float
    positions_value: float
    unrealized_pnl: float
    realized_pnl: float
    total_pnl: float
    positions_count: int
    open_trades_count: int
    closed_trades_count: int
