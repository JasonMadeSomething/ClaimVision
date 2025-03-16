import pytest
import json
import uuid
from items.get_items import lambda_handler
from models.item import Item

def test_get_items_success(api_gateway_event, test_db, seed_multiple_items):
    """ Test retrieving multiple items."""
    claim_id, user_id, item_ids = seed_multiple_items

    event = api_gateway_event("GET", path_params={"claim_id": str(claim_id)}, auth_user=str(user_id))
    response = lambda_handler(event, {}, db_session=test_db)

    assert response["statusCode"] == 200
    response_data = json.loads(response["body"])
    assert "items" in response_data["data"]
    assert len(response_data["data"]["items"]) == len(item_ids)
    
    # Verify pagination metadata is included
    assert "pagination" in response_data["data"]
    pagination = response_data["data"]["pagination"]
    assert pagination["total"] == len(item_ids)
    assert pagination["limit"] == 10  # Default limit
    assert pagination["offset"] == 0  # Default offset

def test_get_items_with_pagination(api_gateway_event, test_db, seed_claim):
    """ Test retrieving items with pagination parameters."""
    claim_id, user_id, _ = seed_claim
    
    # Create 15 items for pagination testing
    item_ids = []
    for i in range(15):
        item_id = uuid.uuid4()
        item = Item(
            id=item_id,
            claim_id=claim_id,
            name=f"Test Item {i}",
            description=f"Description for item {i}"
        )
        test_db.add(item)
        item_ids.append(item_id)
    test_db.commit()
    
    # Test first page (limit=5, offset=0)
    event = api_gateway_event(
        "GET", 
        path_params={"claim_id": str(claim_id)}, 
        query_params={"limit": "5", "offset": "0"},
        auth_user=str(user_id)
    )
    response = lambda_handler(event, {}, db_session=test_db)
    
    assert response["statusCode"] == 200
    response_data = json.loads(response["body"])
    assert len(response_data["data"]["items"]) == 5
    pagination = response_data["data"]["pagination"]
    assert pagination["total"] == 15
    assert pagination["limit"] == 5
    assert pagination["offset"] == 0
    
    # Test second page (limit=5, offset=5)
    event = api_gateway_event(
        "GET", 
        path_params={"claim_id": str(claim_id)}, 
        query_params={"limit": "5", "offset": "5"},
        auth_user=str(user_id)
    )
    response = lambda_handler(event, {}, db_session=test_db)
    
    assert response["statusCode"] == 200
    response_data = json.loads(response["body"])
    assert len(response_data["data"]["items"]) == 5
    pagination = response_data["data"]["pagination"]
    assert pagination["total"] == 15
    assert pagination["limit"] == 5
    assert pagination["offset"] == 5
    
    # Test last page (limit=5, offset=10)
    event = api_gateway_event(
        "GET", 
        path_params={"claim_id": str(claim_id)}, 
        query_params={"limit": "5", "offset": "10"},
        auth_user=str(user_id)
    )
    response = lambda_handler(event, {}, db_session=test_db)
    
    assert response["statusCode"] == 200
    response_data = json.loads(response["body"])
    assert len(response_data["data"]["items"]) == 5
    pagination = response_data["data"]["pagination"]
    assert pagination["total"] == 15
    assert pagination["limit"] == 5
    assert pagination["offset"] == 10

def test_get_items_invalid_pagination(api_gateway_event, test_db, seed_claim):
    """ Test retrieving items with invalid pagination parameters."""
    claim_id, user_id, _ = seed_claim
    
    # Test invalid limit (negative)
    event = api_gateway_event(
        "GET", 
        path_params={"claim_id": str(claim_id)}, 
        query_params={"limit": "-5"},
        auth_user=str(user_id)
    )
    response = lambda_handler(event, {}, db_session=test_db)
    
    assert response["statusCode"] == 400
    response_data = json.loads(response["body"])
    assert "Invalid pagination parameters" in response_data["error_details"]
    
    # Test invalid limit (non-numeric)
    event = api_gateway_event(
        "GET", 
        path_params={"claim_id": str(claim_id)}, 
        query_params={"limit": "abc"},
        auth_user=str(user_id)
    )
    response = lambda_handler(event, {}, db_session=test_db)
    
    assert response["statusCode"] == 400
    response_data = json.loads(response["body"])
    assert "Invalid pagination parameters" in response_data["error_details"]
    
    # Test invalid offset (negative)
    event = api_gateway_event(
        "GET", 
        path_params={"claim_id": str(claim_id)}, 
        query_params={"offset": "-1"},
        auth_user=str(user_id)
    )
    response = lambda_handler(event, {}, db_session=test_db)
    
    assert response["statusCode"] == 400
    response_data = json.loads(response["body"])
    assert "Invalid pagination parameters" in response_data["error_details"]
    
    # Test invalid offset (non-numeric)
    event = api_gateway_event(
        "GET", 
        path_params={"claim_id": str(claim_id)}, 
        query_params={"offset": "abc"},
        auth_user=str(user_id)
    )
    response = lambda_handler(event, {}, db_session=test_db)
    
    assert response["statusCode"] == 400
    response_data = json.loads(response["body"])
    assert "Invalid pagination parameters" in response_data["error_details"]

def test_get_items_unauthorized(api_gateway_event, test_db, seed_claim):
    """Test attempting to get items without authentication."""
    claim_id, user_id, file_id = seed_claim
    
    # Create some items
    for i in range(3):
        item = Item(
            id=uuid.uuid4(),
            claim_id=claim_id,
            name=f"Test Item {i}",
            description=f"Description for test item {i}"
        )
        test_db.add(item)
    test_db.commit()
    
    # Attempt to get items without authentication
    event = api_gateway_event("GET", query_params={"claim_id": str(claim_id)}, auth_user=None)
    response = lambda_handler(event, {}, db_session=test_db)
    
    # Check that the response indicates unauthorized access
    assert response["statusCode"] == 401
    response_body = json.loads(response["body"])
    assert "Unauthorized: Missing authentication" in response_body["error_details"]

def test_get_items_missing_claim_id(api_gateway_event, test_db, seed_claim):
    """Test attempting to get items without providing a claim ID."""
    claim_id, user_id, file_id = seed_claim
    
    event = api_gateway_event("GET", path_params={}, auth_user=str(user_id))
    response = lambda_handler(event, {}, db_session=test_db)
    
    assert response["statusCode"] == 400
    response_body = json.loads(response["body"])
    assert "Missing required path parameter: claim_id" in response_body["error_details"]

def test_get_items_invalid_claim_id(api_gateway_event, test_db, seed_claim):
    """Test attempting to get items with an invalid claim ID format."""
    claim_id, user_id, file_id = seed_claim
    
    event = api_gateway_event("GET", path_params={"claim_id": "not-a-uuid"}, auth_user=str(user_id))
    response = lambda_handler(event, {}, db_session=test_db)
    
    assert response["statusCode"] == 400
    response_body = json.loads(response["body"])
    assert "Invalid claim_id format" in response_body["error_details"]

def test_get_items_empty_result(api_gateway_event, test_db, seed_claim):
    """ Test retrieving items for a claim with no items."""
    claim_id, user_id, _ = seed_claim
    
    # Attempt to get items for a claim with no items
    event = api_gateway_event("GET", path_params={"claim_id": str(claim_id)}, auth_user=str(user_id))
    response = lambda_handler(event, {}, db_session=test_db)
    
    # Check that the response contains an empty items list
    assert response["statusCode"] == 200
    response_body = json.loads(response["body"])
    assert len(response_body["data"]["items"]) == 0
    assert response_body["data"]["pagination"]["total"] == 0
