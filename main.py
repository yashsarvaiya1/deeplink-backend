import uvicorn
from fastapi import FastAPI
from app.routers import users, referral

app = FastAPI(title="Referral Deep Link Backend")

app.include_router(users.router)
app.include_router(referral.router)

@app.get("/")
async def root():
    return {"message": "Referral Deep Link Backend is running 🚀"}
