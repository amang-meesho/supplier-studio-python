from fastapi import APIRouter, HTTPException, File, UploadFile, Form, BackgroundTasks
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
import motor.motor_asyncio
import asyncio
from datetime import datetime
import base64
import logging
from bson import ObjectId
import sys
import os

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
    reels: Dict[str, Any]
    tryons: Dict[str, Any]
    photoshoot: Dict[str, Any]
    status: str

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
        
        # Call content generation function directly
        content_result = await process_content_generation(
            image_base64, product_id, title, price, description
        )
        
        # Update processing status
        processing_status = {
            content_result.api_name: "completed" if content_result.success else "failed"
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

@router.get("/product/{object_id}", response_model=CompleteProductResponse)
async def get_complete_product(object_id: str):
    """
    Get product processing status and AI service results by object_id.
    Returns only: content_generation, reels, tryons, photoshoot, and status.
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
        
        # Extract only the required fields
        content_generation = product.get("content_generation", {})
        reels = product.get("reels", {})
        tryons = product.get("tryons", {})
        photoshoot = product.get("photoshoot", {})
        status = product.get("processing_status", "unknown")
        
        logger.info(f"Successfully retrieved product {object_id} with status: {status}")
        
        return CompleteProductResponse(
            content_generation=content_generation,
            reels=reels,
            tryons=tryons,
            photoshoot=photoshoot,
            status=status
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching product {object_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to retrieve product: {str(e)}")

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
            "configured_services": ["content_generation", "reels", "tryons", "photoshoot"],
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        } 