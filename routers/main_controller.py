from fastapi import APIRouter, HTTPException, File, UploadFile, Form, BackgroundTasks
from pydantic import BaseModel
from typing import Optional, Dict, Any, List, Union
import motor.motor_asyncio
import asyncio
from datetime import datetime
import base64
import logging
from bson import ObjectId
import sys
import os
import aiohttp
from ImageToText import analyze_image
from PIL import Image
import io

# Add content_generation to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Direct imports from modules
from content_generation.agent import analyze_and_generate_content

# Setup logging
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["Main Controller"])

# Hardcoded MongoDB configuration
MONGODB_URL = "mongodb+srv://meesho:ES4AHZ7FkR6ggFjW@cluster0.eexndjk.mongodb.net/"
DATABASE_NAME = "meesho_supplier_ai"

if not MONGODB_URL:
    raise ValueError("MONGODB_URL is required")

client = motor.motor_asyncio.AsyncIOMotorClient(MONGODB_URL)
db = client[DATABASE_NAME]
products_collection = db.products

# Response models
class ProductProcessingResponse(BaseModel):
    success: bool
    object_id: str  # Changed from product_id to object_id
    message: str
    processing_status: Dict[str, str]

class CompleteProductResponse(BaseModel):
    content_generation: Dict[str, Any]
    reels: Optional[str]  # Changed to Optional[str] to store video URL directly
    tryons: Dict[str, Any]
    photoshoot: Dict[str, Any]
    operation_name: Optional[str]  # Changed to Optional[str] for simple string storage
    status: str

class FetchOperationResponse(BaseModel):
    status: str
    response: Dict[str, Any]
    formatted_video_url: Optional[str] = None

class APICallResult(BaseModel):
    api_name: str
    success: bool
    response: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

async def process_content_generation(image_base64: str, product_id: str, title: str, 
                                   price: int, description: str) -> APICallResult:
    """Call content generation function directly"""
    try:
        logger.info(f"Calling content generation function for product {product_id}")
        
        # Call the content generation function directly
        content_result = analyze_and_generate_content(
            image_data=image_base64,
            title=title,
            price=price,
            description=description
        )
        
        # Update the main product document with content generation result
        await products_collection.update_one(
            {"_id": ObjectId(product_id)},
            {
                "$set": {
                    "content_generation": {
                        "result": content_result,
                        "success": content_result.get("status") == "success",
                        "processed_at": datetime.utcnow()
                    },
                    "updated_at": datetime.utcnow()
                }
            }
        )
        
        logger.info(f"Content generation completed successfully for product {product_id}")
        return APICallResult(
            api_name="content_generation",
            success=content_result.get("status") == "success",
            response=content_result
        )
        
    except Exception as e:
        error_msg = f"Content generation failed: {str(e)}"
        logger.error(f"{error_msg} for product {product_id}")
        
        # Update the main product document with error
        await products_collection.update_one(
            {"_id": ObjectId(product_id)},
            {
                "$set": {
                    "content_generation": {
                        "error": error_msg,
                        "success": False,
                        "processed_at": datetime.utcnow()
                    },
                    "updated_at": datetime.utcnow()
                }
            }
        )
        
        return APICallResult(api_name="content_generation", success=False, error=error_msg)

