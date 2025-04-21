import json
import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import patch
from sqlalchemy.exc import SQLAlchemyError
import base64

from claims.create_claim import lambda_handler
from models.claim import Claim

# Patch auth_utils at the class level to completely bypass authentication
@patch("utils.auth_utils.extract_user_id")
@patch("utils.auth_utils.get_authenticated_user")
class TestCreateClaim:
    def test_create_claim_success(self, mock_get_user, mock_extract_id, test_db, api_gateway_event, seed_user_and_group):
        """Test successful claim creation with real test DB"""
        group_id = seed_user_and_group["group_id"]
        user = seed_user_and_group["user"]
        
        # Configure the mocks to return success
        mock_extract_id.return_value = (True, user.cognito_sub)
        mock_get_user.return_value = (True, user)
        
        # Create a valid JWT token with the correct format
        header = base64.b64encode(json.dumps({"alg": "none"}).encode()).decode()
        # Use the exact cognito_sub value
        payload = base64.b64encode(json.dumps({"sub": user.cognito_sub}).encode()).decode()
        signature = base64.b64encode(b"").decode()
        valid_token = f"{header}.{payload}.{signature}"
        
        event = api_gateway_event(
            http_method="POST",
            body={"title": "Lost Laptop", "date_of_loss": "2024-01-10", "group_id": str(group_id)},
            auth_user=user.cognito_sub
        )
        
        # Replace the placeholder token with a valid JWT token
        event["headers"]["Authorization"] = f"Bearer {valid_token}"
    
        response = lambda_handler(event, {})
        body = json.loads(response["body"])
    
        claim = test_db.query(Claim).filter_by(title="Lost Laptop").first()
    
        assert response["statusCode"] == 201, f"Expected 201, got {response['statusCode']}: {body}"
        assert claim is not None, "Claim was not stored in the database"
        assert claim.date_of_loss.strftime("%Y-%m-%d") == "2024-01-10"
        assert claim.group_id == group_id
        assert "id" in body["data"]

    def test_create_claim_missing_fields(self, mock_get_user, mock_extract_id, test_db, api_gateway_event, seed_user_and_group):
        """Test creating a claim with missing required fields"""
        user = seed_user_and_group["user"]
        
        # Configure the mocks to return success
        mock_extract_id.return_value = (True, user.cognito_sub)
        mock_get_user.return_value = (True, user)
        
        # Create a valid JWT token with the correct format
        header = base64.b64encode(json.dumps({"alg": "none"}).encode()).decode()
        # Use the exact cognito_sub value
        payload = base64.b64encode(json.dumps({"sub": user.cognito_sub}).encode()).decode()
        signature = base64.b64encode(b"").decode()
        valid_token = f"{header}.{payload}.{signature}"
        
        event = api_gateway_event(
            http_method="POST", 
            body={"title": "Lost Laptop"},  # Missing `date_of_loss`
            auth_user=user.cognito_sub
        )
        
        # Replace the placeholder token with a valid JWT token
        event["headers"]["Authorization"] = f"Bearer {valid_token}"
        
        response = lambda_handler(event, {})
        body = json.loads(response["body"])
        
        assert response["statusCode"] == 400
        assert "error_details" in body
        assert "Missing required fields" in body["error_details"]

    def test_create_claim_invalid_date_format(self, mock_get_user, mock_extract_id, test_db, api_gateway_event, seed_user_and_group):
        """Test creating a claim with an invalid date format"""
        group_id = seed_user_and_group["group_id"]
        user = seed_user_and_group["user"]
        
        # Configure the mocks to return success
        mock_extract_id.return_value = (True, user.cognito_sub)
        mock_get_user.return_value = (True, user)
        
        # Create a valid JWT token with the correct format
        header = base64.b64encode(json.dumps({"alg": "none"}).encode()).decode()
        # Use the exact cognito_sub value
        payload = base64.b64encode(json.dumps({"sub": user.cognito_sub}).encode()).decode()
        signature = base64.b64encode(b"").decode()
        valid_token = f"{header}.{payload}.{signature}"
        
        event = api_gateway_event(
            http_method="POST",
            body={"title": "Lost Laptop", "date_of_loss": "01/10/2024", "group_id": str(group_id)},
            auth_user=user.cognito_sub
        )
        
        # Replace the placeholder token with a valid JWT token
        event["headers"]["Authorization"] = f"Bearer {valid_token}"
        
        response = lambda_handler(event, {})
        body = json.loads(response["body"])
        
        assert response["statusCode"] == 400
        assert "error_details" in body
        assert "date format" in body["error_details"].lower()

    def test_create_claim_database_failure(self, mock_get_user, mock_extract_id, test_db, api_gateway_event, seed_user_and_group):
        """Test creating a claim when PostgreSQL connection fails"""
        group_id = seed_user_and_group["group_id"]
        user = seed_user_and_group["user"]
        
        # Configure the mocks to return success
        mock_extract_id.return_value = (True, user.cognito_sub)
        mock_get_user.return_value = (True, user)
        
        # Create a valid JWT token with the correct format
        header = base64.b64encode(json.dumps({"alg": "none"}).encode()).decode()
        # Use the exact cognito_sub value
        payload = base64.b64encode(json.dumps({"sub": user.cognito_sub}).encode()).decode()
        signature = base64.b64encode(b"").decode()
        valid_token = f"{header}.{payload}.{signature}"
        
        # Mock the database session to raise an exception
        with patch("sqlalchemy.orm.session.Session.add") as mock_db_add:
            mock_db_add.side_effect = SQLAlchemyError("Database error")
            
            event = api_gateway_event(
                http_method="POST",
                body={"title": "Lost Laptop", "date_of_loss": "2024-01-10", "group_id": str(group_id)},
                auth_user=user.cognito_sub
            )
            
            # Replace the placeholder token with a valid JWT token
            event["headers"]["Authorization"] = f"Bearer {valid_token}"
            
            response = lambda_handler(event, {})
            body = json.loads(response["body"])
            
            assert response["statusCode"] == 500
            assert "error_details" in body
            assert "database" in body["error_details"].lower()

    def test_create_claim_duplicate_title(self, mock_get_user, mock_extract_id, test_db, api_gateway_event, seed_user_and_group):
        """Test creating a duplicate claim title in the same group"""
        group_id = seed_user_and_group["group_id"]
        user = seed_user_and_group["user"]
        
        # Configure the mocks to return success
        mock_extract_id.return_value = (True, user.cognito_sub)
        mock_get_user.return_value = (True, user)
        
        # Create a valid JWT token with the correct format
        header = base64.b64encode(json.dumps({"alg": "none"}).encode()).decode()
        # Use the exact cognito_sub value
        payload = base64.b64encode(json.dumps({"sub": user.cognito_sub}).encode()).decode()
        signature = base64.b64encode(b"").decode()
        valid_token = f"{header}.{payload}.{signature}"
        
        # Create a claim with the same title first
        existing_claim = Claim(
            id=uuid.uuid4(),
            title="Duplicate Title",
            date_of_loss=datetime.now(timezone.utc),
            group_id=group_id,
            created_by=user.id  # Use created_by with user.id
        )
        test_db.add(existing_claim)
        test_db.commit()
        
        # Now try to create another claim with the same title
        event = api_gateway_event(
            http_method="POST",
            body={"title": "Duplicate Title", "date_of_loss": "2024-01-10", "group_id": str(group_id)},
            auth_user=user.cognito_sub
        )
        
        # Replace the placeholder token with a valid JWT token
        event["headers"]["Authorization"] = f"Bearer {valid_token}"
        
        response = lambda_handler(event, {})
        body = json.loads(response["body"])
        
        assert response["statusCode"] == 409
        assert "error_details" in body
        assert "duplicate" in body["error_details"].lower() or "already exists" in body["error_details"].lower()

    def test_create_claim_future_date(self, mock_get_user, mock_extract_id, test_db, api_gateway_event, seed_user_and_group):
        """Test creating a claim with a future date"""
        group_id = seed_user_and_group["group_id"]
        user = seed_user_and_group["user"]
        
        # Configure the mocks to return success
        mock_extract_id.return_value = (True, user.cognito_sub)
        mock_get_user.return_value = (True, user)
        
        # Create a valid JWT token with the correct format
        header = base64.b64encode(json.dumps({"alg": "none"}).encode()).decode()
        # Use the exact cognito_sub value
        payload = base64.b64encode(json.dumps({"sub": user.cognito_sub}).encode()).decode()
        signature = base64.b64encode(b"").decode()
        valid_token = f"{header}.{payload}.{signature}"
        
        # Get a date 7 days in the future
        future_date = (datetime.now(timezone.utc) + timedelta(days=7)).strftime("%Y-%m-%d")
        
        event = api_gateway_event(
            http_method="POST",
            body={"title": "Future Loss", "date_of_loss": future_date, "group_id": str(group_id)},
            auth_user=user.cognito_sub
        )
        
        # Replace the placeholder token with a valid JWT token
        event["headers"]["Authorization"] = f"Bearer {valid_token}"
        
        response = lambda_handler(event, {})
        body = json.loads(response["body"])
        
        assert response["statusCode"] == 400
        assert "error_details" in body
        assert "future" in body["error_details"].lower()

    def test_create_claim_empty_title(self, mock_get_user, mock_extract_id, test_db, api_gateway_event, seed_user_and_group):
        """Test creating a claim with an empty title"""
        group_id = seed_user_and_group["group_id"]
        user = seed_user_and_group["user"]
        
        # Configure the mocks to return success
        mock_extract_id.return_value = (True, user.cognito_sub)
        mock_get_user.return_value = (True, user)
        
        # Create a valid JWT token with the correct format
        header = base64.b64encode(json.dumps({"alg": "none"}).encode()).decode()
        # Use the exact cognito_sub value
        payload = base64.b64encode(json.dumps({"sub": user.cognito_sub}).encode()).decode()
        signature = base64.b64encode(b"").decode()
        valid_token = f"{header}.{payload}.{signature}"
        
        event = api_gateway_event(
            http_method="POST",
            body={"title": "", "date_of_loss": "2024-01-10", "group_id": str(group_id)},
            auth_user=user.cognito_sub
        )
        
        # Replace the placeholder token with a valid JWT token
        event["headers"]["Authorization"] = f"Bearer {valid_token}"
        
        response = lambda_handler(event, {})
        body = json.loads(response["body"])
        
        assert response["statusCode"] == 400
        assert "error_details" in body
        assert "title" in body["error_details"].lower()

    def test_create_claim_infer_group(self, mock_get_user, mock_extract_id, test_db, api_gateway_event, seed_user_and_group):
        """Test creating a claim without specifying group_id (should be inferred)"""
        user = seed_user_and_group["user"]
        
        # Configure the mocks to return success
        mock_extract_id.return_value = (True, user.cognito_sub)
        mock_get_user.return_value = (True, user)
        
        # Create a valid JWT token with the correct format
        header = base64.b64encode(json.dumps({"alg": "none"}).encode()).decode()
        # Use the exact cognito_sub value
        payload = base64.b64encode(json.dumps({"sub": user.cognito_sub}).encode()).decode()
        signature = base64.b64encode(b"").decode()
        valid_token = f"{header}.{payload}.{signature}"
        
        event = api_gateway_event(
            http_method="POST",
            body={"title": "Inferred Group Claim", "date_of_loss": "2024-01-10"},  # No group_id
            auth_user=user.cognito_sub
        )
        
        # Replace the placeholder token with a valid JWT token
        event["headers"]["Authorization"] = f"Bearer {valid_token}"
        
        response = lambda_handler(event, {})
        body = json.loads(response["body"])
        
        assert response["statusCode"] == 201, f"Expected 201, got {response['statusCode']}: {body}"
        
        claim = test_db.query(Claim).filter_by(title="Inferred Group Claim").first()
        assert claim is not None, "Claim was not stored in the database"
