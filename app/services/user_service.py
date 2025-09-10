import time
from app.core.redis_client import redis_client

USER_KEY_PREFIX = "user:"
CLICK_PREFIX = "click:"  # For IP-based deferred token storage

# -------------------------
# User CRUD
# -------------------------

async def user_exists(username: str) -> bool:
    key = USER_KEY_PREFIX + username
    return await redis_client.exists(key) == 1

async def create_user(username: str, name: str) -> None:
    key = USER_KEY_PREFIX + username
    await redis_client.hset(key, mapping={
        "name": name,
        "total_referrals": "0",
        "referral_token": ""
    })

async def get_user(username: str) -> dict | None:
    key = USER_KEY_PREFIX + username
    data = await redis_client.hgetall(key)
    if not data:
        return None
    return {
        "username": username,
        "name": data.get("name"),
        "total_referrals": int(data.get("total_referrals", "0")),
        "referral_token": data.get("referral_token") or None
    }

async def increment_referrals(username: str) -> int:
    key = USER_KEY_PREFIX + username
    new_count = await redis_client.hincrby(key, "total_referrals", 1)
    return int(new_count)

async def set_user_referral_token(username: str, token: str) -> None:
    key = USER_KEY_PREFIX + username
    await redis_client.hset(key, "referral_token", token)

async def clear_user_referral_token(username: str) -> None:
    key = USER_KEY_PREFIX + username
    await redis_client.hset(key, "referral_token", "")

# -------------------------
# IP-based Deferred Token Storage
# -------------------------

def generate_ip_hash(ip: str) -> str:
    import hashlib
    return hashlib.sha256(ip.encode()).hexdigest()

async def store_click_token(ip: str, token: str, ttl: int) -> None:
    """
    Store token in Redis keyed by hashed IP for deferred retrieval.
    """
    ip_hash = generate_ip_hash(ip)
    click_key = CLICK_PREFIX + ip_hash
    await redis_client.set(click_key, token, ex=ttl)

async def get_click_token(ip: str) -> str | None:
    """
    Retrieve token stored for a given IP.
    """
    ip_hash = generate_ip_hash(ip)
    click_key = CLICK_PREFIX + ip_hash
    return await redis_client.get(click_key)

async def clear_click_token(ip: str) -> None:
    ip_hash = generate_ip_hash(ip)
    click_key = CLICK_PREFIX + ip_hash
    await redis_client.delete(click_key)
