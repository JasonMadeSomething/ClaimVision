import os
import sys
import boto3
import pytest
import json
from unittest.mock import patch, MagicMock
from moto import mock_aws

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../src")))

@pytest.fixture(autouse=True)
def mock_env():
    """Set required environment variables for testing."""
    os.environ["FILES_TABLE"] = "test-files-table"
    os.environ["CLAIMS_TABLE"] = "test-claims-table"
    os.environ["S3_BUCKET_NAME"] = "test-bucket"
    os.environ["COGNITO_USER_POOL_ID"] = "test-user-pool-id"
    os.environ["COGNITO_USER_POOL_CLIENT_ID"] = "test-user-pool-client-id"
    os.environ["AWS_REGION"] = "us-east-1"
    os.environ["COGNITO_USER_POOL_CLIENT_SECRET"] = "test-user-pool-client-secret"


@pytest.fixture
def mock_dynamodb():
    """Mock the entire DynamoDB service and allow dynamic table creation."""
    with patch("boto3.resource") as mock_resource:
        mock_dynamodb = MagicMock()
        mock_resource.return_value = mock_dynamodb

        tables = {}

        def get_mock_table(table_name):
            """Dynamically create a mock table if it doesn’t exist."""
            if table_name not in tables:
                mock_table = MagicMock()
                tables[table_name] = mock_table
            return tables[table_name]

        # Set up the Table() function to return dynamically created tables
        mock_dynamodb.Table.side_effect = get_mock_table

        yield mock_dynamodb

@pytest.fixture
def api_gateway_event():
    """Creates a mock API Gateway event for testing"""

    def _event(http_method="GET", path_params=None, query_params=None, body=None, auth_user="user-123"):
        """Generate an API event, allowing optional auth_user=None for unauthenticated tests"""
        event = {
            "httpMethod": http_method,
            "pathParameters": path_params or {},
            "queryStringParameters": query_params or {},
            "headers": {"Authorization": "Bearer fake-jwt-token"} if auth_user else {},
            "requestContext": {
                "authorizer": {"claims": {"sub": auth_user}} if auth_user else {}
            },
            "body": json.dumps(body) if isinstance(body, dict) else body,
        }
        return event

    return _event

@pytest.fixture
def mock_s3():
    """Mock S3 client for testing"""
    with mock_aws():
        s3 = boto3.client("s3", region_name="us-east-1")
        s3.create_bucket(Bucket="test-bucket")
        yield s3

@pytest.fixture
def auth_event():
    """Mock API Gateway event with an authenticated user."""
    return {
        "requestContext": {
            "authorizer": {"claims": {"sub": "test-user-id"}}
        }
    }


@pytest.fixture
def mock_dynamodb(mock_boto3):
    """Mock DynamoDB resource with tables."""
    with mock_boto3:
        dynamodb = boto3.resource("dynamodb", region_name="us-east-1")

        tables = {
            "FilesTable": dynamodb.create_table(
                TableName="FilesTable",
                KeySchema=[{"AttributeName": "id", "KeyType": "HASH"}],
                AttributeDefinitions=[{"AttributeName": "id", "AttributeType": "S"}],
                BillingMode="PAY_PER_REQUEST"
            ),
            "ClaimsTable": dynamodb.create_table(
                TableName="ClaimsTable",
                KeySchema=[{"AttributeName": "claim_id", "KeyType": "HASH"}],
                AttributeDefinitions=[{"AttributeName": "claim_id", "AttributeType": "S"}],
                BillingMode="PAY_PER_REQUEST"
            ),
        }

        for table in tables.values():
            table.wait_until_exists()

        yield tables
