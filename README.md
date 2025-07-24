# FastAPI Hello World Application

A simple Hello World application built with FastAPI.

## Setup

1. Install the required dependencies:
```bash
pip install -r requirements.txt
```

## Running the Application

First, activate the virtual environment, then start the server:

```bash
# Activate virtual environment
source venv/bin/activate

# Start the server
python main.py
# OR
uvicorn main:app --reload
```

The application will be available at: http://localhost:8000

## Available Endpoints

- **GET /** - Returns a simple "Hello World" message
- **GET /hello/{name}** - Returns a personalized greeting
- **GET /health** - Health check endpoint
- **GET /docs** - Interactive API documentation (Swagger UI)
- **GET /redoc** - Alternative API documentation

## Example Usage

```bash
# Hello World endpoint
curl http://localhost:8000/

# Personalized greeting
curl http://localhost:8000/hello/John

# Health check
curl http://localhost:8000/health
```

## API Documentation

Once the server is running, you can access the interactive API documentation at:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc 