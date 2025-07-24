from pymongo import MongoClient
from bson import ObjectId
from dotenv import load_dotenv
import os
from typing import Optional

# Load environment variables
load_dotenv()

OPERATION_NAME_COLUMN = "operation_name"

class MongoRepo:
    def __init__(self):
        """Initialize MongoDB connection"""
        self.mongo_url = os.getenv('MONGODB_URL')
        if not self.mongo_url:
            raise ValueError("MONGODB_URL not found in environment variables")
        
        self.client = MongoClient(self.mongo_url)
        # You can specify your database name here
        self.db_name = os.getenv('MONGODB_DATABASE')
        self.collection_name = os.getenv('MONGODB_COLLECTION')
        
        self.db = self.client[self.db_name]
        self.collection = self.db[self.collection_name]
        
        print(f"Connected to MongoDB: {self.db_name}.{self.collection_name}")
    
    def update_gen_reel(self, object_id: str, operation_id: str) -> bool:
        """
        Update the gen_reel field with operation_id for the document with given object_id
        
        Args:
            object_id (str): The objectId to find the document
            operation_id (str): The operation_id to store in gen_reel field
            
        Returns:
            bool: True if update was successful, False otherwise
        """
        try:
            print(f"Updating document with objectId: {object_id}")
            print(f"Setting gen_reel to: {operation_id}")
            
            # Update the document
            result = self.collection.update_one(
                {"_id": ObjectId(object_id)},  # Filter by objectId
                {"$set": {
                    OPERATION_NAME_COLUMN: operation_id
                    }}  # Set gen_reel field
            )
            
            if result.matched_count > 0:
                print(f"✅ Successfully updated document. Modified count: {result.modified_count}")
                return True
            else:
                print(f"❌ No document found with objectId: {object_id}")
                return False
                
        except Exception as e:
            print(f"❌ Error updating MongoDB document: {e}")
            return False
    
    def get_document_by_id(self, object_id: str) -> Optional[dict]:
        """
        Retrieve a document by its objectId
        
        Args:
            object_id (str): The objectId to find the document
            
        Returns:
            dict: The document if found, None otherwise
        """
        try:
            document = self.collection.find_one({"_id": object_id})
            if document:
                print(f"✅ Found document with objectId: {object_id}")
                return document
            else:
                print(f"❌ No document found with objectId: {object_id}")
                return None
                
        except Exception as e:
            print(f"❌ Error fetching document from MongoDB: {e}")
            return None
    

    
    def close_connection(self):
        """Close MongoDB connection"""
        if self.client:
            self.client.close()
            print("MongoDB connection closed")
