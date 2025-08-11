import os
import json
import boto3
import logging

# Initialize DynamoDB client
logger = logging.getLogger()
logger.setLevel(logging.INFO)

dynamodb = boto3.resource('dynamodb')
table = None  # lazy-init after env validation

def lambda_handler(event, context):
    """
    Handle WebSocket $default route.
    This handles any messages sent from the client to the server.
    
    Currently, this is a simple echo handler, but could be extended to:
    - Handle subscription requests for specific claims
    - Process custom commands from clients
    - Implement heartbeat mechanism
    """
    connection_id = event.get('requestContext', {}).get('connectionId')

    if not connection_id:
        return {
            'statusCode': 400,
            'body': json.dumps({'message': 'Missing connectionId'})
        }
    
    try:
        connections_table_name = os.environ.get('CONNECTIONS_TABLE_NAME')
        if not connections_table_name:
            logger.error("Missing CONNECTIONS_TABLE_NAME env var", extra={"event": event})
            return {
                'statusCode': 500,
                'body': json.dumps({'error': 'MissingEnv', 'message': 'CONNECTIONS_TABLE_NAME is not set'})
            }
        # Get the connection record to verify it exists
        global table
        connections_table_name = os.environ.get('CONNECTIONS_TABLE_NAME')
        table = table or dynamodb.Table(connections_table_name)
        connection = table.get_item(
            Key={
                'connectionId': connection_id
            }
        ).get('Item')
        
        if not connection:
            return {
                'statusCode': 400,
                'body': json.dumps({'message': 'Connection not found'})
            }
        
        # Parse the message body
        body = event.get('body', '{}')
        try:
            message = json.loads(body)
        except json.JSONDecodeError:
            message = {'text': body}
        
        # Handle different message types
        message_type = message.get('action', 'echo')
        
        if message_type == 'ping':
            # Handle ping/heartbeat
            return send_to_connection(connection_id, {
                'type': 'pong',
                'timestamp': context.invoked_function_arn
            })
        elif message_type == 'subscribe':
            # Handle subscription to specific claim
            claim_id = message.get('claimId')
            if claim_id:
                # Read current subscriptions
                current = table.get_item(Key={'connectionId': connection_id}).get('Item') or {}
                existing = current.get('subscriptions') or []
                try:
                    unique = list({*existing, claim_id})  # dedupe
                except TypeError:
                    # Fallback if existing not iterable
                    unique = [claim_id]
                # Write back the deduped list
                table.update_item(
                    Key={'connectionId': connection_id},
                    UpdateExpression='SET subscriptions = :subs',
                    ExpressionAttributeValues={':subs': unique}
                )
                return send_to_connection(connection_id, {
                    'type': 'subscribed',
                    'claimId': claim_id,
                    'subscriptions': unique
                })
            else:
                return send_to_connection(connection_id, {
                    'type': 'error',
                    'error': 'BadRequest',
                    'message': 'Missing claimId for subscription'
                })
        else:
            # Default echo behavior
            return send_to_connection(connection_id, {
                'type': 'echo',
                'message': message
            })
            
    except (ValueError, KeyError, TypeError):
        logger.exception("Error in default handler")
        return {
            'statusCode': 500,
            'body': json.dumps({'error': 'InternalError', 'message': 'Internal server error'})
        }

def send_to_connection(connection_id, data):
    """
    Helper function to send a message to a WebSocket connection
    """
    api_endpoint = os.environ.get('WS_API_ENDPOINT')
    if not api_endpoint:
        logger.error("Missing WS_API_ENDPOINT environment variable")
        return {
            'statusCode': 500,
            'body': json.dumps({'error': 'MissingEnv', 'message': 'Missing API endpoint configuration'})
        }
        
    gateway_management = boto3.client(
        'apigatewaymanagementapi',
        endpoint_url=api_endpoint
    )
    
    try:
        gateway_management.post_to_connection(
            ConnectionId=connection_id,
            Data=json.dumps(data)
        )
        return {
            'statusCode': 200,
            'body': json.dumps({'message': 'Message sent'})
        }
    except gateway_management.exceptions.GoneException:
        # Connection is no longer valid
        try:
            global table
            connections_table_name = os.environ.get('CONNECTIONS_TABLE_NAME')
            if connections_table_name:
                table = table or dynamodb.Table(connections_table_name)
                table.delete_item(Key={'connectionId': connection_id})
        except Exception:
            # Best-effort cleanup
            pass
        return {
            'statusCode': 410,
            'body': json.dumps({'message': 'Connection is gone'})
        }
