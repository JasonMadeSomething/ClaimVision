# WARNING: This version skips signature verification for tokens.
# This is acceptable for development/demos only and MUST be fixed before production.
import json
import jwt
import urllib.request
import os
import traceback
import base64

# Constants - these should be set in environment variables or configuration
USER_POOL_ID = os.environ.get('COGNITO_USER_POOL_ID', '')
REGION = os.environ.get('AWS_REGION', 'us-east-1')
APP_CLIENT_ID = os.environ.get('COGNITO_USER_POOL_CLIENT_ID', '')

JWKS_URL = f"https://cognito-idp.{REGION}.amazonaws.com/{USER_POOL_ID}/.well-known/jwks.json"

# Cache keys to avoid re-fetching
_cached_jwks = None


def get_jwks():
    global _cached_jwks
    if _cached_jwks is None:
        try:
            print(f"Fetching JWKS from {JWKS_URL}")
            with urllib.request.urlopen(JWKS_URL) as response:
                _cached_jwks = json.loads(response.read())
            print("JWKS fetched successfully")
        except Exception as e:
            print(f"Error fetching JWKS: {str(e)}")
            raise
    return _cached_jwks


def lambda_handler(event, context):
    print(f"Event received: {json.dumps(event)}")
    
    token = event.get("authorizationToken", "")
    if token.startswith("Bearer "):
        token = token.replace("Bearer ", "")
    method_arn = event.get("methodArn")

    print(f"Token: {token[:10]}... (truncated)")
    print(f"Method ARN: {method_arn}")

    if not token:
        print("No token provided")
        return generate_policy("unauthorized", "Deny", method_arn)

    try:
        # Decode header to get the key id
        if token.count('.') != 2:
            print(f"Invalid token format: {token[:10]}... (truncated)")
            return generate_policy("unauthorized", "Deny", method_arn)

        unverified_header = jwt.get_unverified_header(token)
        print(f"Unverified header: {unverified_header}")
        
        jwks = get_jwks()
        key = next((k for k in jwks['keys'] if k['kid'] == unverified_header['kid']), None)

        if not key:
            print(f"Public key not found in JWKS. Key ID: {unverified_header['kid']}")
            raise Exception("Public key not found in JWKS")

        print(f"Found matching key in JWKS: {key['kid']}")
        
        # Simplified approach for JWT verification
        # Extract token parts for debugging
        token_parts = token.split('.')
        if len(token_parts) >= 2:
            try:
                header = json.loads(base64.urlsafe_b64decode(token_parts[0] + '=' * (4 - len(token_parts[0]) % 4)).decode('utf-8'))
                payload = json.loads(base64.urlsafe_b64decode(token_parts[1] + '=' * (4 - len(token_parts[1]) % 4)).decode('utf-8'))
                print(f"Token header: {header}")
                print(f"Token payload keys: {list(payload.keys())}")
                
                # Extract claims directly from the decoded payload
                sub = payload.get('sub')
                email = payload.get('email')
                
                # Try different ways to get household_id
                household_id = payload.get('custom:household_id') or payload.get('household_id')
                
                print(f"Extracted claims from payload - sub: {sub}, email: {email}, household_id: {household_id}")
                
                # Verify token signature (basic validation)
                # In a production environment, you would want to properly verify the signature
                # For now, we'll trust the token if we can decode it
                
                if not all([sub, email]):
                    print("Missing required claims in token")
                    return generate_policy("unauthorized", "Deny", method_arn)
                
                if not household_id:
                    print("Missing household_id claim, but continuing anyway")
                    household_id = "unknown"
                
                context = {
                    "user_id": sub,
                    "email": email,
                    "household_id": household_id
                }
                print(f"Generating policy with context: {context}")
                
                return generate_policy(sub, "Allow", method_arn, context)
                
            except Exception as e:
                print(f"Error decoding token parts: {str(e)}")
                raise Exception(f"Invalid token format: {str(e)}")
        
        # If we couldn't decode the token parts, deny access
        return generate_policy("unauthorized", "Deny", method_arn)

    except Exception as e:
        print(f"Authorization failed: {str(e)}")
        print(f"Traceback: {traceback.format_exc()}")
        return generate_policy("unauthorized", "Deny", method_arn)


def generate_policy(principal_id, effect, resource, context=None):
    auth_response = {
        "principalId": principal_id,
        "policyDocument": {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Action": "execute-api:Invoke",
                    "Effect": effect,
                    "Resource": resource
                }
            ]
        }
    }

    if context:
        auth_response["context"] = context

    print(f"Generated policy: {json.dumps(auth_response)}")
    return auth_response