async def process_ai_services_background(product_id: str, image_content: bytes, title: str, 
                                       price: int, description: str):
    """Process AI services in the background after returning response"""
    try:
        logger.info(f"Starting background AI processing for product {product_id}")
        
        # Do image processing in background
        image_base64 = base64.b64encode(image_content).decode('utf-8')
        
        # Convert bytes to PIL Image for analyze_image function
        image_pil = Image.open(io.BytesIO(image_content))
        
        # Update product with image data
        await products_collection.update_one(
            {"_id": ObjectId(product_id)},
            {
                "$set": {
                    "image_data": image_base64,
                    "updated_at": datetime.utcnow()
                }
            }
        )
        
        # Create async wrapper for analyze_image (since it's synchronous)
        async def run_analyze_image():
            try:
                # Call analyze_image function in a thread pool since it's synchronous
                import concurrent.futures
                loop = asyncio.get_event_loop()
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    result = await loop.run_in_executor(
                        executor, 
                        analyze_image, 
                        image_pil, 
                        product_id
                    )
                return result
            except Exception as e:
                logger.error(f"Image analysis failed for product {product_id}: {str(e)}")
                return None
        
        # Run both content generation and image analysis in parallel
        content_task = process_content_generation(
            image_base64, product_id, title, price, description
        )
        image_analysis_task = run_analyze_image()
        
        # Wait for both tasks to complete
        content_result, image_analysis_result = await asyncio.gather(
            content_task, 
            image_analysis_task,
            return_exceptions=True
        )
        
        # Handle content generation result
        if isinstance(content_result, Exception):
            logger.error(f"Content generation failed: {content_result}")
            content_success = False
        else:
            content_success = content_result.success
        
        # Handle image analysis result
        if image_analysis_result and not isinstance(image_analysis_result, Exception):
            result_text, operation_name = image_analysis_result
            logger.info(f"Image analysis completed for product {product_id}")
            logger.info(f"Operation name: {operation_name}")
            
            # Update product with operation_name
            if operation_name:
                await products_collection.update_one(
                    {"_id": ObjectId(product_id)},
                    {
                        "$set": {
                            "operation_name": operation_name,  # Store as simple string
                            "image_analysis_text": result_text,
                            "updated_at": datetime.utcnow()
                        }
                    }
                )
        else:
            logger.error(f"Image analysis failed for product {product_id}")
        
        # Update processing status
        processing_status = {
            "content_generation": "completed" if content_success else "failed",
            "image_analysis": "completed" if image_analysis_result and not isinstance(image_analysis_result, Exception) else "failed"
        }
        
        # TODO: Add other services here when implemented
        # - reels processing
        # - tryons processing  
        # - photoshoot processing
        
        # Update final product status in MongoDB
        await products_collection.update_one(
            {"_id": ObjectId(product_id)},
            {
                "$set": {
                    "processing_status": "completed",
                    "updated_at": datetime.utcnow(),
                    "api_call_status": processing_status
                }
            }
        )
        
        logger.info(f"Background AI processing completed for product {product_id}")
        
    except Exception as e:
        logger.error(f"Background processing failed for product {product_id}: {str(e)}")
        
        # Update status to show processing failed
        await products_collection.update_one(
            {"_id": ObjectId(product_id)},
            {
                "$set": {
                    "processing_status": "failed",
                    "processing_error": str(e),
                    "updated_at": datetime.utcnow()
                }
            }
        )

async def fetch_and_populate_reels_background(object_id: str, operation_name_string: str):
    """
    Background task to fetch video operation and populate reels field
    """
    try:
        logger.info(f"Debug - operation_name_string received: {operation_name_string}")
        
        if not operation_name_string:
            logger.warning(f"No operation name found for object_id {object_id}")
            return
            
        logger.info(f"Starting background fetch operation for object_id {object_id} with operation_name {operation_name_string}")
        
        # Call the fetch operation function
        fetch_result = await fetch_operation(operation_name_string)
        
        logger.info(f"Fetch result for {object_id}: {fetch_result.status}")
        
        # Store only the video URL directly in reels field
        if fetch_result.status == "success" and fetch_result.formatted_video_url:
            reels_value = fetch_result.formatted_video_url
        else:
            reels_value = None  # or empty string if you prefer
        
        # Update the product document with just the video URL
        await products_collection.update_one(
            {"_id": ObjectId(object_id)},
            {
                "$set": {
                    "reels": reels_value,
                    "updated_at": datetime.utcnow()
                }
            }
        )
        
        logger.info(f"Successfully populated reels field for object_id {object_id} with video URL: {reels_value}")
        
    except Exception as e:
        logger.error(f"Failed to fetch and populate reels for object_id {object_id}: {str(e)}")
        
        # Update with null value on error
        await products_collection.update_one(
            {"_id": ObjectId(object_id)},
            {
                "$set": {
                    "reels": None,
                    "updated_at": datetime.utcnow()
                }
            }
        )

