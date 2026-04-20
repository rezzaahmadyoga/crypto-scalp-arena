"""
API Server: FastAPI server for REST API and WebSocket connections.
Provides endpoints for portfolio, trades, strategies, and real-time updates.
"""

import asyncio
import json
import logging
from typing import Dict, List, Optional
from datetime import datetime

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import redis.asyncio as redis
import uvicorn

logger = logging.getLogger(__name__)


# Pydantic models for API responses
class PortfolioResponse(BaseModel):
    """Portfolio response model."""
    total_value: float
    cash: float
    positions_value: float
    unrealized_pnl: float
    realized_pnl: float
    total_pnl: float
    positions_count: int
    open_trades_count: int
    closed_trades_count: int


class TradeResponse(BaseModel):
    """Trade response model."""
    id: str
    symbol: str
    side: str
    entry_price: float
    quantity: float
    exit_price: Optional[float]
    entry_time: str
    exit_time: Optional[str]
    status: str
    pnl: float
    pnl_percent: float


class StrategyPerformanceResponse(BaseModel):
    """Strategy performance response model."""
    bot_id: str
    strategy: str
    symbol: str
    portfolio_value: float
    roi_percent: float
    trades_executed: int
    closed_trades: int
    winning_trades: int
    losing_trades: int
    winrate_percent: float
    profit_factor: float


class ArenaPerformanceResponse(BaseModel):
    """Arena performance response model."""
    total_bots: int
    total_portfolio_value: float
    total_trades: int
    average_roi_percent: float


class APIServer:
    """FastAPI server for trading arena."""
    
    def __init__(
        self,
        redis_url: str = 'redis://localhost:6379/0',
        host: str = '0.0.0.0',
        port: int = 8000,
    ):
        """Initialize API server."""
        self.redis_url = redis_url
        self.host = host
        self.port = port
        self.redis = None
        
        # Create FastAPI app
        self.app = FastAPI(
            title="Crypto Scalp Arena API",
            description="API for crypto scalping trading arena",
            version="0.1.0",
        )
        
        # Add CORS middleware
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
        
        # Setup routes
        self._setup_routes()
        
        # WebSocket connections
        self.websocket_connections: List[WebSocket] = []
    
    def _setup_routes(self):
        """Setup API routes."""
        
        @self.app.on_event("startup")
        async def startup():
            """Connect to Redis on startup."""
            self.redis = await redis.from_url(self.redis_url, decode_responses=True)
            logger.info("API Server started")
        
        @self.app.on_event("shutdown")
        async def shutdown():
            """Disconnect from Redis on shutdown."""
            if self.redis:
                await self.redis.close()
            logger.info("API Server stopped")
        
        @self.app.get("/health")
        async def health_check():
            """Health check endpoint."""
            return {"status": "healthy", "timestamp": datetime.now().isoformat()}
        
        @self.app.get("/api/arena/performance", response_model=ArenaPerformanceResponse)
        async def get_arena_performance():
            """Get arena performance metrics."""
            try:
                data = await self.redis.get('arena_performance')
                if data:
                    perf = json.loads(data)
                    return ArenaPerformanceResponse(
                        total_bots=perf.get('total_bots', 0),
                        total_portfolio_value=perf.get('total_portfolio_value', 0),
                        total_trades=perf.get('total_trades', 0),
                        average_roi_percent=perf.get('average_roi_percent', 0),
                    )
            except Exception as e:
                logger.error(f"Error getting arena performance: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.get("/api/strategies/performance")
        async def get_strategies_performance():
            """Get all strategies performance."""
            try:
                data = await self.redis.get('arena_performance')
                if data:
                    perf = json.loads(data)
                    return perf.get('all_bots_performance', [])
                return []
            except Exception as e:
                logger.error(f"Error getting strategies performance: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.get("/api/strategies/{strategy_id}/performance")
        async def get_strategy_performance(strategy_id: str):
            """Get specific strategy performance."""
            try:
                data = await self.redis.get('arena_performance')
                if data:
                    perf = json.loads(data)
                    for bot_perf in perf.get('all_bots_performance', []):
                        if bot_perf['bot_id'] == strategy_id:
                            return bot_perf
                raise HTTPException(status_code=404, detail="Strategy not found")
            except Exception as e:
                logger.error(f"Error getting strategy performance: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.websocket("/ws/performance")
        async def websocket_performance(websocket: WebSocket):
            """WebSocket endpoint for real-time performance updates."""
            await websocket.accept()
            self.websocket_connections.append(websocket)
            
            try:
                while True:
                    # Send performance data every 5 seconds
                    data = await self.redis.get('arena_performance')
                    if data:
                        await websocket.send_text(data)
                    
                    await asyncio.sleep(5)
            
            except WebSocketDisconnect:
                self.websocket_connections.remove(websocket)
                logger.info("WebSocket disconnected")
            except Exception as e:
                logger.error(f"WebSocket error: {e}")
                if websocket in self.websocket_connections:
                    self.websocket_connections.remove(websocket)
        
        @self.app.websocket("/ws/trades")
        async def websocket_trades(websocket: WebSocket):
            """WebSocket endpoint for real-time trade updates."""
            await websocket.accept()
            
            try:
                pubsub = self.redis.pubsub()
                await pubsub.subscribe('trade_events')
                
                async for message in pubsub.listen():
                    if message['type'] == 'message':
                        await websocket.send_text(message['data'])
            
            except WebSocketDisconnect:
                logger.info("Trade WebSocket disconnected")
            except Exception as e:
                logger.error(f"Trade WebSocket error: {e}")
    
    async def run(self):
        """Run the API server."""
        config = uvicorn.Config(
            self.app,
            host=self.host,
            port=self.port,
            log_level="info",
        )
        server = uvicorn.Server(config)
        await server.serve()


async def main():
    """Main entry point for API server."""
    import os
    from dotenv import load_dotenv
    
    load_dotenv()
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    )
    
    # Initialize and run server
    server = APIServer(
        redis_url=os.getenv('REDIS_URL', 'redis://localhost:6379/0'),
        host=os.getenv('API_HOST', '0.0.0.0'),
        port=int(os.getenv('API_PORT', 8000)),
    )
    
    try:
        await server.run()
    except KeyboardInterrupt:
        logger.info("Shutting down...")


if __name__ == '__main__':
    asyncio.run(main())
