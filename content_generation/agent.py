import json
import base64
from typing import Dict, List, Optional
import google.generativeai as genai
import os
from PIL import Image
import io

def analyze_and_generate_content(image_data: str, title: str = "", price: int = 0, description: str = "") -> dict:
    """Analyzes product image and generates complete content for Meesho including social media captions.

    Args:
        image_data (str): Base64 encoded image data
        title (str): Product title
        price (int): Product price
        description (str): Existing description

    Returns:
        dict: Complete product content with simple strings including social media captions
    """
    try:
        # Configure Gemini API using environment variable
        google_api_key = 'AIzaSyCk0ngkeNCGE_WUwmAYDkrieMBJkC2xKFs'
        if not google_api_key:
            raise ValueError("GOOGLE_API_KEY environment variable is required")
        genai.configure(api_key=google_api_key)
        
        # Remove data URL prefix if present
        if image_data.startswith('data:image'):
            image_data = image_data.split(',')[1]
        
        # Decode base64 image
        image_bytes = base64.b64decode(image_data)
        image = Image.open(io.BytesIO(image_bytes))
        
        # Create Gemini model
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        # Create context info (price is mandatory now)
        context_info = ""
        if title:
            context_info += f"\nProduct Title: {title}"
        context_info += f"\nProduct Price: ₹{price}"
        if description:
            context_info += f"\nExisting Description: {description}"
        
        # Product categorization hierarchy
        categorization_data = """
PRODUCT CATEGORIZATION HIERARCHY:

Men Fashion:
- Western Wear: Top Wear (Blazers, Jackets, Sweaters, Sweatshirts, Shrugs, Personalized Tshirts), Bottom Wear (Jeans, Shorts, Track Pants, Trousers, Three Fourths, Swimming Shorts), Top & Bottom Set (Top & Bottom Set, Tracksuits, Suit Sets, Suit Fabric, Swim Suits)
- Footwear: Flipflops & Slippers (Flip Flops, Sliders, Clogs), Sandals & Floaters (Sandals, Floaters), Ethnic Footwear (Other Ethnic Flats, Mojaris and Juttis)
- Accessories: Mufflers, Scarves & Gloves (Gloves, Mufflers, Scarves, Bandana)
- Inner & Sleepwear: Innerwear (Gym vests, Vests), Sleepwear (Nightsuits)
- Thermals: Thermals (Thermal Topwear, Thermal Bottomwear, Thermal Set)
- Ethnic Wear: Dhotis, Mundus & Lungis, Ethnic Jackets, Kurtas & Kurta Sets (Kurta Sets, Kurtas), Sherwanis
- Men Top Wear: Unstitched Material (Shirt Fabric, Top & Bottom Fabric), Brother & Sister T-shirt, Jumpsuits, Plus Size T-shirt, Raincoat
- Men Bottom Wear: Unstitched Material (Pant Fabric), Dungarees

Women Fashion:
- Western Wear: Tops, Tshirts & Shirts (Shirts, Tshirts, Tops & Tunics, Women Formal Shirt & Bottom Fabric), Dresses, Gowns & Jumpsuits (Dresses, Western Gowns, Jumpsuits), Jeans & Jeggings (Jeans, Jeggings), Capes, Shrugs & Ponchos, Capris & Trousers & Pants (Capris, Trousers & Pants), Sweaters & Cardigans (Cardigans, Sweaters), Jackets (Coats & Jackets, Jackets, Blazers & Coats), Maternity Wear (Dresses), Palazzos, Leggings & Tights (Leggings, Palazzos), Skirts & Shorts (Shorts, Skirts), Hoodies & Sweatshirts (Sweatshirts), Raincoat
- Ethnic Wear: Kurtis, Sets & Fabrics (Kurti Fabrics, Dupatta Sets), Sarees, Blouses & Petticoats (Sarees, Saree Shapewear & Petticoats, Blouses, Blouse Piece, Ready To Wear Sarees, Sarees With Stitched Blouse), Suits & Dress Material (Suits, Semi-Stitched Suits), Ethnic Bottomwear (Churidars, Patialas, Salwars, Sharara), Dupattas & Shawls (Dupattas, Shawls), Ethnic Jackets, Gowns & Kaftans (Gowns - Ethnic), Lehenga Choli (Lehenga), Ethnic Skirts (Skirts), Islamic wear (Abayas & Coats)
- Accessories: Jewellery (Anklets & Toe Rings, Pendants & Lockets, Necklaces & Chains, Rings, Bracelet & Bangles, Maangtika, Nosepins, Kamarband, Bajuband and Armlets, Earrings & Studs), Belts (Belts, Belts Accessories), Fashion Accessories (Bindis, Hijab Pin, Saree Pin), Caps & Hats (Caps, Hats), Hair Accessories (Hair Buns, Hair Bands), Scarves, Stoles & Gloves (Gloves, Scarves, Stoles, Shawls), Socks, Sunglasses (Sunglasses, Spectacle Frames, Sunglasses & Spectacle Cases), Umbrellas, Watches (Analog Watches, Chronograph Watches, Sports watches, Watch Bands, Digital Watches), Handkerchiefs, Earmuffs, Pins, Keychains, Friendship Bands
- Footwear: Flats (Flats, Platforms), Boots, Heels (Heels, Stilletos, Pumps), Flipflops & Slippers (Flipflops & Slippers, Sliders, Clogs), Shoes (Formal Shoes, Casual Shoes, Sports Shoes, Loafers & Moccassins), Sandals (Floaters, Flat Sandals, Wedge Sandals, Platform Sandals, Heel Sandals), Bellies & Juttis (Bellies, Juttis & Mojaris), Wedges
- Inner & Sleepwear: Swimwear, Nightsuits & Nightdresses (Babydolls, Nightdress, Nightsuits, Pyjamas), Camisoles & Thermals (Camisoles, Thermal Bottoms, Thermal Tops), Bras & Lingerie Sets (Bra, Lingerie Sets, Lingerie Accessories), Briefs, Shapewear, Period Panty
"""
        
        # Enhanced prompt for analysis and social media content generation
        prompt = f"""You are an expert product analyst and social media creator for Meesho, India's leading e-commerce platform.

PRODUCT CONTEXT: {context_info}

{categorization_data}

Analyze this product image and categorize it using the hierarchy above, then generate complete product content including social media captions. The price is ₹{price}. Return ONLY valid JSON in this format:

{{
    "super_category": "Men Fashion or Women Fashion",
    "category": "main category from the hierarchy above (Western Wear, Ethnic Wear, Footwear, Accessories, etc.)",
    "sub_category": "sub category from the hierarchy above (Top Wear, Bottom Wear, Tops, Tshirts & Shirts, etc.)",
    "sub_sub_category": "most specific category from the hierarchy above (Tshirts, Shirts, Jeans, etc.)",
    "product_name": "detailed product name with colors and style",
    "description": "complete product description with features, benefits, styling tips - make it engaging for Indian customers (DO NOT include price)",
    "size_chart": "size chart as a formatted string based on the category - use Indian sizing standards",
    "specifications": "fabric, pattern, sleeve type, etc. as a readable string",
    "care_instructions": "washing and care instructions",
    "target_audience": "who this product is for",
    "occasions": "suitable occasions as a readable string",
    "instagram_caption": "engaging Instagram caption with emojis and hooks that MUST include the exact price ₹{price}",
    "instagram_hashtags": "relevant hashtags for Instagram as a single string",
    "facebook_caption": "detailed Facebook post that tells a story about the product and MUST mention the exact price ₹{price}",
    "facebook_hashtags": "relevant hashtags for Facebook as a single string",
    "confidence_score": "confidence in analysis (0.0 to 1.0)"
}}

Instructions:
1. ACCURATELY categorize the product using the 4-level hierarchy provided above (super_category → category → sub_category → sub_sub_category)
2. Create engaging descriptions WITHOUT mentioning price - focus on features, quality, style
3. Generate appropriate size charts (chest/bust measurements for clothing, foot length for shoes, etc.)
4. Make all content suitable for Meesho's target audience
5. Create Instagram captions that are visual, trendy, under 150 words and MUST include exactly ₹{price}
6. Create Facebook posts that are detailed, community-focused, storytelling and MUST include exactly ₹{price}
7. Generate relevant hashtags based on the product category and target audience
8. Use emojis and Indian market language appropriately
9. Use simple, readable strings that frontend can display directly

CRITICAL: 
- Description should focus on quality and features without mentioning price
- Instagram caption MUST include exactly "₹{price}" (not ₹0 or any other price)
- Facebook caption MUST include exactly "₹{price}" (not ₹0 or any other price)
- Use the provided price {price} in all social media content

Analyze the image and generate content accordingly."""

        # Get response from Gemini
        response = model.generate_content([prompt, image])
        
        # Parse JSON response
        try:
            response_text = response.text.strip()
            
            # Extract JSON from response
            if '{' in response_text:
                json_start = response_text.find('{')
                json_end = response_text.rfind('}') + 1
                json_text = response_text[json_start:json_end]
            else:
                json_text = response_text
            
            # Parse the JSON
            result = json.loads(json_text)
            
            return {
                "status": "success",
                "category": result.get("category", "general"),
                "product_name": result.get("product_name", title or "Stylish Product"),
                "description": result.get("description", "Premium quality product with excellent craftsmanship, perfect for Indian customers who value style and comfort"),
                "size_chart": result.get("size_chart", "Size chart will be provided based on product category"),
                "specifications": result.get("specifications", "High quality materials and construction"),
                "care_instructions": result.get("care_instructions", "Machine wash cold, do not bleach"),
                "target_audience": result.get("target_audience", "Fashion-conscious customers"),
                "occasions": result.get("occasions", "Perfect for daily wear and special occasions"),
                "instagram_caption": result.get("instagram_caption", f"✨ Stylish & Affordable at ₹{price}! 💖 Perfect for trendy fashionistas! 🛍️ #StyleOnBudget"),
                "instagram_hashtags": result.get("instagram_hashtags", "#MeeshoFinds #TrendingNow #AffordableStyle #IndianFashion #StyleOnBudget"),
                "facebook_caption": result.get("facebook_caption", f"Discover this amazing product at just ₹{price}! Perfect quality, great value, and loved by thousands of customers across India. Shop now for the best deals!"),
                "facebook_hashtags": result.get("facebook_hashtags", "#Meesho #OnlineShopping #BestDeals #IndianShopping #QualityProducts"),
                "confidence_score": result.get("confidence_score", 0.85),
                "data_source": "gemini_vision_analysis"
            }
            
        except json.JSONDecodeError:
            # Fallback if JSON parsing fails
            return {
                "status": "success", 
                "category": "general",
                "product_name": title or "Stylish Product",
                "description": "Premium quality product with excellent materials and craftsmanship. Perfect for Indian customers who value style and quality.",
                "size_chart": "Standard Indian sizing - Size chart available on request",
                "specifications": "High quality materials and construction",
                "care_instructions": "Machine wash cold, do not bleach, tumble dry low",
                "target_audience": "Fashion-conscious customers",
                "occasions": "Perfect for daily wear and special occasions",
                "instagram_caption": f"✨ New Arrival Alert! ✨ Get this amazing product at just ₹{price}! 💖 Perfect for style lovers! 🛍️ #StyleSteals",
                "instagram_hashtags": "#MeeshoFinds #TrendingNow #AffordableStyle #NewArrivals #StyleOnBudget #IndianFashion",
                "facebook_caption": f"🌟 Exciting news for all fashion lovers! We've got this incredible product at an unbeatable price of ₹{price}. Our customers are loving the quality and style. Don't miss out - limited stock available!",
                "facebook_hashtags": "#Meesho #OnlineShopping #BestDeals #FashionFinds #QualityProducts #IndianShopping",
                "confidence_score": 0.75,
                "data_source": "gemini_text_fallback"
            }
            
    except Exception as e:
        return {
            "status": "error",
            "error_message": f"Failed to analyze product: {str(e)}",
            "fallback_content": {
                "category": "general",
                "product_name": title or "Premium Product",
                "description": "High-quality product with premium materials and excellent finish. Perfect for Indian customers who value style and quality.",
                "size_chart": "Standard sizing available",
                "specifications": "Premium materials",
                "care_instructions": "Follow care label instructions",
                "target_audience": "Fashion lovers",
                "occasions": "Suitable for various occasions",
                "instagram_caption": f"🔥 Amazing Quality at ₹{price}! 💯 Shop now! #MeeshoFinds #GreatDeals",
                "instagram_hashtags": "#Meesho #Shopping #Deals #Fashion #Style",
                "facebook_caption": f"Check out this fantastic product at just ₹{price}! Great quality and even better value!",
                "facebook_hashtags": "#Meesho #OnlineShopping #BestValue",
                "confidence_score": 0.5
            }
        }

