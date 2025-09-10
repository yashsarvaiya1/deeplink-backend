from pydantic import BaseModel

class UserCreate(BaseModel):
    username: str
    name: str

class UserOut(BaseModel):
    username: str
    name: str
    total_referrals: int = 0
    referral_token: str | None = None
