"""WebSocket $connect handler for authenticating Cognito JWTs and
storing connection info in DynamoDB.

Performs basic rate limiting per user and verifies tokens against the
user pool JWKs.
"""

import json
import os
import time
import urllib.request

import boto3
from botocore.exceptions import ClientError

# Initialize DynamoDB client
dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table(os.environ.get('CONNECTIONS_TABLE_NAME'))
cognito_user_pool_id = os.environ.get('COGNITO_USER_POOL_ID')
region = os.environ.get('AWS_REGION', 'us-east-1')

def lambda_handler(event, _context):
    """
    Handle WebSocket $connect route.
    Validates JWT token using Cognito and stores connection details in DynamoDB.

    Rate limiting is implemented by checking existing connections for the user.
    """
    connection_id = event.get('requestContext', {}).get('connectionId')

    if not connection_id:
        return {
            'statusCode': 400,
            'body': json.dumps({'message': 'Missing connectionId'})
        }

    # Get query string parameters
    query_params = event.get('queryStringParameters', {}) or {}

    # Check for token in query string
    token = query_params.get('token')

    if not token:
        return {
            'statusCode': 401,
            'body': json.dumps({'message': 'Missing authentication token'})
        }

    try:
        # Verify JWT token with Cognito
        claims = verify_cognito_token(token)
        user_id = claims.get('sub')

        if not user_id:
            return {
                'statusCode': 401,
                'body': json.dumps({'message': 'Invalid token: missing user ID'})
            }

        # Check for rate limiting - max 5 connections per user
        user_connections = table.query(
            IndexName='UserIdIndex',
            KeyConditionExpression='userId = :uid',
            ExpressionAttributeValues={':uid': user_id}
        ).get('Items', [])

        if len(user_connections) >= 5:
            return {
                'statusCode': 429,
                'body': json.dumps({'message': 'Too many connections for this user'})
            }

        # Store connection in DynamoDB
        expiration = int(time.time()) + 86400  # 24-hour TTL

        table.put_item(
            Item={
                'connectionId': connection_id,
                'userId': user_id,
                'connectedAt': int(time.time()),
                'ttl': expiration,
                'userInfo': {
                    'email': claims.get('email', ''),
                    'name': claims.get('name', '')
                }
            }
        )

        return {
            'statusCode': 200,
            'body': json.dumps({'message': 'Connected'})
        }

    except (ValueError, ClientError) as e:
        print(f"Error in connect handler: {str(e)}")
        return {
            'statusCode': 401,
            'body': json.dumps({'message': f'Authentication failed: {str(e)}'})
        }

def verify_cognito_token(token):
    """
    Verify a JWT token from Amazon Cognito.

    Args:
        token (str): The JWT token to verify

    Returns:
        dict: The decoded JWT claims if valid

    Raises:
        Exception: If the token is invalid
    """
    try:
        from jose import jwk, jwt  # type: ignore
        from jose.utils import base64url_decode  # type: ignore
    except ImportError as ie:
        raise ValueError("Missing dependency 'python-jose'. Install it to verify Cognito tokens.") from ie

    # Get the kid (key ID) from the token headers
    headers = jwt.get_unverified_headers(token)
    kid = headers['kid']

    # Get the public keys from Cognito
    keys_url = f'https://cognito-idp.{region}.amazonaws.com/{cognito_user_pool_id}/.well-known/jwks.json'
    with urllib.request.urlopen(keys_url) as f:
        response = f.read()
    keys = json.loads(response.decode('utf-8'))['keys']

    # Find the key matching the kid
    key = next((k for k in keys if k['kid'] == kid), None)
    if not key:
        raise ValueError('Public key not found in jwks.json')

    # Construct the public key
    public_key = jwk.construct(key)

    # Get the last section of the token (the signature)
    message, encoded_signature = token.rsplit('.', 1)
    decoded_signature = base64url_decode(encoded_signature.encode('utf-8'))

    # Verify the signature
    if not public_key.verify(message.encode('utf-8'), decoded_signature):
        raise ValueError('Signature verification failed')

    # Verify the claims
    claims = jwt.get_unverified_claims(token)

    # Check expiration
    if time.time() > claims['exp']:
        raise ValueError('Token is expired')

    # Check audience (client_id)
    # Note: This check is optional and depends on your security requirements
    # if claims['aud'] != app_client_id:
    #     raise Exception('Token was not issued for this audience')

    return claims
