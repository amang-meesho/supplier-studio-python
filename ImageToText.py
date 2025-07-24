from PIL import Image
from google import genai
import os
import requests
from io import BytesIO
from dotenv import load_dotenv
from veo_video_generator import VeoVideoGenerator

# Load environment variables from .env file
load_dotenv()

# Set the environment variable that Google AI SDK expects
os.environ['GOOGLE_API_KEY'] = os.getenv('GOOGLE_API_KEY')

IMAGE_TO_TEXTMODEL = "gemini-2.5-pro"

PROMPT_IMAGE_TO_TEXT = """You are a fashion creative director for a video ad generation tool used in a fashion e-commerce platform.

Given an image of a clothing product (such as a dress, kurta, t-shirt, saree, or jacket), write a visually rich, aspirational, and emotionally engaging scene that can be used to generate an 8-second short video ad creative.

Take **extra care** to preserve **all product-specific details exactly as shown in the image** — including fabric type, color tones, stitching, embroidery, patterns, texture, silhouette, and design features. The generated video prompt must reflect the **exact same garment** seen in the image, without stylistic reinterpretation or omission.

The video will have **two clips**:
1. **0 to 4 seconds**: A wide shot clearly showcasing the entire outfit on a model or mannequin in a lifestyle setting.
2. **4 to 8 seconds**: A close-up shot capturing intricate product features such as fabric weave, embroidery, labels, or stitching.

Describe:
- The setting or context (e.g., festive, street-style, casual day out)
- The mood and emotion of the scene (e.g., confidence, grace, comfort)
- Lighting and background setup
- Camera movements (wide pan, slow twirl, close-in texture reveal)
- Optional music/emotion tones (e.g., playful, elegant, cinematic)
- Final moment idea: tagline, brand impression, or fade-out

Output should be formatted as a detailed natural-language prompt suitable for input into a video generation model like Google Veo.

The goal is to generate a high-quality, fashion-forward video ad that captures **exactly** what’s shown in the product image, with high fidelity and emotional resonance.
Output only the raw scene description suitable for text-to-video generation. Do not include explanations or assistant commentary.
"""

client = genai.Client()

def count_words(text):
    """Count the number of words in a text string."""
    if not text:
        return 0
    return len(text.split())

def analyze_image(image, max_retries=5, min_words=50):
    
    if image is None:
        print("No image provided")
        return None
    
    print(f"Image loaded successfully: {image.size} pixels")
    
    for attempt in range(max_retries):
        try:
            # Generate content using Gemini
            if attempt == 0:
                print("Analyzing image with Gemini...")
            else:
                print(f"Retry attempt {attempt + 1}/{max_retries} (previous response too short)...")
            
            print(PROMPT_IMAGE_TO_TEXT)
            response = client.models.generate_content(
                model = IMAGE_TO_TEXTMODEL,
                contents=[image, PROMPT_IMAGE_TO_TEXT]
            )
            
            result_text = response.text
            word_count = count_words(result_text)
            
            print(f"Response received: {word_count} words")
            
            # Check if response meets minimum word requirement
            if word_count >= min_words:
                print(f"Response meets minimum word requirement ({min_words} words)")
                break
            else:
                print(f"Response too short ({word_count} words < {min_words} required)")
                if attempt < max_retries - 1:
                    print("Retrying with same prompt...")
                else:
                    print(f"Max retries ({max_retries}) reached. Returning short response.")
                    break
            
        except Exception as e:
            print(f"Error analyzing image (attempt {attempt + 1}): {e}")
            if attempt == max_retries - 1:
                return None
            print("🔄 Retrying...")
    
    generate_video(result_text)

    return result_text

def generate_video(prompt):
    if prompt:
        print("\n" + "="*60)
        print("🎬 STARTING VIDEO GENERATION")
        print("="*60)

        # Configuration for video generation
        ACCESS_TOKEN = os.getenv('GOOGLE_ACCESS_TOKEN')

        if not ACCESS_TOKEN:
            print("❌ Error: GOOGLE_ACCESS_TOKEN not found in environment variables")
            print("Please add GOOGLE_ACCESS_TOKEN to your .env file")
            exit(1)

        try:
            # Initialize video generator
            generator = VeoVideoGenerator(ACCESS_TOKEN)

            print(f"📝 Using prompt ({count_words(prompt)} words):")
            print(f"   {prompt[:100]}{'...' if len(prompt) > 100 else ''}")

            # Call generate_video method
            operation_id = generator.generate_video(prompt)

            if operation_id:
                print(f"✅ Video generation started successfully!")
                print(f"🆔 Operation ID: {operation_id}")

                with open("video_operation_id.txt", "w") as f:
                    f.write(operation_id)
                print(f"💾 Operation ID saved to: video_operation_id.txt")

                # Optional: Wait for completion (uncomment if you want to wait)
                """
                print("\n⏰ Waiting for video generation to complete...")
                result_data = generator.wait_for_completion(operation_id, max_wait_time=600)
                
                if result_data and result_data["status"] == "success":
                    videos = result_data.get("videos", [])
                    if videos:
                        saved_files = generator.save_videos(videos, "fashion_video")
                        print(f"🎥 Videos saved: {saved_files}")
                    else:
                        print("⚠️ No videos found in result")
                else:
                    print("❌ Video generation failed or timed out")
                """

            else:
                print("❌ Failed to start video generation")

        except Exception as e:
            print(f"❌ Error during video generation: {e}")

    else:
        print("❌ No result available for video generation")


def analyze_image_from_url(image_url, prompt="Tell me about this image", max_retries=5, min_words=50):
    """
    Analyze an image from URL using Gemini with fallback for short responses.
    
    Args:
        image_url (str): The URL of the image
        prompt (str): The prompt/question about the image
        max_retries (int): Maximum number of retry attempts if response is too short
        min_words (int): Minimum word count required for a valid response
        
    Returns:
        str: The AI's response or None if failed
    """
    print(f"Fetching image from: {image_url}")
    
    image = fetch_image_from_url(image_url)
    
    if image is None:
        print("Failed to fetch image from URL")
        return None
    
    # Use the new analyze_image function
    return analyze_image(image, max_retries, min_words)

