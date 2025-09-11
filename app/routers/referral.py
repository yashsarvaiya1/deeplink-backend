from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import RedirectResponse, JSONResponse, HTMLResponse
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
      - Try to open installed app first, then redirect to store
    """
    ref = await referral_service.get_referral(token)
    if not ref:
        raise HTTPException(status_code=404, detail="invalid or expired token")

    ip = request.client.host or "0.0.0.0"
    await referral_service.store_click_for_ip(ip, token)

    ua = (request.headers.get("user-agent") or "").lower()
    
    # Improved Android detection
    is_android = ("android" in ua) and (
        "mobile" in ua or "tablet" in ua or "mozilla" in ua
    )
    
    # Improved iOS detection
    is_ios = any(device in ua for device in ["iphone", "ipad", "ipod"]) or (
        "mac os x" in ua and "mobile" in ua
    )

    # Extract app name from package name (e.g., "in.npswala.nps" -> "NPS")
    app_name = getattr(settings, 'APP_NAME', None)
    if not app_name:
        # Fallback: extract from package name if APP_NAME not set
        package_parts = settings.ANDROID_PACKAGE_NAME.split('.')
        app_name = package_parts[-1].upper()  # Get last part and uppercase
    
    # Extract custom scheme from package name or use APP_SCHEME if available
    app_scheme = getattr(settings, 'APP_SCHEME', None)
    if not app_scheme:
        # Fallback: use last part of package name as scheme
        package_parts = settings.ANDROID_PACKAGE_NAME.split('.')
        app_scheme = package_parts[-1].lower()  # Get last part and lowercase

    if is_android:
        # Try to open the app first with intent, then fallback to Play Store
        referrer_val = urllib.parse.quote_plus(f"ref_token={token}")
        
        # Create HTML page that tries app intent first, then Play Store
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <title>Opening {app_name} App...</title>
            <meta name="viewport" content="width=device-width, initial-scale=1">
            <style>
                body {{ 
                    font-family: Arial, sans-serif; 
                    text-align: center; 
                    padding: 50px 20px; 
                    background: #f5f5f5; 
                }}
                .loading {{ 
                    color: #666; 
                    font-size: 18px; 
                }}
                .spinner {{
                    border: 4px solid #f3f3f3;
                    border-top: 4px solid #3498db;
                    border-radius: 50%;
                    width: 40px;
                    height: 40px;
                    animation: spin 1s linear infinite;
                    margin: 20px auto;
                }}
                @keyframes spin {{
                    0% {{ transform: rotate(0deg); }}
                    100% {{ transform: rotate(360deg); }}
                }}
            </style>
        </head>
        <body>
            <div class="spinner"></div>
            <div class="loading">Opening {app_name} App...</div>
            <script>
                // Multiple approaches to open the app
                
                // Method 1: Custom scheme
                var customScheme = "{app_scheme}://referral?token={token}";
                
                // Method 2: Intent with package name
                var intentUrl = "intent://referral?token={token}#Intent;scheme={app_scheme};package={settings.ANDROID_PACKAGE_NAME};S.browser_fallback_url=https%3A%2F%2Fplay.google.com%2Fstore%2Fapps%2Fdetails%3Fid%3D{settings.ANDROID_PACKAGE_NAME}%26referrer%3D{referrer_val};end";
                
                // Method 3: Market intent (preferred for installed apps)
                var marketIntent = "market://details?id={settings.ANDROID_PACKAGE_NAME}&referrer={referrer_val}";
                
                // Method 4: Direct package launch intent
                var packageIntent = "intent:#Intent;package={settings.ANDROID_PACKAGE_NAME};scheme={app_scheme};S.ref_token={token};end";
                
                // Try custom scheme first
                var startTime = Date.now();
                var iframe = document.createElement('iframe');
                iframe.style.display = 'none';
                iframe.src = customScheme;
                document.body.appendChild(iframe);
                
                // Check if app opened (if user stays on page, app didn't open)
                var checkAppOpened = function() {{
                    if (Date.now() - startTime < 2500) {{
                        // Try package intent
                        try {{
                            window.location.href = packageIntent;
                        }} catch(e) {{
                            // Try intent URL as backup
                            window.location.href = intentUrl;
                        }}
                    }}
                }};
                
                // Final fallback to Play Store after 3 seconds
                setTimeout(function() {{
                    // Try market intent first (opens Play Store app)
                    try {{
                        window.location.href = marketIntent;
                    }} catch(e) {{
                        // If market intent fails, use web URL
                        window.location.href = "https://play.google.com/store/apps/details?id={settings.ANDROID_PACKAGE_NAME}&referrer={referrer_val}";
                    }}
                }}, 3000);
                
                setTimeout(checkAppOpened, 2000);
                
                // Hide loading message after 5 seconds and show manual link
                setTimeout(function() {{
                    document.querySelector('.loading').innerHTML = 'If the app didn\\'t open, <a href="https://play.google.com/store/apps/details?id={settings.ANDROID_PACKAGE_NAME}&referrer={referrer_val}">click here</a> to download {app_name}.';
                }}, 5000);
            </script>
        </body>
        </html>
        """
        
        return HTMLResponse(content=html_content)
        
    elif is_ios:
        # For iOS, create HTML that tries universal link first, then App Store
        universal_link_domain = getattr(settings, 'UNIVERSAL_LINK_DOMAIN', None)
        universal_link = f"https://{universal_link_domain}/referral/{token}" if universal_link_domain else None
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <title>Opening {app_name} App...</title>
            <meta name="viewport" content="width=device-width, initial-scale=1">
            <style>
                body {{ 
                    font-family: Arial, sans-serif; 
                    text-align: center; 
                    padding: 50px 20px; 
                    background: #f5f5f5; 
                }}
                .loading {{ 
                    color: #666; 
                    font-size: 18px; 
                }}
                .spinner {{
                    border: 4px solid #f3f3f3;
                    border-top: 4px solid #3498db;
                    border-radius: 50%;
                    width: 40px;
                    height: 40px;
                    animation: spin 1s linear infinite;
                    margin: 20px auto;
                }}
                @keyframes spin {{
                    0% {{ transform: rotate(0deg); }}
                    100% {{ transform: rotate(360deg); }}
                }}
            </style>
        </head>
        <body>
            <div class="spinner"></div>
            <div class="loading">Opening {app_name} App...</div>
            <script>
                // Try to open the app with custom scheme
                var appUrl = "{app_scheme}://referral?token={token}";
                
                var startTime = Date.now();
                
                // Try custom scheme first
                window.location.href = appUrl;
                
                // Check if still on page after attempt
                setTimeout(function() {{
                    if (Date.now() - startTime < 2500) {{
                        {"// Try universal link" if universal_link else "// No universal link configured"}
                        {f'window.location.href = "{universal_link}";' if universal_link else '// Skip universal link attempt'}
                    }}
                }}, 1500);
                
                // Final fallback to App Store after 3 seconds
                setTimeout(function() {{
                    window.location.href = "https://apps.apple.com/app/{settings.IOS_APP_ID}?ref_token={token}";
                }}, 3000);
                
                // Hide loading message after 5 seconds and show manual link
                setTimeout(function() {{
                    document.querySelector('.loading').innerHTML = 'If the app didn\\'t open, <a href="https://apps.apple.com/app/{settings.IOS_APP_ID}?ref_token={token}">click here</a> to download {app_name}.';
                }}, 5000);
            </script>
        </body>
        </html>
        """
        
        return HTMLResponse(content=html_content)
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
