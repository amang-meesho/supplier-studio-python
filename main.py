from fastapi import FastAPI, File, UploadFile
from fastapi.responses import JSONResponse
from PIL import Image
import io
from ImageToText import analyze_image
from routers import users, items, catalog, content_generation
from reel_gen.controller.agent_controller import router as agent_router
from test_agent.controller.agent_controller import router as test_agent_router

app = FastAPI(
    title="Meesho Supplier AI Studio",
    description="AI-powered content generation and tools for Meesho sellers",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

app.include_router(users.router)
app.include_router(items.router)
app.include_router(agent_router, prefix="/reel-gen")
app.include_router(test_agent_router, prefix="/test-agent")
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


@app.post("/upload-image")
async def upload_image(file: UploadFile = File(...)):
    """
    Upload an image and get confirmation with AI analysis.
    """
    try:
        # Read the uploaded file
        image_data = await file.read()
        
        # Convert to PIL Image
        image = Image.open(io.BytesIO(image_data))
        
        # Convert to RGB if necessary
        if image.mode != 'RGB':
            image = image.convert('RGB')
        
        # Analyze the image
        analysis_result = analyze_image(image)
        
        return JSONResponse(
            content={
                "message": "image received", 
                "filename": file.filename,
                "analysis": analysis_result if analysis_result else "Analysis failed"
            },
            status_code=200
        )
        
    except Exception as e:
        return JSONResponse(
            content={
                "message": "image received", 
                "filename": file.filename,
                "error": f"Processing failed: {str(e)}"
            },
            status_code=200
        )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 