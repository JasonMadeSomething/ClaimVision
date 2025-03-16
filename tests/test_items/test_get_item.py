import pytest
import json
import uuid
from unittest.mock import patch
from sqlalchemy.exc import SQLAlchemyError
from items.get_item import lambda_handler
from models.item import Item
from models.item_files import ItemFile
from models.item_labels import ItemLabel
from models.claim import Claim
from models.label import Label

def test_get_item_success(api_gateway_event, test_db, seed_item):
    """Test retrieving an item successfully."""
    item_id, user_id, file_id = seed_item

    event = api_gateway_event("GET", path_params={"item_id": str(item_id)}, auth_user=str(user_id))
    response = lambda_handler(event, {}, db_session=test_db)

    assert response["statusCode"] == 200
    # Parse the JSON string in the body
    body = json.loads(response["body"])
    assert body["data"]["id"] == str(item_id)
    assert "name" in body["data"]
    assert "description" in body["data"]

def test_get_item_with_labels(api_gateway_event, test_db, seed_claim):
    """Test retrieving an item with associated labels."""
    claim_id, user_id, file_id = seed_claim
    
    # Create an item
    item_id = uuid.uuid4()
    item = Item(
        id=item_id,
        claim_id=claim_id,
        name="Item with Labels",
        description="Item with label associations",
        estimated_value=150.00,
        condition="Good"
    )
    test_db.add(item)
    test_db.commit()  # Commit the item first
    
    # Create labels
    household_id = test_db.query(Claim).filter(Claim.id == claim_id).first().household_id
    label_ids = []
    
    # Create AI-generated label
    ai_label_id = uuid.uuid4()
    label_ids.append(ai_label_id)
    ai_label = Label(
        id=ai_label_id,
        label_text="AI Generated Label",
        is_ai_generated=True,
        deleted=False,
        household_id=household_id
    )
    test_db.add(ai_label)
    
    # Create user-created label
    user_label_id = uuid.uuid4()
    label_ids.append(user_label_id)
    user_label = Label(
        id=user_label_id,
        label_text="User Created Label",
        is_ai_generated=False,
        deleted=False,
        household_id=household_id
    )
    test_db.add(user_label)
    test_db.commit()  # Commit the labels before creating associations
    
    # Create item-label associations
    for label_id in label_ids:
        item_label = ItemLabel(
            item_id=item_id,
            label_id=label_id,
            deleted=False
        )
        test_db.add(item_label)
    
    test_db.commit()
    
    # Get the item
    event = api_gateway_event("GET", path_params={"item_id": str(item_id)}, auth_user=str(user_id))
    response = lambda_handler(event, {}, db_session=test_db)
    
    assert response["statusCode"] == 200
    body = json.loads(response["body"])
    
    # Verify item details
    assert body["data"]["id"] == str(item_id)
    assert body["data"]["name"] == "Item with Labels"
    assert body["data"]["description"] == "Item with label associations"
    assert body["data"]["estimated_value"] == 150.00
    assert body["data"]["condition"] == "Good"
    
    # Verify labels
    assert "labels" in body["data"]
    assert len(body["data"]["labels"]) == 2
    
    # Check that both labels are present
    label_texts = [label["text"] for label in body["data"]["labels"]]
    assert "AI Generated Label" in label_texts
    assert "User Created Label" in label_texts
    
    # Verify AI-generated flag
    for label in body["data"]["labels"]:
        if label["text"] == "AI Generated Label":
            assert label["is_ai_generated"] is True
        elif label["text"] == "User Created Label":
            assert label["is_ai_generated"] is False

def test_get_item_with_file_associations(api_gateway_event, test_db, seed_claim):
    """Test retrieving an item with file associations."""
    claim_id, user_id, file_id = seed_claim
    
    # Create an item
    item_id = uuid.uuid4()
    item = Item(
        id=item_id,
        claim_id=claim_id,
        name="Item with Files",
        description="Item with file associations"
    )
    test_db.add(item)
    
    # Create an item-file association
    item_file = ItemFile(
        item_id=item_id,
        file_id=file_id
    )
    test_db.add(item_file)
    test_db.commit()
    
    # Get the item
    event = api_gateway_event("GET", path_params={"item_id": str(item_id)}, auth_user=str(user_id))
    response = lambda_handler(event, {}, db_session=test_db)
    
    assert response["statusCode"] == 200
    body = json.loads(response["body"])
    
    # Verify item details
    assert body["data"]["id"] == str(item_id)
    assert body["data"]["name"] == "Item with Files"
    assert body["data"]["description"] == "Item with file associations"

def test_get_item_not_found(api_gateway_event, test_db, seed_claim):
    """Test attempting to retrieve an item that doesn't exist."""
    claim_id, user_id, file_id = seed_claim
    
    # Generate a random item ID that doesn't exist
    nonexistent_item_id = uuid.uuid4()
    
    event = api_gateway_event("GET", path_params={"item_id": str(nonexistent_item_id)}, auth_user=str(user_id))
    response = lambda_handler(event, {}, db_session=test_db)
    
    assert response["statusCode"] == 404
    response_body = json.loads(response["body"])
    assert "Item not found" in response_body["error_details"]

def test_get_item_invalid_id_format(api_gateway_event, test_db, seed_claim):
    """Test attempting to get an item with an invalid ID format."""
    claim_id, user_id, file_id = seed_claim
    
    event = api_gateway_event("GET", path_params={"item_id": "not-a-uuid"}, auth_user=str(user_id))
    response = lambda_handler(event, {}, db_session=test_db)
    
    assert response["statusCode"] == 400
    response_body = json.loads(response["body"])
    assert "Invalid item_id format" in response_body["error_details"]

def test_get_item_missing_id(api_gateway_event, test_db, seed_claim):
    """Test attempting to get an item without providing an ID."""
    claim_id, user_id, file_id = seed_claim
    
    event = api_gateway_event("GET", path_params={}, auth_user=str(user_id))
    response = lambda_handler(event, {}, db_session=test_db)
    
    assert response["statusCode"] == 400
    response_body = json.loads(response["body"])
    assert "Missing required path parameter: item_id" in response_body["error_details"]

def test_get_item_unauthorized(api_gateway_event, test_db, seed_claim):
    """Test attempting to get an item without authentication."""
    claim_id, user_id, file_id = seed_claim
    
    # Create an item
    item_id = uuid.uuid4()
    item = Item(
        id=item_id,
        claim_id=claim_id,
        name="Unauthorized Item",
        description="Item to test unauthorized access"
    )
    test_db.add(item)
    test_db.commit()
    
    # Attempt to get without authentication (no user_id)
    event = api_gateway_event("GET", path_params={"item_id": str(item_id)}, auth_user=None)
    response = lambda_handler(event, {}, db_session=test_db)
    
    # Check that the response indicates unauthorized access
    assert response["statusCode"] == 401
    response_body = json.loads(response["body"])
    assert "Unauthorized: Missing authentication" in response_body["error_details"]

@patch("sqlalchemy.orm.Session")
def test_get_item_database_error(mock_session, api_gateway_event, test_db, seed_item):
    """Test handling of database errors when getting an item."""
    item_id, user_id, file_id = seed_item
    
    # Mock the database session to raise an exception
    mock_session.query.side_effect = SQLAlchemyError("Database error")
    
    event = api_gateway_event("GET", path_params={"item_id": str(item_id)}, auth_user=str(user_id))
    response = lambda_handler(event, {}, db_session=mock_session)
    
    assert response["statusCode"] == 500
    response_body = json.loads(response["body"])
    assert "Database error" in response_body["error_details"]
