import os
import sys
import json
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from unittest.mock import patch, MagicMock
from testcontainers.postgres import PostgresContainer  # Optional if using Testcontainers
from models import File, Base 
from dotenv import load_dotenv

load_dotenv()
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../src")))

DATABASE_URL = "postgresql://testuser:testpassword@localhost:5432/testdb"


# -----------------
# ENVIRONMENT MOCKS
# -----------------
# -----------------
@pytest.fixture(autouse=True)
def mock_env():
    """Set required environment variables for testing."""
    os.environ["DATABASE_URL"] = "postgresql://user:password@localhost:5432/testdb"
    os.environ["S3_BUCKET_NAME"] = "test-bucket"
    os.environ["COGNITO_USER_POOL_ID"] = "test-user-pool-id"
    os.environ["COGNITO_USER_POOL_CLIENT_ID"] = "test-user-pool-client-id"
    os.environ["AWS_REGION"] = "us-east-1"
    os.environ["COGNITO_USER_POOL_CLIENT_SECRET"] = "test-user-pool-client-secret"
    
# -----------------
# DATABASE FIXTURE
# -----------------
@pytest.fixture(scope="session")
def test_db():
    """Provides a fresh test database for each test session."""
    engine = create_engine(DATABASE_URL)
    Session = sessionmaker(bind=engine)
    
    Base.metadata.drop_all(engine)
    # ✅ Setup: Create tables before tests run
    Base.metadata.create_all(engine)
    
    session = Session()

    yield session  # ✅ Provide session for tests

    # ✅ Teardown: Drop all tables after tests complete
    session.close()
    Base.metadata.drop_all(engine)
    engine.dispose()

# -----------------
# API GATEWAY MOCKS
# -----------------
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

# -----------------
# MOCK S3
# -----------------
@pytest.fixture
def mock_s3():
    """Mock S3 client for testing"""
    with patch("boto3.client") as mock_client:
        mock_s3 = MagicMock()
        mock_client.return_value = mock_s3
        yield mock_s3

# -----------------
# AUTH MOCKS
# -----------------
@pytest.fixture
def auth_event():
    """Mock API Gateway event with an authenticated user."""
    return {
        "requestContext": {
            "authorizer": {"claims": {"sub": "test-user-id"}}
        }
    }
