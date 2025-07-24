from fastapi import FastAPI
from routers import users, items, catalog

app = FastAPI()

app.include_router(users.router)
app.include_router(items.router)
app.include_router(catalog.router)


@app.get("/")
def read_root():
    return {"message": "Hello World"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 