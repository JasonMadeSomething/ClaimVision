import json
import boto3
import os

dynamodb = boto3.resource("dynamodb")
files_table = dynamodb.Table(os.getenv("FILES_TABLE"))

def lambda_handler(event, context):
    """Retrieve all files for the authenticated user"""
    
    user_id = event["requestContext"]["authorizer"]["claims"]["sub"]
    
    response = files_table.query(
        IndexName="UserIdIndex",
        KeyConditionExpression="user_id = :user_id",
        ExpressionAttributeValues={":user_id": user_id}
    )
    
    return {
        "statusCode": 200,
        "body": json.dumps(response.get("Items", []))
    }
