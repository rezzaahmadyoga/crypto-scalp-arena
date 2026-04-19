"""
Arena Bot Manager: Manages multiple bot instances running different strategies.
Tracks performance, executes trades, and manages risk.
"""

import asyncio
import json
import logging
from datetime import datetime
from typing import Dict, List, Optional
import pandas as pd
import redis.asyncio as redis

from src.models.portfolio import Portfolio, Trade
from src.strategies.implementations import (
    EMAcrossoverStrategy,
    RSIOversoldStrategy,
    BollingerBandsStrategy,
    MACDStrategy,
    AlphaSignalsStrategy,
    PriceActionStrategy,
)

logger = logging.getLogger(__name__)


class ArenaBot:
    """Single bot instance running a specific strategy."""
    
    def __init__(
        self,
        bot_id: str,
        strategy_name: str,
        symbol: str,
        initial_cash: float = 1000.0,
        risk_percent: float = 2.0,
    ):
        """
        Initialize arena bot.
        
        Args:
            bot_id: Unique bot identifier
            strategy_name: Strategy class name
            symbol: Trading symbol
            initial_cash: Initial portfolio cash
            risk_percent: Risk percentage per trade
        """
        self.bot_id = bot_id
        self.strategy_name = strategy_name
        self.symbol = symbol
        self.portfolio = Portfolio(initial_cash=initial_cash)
        self.risk_percent = risk_percent
        
        # Initialize strategy
        self.strategy = self._create_strategy(strategy_name, symbol)
        
        # Performance tracking
        self.trades_executed = 0
        self.last_signal = None
        self.last_trade_time = None
        self.performance_metrics = {}
        self.creation_time = datetime.now()
    
    def _create_strategy(self, strategy_name: str, symbol: str):
        """Create strategy instance."""
        strategies = {
            'EMAcrossover': EMAcrossoverStrategy,
            'RSIOversold': RSIOversoldStrategy,
            'BollingerBands': BollingerBandsStrategy,
            'MACD': MACDStrategy,
            'AlphaSignals': AlphaSignalsStrategy,
            'PriceAction': PriceActionStrategy,
        }
        
        strategy_class = strategies.get(strategy_name)
        if not strategy_class:
            raise ValueError(f"Unknown strategy: {strategy_name}")
        
        return strategy_class(symbol=symbol)
    
    async def run_cycle(
        self,
        ohlcv_data: pd.DataFrame,
        ticker_data: Dict,
        current_prices: Dict[str, float],
    ):
        """
        Run single bot cycle: analyze market and execute trades.
        
        Args:
            ohlcv_data: OHLCV DataFrame
            ticker_data: Current ticker data
            current_prices: Current prices for all symbols
        """
        try:
            # Get signal from strategy
            signal = self.strategy.analyze(ohlcv_data, ticker_data)
            self.last_signal = signal
            
            if signal.action == 'HOLD':
                return
            
            current_price = current_prices.get(self.symbol, 0)
            if current_price == 0:
                return
            
            # Calculate position size
            position_size = self.portfolio.get_total_value(current_prices) * self.risk_percent / 100
            quantity = position_size / current_price if current_price > 0 else 0
            
            if quantity <= 0:
                return
            
            # Execute trade
            if signal.action == 'BUY':
                trade = self.portfolio.buy(
                    symbol=self.symbol,
                    quantity=quantity,
                    price=current_price,
                    strategy_id=self.strategy_name,
                    fees=quantity * current_price * 0.001,  # 0.1% fee
                )
                
                if trade:
                    self.trades_executed += 1
                    self.last_trade_time = datetime.now()
                    logger.info(
                        f"[{self.bot_id}] BUY {quantity:.4f} {self.symbol} @ {current_price:.2f}"
                    )
            
            elif signal.action == 'SELL':
                trade = self.portfolio.sell(
                    symbol=self.symbol,
                    quantity=quantity,
                    price=current_price,
                    strategy_id=self.strategy_name,
                    fees=quantity * current_price * 0.001,  # 0.1% fee
                )
                
                if trade:
                    self.trades_executed += 1
                    self.last_trade_time = datetime.now()
                    logger.info(
                        f"[{self.bot_id}] SELL {quantity:.4f} {self.symbol} @ {current_price:.2f}"
                    )
        
        except Exception as e:
            logger.error(f"Error in bot cycle for {self.bot_id}: {e}")
    
    def get_performance(self, current_prices: Dict[str, float]) -> Dict:
        """Get bot performance metrics."""
        closed_trades = self.portfolio.get_closed_trades()
        winning_trades = self.portfolio.get_winning_trades()
        
        winrate = (len(winning_trades) / len(closed_trades) * 100) if closed_trades else 0
        
        # Calculate profit factor
        winning_pnl = sum(t.pnl for t in winning_trades)
        losing_pnl = abs(sum(t.pnl for t in self.portfolio.get_losing_trades()))
        profit_factor = winning_pnl / losing_pnl if losing_pnl > 0 else 0
        
        total_value = self.portfolio.get_total_value(current_prices)
        roi = ((total_value - self.portfolio.initial_cash) / self.portfolio.initial_cash * 100)
        
        return {
            'bot_id': self.bot_id,
            'strategy': self.strategy_name,
            'symbol': self.symbol,
            'portfolio_value': total_value,
            'initial_cash': self.portfolio.initial_cash,
            'roi_percent': roi,
            'trades_executed': self.trades_executed,
            'closed_trades': len(closed_trades),
            'winning_trades': len(winning_trades),
            'losing_trades': len(self.portfolio.get_losing_trades()),
            'winrate_percent': winrate,
            'profit_factor': profit_factor,
            'realized_pnl': self.portfolio.get_realized_pnl(),
            'unrealized_pnl': self.portfolio.get_unrealized_pnl(current_prices),
            'total_pnl': self.portfolio.get_total_pnl(current_prices),
            'last_signal': self.last_signal.action if self.last_signal else None,
            'last_trade_time': self.last_trade_time.isoformat() if self.last_trade_time else None,
        }


