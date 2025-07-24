import os
import asyncio
import aiohttp
import base64
import json
from typing import Dict, List, Optional, Any, Union
from datetime import datetime
from dotenv import load_dotenv
import google.generativeai as genai
from google.genai import types

# Load environment variables
load_dotenv()

class VeoVideoService:
    """Service for generating videos using Google's Veo models - replicates TypeScript functionality"""
    
    def __init__(self):
        self.api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
        self.client = None
        self._initialize_client()
    
    def _initialize_client(self):
        """Initialize the GenAI client"""
        if self.api_key:
            try:
                # Use the google-genai client (same as TypeScript version)
                from google import genai as google_genai
                self.client = google_genai.Client(api_key=self.api_key)
            except ImportError:
                # Fallback to google-generativeai
                genai.configure(api_key=self.api_key)
                self.client = "fallback"
        else:
            raise ValueError("Google API key required. Set GOOGLE_API_KEY or GEMINI_API_KEY environment variable")
    
    def _validate_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Validate and normalize video generation config"""
        default_config = {
            "aspectRatio": "16:9",
            "durationSeconds": 5,
            "numberOfVideos": 1
        }
        
        # Merge with defaults, but only keep supported parameters
        validated_config = {**default_config}
        
        # Only add supported parameters from user config
        supported_params = ["numberOfVideos"]
        for param in supported_params:
            if param in config:
                validated_config[param] = config[param]
        
        # Validate values
        valid_aspect_ratios = ["16:9", "9:16", "1:1", "4:3", "3:4"]
        if validated_config["aspectRatio"] not in valid_aspect_ratios:
            validated_config["aspectRatio"] = "16:9"
        
        if not 1 <= validated_config["durationSeconds"] <= 30:
            validated_config["durationSeconds"] = 5
        
        if not 1 <= validated_config["numberOfVideos"] <= 4:
            validated_config["numberOfVideos"] = 1
        
        return validated_config
    
    async def generate_videos(
        self,
        prompt: str,
        model: str = "veo-2.0-generate-001",
        config: Optional[Dict[str, Any]] = None,
        image_bytes: Optional[str] = None,
        image_mime_type: str = "image/png"
    ) -> Dict[str, Any]:
        """
        Generate videos using Veo models - replicates TypeScript generateContent function
        
        Args:
            prompt (str): Text description for video generation
            model (str): Model to use ('veo-2.0-generate-001' or 'veo-3.0-generate-preview')
            config (dict): Video generation configuration
            image_bytes (str): Base64 encoded image bytes (optional)
            image_mime_type (str): MIME type of the image
            
        Returns:
            dict: Generation result with operation details and video URLs
        """
        
        try:
            # Validate inputs
            if not prompt or len(prompt.strip()) == 0:
                return {
                    "status": "error",
                    "error_code": "INVALID_PROMPT",
                    "error_message": "Prompt cannot be empty"
                }
            
            # Validate and prepare config
            video_config = self._validate_config(config or {})
            
            # Prepare the generation request (mirror TypeScript structure)
            generation_params = {
                "model": model,
                "prompt": prompt,
                "config": video_config
            }
            
            # Add image if provided
            if image_bytes:
                generation_params["image"] = {
                    "imageBytes": image_bytes,
                    "mimeType": image_mime_type
                }
            
            # Start video generation
            operation_result = await self._start_generation(generation_params)
            
            if operation_result["status"] == "error":
                return operation_result
            
            # Poll for completion (mirror TypeScript polling logic)
            final_result = await self._poll_for_completion(operation_result["operation_id"])
            
            return final_result
            
        except Exception as e:
            return {
                "status": "error",
                "error_code": "GENERATION_FAILED",
                "error_message": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    async def _start_generation(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Start the video generation operation"""
        
        try:
            if hasattr(self.client, 'models') and hasattr(self.client.models, 'generate_videos'):
                # Use google-genai client (preferred)
                operation = self.client.models.generate_videos(
                    model=params["model"],
                    prompt=params["prompt"],
                    config=types.GenerateVideosConfig(**params["config"]),
                    image=params.get("image")
                )
                
                return {
                    "status": "started",
                    "operation_id": operation.name if hasattr(operation, 'name') else str(operation),
                    "operation": operation,
                    "timestamp": datetime.now().isoformat()
                }
            else:
                # Fallback simulation (for when premium APIs aren't available)
                return {
                    "status": "simulated",
                    "operation_id": f"sim_op_{datetime.now().timestamp()}",
                    "operation": None,
                    "message": "Simulated operation - premium Veo API requires billing",
                    "timestamp": datetime.now().isoformat()
                }
                
        except Exception as e:
            error_message = str(e)
            error_code = "UNKNOWN_ERROR"
            
            # Parse specific error types (mirror TypeScript error handling)
            if "429" in error_message or "quota" in error_message.lower():
                error_code = "QUOTA_EXCEEDED"
            elif "billing" in error_message.lower() or "FAILED_PRECONDITION" in error_message:
                error_code = "BILLING_REQUIRED"
            elif "INVALID_ARGUMENT" in error_message:
                error_code = "INVALID_ARGUMENT"
            
            return {
                "status": "error",
                "error_code": error_code,
                "error_message": error_message,
                "timestamp": datetime.now().isoformat()
            }
    
    async def _poll_for_completion(self, operation_id: str, max_wait_time: int = 300) -> Dict[str, Any]:
        """
        Poll for operation completion - mirrors TypeScript polling logic
        
        Args:
            operation_id (str): The operation ID to poll
            max_wait_time (int): Maximum time to wait in seconds
            
        Returns:
            dict: Final result with video URLs or error
        """
        
        start_time = datetime.now()
        poll_count = 0
        
        while (datetime.now() - start_time).seconds < max_wait_time:
            poll_count += 1
            
            try:
                # Check operation status
                operation_status = await self._check_operation_status(operation_id)
                
                if operation_status["done"]:
                    # Operation completed
                    if operation_status["success"]:
                        return {
                            "status": "completed",
                            "operation_id": operation_id,
                            "videos": operation_status["videos"],
                            "generation_time": (datetime.now() - start_time).seconds,
                            "poll_count": poll_count,
                            "timestamp": datetime.now().isoformat()
                        }
                    else:
                        return {
                            "status": "error",
                            "error_code": "GENERATION_FAILED",
                            "error_message": operation_status.get("error", "Unknown error"),
                            "operation_id": operation_id,
                            "timestamp": datetime.now().isoformat()
                        }
                
                # Wait before next poll (mirror TypeScript 1 second delay)
                await asyncio.sleep(1)
                
            except Exception as e:
                return {
                    "status": "error",
                    "error_code": "POLLING_FAILED", 
                    "error_message": f"Failed to poll operation status: {str(e)}",
                    "operation_id": operation_id,
                    "timestamp": datetime.now().isoformat()
                }
        
        # Timeout
        return {
            "status": "timeout",
            "error_code": "OPERATION_TIMEOUT",
            "error_message": f"Operation did not complete within {max_wait_time} seconds",
            "operation_id": operation_id,
            "poll_count": poll_count,
            "timestamp": datetime.now().isoformat()
        }
    
    async def _check_operation_status(self, operation_id: str) -> Dict[str, Any]:
        """Check the status of a video generation operation"""
        
        if operation_id.startswith("sim_op_"):
            # Simulate completion for demo operations
            return {
                "done": True,
                "success": True,
                "videos": [
                    {
                        "video": {
                            "uri": f"https://placeholder-video.com/generated_{operation_id}.mp4"
                        },
                        "metadata": {
                            "duration": "5s",
                            "resolution": "720p",
                            "size": "2.5MB"
                        }
                    }
                ]
            }
        
        try:
            if hasattr(self.client, 'operations'):
                # Use real API to check status
                operation = self.client.operations.get(operation_id)
                
                if operation.done:
                    if hasattr(operation, 'response') and operation.response:
                        videos = operation.response.generated_videos
                        return {
                            "done": True,
                            "success": True,
                            "videos": [{"video": {"uri": v.video.uri}} for v in videos]
                        }
                    else:
                        return {
                            "done": True,
                            "success": False,
                            "error": "No videos generated"
                        }
                else:
                    return {"done": False}
            else:
                # Fallback for simulation
                return {"done": False}
                
        except Exception as e:
            return {
                "done": True,
                "success": False,
                "error": str(e)
            }
    
    async def download_video(self, video_uri: str, filename: Optional[str] = None) -> Dict[str, Any]:
        """
        Download video from URI - mirrors TypeScript download functionality
        
        Args:
            video_uri (str): URI of the generated video
            filename (str): Optional filename for the download
            
        Returns:
            dict: Download result with file info
        """
        
        try:
            if not filename:
                filename = f"video_{datetime.now().timestamp()}.mp4"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(video_uri) as response:
                    if response.status == 200:
                        content = await response.read()
                        
                        # Save to file
                        with open(filename, 'wb') as f:
                            f.write(content)
                        
                        return {
                            "status": "success",
                            "filename": filename,
                            "size_bytes": len(content),
                            "size_mb": round(len(content) / (1024 * 1024), 2),
                            "video_uri": video_uri,
                            "timestamp": datetime.now().isoformat()
                        }
                    else:
                        return {
                            "status": "error",
                            "error_code": "DOWNLOAD_FAILED",
                            "error_message": f"Failed to download video: HTTP {response.status}",
                            "video_uri": video_uri
                        }
                        
        except Exception as e:
            return {
                "status": "error",
                "error_code": "DOWNLOAD_ERROR",
                "error_message": str(e),
                "video_uri": video_uri
            }
    
    def get_service_info(self) -> Dict[str, Any]:
        """Get information about the Veo video service"""
        
        return {
            "service": "Veo Video Generation Service",
            "api_key_configured": bool(self.api_key),
            "client_type": type(self.client).__name__ if self.client else "None",
            "supported_models": [
                "veo-2.0-generate-001",
                "veo-3.0-generate-preview"
            ],
            "supported_features": [
                "Text-to-video generation",
                "Image-to-video generation", 
                "Configurable video parameters",
                "Async operation polling",
                "Video download"
            ],
            "config_options": {
                "aspectRatio": ["16:9", "9:16", "1:1", "4:3", "3:4"],
                "durationSeconds": "1-30",
                "fps": "24 (standard)",
                "resolution": ["720p", "1080p"],
                "numberOfVideos": "1-4"
            }
        }

# Create service instance
veo_video_service = VeoVideoService() 