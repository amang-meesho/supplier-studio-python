from fastapi import FastAPI
from routers import catalog, content_generation

app = FastAPI(
    title="Meesho Supplier AI Studio",
    description="AI-powered content generation and tools for Meesho sellers",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Include functional routers only
app.include_router(catalog.router)
app.include_router(content_generation.router)


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
            "upload_and_generate": "/content/upload-and-generate",
            "get_content": "/content/{content_id}",
            "health_check": "/content/health"
        },
        "documentation": "/docs",
        "status": "ready_for_hackathon"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 