@router.post("/process-product", response_model=ProductProcessingResponse)
async def process_product_with_ai(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    title: str = Form(""),
    price: int = Form(...),
    description: str = Form("")
):
    """
    Main controller endpoint that:
    1. Stores minimal product data in MongoDB and returns object_id immediately
    2. Processes image and AI services in the background
    """
    
    # Validate inputs
    if price <= 0:
        raise HTTPException(status_code=400, detail="Price must be greater than 0")
    
    # Validate file type quickly
    allowed_types = ['image/', 'application/']
    is_image = any(file.content_type.startswith(t) for t in allowed_types) or \
               file.filename.lower().endswith(('.jpg', '.jpeg', '.png', '.gif', '.webp', '.avif'))
    
    if not is_image:
        raise HTTPException(status_code=400, detail="File must be an image")

    try:
        logger.info(f"Processing product: title={title}, price={price}")
        
        # Read image data but don't process it yet
        image_content = await file.read()
        
        # Store minimal product data in MongoDB (without image_data for speed)
        product_doc = {
            "title": title,
            "price": price,
            "description": description,
            "image_metadata": {
                "filename": file.filename,
                "content_type": file.content_type,
                "size": len(image_content)
            },
            "processing_status": "processing",
            "content_generation": {},
            "reels": {},
            "tryons": {},
            "photoshoot": {},
            "operation_name": None,  # Initialize as None instead of empty dict
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        
        # Insert into MongoDB and get ObjectID immediately
        result = await products_collection.insert_one(product_doc)
        product_id = str(result.inserted_id)
        
        logger.info(f"Product stored in MongoDB with ID: {product_id}")
        
        # Add background task to process image and AI services
        background_tasks.add_task(
            process_ai_services_background,

            product_id, image_content, title, price, description
        )
        
        # Return response immediately with object_id
        return ProductProcessingResponse(
            success=True,
            object_id=product_id,
            message="Product created successfully. AI services are processing in the background.",
            processing_status={"status": "processing"}
        )
        
    except Exception as e:
        logger.error(f"Error in process_product_with_ai: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to process product: {str(e)}")




async def fetch_operation(operationName):
    """
    Fetch the result of a video generation operation using operation name
    Takes only operationName and returns the operation result with formatted video URL
    """
    
    fetch_url = "https://us-central1-aiplatform.googleapis.com/v1/projects/meesho-hackmee-3-proj-49/locations/us-central1/publishers/google/models/veo-2.0-generate-001:fetchPredictOperation"
    
    headers = {
        "Authorization": "Bearer ya29.A0AS3H6NzlIcRpREcGxf6J4u-2Fe__X9LPN_dsXq_50QWkFLN4Yml8ywimAYoCx9pZPjzV6v8QVYjW3yAdoDu3h8sgzyJ7SQUsIZRwf3U3EdhZSQ_Enk6mHjlZcfXG2WhIVNrcjhklKSyWk2rt_pSshMryQv2nL0ASKv7VFPC2r4gymZ2JrMs_3vCOYoFSdsGvA2IA6YJqw0aPH2Ec-tVK3leW6LHYK5_MJp808Y9ZjXA8nDRhxpm3vLKfGtAjC6xnFFYXxBJ1ivuESvhOXG36yjvBAXO-vekq_G2aRIEBXFdP_BOKVekbS-6tiEnC2pWW45_3NEjkmTyhzixv9QZSOQCyohRuZhKtrBE1aCgYKAYkSARESFQHGX2MiNT8UJSJQVl4icWvXwwuLgg0363",
        "Content-Type": "application/json"
    }
    
    payload = {
        "operationName": operationName
    }
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(fetch_url, headers=headers, json=payload) as response:
                if response.status == 200:
                    response_data = await response.json()
                    
                    # Extract and format the video URL if available
                    formatted_video_url = None
                    try:
                        # Navigate to the gcsUri in the response structure
                        if ("response" in response_data and 
                            "videos" in response_data["response"] and 
                            len(response_data["response"]["videos"]) > 0 and
                            "gcsUri" in response_data["response"]["videos"][0]):
                            
                            gcs_uri = response_data["response"]["videos"][0]["gcsUri"]
                            # Convert gs:// to https://storage.cloud.google.com/
                            formatted_video_url = gcs_uri.replace("gs://", "https://storage.cloud.google.com/")
                    except (KeyError, IndexError, TypeError):
                        # If URL extraction fails, continue without it
                        pass
                    
                    return FetchOperationResponse(
                        status="success",
                        response=response_data,
                        formatted_video_url=formatted_video_url
                    )
                else:
                    error_text = await response.text()
                    raise HTTPException(
                        status_code=response.status,
                        detail=f"Fetch operation API call failed: {error_text}"
                    )
                    
    except aiohttp.ClientError as e:
        raise HTTPException(
            status_code=400,
            detail=f"Network error: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Unexpected error: {str(e)}"
        )

@router.get("/product/{object_id}", response_model=CompleteProductResponse)
async def get_complete_product(object_id: str, background_tasks: BackgroundTasks):
    """
    Get product processing status and AI service results by object_id.
    Returns only: content_generation, reels, tryons, photoshoot, operation_name, and status.
    If reels is empty and operation_name exists, triggers background fetch to populate reels.
    """
    try:
        # Validate ObjectId format
        if not ObjectId.is_valid(object_id):
            raise HTTPException(status_code=400, detail="Invalid object_id format")
        
        logger.info(f"Fetching product data for object_id: {object_id}")
        
        # Get product document from MongoDB
        product = await products_collection.find_one({"_id": ObjectId(object_id)})
        
        if not product:
            raise HTTPException(status_code=404, detail="Product not found")
        
        # Debug: Print the entire document structure (excluding large image_data)
        debug_product = {k: v for k, v in product.items() if k != "image_data"}
        logger.info(f"Debug - Full document structure: {debug_product}")
        
        # Extract only the required fields and ensure they are dictionaries
        content_generation = product.get("content_generation", {})
        if not isinstance(content_generation, dict):
            content_generation = {}
            
        reels = product.get("reels", {})
        # Handle both old dict format and new string format
        if isinstance(reels, dict):
            # Old format - check if it has success field
            reels_is_empty = not reels or not reels.get("success")
            # Extract video URL from old format for response
            reels_response = reels.get("video_url") if reels and reels.get("success") else None
        else:
            # New format - check if it's a non-empty string
            reels_is_empty = not reels or reels == ""
            reels_response = reels
            
        tryons = product.get("tryons", {})
        if not isinstance(tryons, dict):
            tryons = {}
            
        photoshoot = product.get("photoshoot", {})
        if not isinstance(photoshoot, dict):
            photoshoot = {}
            
        # Check multiple possible ways operation_name might be stored
        operation_name = product.get("operation_name", None)  # Default to None instead of empty dict
        if not isinstance(operation_name, (str, dict, type(None))):
            operation_name = None  # Reset to None if invalid type
        
        # Also check other possible field names
        if not operation_name:
            for field_name in ["operationName", "operation", "operation_id"]:
                if field_name in product:
                    operation_name = {"operation_name": product[field_name]}
                    break
            
        status = product.get("processing_status", "unknown")
        
        # Debug logging
        logger.info(f"Debug - object_id: {object_id}")
        logger.info(f"Debug - reels: {reels}")
        logger.info(f"Debug - operation_name: {operation_name}")
        
        # Fix the operation_name_exists check
        operation_name_value = None
        if operation_name:
            if isinstance(operation_name, str):
                # New format - simple string
                operation_name_value = operation_name
            elif isinstance(operation_name, dict):
                # Old format - nested dict (for backward compatibility)
                operation_name_value = (
                    operation_name.get("operation_name") or
                    operation_name.get("operationName") or
                    operation_name.get("operation")
                )
        operation_name_exists = bool(operation_name_value)
        
        logger.info(f"Debug - reels_is_empty: {reels_is_empty}")
        logger.info(f"Debug - operation_name_value: {operation_name_value}")
        logger.info(f"Debug - operation_name_exists: {operation_name_exists}")
        
        if reels_is_empty and operation_name_exists:
            logger.info(f"Reels is empty and operation_name exists. Triggering background fetch for {object_id}")
            # Add background task to fetch operation and populate reels
            background_tasks.add_task(
                fetch_and_populate_reels_background,
                object_id, operation_name_value  # Pass the actual operation name string
            )
        else:
            logger.info(f"Skipping background fetch - reels_is_empty: {reels_is_empty}, operation_name_exists: {operation_name_exists}")
        
        logger.info(f"Successfully retrieved product {object_id} with status: {status}")
        
        return CompleteProductResponse(
            content_generation=content_generation,
            reels=reels_response,  # Use converted value
            tryons=tryons,
            photoshoot=photoshoot,
            operation_name=operation_name_value,
            status=status
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching product {object_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to retrieve product: {str(e)}")

@router.post("/product/{object_id}/set-operation-name")
async def set_operation_name(object_id: str, operation_name: str = Form(...)):
    """
    Manually set operation_name for testing purposes
    """
    try:
        # Validate ObjectId format
        if not ObjectId.is_valid(object_id):
            raise HTTPException(status_code=400, detail="Invalid object_id format")
        
        logger.info(f"Setting operation_name for object_id: {object_id}")
        
        # Update the product document with operation_name
        result = await products_collection.update_one(
            {"_id": ObjectId(object_id)},
            {
                "$set": {
                    "operation_name": {
                        "operation_name": operation_name,
                        "set_manually": True,
                        "set_at": datetime.utcnow()
                    },
                    "updated_at": datetime.utcnow()
                }
            }
        )
        
        if result.modified_count == 0:
            raise HTTPException(status_code=404, detail="Product not found")
        
        logger.info(f"Successfully set operation_name for object_id: {object_id}")
        
        return {
            "success": True,
            "message": f"Operation name set successfully for {object_id}",
            "operation_name": operation_name
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error setting operation_name for {object_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to set operation_name: {str(e)}")

@router.get("/product-results/{product_id}")
async def get_product_results(product_id: str):
    """
    DEPRECATED: Use /product/{object_id} instead.
    Get the product with all AI processing results by product ID
    """
    try:
        # Validate ObjectId
        if not ObjectId.is_valid(product_id):
            raise HTTPException(status_code=400, detail="Invalid product ID format")
        
        # Get product data with all AI results embedded
        product = await products_collection.find_one({"_id": ObjectId(product_id)})
        if not product:
            raise HTTPException(status_code=404, detail="Product not found")
        
        # Convert ObjectId to string for JSON serialization
        product["_id"] = str(product["_id"])
        
        # Get all service results from root level
        content_generation = product.get("content_generation", {})
        reels = product.get("reels", {})
        tryons = product.get("tryons", {})
        photoshoot = product.get("photoshoot", {})
        
        # Count completed services
        services = [content_generation, reels, tryons, photoshoot]
        completed_successfully = sum(1 for service in services if service.get("success", False))
        
        return {
            "object_id": str(product["_id"]),
            "product_info": {
                "title": product.get("title"),
                "price": product.get("price"),
                "description": product.get("description"),
                "processing_status": product.get("processing_status"),
                "created_at": product.get("created_at"),
                "updated_at": product.get("updated_at")
            },
            "content_generation": content_generation,
            "reels": reels,
            "tryons": tryons,
            "photoshoot": photoshoot,
            "total_services": len(services),
            "completed_successfully": completed_successfully
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in get_product_results: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to retrieve product results: {str(e)}")

@router.get("/health")
async def health_check():
    """Health check endpoint for the main controller"""
    try:
        # Test MongoDB connection
        await client.admin.command('ping')
        
        return {
            "status": "healthy",
            "service": "Main AI Controller",
            "database": "connected",
            "configured_services": ["content_generation", "reels", "tryons", "photoshoot", "operation_name"],
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        } 