from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import logging

from fastapi import FastAPI, File, UploadFile, Header
from fastapi.responses import JSONResponse
from PIL import Image
import io
from ImageToText import analyze_image
from routers import users, items, catalog, content_generation
from reel_gen.controller.agent_controller import router as agent_router
from test_agent.controller.agent_controller import router as test_agent_router


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


@app.post("/upload-image")
async def upload_image(file: UploadFile = File(...), objectId: str = Header(...)):
    """
    Upload an image and get confirmation with AI analysis.
    ObjectId should be passed in the request header.
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
        analysis_result = analyze_image(image, objectId)
        
        return JSONResponse(
            content={
                "message": "image received", 
                "filename": file.filename,
                "objectId": objectId,
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
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    ) 