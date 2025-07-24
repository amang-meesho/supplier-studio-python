from fastapi import FastAPI
from routers import users, items, catalog, video_generation, gemini, veo_video
from dotenv import load_dotenv
import os

# Load environment variables from .env file
load_dotenv()

app = FastAPI(
    title="Supplier Studio API",
    description="API for managing supplier catalog, products, AI video generation, Gemini AI content generation, and Veo video generation",
    version="1.0.0"
)

app.include_router(users.router)
app.include_router(items.router)
app.include_router(catalog.router)
app.include_router(video_generation.router)
app.include_router(gemini.router)
app.include_router(veo_video.router)


@app.get("/")
def read_root():
    return {"message": "Hello World"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 