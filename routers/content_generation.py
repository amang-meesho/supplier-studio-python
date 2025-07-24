from fastapi import APIRouter, HTTPException, File, UploadFile, Form
from pydantic import BaseModel
from typing import Optional, Dict, Any
import motor.motor_asyncio
import os
from datetime import datetime
import base64
import io
from PIL import Image
import sys
from bson import ObjectId
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add content_generation to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from content_generation.agent import (
    analyze_and_generate_content,
    content_generation_agent
)

router = APIRouter(prefix="/content", tags=["AI Content Generation"])

# MongoDB connection
import logging
logger = logging.getLogger(__name__)

# Hardcoded MongoDB configuration
MONGODB_URL = "mongodb+srv://meesho:ES4AHZ7FkR6ggFjW@cluster0.eexndjk.mongodb.net/"
DATABASE_NAME = "meesho_supplier_ai"

if not MONGODB_URL:
    raise ValueError("MONGODB_URL is required")

logger.info(f"Connecting to MongoDB database: {DATABASE_NAME}")
client = motor.motor_asyncio.AsyncIOMotorClient(MONGODB_URL)
db = client[DATABASE_NAME]
products_collection = db.products  # Changed from catalog to products to match main controller
generated_content_collection = db.generated_content
catalog_collection = db.catalog

# Pydantic models
class ProductResponse(BaseModel):
    success: bool
    content_id: str
    message: str


@router.post("/upload-and-generate")
async def upload_image_and_generate_content(
    file: UploadFile = File(...),
    title: str = Form(""),
    price: int = Form(...),  # Price is now mandatory
    description: str = Form(""),
    product_id: str = Form(None)  # Optional product_id for main controller
):
    """Upload an image and generate comprehensive product content for Meesho marketplace."""
    
    # Validate price
    if price <= 0:
        raise HTTPException(status_code=400, detail="Price must be greater than 0")
    
    # Validate file type (including AVIF)
    allowed_types = ['image/', 'application/']  # AVIF might come as application/octet-stream
    is_image = any(file.content_type.startswith(t) for t in allowed_types) or file.filename.lower().endswith(('.jpg', '.jpeg', '.png', '.gif', '.webp', '.avif'))
    
    if not is_image:
        raise HTTPException(status_code=400, detail="File must be an image (jpg, png, gif, webp, avif)")

    try:
        logger.info(f"Content generation request - title: {title}, price: {price}, product_id: {product_id}")
        
        # Read and encode image
        image_content = await file.read()
        image_base64 = base64.b64encode(image_content).decode('utf-8')
        image_format = file.content_type.split('/')[-1]
        logger.info(f"Image processed, size: {len(image_base64)}")

        # Analyze the uploaded image and generate all content in one go
        logger.info("Calling analyze_and_generate_content...")
        content_result = analyze_and_generate_content(
            image_base64, 
            title=title, 
            price=price, 
            description=description
        )
        logger.info(f"Content result status: {content_result.get('status')}")
        
        # Auto-generate title if not provided
        if not title and content_result.get("status") == "success":
            title = content_result.get("product_name", "Stylish Product")
        
        # Price is now mandatory, so we use the provided price directly

        # Handle content storage based on whether this is called from main controller or standalone
        if product_id:
            # Called from main controller - update the existing product document
            try:
                await products_collection.update_one(
                    {"_id": ObjectId(product_id)},
                    {
                        "$set": {
                            "content_generation": {
                                "generated_content": content_result,
                                "success": True,
                                "processed_at": datetime.utcnow()
                            },
                            "updated_at": datetime.utcnow()
                        }
                    }
                )
                content_id = product_id
                logger.info(f"Updated product {product_id} with content generation results")
            except Exception as db_error:
                logger.error(f"MongoDB update failed: {db_error}")
                content_id = "temp_id_" + str(int(datetime.utcnow().timestamp()))
        else:
            # Standalone call - create new document
            mongodb_document = {
                "title": title,
                "price": price,
                "description": description,
                "generated_content": content_result,
                "image_metadata": {
                    "filename": file.filename,
                    "size": len(image_base64),
                    "format": image_format,
                    "upload_timestamp": datetime.utcnow()
                },
                "created_at": datetime.utcnow()
            }
            
            try:
                result = await products_collection.insert_one(mongodb_document)
                content_id = str(result.inserted_id)
                logger.info(f"Created new content document with ID: {content_id}")
            except Exception as db_error:
                logger.error(f"MongoDB insertion failed: {db_error}")
                content_id = "temp_id_" + str(int(datetime.utcnow().timestamp()))

        # Return simplified response with social media content
        if content_result.get("status") == "success":
            return {
                "success": True,
                "content_id": content_id,
                "super_category": content_result.get("super_category"),
                "category": content_result.get("category"),
                "sub_category": content_result.get("sub_category"),
                "sub_sub_category": content_result.get("sub_sub_category"),
                "product_name": content_result.get("product_name"),
                "description": content_result.get("description"),
                "size_chart": content_result.get("size_chart"),
                "specifications": content_result.get("specifications"),
                "care_instructions": content_result.get("care_instructions"),
                "target_audience": content_result.get("target_audience"),
                "occasions": content_result.get("occasions"),
                "social_media": {
                    "instagram_caption": content_result.get("instagram_caption"),
                    "instagram_hashtags": content_result.get("instagram_hashtags"),
                    "facebook_caption": content_result.get("facebook_caption"),
                    "facebook_hashtags": content_result.get("facebook_hashtags")
                },
                "confidence_score": content_result.get("confidence_score"),
                "message": f"🎉 Successfully analyzed {file.filename} and generated content with social media captions for {title}!"
            }
        else:
            return {
                "success": False,
                "error": content_result.get("error_message"),
                "content_id": content_id,
                "message": "Analysis completed with fallback content"
            }

    except Exception as e:
        print(f"ERROR in content generation: {str(e)}")
        print(f"ERROR type: {type(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.get("/content/{content_id}")
async def get_generated_content(content_id: str):
    """
    Retrieve previously generated content by ID.
    """
    try:
        from bson import ObjectId
        
        content = await generated_content_collection.find_one({"_id": ObjectId(content_id)})
        if not content:
            raise HTTPException(status_code=404, detail="Content not found")
        
        # Convert ObjectId to string for JSON serialization
        content["_id"] = str(content["_id"])
        
        return {
            "success": True,
            "content": content
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve content: {str(e)}")




@router.get("/health")
async def health_check():
    """
    Health check endpoint for the content generation service.
    """
    try:
        # Test MongoDB connection
        await client.admin.command('ping')
        
        return {
            "status": "healthy",
            "service": "AI Content Generation",
            "database": "connected",
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        } 