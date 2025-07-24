#!/usr/bin/env python3
"""
Veo-2.0 Video Generation Class
Complete workflow: Prompt -> Generate -> Fetch -> Save Video
"""

import requests
import base64
import json
import time
from datetime import datetime
from typing import Optional, Dict, Any, List

TEXT_TO_VIDEO_MODEL = "veo-2.0-generate-001"
LOCATION_ID = "us-central1"
API_ENDPOINT = "https://us-central1-aiplatform.googleapis.com"

class VeoVideoGenerator:
    """
    Complete Veo-2.0 video generation workflow class.
    Handles prompt submission, operation tracking, and video retrieval.
    """
    
    def __init__(self, access_token: str, project_id: str = "meesho-hackmee-3-proj-49"):
        """
        Initialize the Veo Video Generator.
        
        Args:
            access_token (str): Google Cloud access token
            project_id (str): Google Cloud project ID
        """
        self.access_token = access_token
        self.project_id = project_id
        self.location_id = LOCATION_ID
        self.model_id = TEXT_TO_VIDEO_MODEL
        self.api_endpoint = API_ENDPOINT
        
        # Default parameters
        self.default_params = {
            "aspectRatio": "9:16",
            "sampleCount": 1,
            "durationSeconds": "8",
            "personGeneration": "allow_all",
            "addWatermark": True,
            "includeRaiReason": True,
            "generateAudio": False,
            "resolution": "720p",
            "storageUri": "gs://videobucketai1/videos/"
        }
    
    def print_status(self, message: str) -> None:
        """Print status message with timestamp."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] {message}")
    
    def generate_video(self, prompt: str, custom_params: Optional[Dict] = None) -> Optional[str]:
        """
        Generate a video from a text prompt.
        
        Args:
            prompt (str): The text prompt for video generation
            custom_params (dict, optional): Custom parameters to override defaults
            
        Returns:
            str: Operation ID if successful, None if failed
        """
        self.print_status(f"🎬 Starting video generation...")
        # self.print_status(f"📝 Prompt: {prompt[:100]}{'...' if len(prompt) > 100 else ''}")
        
        # Prepare parameters
        params = self.default_params.copy()
        if custom_params:
            params.update(custom_params)
        
        # Prepare request data
        url = f"{self.api_endpoint}/v1/projects/{self.project_id}/locations/{self.location_id}/publishers/google/models/{self.model_id}:predictLongRunning"
        
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {self.access_token}'
        }
        
        data = {
            "endpoint": f"projects/{self.project_id}/locations/{self.location_id}/publishers/google/models/{self.model_id}",
            "instances": [
                {
                    "prompt": prompt
                }
            ],
            "parameters": params
        }
        
        try:
            self.print_status("📡 Making API request...")
            response = requests.post(url, headers=headers, json=data)
            response.raise_for_status()
            # print(url)
            # print(headers)
            print(data)
            result = response.json()
            
            # Extract operation ID
            operation_name = result.get('name', '')
            if not operation_name:
                self.print_status("❌ No operation name in response")
                return None
            
            # Extract the operation ID (last part after /operations/)
            operation_id = operation_name.split('/operations/')[-1]
            
            self.print_status(f"✅ Video generation started!")
            self.print_status(f"🆔 Operation ID: {operation_id}")
            self.print_status(f"📋 Full operation name: {operation_name}")
            
            print(f"Operation ID: {operation_name}")
            return operation_id
            
        except requests.exceptions.RequestException as e:
            self.print_status(f"❌ API request failed: {e}")
            if hasattr(e, 'response') and e.response:
                self.print_status(f"Status: {e.response.status_code}")
                self.print_status(f"Response: {e.response.text}")
            return None
        except Exception as e:
            self.print_status(f"❌ Unexpected error: {e}")
            return None
    
# Example usage and testing
if __name__ == "__main__":
    # Configuration
    import os
    from dotenv import load_dotenv
    
    # Load environment variables
    load_dotenv()
    ACCESS_TOKEN = os.getenv('GOOGLE_ACCESS_TOKEN')
    
    if not ACCESS_TOKEN:
        print("❌ Error: GOOGLE_ACCESS_TOKEN not found in environment variables")
        print("Please add GOOGLE_ACCESS_TOKEN to your .env file")
        exit(1)
    
    # Initialize the generator
    generator = VeoVideoGenerator(ACCESS_TOKEN)
    
    print("\n" + "=" * 60)
    print("🎬 EXAMPLE 2: Manual Workflow")
    print("=" * 60)
    
    # Example 2: Manual workflow (generate now, fetch later)
    operation_id = generator.generate_video("A cat playing with a ball")
    
    if operation_id:
        print(f"🆔 Operation ID: {operation_id}")
        print("💡 You can fetch the result later using:")
        print(f"result = generator.fetch_video_result('{operation_id}')")
        
        # Optionally fetch immediately
        print("\n🔍 Fetching result immediately...")
        result = generator.fetch_video_result(operation_id)
        
        if result and result["status"] == "success":
            videos = result.get("videos", [])
            if videos:
                saved_files = generator.save_videos(videos, "manual_fetch")
                print(f"✅ Videos saved: {saved_files}")
        elif result and result["status"] == "running":
            print("⏳ Video is still generating...")
        else:
            print("❌ Failed to fetch result") 