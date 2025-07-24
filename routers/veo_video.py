from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any, Union
from datetime import datetime
import base64

# Import our Veo video service
try:
    from services.veo_video_service import veo_video_service
    VEO_SERVICE_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Veo video service not available: {e}")
    VEO_SERVICE_AVAILABLE = False
    veo_video_service = None

router = APIRouter(prefix="/veo", tags=["veo-video"])

# Response Contracts (Pydantic Models)

class VideoMetadata(BaseModel):
    """Video metadata information"""
    duration: Optional[str] = None
    resolution: Optional[str] = None
    size: Optional[str] = None

class GeneratedVideo(BaseModel):
    """Individual generated video information"""
    video_uri: str = Field(..., description="URI of the generated video")
    metadata: Optional[VideoMetadata] = None

class VideoGenerationConfig(BaseModel):
    """Video generation configuration parameters"""
    aspectRatio: str = Field(default="16:9", description="Video aspect ratio")
    durationSeconds: int = Field(default=5, description="Video duration in seconds", ge=1, le=30)
    resolution: Optional[str] = Field(default="720p", description="Video resolution")
    numberOfVideos: int = Field(default=1, description="Number of videos to generate", ge=1, le=4)

class VideoGenerationRequest(BaseModel):
    """Video generation request - mirrors TypeScript interface"""
    prompt: str = Field(..., description="Text description for video generation", min_length=1, max_length=2000)
    model: str = Field(default="veo-2.0-generate-001", description="Veo model to use")
    config: Optional[VideoGenerationConfig] = Field(default_factory=VideoGenerationConfig)
    image_bytes: Optional[str] = Field(default=None, description="Base64 encoded image bytes")
    image_mime_type: str = Field(default="image/png", description="MIME type of the image")

class VideoGenerationResponse(BaseModel):
    """Video generation response - mirrors TypeScript response structure"""
    status: str = Field(..., description="Operation status: started, completed, error, timeout, simulated")
    operation_id: Optional[str] = None
    videos: Optional[List[GeneratedVideo]] = None
    generation_time: Optional[int] = None
    poll_count: Optional[int] = None
    error_code: Optional[str] = None
    error_message: Optional[str] = None
    message: Optional[str] = None
    timestamp: str

class OperationStatusResponse(BaseModel):
    """Operation status check response"""
    status: str
    operation_id: str
    done: bool
    videos: Optional[List[GeneratedVideo]] = None
    error_code: Optional[str] = None
    error_message: Optional[str] = None
    timestamp: str

class VideoDownloadResponse(BaseModel):
    """Video download response"""
    status: str
    filename: Optional[str] = None
    size_bytes: Optional[int] = None
    size_mb: Optional[float] = None
    video_uri: Optional[str] = None
    error_code: Optional[str] = None
    error_message: Optional[str] = None
    timestamp: str

class ServiceInfoResponse(BaseModel):
    """Service information response"""
    service: str
    api_key_configured: bool
    client_type: str
    supported_models: List[str]
    supported_features: List[str]
    config_options: Dict[str, Any]

# Helper function to check service availability
def check_service_available():
    if not VEO_SERVICE_AVAILABLE or veo_video_service is None:
        raise HTTPException(
            status_code=503, 
            detail="Veo video service not available - missing dependencies or configuration"
        )

@router.post("/generate", response_model=VideoGenerationResponse)
async def generate_videos(request: VideoGenerationRequest):
    """
    Generate videos using Google's Veo models
    
    This endpoint replicates the TypeScript video generation functionality.
    Supports both text-to-video and image-to-video generation.
    
    **Models:**
    - veo-2.0-generate-001: Standard Veo 2.0 model
    - veo-3.0-generate-preview: Latest Veo 3.0 preview (requires billing)
    
    **Configuration:**
    - aspectRatio: Video aspect ratio (16:9, 9:16, 1:1, etc.)
    - durationSeconds: Video length (1-30 seconds)
    - resolution: Video quality (720p, 1080p)
    - numberOfVideos: How many videos to generate (1-4)
    """
    check_service_available()
    
    try:
        # Convert Pydantic models to dict
        config_dict = request.config.dict() if request.config else {}
        
        result = await veo_video_service.generate_videos(
            prompt=request.prompt,
            model=request.model,
            config=config_dict,
            image_bytes=request.image_bytes,
            image_mime_type=request.image_mime_type
        )
        
        # Handle different status types
        if result["status"] == "error":
            if result.get("error_code") == "QUOTA_EXCEEDED":
                raise HTTPException(status_code=429, detail=result["error_message"])
            elif result.get("error_code") == "BILLING_REQUIRED":
                raise HTTPException(status_code=402, detail=result["error_message"])
            else:
                raise HTTPException(status_code=400, detail=result["error_message"])
        
        return VideoGenerationResponse(**result)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Video generation failed: {str(e)}")

@router.get("/status/{operation_id}", response_model=OperationStatusResponse)
async def check_operation_status(operation_id: str):
    """
    Check the status of a video generation operation
    
    Use the operation_id returned from the generate endpoint to check
    if the video generation is complete and get the video URLs.
    """
    check_service_available()
    
    try:
        result = await veo_video_service._check_operation_status(operation_id)
        
        response_data = {
            "status": "completed" if result["done"] else "in_progress",
            "operation_id": operation_id,
            "done": result["done"],
            "timestamp": datetime.now().isoformat()
        }
        
        if result["done"]:
            if result.get("success"):
                response_data["videos"] = [
                    GeneratedVideo(video_uri=v["video"]["uri"], metadata=v.get("metadata"))
                    for v in result["videos"]
                ]
            else:
                response_data["status"] = "error"
                response_data["error_message"] = result.get("error", "Unknown error")
                response_data["error_code"] = "GENERATION_FAILED"
        
        return OperationStatusResponse(**response_data)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Status check failed: {str(e)}")

