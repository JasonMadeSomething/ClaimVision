"""
WebSocket Lambda Authorizer for Cognito JWT Token Validation

This Lambda function validates Cognito JWT tokens for WebSocket API Gateway connections.
It returns an IAM policy allowing or denying the connection.
"""

import json
import os
import logging
from typing import Dict, Any
import jwt
import requests
from jwt.algorithms import RSAAlgorithm

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Cache for Cognito public keys
_cognito_keys = None


def get_cognito_public_keys() -> Dict[str, Any]:
    """
    Fetch and cache Cognito public keys for JWT verification.
    """
    global _cognito_keys
    
    if _cognito_keys is None:
        user_pool_id = os.environ['COGNITO_USER_POOL_ID']
        region = user_pool_id.split('_')[0]  # Extract region from pool ID
        
        keys_url = f"https://cognito-idp.{region}.amazonaws.com/{user_pool_id}/.well-known/jwks.json"
        
        try:
            response = requests.get(keys_url, timeout=10)
            response.raise_for_status()
            _cognito_keys = response.json()
            logger.info("Successfully fetched Cognito public keys")
        except Exception as e:
            logger.error(f"Failed to fetch Cognito public keys: {e}")
            raise
    
    return _cognito_keys


def verify_cognito_token(token: str) -> Dict[str, Any]:
    """
    Verify a Cognito JWT token and return the claims.
    
    Args:
        token: The JWT token to verify
        
    Returns:
        Dict containing the token claims
        
    Raises:
        Exception: If token verification fails
    """
    try:
        # Get the token header to find the key ID
        header = jwt.get_unverified_header(token)
        kid = header.get('kid')
        
        if not kid:
            raise ValueError("Token missing key ID")
        
        # Get Cognito public keys
        keys_data = get_cognito_public_keys()
        
        # Find the matching key
        public_key = None
        for key_data in keys_data['keys']:
            if key_data['kid'] == kid:
                # Convert JWK to PEM format
                public_key = RSAAlgorithm.from_jwk(json.dumps(key_data))
                break
        
        if not public_key:
            raise ValueError(f"Public key not found for kid: {kid}")
        
        # Verify the token
        user_pool_id = os.environ['COGNITO_USER_POOL_ID']
        region = user_pool_id.split('_')[0]
        
        claims = jwt.decode(
            token,
            public_key,
            algorithms=['RS256'],
            issuer=f"https://cognito-idp.{region}.amazonaws.com/{user_pool_id}",
            options={
                "verify_signature": True,
                "verify_exp": True,
                "verify_iat": True,
                "verify_aud": False  # We'll validate token_use instead
            }
        )
        
        # Validate token use
        if claims.get('token_use') != 'id':
            raise ValueError("Token is not an ID token")
        
        logger.info(f"Token verified successfully for user: {claims.get('sub')}")
        return claims
        
    except jwt.ExpiredSignatureError:
        logger.warning("Token has expired")
        raise ValueError("Token has expired")
    except jwt.InvalidTokenError as e:
        logger.warning(f"Invalid token: {e}")
        raise ValueError(f"Invalid token: {e}")
    except Exception as e:
        logger.error(f"Token verification failed: {e}")
        raise


def generate_policy(principal_id: str, effect: str, resource: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    Generate an IAM policy for API Gateway.
    
    Args:
        principal_id: The principal user identification
        effect: Allow or Deny
        resource: The resource ARN
        context: Additional context to pass to the Lambda function
        
    Returns:
        Dict containing the IAM policy
    """
    policy = {
        'principalId': principal_id,
        'policyDocument': {
            'Version': '2012-10-17',
            'Statement': [
                {
                    'Action': 'execute-api:Invoke',
                    'Effect': effect,
                    'Resource': resource
                }
            ]
        }
    }
    
    if context:
        policy['context'] = context
    
    return policy


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda authorizer handler for WebSocket API Gateway.
    
    Args:
        event: The API Gateway authorizer event
        context: Lambda context object
        
    Returns:
        IAM policy allowing or denying the connection
    """
    try:
        logger.info(f"Authorizer event: {json.dumps(event, default=str)}")
        
        # Extract token from query string parameters
        query_params = event.get('queryStringParameters', {}) or {}
        token = query_params.get('token')
        
        if not token:
            logger.warning("No token provided in query parameters")
            return generate_policy('user', 'Deny', event['methodArn'])
        
        # Verify the Cognito token
        try:
            claims = verify_cognito_token(token)
            user_id = claims.get('sub')
            username = claims.get('cognito:username', user_id)
            
            # Create context to pass to the connect handler
            auth_context = {
                'userId': user_id,
                'username': username,
                'email': claims.get('email', ''),
                'tokenExp': str(claims.get('exp', 0))
            }
            
            logger.info(f"Authorization successful for user: {username}")
            return generate_policy(user_id, 'Allow', event['methodArn'], auth_context)
            
        except ValueError as e:
            logger.warning(f"Token validation failed: {e}")
            return generate_policy('user', 'Deny', event['methodArn'])
        
    except Exception as e:
        logger.error(f"Authorizer error: {e}")
        return generate_policy('user', 'Deny', event['methodArn'])
