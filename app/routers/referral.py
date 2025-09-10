from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import RedirectResponse, JSONResponse
from app.models.referral import ReferralCreateResponse, ReferralResolveOut
from app.services import referral_service, user_service
from app.core.config import settings
import urllib.parse

router = APIRouter(prefix="/referral", tags=["Referral"])

# -------------------------
# Create Referral
# -------------------------
@router.post("/{username}", response_model=ReferralCreateResponse)
async def create_referral(username: str):
    username = username.strip().lower()
    user = await user_service.get_user(username)
    if not user:
        raise HTTPException(status_code=404, detail="user not found")
    token, url = await referral_service.create_or_replace_referral_for_user(username)
    return {"url": url, "token": token}


# -------------------------
# Click / Redirect Handler
# -------------------------
@router.get("/{token}")
async def handle_redirect(token: str, request: Request):
    """
    Handle referral link clicks:
      - Store token keyed by IP for deferred retrieval
      - Redirect to App Store / Play Store / fallback page
    """
    ref = await referral_service.get_referral(token)
    if not ref:
        raise HTTPException(status_code=404, detail="invalid or expired token")

    ip = request.client.host or "0.0.0.0"
    await referral_service.store_click_for_ip(ip, token)

    ua = (request.headers.get("user-agent") or "").lower()
    is_android = "android" in ua and "mobile" in ua or "android" in ua and "mozilla" in ua
    is_ios = "iphone" in ua or "ipad" in ua or "ipod" in ua

    if is_android:
        referrer_val = urllib.parse.quote_plus(f"ref_token={token}")
        play_store_url = f"https://play.google.com/store/apps/details?id={settings.ANDROID_PACKAGE_NAME}&referrer={referrer_val}"
        return RedirectResponse(play_store_url)
    elif is_ios:
        app_store_url = f"https://apps.apple.com/app/{settings.IOS_APP_ID}?ref_token={token}"
        return RedirectResponse(app_store_url)
    else:
        return RedirectResponse(settings.FALLBACK_URL)


# -------------------------
# Check pending referral by IP
# -------------------------
@router.get("/check/{ip}")
async def check_referral(ip: str):
    """
    Mobile app calls this on first launch, passing its current IP.
    Backend hashes IP and retrieves any pending referral token.
    """
    token = await referral_service.get_click_for_ip(ip)
    if not token:
        return JSONResponse({"detail": "no referral found"}, status_code=404)
    # optional: delete click so it cannot be claimed multiple times
    await referral_service.clear_click_for_ip(ip)
    return {"token": token}


# -------------------------
# Resolve Referral
# -------------------------
@router.post("/resolve/{token}", response_model=ReferralResolveOut)
async def resolve_referral(token: str):
    """
    Mobile app calls this after install to increment referrer count.
    """
    res = await referral_service.resolve_referral(token)
    if not res:
        raise HTTPException(status_code=404, detail="invalid or expired token")
    username, new_total = res
    return {"referrer_username": username, "total_referrals": new_total}