class ArenaBotManager:
    """Manages multiple arena bots and coordinates their activities."""
    
    def __init__(
        self,
        symbols: List[str] = None,
        initial_cash: float = 1000.0,
        redis_url: str = 'redis://localhost:6379/0',
    ):
        """
        Initialize arena bot manager.
        
        Args:
            symbols: List of trading symbols
            initial_cash: Initial cash per bot
            redis_url: Redis connection URL
        """
        self.symbols = symbols or ['BTC/USDT', 'ETH/USDT', 'BNB/USDT']
        self.initial_cash = initial_cash
        self.redis_url = redis_url
        
        # Bot instances
        self.bots: Dict[str, ArenaBot] = {}
        self.redis = None
        
        # Performance tracking
        self.arena_start_time = datetime.now()
        self.market_data_cache: Dict[str, Dict] = {}
    
    async def connect(self):
        """Connect to Redis."""
        self.redis = await redis.from_url(self.redis_url, decode_responses=True)
        logger.info(f"Connected to Redis: {self.redis_url}")
    
    async def disconnect(self):
        """Disconnect from Redis."""
        if self.redis:
            await self.redis.close()
            logger.info("Disconnected from Redis")
    
    def create_bot(self, strategy_name: str, symbol: str) -> ArenaBot:
        """Create and register a new bot."""
        bot_id = f"{strategy_name}_{symbol}_{len(self.bots)}"
        bot = ArenaBot(
            bot_id=bot_id,
            strategy_name=strategy_name,
            symbol=symbol,
            initial_cash=self.initial_cash,
            risk_percent=2.0,
        )
        self.bots[bot_id] = bot
        logger.info(f"Created bot: {bot_id}")
        return bot
    
    async def get_market_data(self, symbol: str) -> Optional[Dict]:
        """Get market data from Redis cache."""
        try:
            data = await self.redis.get(f"market_data:{symbol}")
            if data:
                return json.loads(data)
        except Exception as e:
            logger.error(f"Error getting market data for {symbol}: {e}")
        
        return None
    
    async def run_cycle(self):
        """Run single arena cycle: fetch market data and run all bots."""
        try:
            # Fetch market data for all symbols
            current_prices = {}
            market_data_all = {}
            
            for symbol in self.symbols:
                data = await self.get_market_data(symbol)
                if data:
                    market_data_all[symbol] = data
                    current_prices[symbol] = data.get('ticker', {}).get('last', 0)
            
            if not current_prices:
                logger.warning("No market data available")
                return
            
            # Run each bot
            for bot in self.bots.values():
                if bot.symbol in market_data_all:
                    data = market_data_all[bot.symbol]
                    
                    # Convert to DataFrame for OHLCV
                    ohlcv_data = pd.DataFrame([data['ohlcv']])
                    ticker_data = data['ticker']
                    
                    await bot.run_cycle(ohlcv_data, ticker_data, current_prices)
            
            # Take portfolio snapshots
            for bot in self.bots.values():
                bot.portfolio.take_snapshot(current_prices)
            
            # Publish performance metrics
            await self.publish_performance()
        
        except Exception as e:
            logger.error(f"Error in arena cycle: {e}")
    
    async def publish_performance(self):
        """Publish performance metrics to Redis."""
        if not self.redis:
            return
        
        try:
            performance_data = {}
            for bot_id, bot in self.bots.items():
                # Get current prices (dummy for now)
                current_prices = {bot.symbol: 0}
                performance_data[bot_id] = bot.get_performance(current_prices)
            
            await self.redis.set(
                'arena_performance',
                json.dumps(performance_data, default=str),
                ex=60,  # Expire in 60 seconds
            )
            
            logger.debug("Published arena performance metrics")
        
        except Exception as e:
            logger.error(f"Error publishing performance: {e}")
    
    async def start_arena(self, update_interval: int = 10):
        """Start the arena bot manager."""
        logger.info(f"Starting arena with {len(self.bots)} bots")
        
        try:
            while True:
                await self.run_cycle()
                await asyncio.sleep(update_interval)
        
        except asyncio.CancelledError:
            logger.info("Arena stopped")
        except Exception as e:
            logger.error(f"Error in arena: {e}")
    
    def get_arena_performance(self) -> Dict:
        """Get overall arena performance."""
        all_performance = []
        total_portfolio_value = 0
        total_trades = 0
        
        for bot in self.bots.values():
            # Dummy current prices for now
            current_prices = {bot.symbol: 0}
            perf = bot.get_performance(current_prices)
            all_performance.append(perf)
            total_portfolio_value += perf['portfolio_value']
            total_trades += perf['trades_executed']
        
        avg_roi = sum(p['roi_percent'] for p in all_performance) / len(all_performance) if all_performance else 0
        best_bot = max(all_performance, key=lambda x: x['roi_percent']) if all_performance else None
        worst_bot = min(all_performance, key=lambda x: x['roi_percent']) if all_performance else None
        
        return {
            'arena_start_time': self.arena_start_time.isoformat(),
            'total_bots': len(self.bots),
            'total_portfolio_value': total_portfolio_value,
            'total_trades': total_trades,
            'average_roi_percent': avg_roi,
            'best_performer': best_bot,
            'worst_performer': worst_bot,
            'all_bots_performance': all_performance,
        }


async def main():
    """Main entry point for arena manager."""
    import os
    from dotenv import load_dotenv
    
    load_dotenv()
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    )
    
    # Initialize manager
    symbols = os.getenv('TRADING_SYMBOLS', 'BTC/USDT,ETH/USDT,BNB/USDT').split(',')
    manager = ArenaBotManager(
        symbols=symbols,
        initial_cash=float(os.getenv('INITIAL_CASH', 1000)),
        redis_url=os.getenv('REDIS_URL', 'redis://localhost:6379/0'),
    )
    
    # Create bots for each strategy
    strategies = [
        'EMAcrossover',
        'RSIOversold',
        'BollingerBands',
        'MACD',
        'AlphaSignals',
        'PriceAction',
    ]
    
    for strategy in strategies:
        for symbol in symbols:
            manager.create_bot(strategy, symbol)
    
    # Start arena
    try:
        await manager.connect()
        await manager.start_arena(update_interval=10)
    except KeyboardInterrupt:
        logger.info("Shutting down...")
    finally:
        await manager.disconnect()


if __name__ == '__main__':
    asyncio.run(main())
