import os
import random
import json
import time
from datetime import datetime

def lambda_handler(event, context):
    """
    Handles preflight requests for API Gateway.
    """
    # Get the origin from the request headers
    headers = event.get('headers', {}) or {}
    origin = headers.get('origin') or headers.get('Origin')
    path = event.get('path', 'unknown path')
    
    # Get environment
    env = os.getenv("ENV", "dev").lower()
    frontend_origin = os.getenv("FRONTEND_ORIGIN", "")
    
    # Define allowed origins based on environment
    allowed_origins = []
    
    # Always add the configured frontend origin if it exists
    if frontend_origin:
        allowed_origins.append(frontend_origin)
    
    # For non-production environments, allow localhost and made-something.com domains
    if env != "prod":
        # Add localhost with various ports
        for port in ["3000", "3001", "3002", "8000", "8080", ""]:
            port_suffix = f":{port}" if port else ""
            allowed_origins.append(f"http://localhost{port_suffix}")
            allowed_origins.append(f"http://127.0.0.1{port_suffix}")
        # Add made-something.com base and wildcard (multi-level subdomains)
        allowed_origins.append("https://*.made-something.com")
        allowed_origins.append("https://made-something.com")
        
    # Log the request for debugging
    print(f"Preflight request received from: {origin} for path: {path}")
    print(f"Allowed origins: {allowed_origins}")
    
    # Check if the origin is allowed
    access_control_origin = "*"  # Default for development if no origin
    
    if origin:
        # Check for exact matches first
        if origin in allowed_origins:
            access_control_origin = origin
        else:
            # Check for wildcard matches (for subdomains)
            for allowed in allowed_origins:
                if allowed.startswith("https://*.") and origin.startswith("https://"):
                    # Allow any subdomain depth: ensure the origin ends with the base domain
                    base_domain = allowed.replace("https://*.", "")
                    if origin.endswith(f".{base_domain}"):
                        access_control_origin = origin
                        break
    
    print(f"Setting Access-Control-Allow-Origin: {access_control_origin}")
    
    # Start timer for dramatic effect
    start_time = time.time()
    
    # Pretend we're doing something complex
    time.sleep(0.01)
    
    # Calculate processing time (for dramatic effect)
    processing_time = time.time() - start_time
    
    return {
        "statusCode": 200,
        "headers": {
            "Access-Control-Allow-Origin": access_control_origin,
            "Access-Control-Allow-Methods": "OPTIONS,POST,GET,PUT,DELETE,PATCH",
            "Access-Control-Allow-Headers": "Content-Type,Authorization,X-Amz-Date,X-Api-Key,X-Amz-Security-Token",
            "Access-Control-Allow-Credentials": "true" if access_control_origin != "*" else "false",
            "Access-Control-Max-Age": "7200",  # Cache preflight response for 2 hours
            "X-Preflight-Time": f"{processing_time:.6f}s",  # Just for fun
            "X-Powered-By": "ClaimVision CORS Magic"
        },
        "body": json.dumps({
            "message": unhinged_preflight_body(),
            "path": path,
            "timestamp": datetime.now().isoformat(),
            "processing_time": f"{processing_time:.6f}s",
            "origin_allowed": origin == access_control_origin if origin else True
        })
    }

def unhinged_preflight_body():
    """Returns a gloriously unhinged message for the preflight body"""
    messages = [
        "Cleared for takeoff! 🛫",
        "You looked here? Nerd. 🤓",
        "CORS: Can't Obviously Restrict Stuff 🤷‍♂️",
        "Preflight check complete. No snakes on this plane! 🐍",
        "This preflight message brought to you by ClaimVision™ 🌟",
        "All your CORS are belong to us 👾",
        "HTTP Status 418: I'm a teapot. Just kidding, it's 200 OK! ☕",
        "CORS: Cross-Origin Resource Sharing or Complete Overreaction Regarding Security? 🤔",
        "Preflight successful! Your browser and server are now best friends 🤝",
        "OPTIONS request? More like AWESOME request! 🎉",
        "This message will self-destruct in 5... 4... just kidding, it's already gone 💥",
        "If you're reading this, the CORS gods have smiled upon you 🙏",
        "Congratulations! You've won a free CORS header! 🏆",
        "Breaking news: Local server allows cross-origin request, world rejoices 📰",
        f"Current server time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} (in case you were wondering) ⏰",
        "I would tell you a CORS joke, but it wouldn't work across all browsers 🥁",
        "Roses are red, violets are blue, this preflight works, and your API will too 🌹",
        "CORS: Because sharing is caring (but only with the right headers) ❤️",
        "This preflight check has been certified by the Department of Redundant Departments 📜",
        "OPTIONS: The unsung hero of HTTP methods 🦸‍♂️",
        "CORS headers: Apply directly to the forehead! 💆‍♂️",
        "In a world where browsers block cross-origin requests... one server dared to respond with proper headers 🎬",
        "Preflight complete! Your request has been pre-approved for a response 👍",
        "This CORS check sponsored by ClaimVision: Making claims, not causing them 💼",
        "Congratulations on your excellent taste in API endpoints 🧐",
        "Your browser and our server just had a lovely chat about CORS 💬",
        "Preflight status: Magnificent 💯",
        "CORS headers delivered with extra love ❤️",
        "Your OPTIONS request has been handled with the utmost respect and dignity 🎩",
        "This preflight response crafted by artisanal CORS specialists 🧙‍♂️"
    ]
    
    return random.choice(messages)
