from fastapi import APIRouter

router = APIRouter(prefix="/users", tags=["users"])

@router.get("/{user_id}")
def read_user(user_id: int):
    return {"user_id": user_id}

@router.post("/")
def create_user(user: dict):
    return {"message": "User created"}