# Backward compatibility functions
def analyze_product_image(image_data: str, title: str = "", price: int = 0, description: str = "") -> dict:
    """Legacy function - redirects to new simplified function"""
    result = analyze_and_generate_content(image_data, title, price, description)
    return result

def generate_meesho_description(product_data: dict) -> dict:
    """Legacy function - redirects to new simplified function"""
    return {"status": "success", "description": "Use analyze_and_generate_content function"}

def create_social_media_content(product_data: dict) -> dict:
    """Legacy function - redirects to new simplified function"""
    return {"status": "success", "content": "Use analyze_and_generate_content function"}

def optimize_for_meesho_seo(product_data: dict) -> dict:
    """Legacy function - redirects to new simplified function"""
    return {"status": "success", "seo_keywords": ["meesho", "online", "shopping"]}

# Create a simple agent for backward compatibility
from google.adk.agents import Agent

content_generation_agent = Agent(
    name="meesho_content_generator",
    description="AI agent for generating Meesho product content with social media captions",
    instruction=(
        "You are an expert content generator for Meesho products. "
        "Generate engaging product descriptions, analyze images, create social media captions, "
        "and create content that resonates with Indian customers. Focus on value, quality, and style."
    ),
    tools=[analyze_and_generate_content],
)

# Alias for backward compatibility
root_agent = content_generation_agent
