import os
import json
import boto3
import logging
from datetime import datetime

# Set up logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize DynamoDB and API Gateway Management clients
dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table(os.environ.get('CONNECTIONS_TABLE_NAME'))
sqs = boto3.client('sqs')

def lambda_handler(event, context):
    """
    Process messages from the outbound SQS queue and send them to connected WebSocket clients.
    
    This function:
    1. Parses SQS messages
    2. Queries DynamoDB for relevant connections
    3. Sends messages to connected clients
    4. Handles stale connections
    """
    if not event.get('Records'):
        logger.warning("No records found in event")
        return {
            'statusCode': 400,
            'body': json.dumps({'message': 'No records found in event'})
        }
    
    # Initialize API Gateway Management API client
    # Extract the API ID from the endpoint URL
    endpoint_url = os.environ.get('WS_API_ENDPOINT')
    if not endpoint_url:
        logger.error("Missing WS_API_ENDPOINT environment variable")
        return {
            'statusCode': 500,
            'body': json.dumps({'message': 'Missing API endpoint configuration'})
        }
    
    gateway_management = boto3.client(
        'apigatewaymanagementapi',
        endpoint_url=endpoint_url
    )
    
    # Process each SQS message
    results = []
    for record in event['Records']:
        try:
            # Parse the SQS message
            message_body = json.loads(record['body'])
            logger.info(f"Processing message: {json.dumps(message_body)}")
            
            # Extract message details
            message_type = message_body.get('type', 'notification')
            user_id = message_body.get('userId')
            claim_id = message_body.get('claimId')
            
            # Determine which connections should receive this message
            connections = []
            
            if user_id:
                # Send to specific user's connections
                user_connections = table.query(
                    IndexName='UserIdIndex',
                    KeyConditionExpression='userId = :uid',
                    ExpressionAttributeValues={':uid': user_id}
                ).get('Items', [])
                connections.extend(user_connections)
            elif claim_id:
                # TODO: Implement query for connections subscribed to a specific claim
                # This would require a GSI on claimId or a scan with a filter
                pass
            else:
                # Broadcast to all connections (use with caution)
                logger.warning("Broadcasting message to all connections")
                # Use scan with pagination to handle large numbers of connections
                scan_kwargs = {}
                done = False
                while not done:
                    response = table.scan(**scan_kwargs)
                    connections.extend(response.get('Items', []))
                    if 'LastEvaluatedKey' in response:
                        scan_kwargs['ExclusiveStartKey'] = response['LastEvaluatedKey']
                    else:
                        done = True
            
            # Send the message to each connection
            sent_count = 0
            stale_connections = []
            
            for connection in connections:
                connection_id = connection.get('connectionId')
                if not connection_id:
                    continue
                
                try:
                    # Prepare the message payload
                    payload = {
                        'type': message_type,
                        'timestamp': datetime.utcnow().isoformat(),
                        'data': message_body.get('data', {})
                    }
                    
                    # Send the message
                    gateway_management.post_to_connection(
                        ConnectionId=connection_id,
                        Data=json.dumps(payload)
                    )
                    sent_count += 1
                    
                except gateway_management.exceptions.GoneException:
                    # Connection is no longer valid
                    logger.info(f"Removing stale connection: {connection_id}")
                    stale_connections.append(connection_id)
                except Exception as e:
                    logger.error(f"Error sending to connection {connection_id}: {str(e)}")
            
            # Clean up stale connections
            for connection_id in stale_connections:
                try:
                    table.delete_item(
                        Key={
                            'connectionId': connection_id
                        }
                    )
                except Exception as e:
                    logger.error(f"Error removing stale connection {connection_id}: {str(e)}")
            
            results.append({
                'messageId': record.get('messageId'),
                'sentCount': sent_count,
                'staleConnectionsRemoved': len(stale_connections)
            })
            
        except Exception as e:
            logger.error(f"Error processing record: {str(e)}")
            results.append({
                'messageId': record.get('messageId'),
                'error': str(e)
            })

    return {
        'statusCode': 200,
        'body': json.dumps({
            'processedCount': len(event['Records']),
            'results': results
        })
    }
