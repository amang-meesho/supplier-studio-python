import os
from typing import Optional

class Settings:
    # MongoDB Configuration
    MONGODB_URL: str = os.getenv("MONGODB_URL")
    DATABASE_NAME: str = os.getenv("DATABASE_NAME", "supplier_studio")
    
    # API Configuration
    API_TITLE: str = "Supplier Studio API"
    API_VERSION: str = "1.0.0"
    API_DESCRIPTION: str = "API for managing supplier catalog and products"

settings = Settings() 