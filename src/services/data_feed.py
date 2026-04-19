"""
Data Feed Service: Fetches real-time market data from Binance via CCXT.
Streams OHLCV data and ticker updates to message broker (Redis).
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import pandas as pd
import ccxt
import redis.asyncio as redis

logger = logging.getLogger(__name__)


class DataFeedService:
    """Service for fetching and streaming market data."""
    
    def __init__(
        self,
        exchange_name: str = 'binance',
        symbols: List[str] = None,
        timeframe: str = '5m',
        redis_url: str = 'redis://localhost:6379/0',
    ):
        """
        Initialize data feed service.
        
        Args:
            exchange_name: Exchange name (binance, coinbase, etc.)
            symbols: List of trading symbols (e.g., ['BTC/USDT', 'ETH/USDT'])
            timeframe: Candle timeframe (1m, 5m, 15m, etc.)
            redis_url: Redis connection URL
        """
        self.exchange_name = exchange_name
        self.symbols = symbols or ['BTC/USDT', 'ETH/USDT', 'BNB/USDT']
        self.timeframe = timeframe
        self.redis_url = redis_url
        
        # Initialize exchange
        exchange_class = getattr(ccxt, exchange_name)
        self.exchange = exchange_class({'enableRateLimit': True})
        
        # Redis connection (will be initialized in async context)
        self.redis = None
        
        # Data cache
        self.ohlcv_cache: Dict[str, pd.DataFrame] = {}
        self.ticker_cache: Dict[str, Dict] = {}
        self.last_update: Dict[str, datetime] = {}
    
    async def connect(self):
        """Connect to Redis."""
        self.redis = await redis.from_url(self.redis_url, decode_responses=True)
        logger.info(f"Connected to Redis: {self.redis_url}")
    
    async def disconnect(self):
        """Disconnect from Redis."""
        if self.redis:
            await self.redis.close()
            logger.info("Disconnected from Redis")
    
    async def fetch_ohlcv(self, symbol: str, limit: int = 100) -> Optional[pd.DataFrame]:
        """
        Fetch OHLCV data for a symbol.
        
        Args:
            symbol: Trading symbol
            limit: Number of candles to fetch
        
        Returns:
            DataFrame with OHLCV data or None if failed
        """
        try:
            ohlcv = await asyncio.to_thread(
                self.exchange.fetch_ohlcv,
                symbol,
                self.timeframe,
                limit=limit,
            )
            
            if not ohlcv:
                return None
            
            # Convert to DataFrame
            df = pd.DataFrame(
                ohlcv,
                columns=['timestamp', 'open', 'high', 'low', 'close', 'volume']
            )
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df = df.set_index('timestamp')
            
            self.ohlcv_cache[symbol] = df
            self.last_update[symbol] = datetime.now()
            
            logger.debug(f"Fetched OHLCV for {symbol}: {len(df)} candles")
            return df
        
        except Exception as e:
            logger.error(f"Error fetching OHLCV for {symbol}: {e}")
            return None
    
    async def fetch_ticker(self, symbol: str) -> Optional[Dict]:
        """
        Fetch ticker data for a symbol.
        
        Args:
            symbol: Trading symbol
        
        Returns:
            Ticker data dict or None if failed
        """
        try:
            ticker = await asyncio.to_thread(
                self.exchange.fetch_ticker,
                symbol,
            )
            
            self.ticker_cache[symbol] = ticker
            
            logger.debug(f"Fetched ticker for {symbol}: {ticker['last']}")
            return ticker
        
        except Exception as e:
            logger.error(f"Error fetching ticker for {symbol}: {e}")
            return None
    
    async def publish_market_data(self, symbol: str):
        """
        Publish market data to Redis streams.
        
        Args:
            symbol: Trading symbol
        """
        if not self.redis:
            return
        
        try:
            # Fetch latest data
            ohlcv = await self.fetch_ohlcv(symbol)
            ticker = await self.fetch_ticker(symbol)
            
            if not ohlcv is None and ticker:
                # Prepare data
                latest_candle = ohlcv.iloc[-1]
                data = {
                    'symbol': symbol,
                    'timestamp': datetime.now().isoformat(),
                    'ohlcv': {
                        'open': float(latest_candle['open']),
                        'high': float(latest_candle['high']),
                        'low': float(latest_candle['low']),
                        'close': float(latest_candle['close']),
                        'volume': float(latest_candle['volume']),
                    },
                    'ticker': {
                        'bid': float(ticker.get('bid', 0)),
                        'ask': float(ticker.get('ask', 0)),
                        'last': float(ticker.get('last', 0)),
                        'volume': float(ticker.get('quoteVolume', 0)),
                    }
                }
                
                # Publish to Redis stream
                await self.redis.xadd(
                    f'market_data:{symbol}',
                    {'data': json.dumps(data)},
                    maxlen=1000,  # Keep last 1000 entries
                )
                
                # Also publish to channel for real-time subscribers
                await self.redis.publish(
                    f'market_data:{symbol}',
                    json.dumps(data),
                )
                
                logger.debug(f"Published market data for {symbol}")
        
        except Exception as e:
            logger.error(f"Error publishing market data for {symbol}: {e}")
    
    async def start_streaming(self, update_interval: int = 5):
        """
        Start streaming market data.
        
        Args:
            update_interval: Update interval in seconds
        """
        logger.info(f"Starting data feed for {len(self.symbols)} symbols")
        
        try:
            while True:
                # Fetch and publish data for all symbols
                tasks = [self.publish_market_data(symbol) for symbol in self.symbols]
                await asyncio.gather(*tasks)
                
                # Wait before next update
                await asyncio.sleep(update_interval)
        
        except asyncio.CancelledError:
            logger.info("Data feed stopped")
        except Exception as e:
            logger.error(f"Error in data feed: {e}")
    
    def get_cached_ohlcv(self, symbol: str) -> Optional[pd.DataFrame]:
        """Get cached OHLCV data."""
        return self.ohlcv_cache.get(symbol)
    
    def get_cached_ticker(self, symbol: str) -> Optional[Dict]:
        """Get cached ticker data."""
        return self.ticker_cache.get(symbol)
    
    async def get_market_data(self, symbol: str) -> Optional[Dict]:
        """Get combined market data (OHLCV + ticker)."""
        ohlcv = self.get_cached_ohlcv(symbol)
        ticker = self.get_cached_ticker(symbol)
        
        if ohlcv is None or ticker is None:
            return None
        
        return {
            'symbol': symbol,
            'ohlcv': ohlcv,
            'ticker': ticker,
            'timestamp': self.last_update.get(symbol),
        }


async def main():
    """Main entry point for data feed service."""
    import os
    from dotenv import load_dotenv
    
    # Load environment variables
    load_dotenv()
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    )
    
    # Initialize service
    symbols = os.getenv('TRADING_SYMBOLS', 'BTC/USDT,ETH/USDT,BNB/USDT').split(',')
    service = DataFeedService(
        exchange_name=os.getenv('EXCHANGE_NAME', 'binance'),
        symbols=symbols,
        timeframe=os.getenv('TIMEFRAME', '5m'),
        redis_url=os.getenv('REDIS_URL', 'redis://localhost:6379/0'),
    )
    
    # Connect and start streaming
    try:
        await service.connect()
        await service.start_streaming(update_interval=5)
    except KeyboardInterrupt:
        logger.info("Shutting down...")
    finally:
        await service.disconnect()


if __name__ == '__main__':
    asyncio.run(main())
