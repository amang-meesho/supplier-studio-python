from PIL import Image
from google import genai
import os
import requests
from io import BytesIO
from dotenv import load_dotenv
from MongoRepo import MongoRepo
from veo_video_generator import VeoVideoGenerator

# Load environment variables from .env file
load_dotenv()

# Set the environment variable that Google AI SDK expects
google_api_key = 'AIzaSyBvQwh-uTo_sfgFUWClLjDvSp7c7swqjg4'  # Hardcode the API key
os.environ['GOOGLE_API_KEY'] = google_api_key

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

def analyze_image(image, objectId=None, max_retries=5, min_words=50):
    
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

    operation_name = generate_video(result_text)

    # Update MongoDB with operation_id if objectId is provided
    if objectId and operation_name:
        try:
            mongo_repo = MongoRepo()
            success = mongo_repo.update_gen_reel(objectId, operation_name)
            if success:
                print(f"✅ Successfully updated MongoDB document {objectId} with operation_name: {operation_name}")
            else:
                print(f"❌ Failed to update MongoDB document {objectId}")
            mongo_repo.close_connection()
        except Exception as e:
            print(f"❌ Error updating MongoDB: {e}")

    return result_text, operation_name

def generate_video(prompt):
    if prompt:
        print("\n" + "="*60)
        print("🎬 STARTING VIDEO GENERATION")
        print("="*60)

        # Configuration for video generation
        ACCESS_TOKEN = 'ya29.A0AS3H6Nz_P1HAXQUmkK37vokZa2HnJtUr0H5VQh9k_DyMslo2jCep4A33-6YvmTChBeuHm-9DdMw7LQC2iDmUFO7R4870wbTP-BbPYjMIbJSrRnlgmNMT7GvwefV_o3eQ1XcJnUkL_Qfm2ODKpMhK97L9-ce0C1slkIvDbjk0Oku0Q-NivaGKH-s71Mq1oht-wFEmDGt-9c6p2xwpkkKSVscML9_Ri-Z4QM2dYKZiEweNxThIo5aRwW1YC40uVXxt6bqYD0TfgDUFsua74fyhzxqJhQlRRn5rJlcrfvePpMaOHHVPEG0SrCX-31Ww6OYvJhXbftLvNc6lFh4fvzagdGF9KgLjKHvOU7GYaCgYKAZkSARESFQHGX2MiuwvuZ8Tb_waj7zc4FxtMLQ0363'
        print(f"ACCESS_TOKEN: {ACCESS_TOKEN}")
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
            operation_name = generator.generate_video(prompt)

            if operation_name:
                print(f"🆔 Operation ID: {operation_name}")
                return operation_name
            else:
                print("❌ Failed to start video generation")

        except Exception as e:
            print(f"❌ Error during video generation: {e}")

    else:
        print("❌ No result available for video generation")
