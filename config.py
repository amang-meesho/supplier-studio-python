import os
from typing import Optional
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Settings:
    # MongoDB Configuration
    MONGODB_URL: str = "mongodb+srv://meesho:ES4AHZ7FkR6ggFjW@cluster0.eexndjk.mongodb.net/"
    DATABASE_NAME: str = "meesho_supplier_ai"
    
    # API Configuration
    API_TITLE: str = os.getenv("API_TITLE", "Meesho Supplier AI Studio")
    API_VERSION: str = os.getenv("API_VERSION", "1.0.0")
    API_DESCRIPTION: str = os.getenv("API_DESCRIPTION", "AI-powered content generation and tools for Meesho sellers")

settings = Settings() 