@router.post("/download", response_model=VideoDownloadResponse)
async def download_video(
    video_uri: str = Form(..., description="URI of the video to download"),
    filename: Optional[str] = Form(None, description="Optional filename for the download")
):
    """
    Download a generated video from its URI
    
    This endpoint replicates the TypeScript downloadFile functionality.
    Downloads the video file and saves it locally.
    """
    check_service_available()
    
    try:
        result = await veo_video_service.download_video(video_uri, filename)
        
        if result["status"] == "error":
            raise HTTPException(status_code=400, detail=result["error_message"])
        
        return VideoDownloadResponse(**result)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Download failed: {str(e)}")

@router.post("/generate-with-upload", response_model=VideoGenerationResponse)
async def generate_video_with_image_upload(
    prompt: str = Form(..., description="Text description for video generation"),
    model: str = Form(default="veo-2.0-generate-001", description="Veo model to use"),
    file: Optional[UploadFile] = File(None, description="Image file for image-to-video generation"),
    # Config parameters as form fields
    aspect_ratio: str = Form(default="16:9"),
    duration_seconds: int = Form(default=5, ge=1, le=30),
    resolution: str = Form(default="720p"),
    number_of_videos: int = Form(default=1, ge=1, le=4)
):
    """
    Generate videos with file upload support
    
    This endpoint allows direct file upload instead of base64 encoding,
    making it easier to use from web forms or multipart requests.
    """
    check_service_available()
    
    try:
        # Handle file upload
        image_bytes = None
        image_mime_type = "image/png"
        
        if file:
            content = await file.read()
            image_bytes = base64.b64encode(content).decode('utf-8')
            image_mime_type = file.content_type or "image/png"
        
        # Build config
        config = {
            "aspectRatio": aspect_ratio,
            "durationSeconds": duration_seconds,
            "resolution": resolution,
            "numberOfVideos": number_of_videos
        }
        
        result = await veo_video_service.generate_videos(
            prompt=prompt,
            model=model,
            config=config,
            image_bytes=image_bytes,
            image_mime_type=image_mime_type
        )
        
        if result["status"] == "error":
            if result.get("error_code") == "QUOTA_EXCEEDED":
                raise HTTPException(status_code=429, detail=result["error_message"])
            elif result.get("error_code") == "BILLING_REQUIRED":
                raise HTTPException(status_code=402, detail=result["error_message"])
            else:
                raise HTTPException(status_code=400, detail=result["error_message"])
        
        return VideoGenerationResponse(**result)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Video generation failed: {str(e)}")

@router.get("/info", response_model=ServiceInfoResponse)
async def get_service_info():
    """
    Get information about the Veo video service
    
    Returns service configuration, supported models, and available features.
    """
    check_service_available()
    
    try:
        info = veo_video_service.get_service_info()
        return ServiceInfoResponse(**info)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get service info: {str(e)}")

@router.get("/")
async def veo_service_overview():
    """
    Get overview of the Veo video generation service
    
    Returns basic information about the service and available endpoints.
    Mirrors the TypeScript functionality structure.
    """
    return {
        "service": "Google Veo Video Generation API",
        "version": "1.0.0",
        "description": "Generate videos using Google's Veo models - mirrors TypeScript functionality",
        "service_available": VEO_SERVICE_AVAILABLE,
        "models": {
            "veo-2.0-generate-001": "Standard Veo 2.0 model",
            "veo-3.0-generate-preview": "Latest Veo 3.0 preview (requires billing)"
        },
        "endpoints": {
            "generate": "POST /veo/generate - Generate videos from prompt",
            "generate-with-upload": "POST /veo/generate-with-upload - Generate with file upload",
            "status": "GET /veo/status/{operation_id} - Check operation status",
            "download": "POST /veo/download - Download generated video",
            "info": "GET /veo/info - Get service information"
        },
        "features": [
            "Text-to-video generation",
            "Image-to-video generation",
            "Configurable video parameters",
            "Async operation polling",
            "Video download",
            "File upload support"
        ],
        "typescript_compatibility": {
            "description": "This service replicates the TypeScript video generation functionality",
            "equivalent_functions": {
                "generateContent": "/veo/generate",
                "downloadFile": "/veo/download",
                "operation polling": "/veo/status/{operation_id}"
            }
        },
        "example_curl": {
            "basic_generation": '''curl -X POST "http://localhost:8000/veo/generate" \\
     -H "Content-Type: application/json" \\
     -d '{
       "prompt": "A cinematic shot of a majestic lion in the savannah",
       "model": "veo-2.0-generate-001",
       "config": {
         "aspectRatio": "16:9",
         "durationSeconds": 5,
         "resolution": "720p"
       }
     }' ''',
            "with_file_upload": '''curl -X POST "http://localhost:8000/veo/generate-with-upload" \\
     -F "prompt=A cat playing with a ball" \\
     -F "file=@image.jpg" \\
     -F "duration_seconds=10" '''
        }
    } 