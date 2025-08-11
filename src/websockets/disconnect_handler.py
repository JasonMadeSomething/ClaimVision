import os
import json
import boto3

# Initialize DynamoDB client
dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table(os.environ.get('CONNECTIONS_TABLE_NAME'))

def lambda_handler(event, context):
    """
    Handle WebSocket $disconnect route.
    Removes the connection from DynamoDB.
    """
    connection_id = event.get('requestContext', {}).get('connectionId')
    
    if not connection_id:
        return {
            'statusCode': 400,
            'body': json.dumps({'message': 'Missing connectionId'})
        }
    
    try:
        # Remove connection from DynamoDB
        table.delete_item(
            Key={
                'connectionId': connection_id
            }
        )
        
        return {
            'statusCode': 200,
            'body': json.dumps({'message': 'Disconnected'})
        }
    except Exception as e:
        print(f"Error in disconnect handler: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({'message': 'Internal server error'})
        }
