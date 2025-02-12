import json
import boto3
import os
import base64
import uuid
import magic  # For file type detection
from botocore.exceptions import BotoCoreError, ClientError
from .model import File  # Ensure correct import path
from ..utils import response as response

s3 = boto3.client("s3")
dynamodb = boto3.resource("dynamodb")
files_table = dynamodb.Table(os.getenv("FILES_TABLE"))
BUCKET_NAME = os.getenv("S3_BUCKET_NAME")

def lambda_handler(event, context):
    """Handle single or multiple file uploads to S3 and store metadata in DynamoDB."""
    try:
        user_id = event["requestContext"]["authorizer"]["claims"]["sub"]  # Extract user ID from token

        # Ensure request body exists
        if not event.get("body"):
            return response.api_response(400, message="Missing request body")

        body = json.loads(event["body"])

        # Validate files field
        files = body.get("files")
        if not files or not isinstance(files, list):
            return response.api_response(400, message="Invalid or missing 'files' array")

        uploaded_files = []

        for file in files:
            try:
                # Validate individual file fields
                file_name = file.get("file_name")
                file_data = file.get("file_data")

                if not file_name or not isinstance(file_name, str):
                    return response.api_response(400, message="Missing or invalid 'file_name'")
                
                if not file_data or not isinstance(file_data, str):
                    return response.api_response(400, message="Missing or invalid 'file_data'")

                # Decode file
                decoded_file = base64.b64decode(file_data)

                mime_type = magic.Magic(mime=True).from_buffer(decoded_file[:2048])  # Detect MIME type

                # Generate unique file ID and S3 key
                file_id = str(uuid.uuid4())
                s3_key = f"uploads/{user_id}/{file_id}/{file_name}"

                # Upload to S3
                s3.put_object(Bucket=BUCKET_NAME, Key=s3_key, Body=decoded_file)

                # Create File metadata
                file_metadata = File(
                    id=file_id,
                    user_id=user_id,
                    file_name=file_name,
                    s3_key=s3_key,
                    mime_type=mime_type,
                    size=len(decoded_file),
                    file_url=f"https://{BUCKET_NAME}.s3.amazonaws.com/{s3_key}",
                    labels=[]  # Default empty list
                )

                # Store metadata in DynamoDB
                files_table.put_item(Item=file_metadata.to_dynamodb_dict())

                uploaded_files.append({
                    "file_id": file_id,
                    "file_name": file_name,
                    "file_url": file_metadata.file_url
                })

            except Exception as file_error:
                return response.api_response(400, message=f"Error processing file '{file.get('file_name', 'UNKNOWN')}': {str(file_error)}")

        return response.api_response(201, message=f"{len(uploaded_files)} file(s) uploaded successfully", data=uploaded_files)

    except (BotoCoreError, ClientError) as e:
        return response.api_response(500, message="Internal Server Error", error_details=str(e))
    except json.JSONDecodeError:
        return response.api_response(400, message="Invalid JSON payload")
    except Exception as e:
        return response.api_response(400, message="Internal Server Error", error_details=str(e))
