from pydantic import BaseModel

class ReferralCreateResponse(BaseModel):
    url: str
    token: str

class ReferralResolveOut(BaseModel):
    referrer_username: str
    total_referrals: int
