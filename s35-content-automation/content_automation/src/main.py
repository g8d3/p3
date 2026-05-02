"""
Main application entry point for the Content Automation System
"""
import asyncio
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from src.core.config import settings
from src.core.database import init_db
from src.api.routes import api_router
from src.api.dashboard import dashboard_router
from src.services.content_engine import ContentEngine
from src.services.scheduler import ContentScheduler

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Starting Content Automation System...")
    await init_db()
    
    # Initialize services
    content_engine = ContentEngine()
    scheduler = ContentScheduler(content_engine)
    
    # Start the scheduler
    await scheduler.start()
    
    # Store in app state for access in routes
    app.state.content_engine = content_engine
    app.state.scheduler = scheduler
    
    logger.info("Content Automation System started successfully")
    
    yield
    
    # Shutdown
    logger.info("Shutting down Content Automation System...")
    await scheduler.stop()
    logger.info("Content Automation System stopped")

# Create FastAPI app
app = FastAPI(
    title="Content Automation System",
    description="Automated content creation and posting platform",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(api_router, prefix="/api/v1")

# Include dashboard
app.include_router(dashboard_router)

@app.get("/")
async def root():
    return {"message": "Content Automation System is running"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}