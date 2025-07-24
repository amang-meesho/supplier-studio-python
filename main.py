from fastapi import FastAPI

# Create FastAPI instance
app = FastAPI(
    title="Hello World API",
    description="A simple FastAPI Hello World application",
    version="1.0.0"
)

# Root endpoint
@app.get("/")
async def read_root():
    return {"message": "Hello World from FastAPI!"}

# Parameterized greeting endpoint
@app.get("/hello/{name}")
async def say_hello(name: str):
    return {"message": f"Hello {name}!"}

# Health check endpoint
@app.get("/health")
async def health_check():
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 