from fastapi import FastAPI
from routers import users, items, catalog, content_generation, main_controller, placeholder_apis
from dotenv import load_dotenv
import os

# Load environment variables from .env file
load_dotenv()

app = FastAPI(
    title="Meesho Supplier AI Studio",
    description="AI-powered content generation and tools for Meesho sellers",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Include all routers
app.include_router(users.router)
app.include_router(items.router)
app.include_router(catalog.router)
app.include_router(content_generation.router)
app.include_router(main_controller.router)
app.include_router(placeholder_apis.photo_router)
app.include_router(placeholder_apis.tryon_router)
app.include_router(placeholder_apis.seo_router)


@app.get("/")
def read_root():
    return {
        "message": "🚀 Meesho Supplier AI Studio",
        "description": "Empowering Meesho Sellers with AI-Driven Growth",
        "features": [
            "AI Content Generation",
            "Smart Product Photography", 
            "AI Try-On Technology",
            "Product Catalog Management"
        ],
        "content_generation_endpoints": {
            "generate_content": "/content/generate",
            "upload_and_generate": "/content/upload-and-generate",
            "enhance_existing": "/content/enhance-existing",
            "analytics": "/content/analytics/content-performance",
            "test_agent": "/content/test-agent",
            "health_check": "/content/health"
        },
        "documentation": "/docs",
        "status": "ready_for_hackathon"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 