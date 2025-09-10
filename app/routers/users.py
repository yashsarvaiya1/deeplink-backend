from fastapi import APIRouter, HTTPException, status
from app.models.user import UserCreate, UserOut
from app.services import user_service

router = APIRouter(prefix="/users", tags=["Users"])

@router.post("/", response_model=UserOut, status_code=status.HTTP_201_CREATED)
async def create_user(payload: UserCreate):
    username = payload.username.strip().lower()
    if not username:
        raise HTTPException(status_code=400, detail="username required")
    exists = await user_service.user_exists(username)
    if exists:
        raise HTTPException(status_code=409, detail="username already exists")
    await user_service.create_user(username, payload.name)
    user = await user_service.get_user(username)
    return user

@router.get("/{username}", response_model=UserOut)
async def get_user(username: str):
    username = username.strip().lower()
    user = await user_service.get_user(username)
    if not user:
        raise HTTPException(status_code=404, detail="user not found")
    return user
