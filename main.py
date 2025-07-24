from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import logging

# Import routers
from routers import catalog, content_generation, main_controller, photography, try_on, catalog_optimizer

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Create FastAPI app
app = FastAPI(
    title="Meesho Supplier AI Studio",
    version="1.0.0",
    description="AI-powered content generation and tools for Meesho sellers"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

# Include routers
app.include_router(catalog.router)
app.include_router(content_generation.router)
app.include_router(main_controller.router)
app.include_router(photography.router)
app.include_router(try_on.router)
app.include_router(catalog_optimizer.router)

@app.get("/")
async def root():
    return {
        "message": "Welcome to Meesho Supplier AI Studio",
        "version": "1.0.0",
        "description": "AI-powered content generation and tools for Meesho sellers",
        "endpoints": {
            "health": "/api/v1/health",
            "process_product": "/api/v1/process-product",
            "get_product": "/api/v1/product/{object_id}",
            "content_generation": "/content/upload-and-generate",
            "photography": "/photography/enhance",
            "try_on": "/try-on/process",
            "catalog": "/catalog/optimize"
        }
    }

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "Meesho Supplier AI Studio",
        "version": "1.0.0"
    }

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    ) 