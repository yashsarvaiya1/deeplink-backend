import secrets, time, urllib.parse
from app.core.redis_client import redis_client
from app.core.config import settings
from app.services import user_service

REF_KEY_PREFIX = "ref:"

def _generate_token(nbytes: int = 6) -> str:
    # token_urlsafe(6) is short but URL-safe; adjust if you want longer tokens
    return secrets.token_urlsafe(nbytes)

async def create_or_replace_referral_for_user(username: str) -> tuple[str, str]:
    """
    Creates a new referral token for the given username.
    If user already had a token, invalidate (delete) the old token entry and replace it.
    Returns (token, url)
    """
    # ensure user exists
    user = await user_service.get_user(username)
    if not user:
        raise ValueError("user_not_found")

    # if user has existing token, delete old ref mapping
    old_token = user.get("referral_token")
    if old_token:
        old_key = REF_KEY_PREFIX + old_token
        await redis_client.delete(old_key)

    token = _generate_token()
    key = REF_KEY_PREFIX + token
    now = int(time.time())
    mapping = {
        "referrer_username": username,
        "created_at": str(now)
    }
    await redis_client.hset(key, mapping=mapping)
    await redis_client.expire(key, settings.LINK_TTL)

    # set token on user
    await user_service.set_user_referral_token(username, token)

    url = f"{settings.BASE_URL}/referral/{urllib.parse.quote(token)}"
    return token, url

async def get_referral(token: str) -> dict | None:
    key = REF_KEY_PREFIX + token
    data = await redis_client.hgetall(key)
    if not data:
        return None
    return data

async def resolve_referral(token: str) -> tuple[str, int] | None:
    """
    Called when app reports install for token.
    Increments user's total_referrals and returns (username, new_total).
    Multi-use token is allowed.
    """
    ref = await get_referral(token)
    if not ref:
        return None
    username = ref.get("referrer_username")
    new_total = await user_service.increment_referrals(username)
    # We DO NOT delete referral token — multi-use allowed.
    return username, int(new_total)

# -------------------------
# IP-based Deferred Click Storage
# -------------------------

async def store_click_for_ip(ip: str, token: str) -> None:
    """
    Store token in Redis keyed by hashed IP for deferred retrieval.
    """
    await user_service.store_click_token(ip, token, settings.LINK_TTL)

async def get_click_for_ip(ip: str) -> str | None:
    """
    Retrieve token stored for a given IP.
    """
    return await user_service.get_click_token(ip)

async def clear_click_for_ip(ip: str) -> None:
    """
    Remove stored click for an IP after resolve.
    """
    await user_service.clear_click_token(ip)
