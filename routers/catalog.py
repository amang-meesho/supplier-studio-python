from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, HttpUrl
from typing import Optional
from motor.motor_asyncio import AsyncIOMotorClient
from bson import ObjectId
import os
import logging
from datetime import datetime

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/catalog-upload", tags=["catalog"])

# MongoDB connection
MONGODB_URL = os.getenv("MONGODB_URL")
if not MONGODB_URL:
    raise ValueError("MONGODB_URL environment variable is required")
logger.info("Connecting to MongoDB Atlas")
client = AsyncIOMotorClient(MONGODB_URL)
db = client.supplier_studio
products_collection = db.products
logger.info("MongoDB Atlas client initialized")

# Pydantic model for product upload
class ProductUpload(BaseModel):
    image_url: HttpUrl
    price: float
    title: str
    description: Optional[str] = None

# Pydantic model for response
class ProductResponse(BaseModel):
    product_id: str
    message: str

@router.post("/", response_model=ProductResponse)
async def upload_product(product: ProductUpload):
    """
    Upload a product to the catalog with image URL, price, title, and optional description.
    Returns the MongoDB document ID.
    """
    try:
        logger.info(f"Attempting to upload product: {product.title}")
        
        # Create product document
        product_doc = {
            "image_url": str(product.image_url),
            "price": product.price,
            "title": product.title,
            "description": product.description,
            "created_at": datetime.utcnow()
        }
        
        logger.info(f"Product document created: {product_doc}")
        
        # Test MongoDB connection
        try:
            await client.admin.command('ping')
            logger.info("MongoDB connection successful")
        except Exception as conn_error:
            logger.error(f"MongoDB connection failed: {conn_error}")
            raise HTTPException(status_code=500, detail=f"MongoDB connection failed: {str(conn_error)}")
        
        # Insert into MongoDB
        result = await products_collection.insert_one(product_doc)
        logger.info(f"Product inserted with ID: {result.inserted_id}")
        
        # Return the document ID
        return ProductResponse(
            product_id=str(result.inserted_id),
            message="Product uploaded successfully"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in upload_product: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to upload product: {str(e)}")