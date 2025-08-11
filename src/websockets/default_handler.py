import os
import json
import boto3

# Initialize DynamoDB client
dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table(os.environ.get('CONNECTIONS_TABLE_NAME'))

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
        # Get the connection record to verify it exists
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
                # Update the connection record with subscription info
                table.update_item(
                    Key={
                        'connectionId': connection_id
                    },
                    UpdateExpression="SET subscriptions = list_append(if_not_exists(subscriptions, :empty_list), :claim)",
                    ExpressionAttributeValues={
                        ':empty_list': [],
                        ':claim': [claim_id]
                    }
                )
                return send_to_connection(connection_id, {
                    'type': 'subscribed',
                    'claimId': claim_id
                })
            else:
                return send_to_connection(connection_id, {
                    'type': 'error',
                    'message': 'Missing claimId for subscription'
                })
        else:
            # Default echo behavior
            return send_to_connection(connection_id, {
                'type': 'echo',
                'message': message
            })
            
    except (ValueError, KeyError, TypeError) as e:
        print("Error in default handler: " + str(e))
        return {
            'statusCode': 500,
            'body': json.dumps({'message': 'Internal server error'})
        }

def send_to_connection(connection_id, data):
    """
    Helper function to send a message to a WebSocket connection
    """
    api_endpoint = os.environ.get('WS_API_ENDPOINT')
    if not api_endpoint:
        print("Missing WS_API_ENDPOINT environment variable")
        return {
            'statusCode': 500,
            'body': json.dumps({'message': 'Missing API endpoint configuration'})
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
        table.delete_item(
            Key={
                'connectionId': connection_id
            }
        )
        return {
            'statusCode': 410,
            'body': json.dumps({'message': 'Connection is gone'})
        }
