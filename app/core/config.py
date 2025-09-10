import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    PROJECT_NAME: str = "Referral Deep Link Backend"
    # Base HTTP(S) url used to build referral links; set to your public domain in production
    BASE_URL: str = os.getenv("BASE_URL", "http://127.0.0.1:8000")
    LINK_TTL: int = int(os.getenv("LINK_TTL", 60 * 60 * 24 * 30))  # default 30 days
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    # Your app IDs for store redirects (change these to your real ids)
    ANDROID_PACKAGE_NAME: str = os.getenv("ANDROID_PACKAGE_NAME", "com.yourapp.package")
    IOS_APP_ID: str = os.getenv("IOS_APP_ID", "id123456789")
    # What to return for unknown token
    FALLBACK_URL: str = os.getenv("FALLBACK_URL", "https://yourdomain.com")

settings = Settings()
