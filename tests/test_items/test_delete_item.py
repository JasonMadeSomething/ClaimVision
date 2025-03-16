import pytest
import json
import uuid
from unittest.mock import patch, MagicMock
from sqlalchemy.exc import SQLAlchemyError
from items.delete_item import lambda_handler
from models.item import Item
from models.file import File
from models.item_files import ItemFile
from models.item_labels import ItemLabel
from models.claim import Claim
from models.label import Label

def test_delete_item_success(api_gateway_event, test_db, seed_item, seed_file):
    """ Test deleting an item and ensuring the file remains."""
    item_id, user_id, file_id = seed_item
    
    event = api_gateway_event("DELETE", path_params={"item_id": str(item_id)}, auth_user=str(user_id))
    response = lambda_handler(event, {}, db_session=test_db)

    assert response["statusCode"] == 204

    # Ensure item is gone, but file still exists
    assert test_db.query(Item).filter(Item.id == item_id).first() is None
    assert test_db.query(File).filter(File.id == file_id).first() is not None

def test_delete_item_with_file_associations(api_gateway_event, test_db, seed_claim):
    """Test deleting an item with file associations and verifying associations are removed."""
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
    
    # Verify association exists
    association = test_db.query(ItemFile).filter(ItemFile.item_id == item_id, ItemFile.file_id == file_id).first()
    assert association is not None
    
    # Delete the item
    event = api_gateway_event("DELETE", path_params={"item_id": str(item_id)}, auth_user=str(user_id))
    response = lambda_handler(event, {}, db_session=test_db)
    
    assert response["statusCode"] == 204
    
    # Verify item is deleted
    assert test_db.query(Item).filter(Item.id == item_id).first() is None
    
    # Verify association is deleted but file still exists
    assert test_db.query(ItemFile).filter(ItemFile.item_id == item_id, ItemFile.file_id == file_id).first() is None
    assert test_db.query(File).filter(File.id == file_id).first() is not None

def test_delete_item_with_label_associations(api_gateway_event, test_db, seed_claim):
    """Test deleting an item with label associations and verifying associations are removed."""
    claim_id, user_id, file_id = seed_claim
    
    # Create an item
    item_id = uuid.uuid4()
    item = Item(
        id=item_id,
        claim_id=claim_id,
        name="Item with Labels",
        description="Item with label associations"
    )
    test_db.add(item)
    test_db.commit()  # Commit the item first
    
    # Create a label
    label_id = uuid.uuid4()
    household_id = test_db.query(Claim).filter(Claim.id == claim_id).first().household_id
    
    # Create the label using the Label model
    label = Label(
        id=label_id,
        label_text="Test Label",
        is_ai_generated=False,
        deleted=False,
        household_id=household_id
    )
    test_db.add(label)
    test_db.commit()  # Commit the label before creating the association
    
    # Create an item-label association
    item_label = ItemLabel(
        item_id=item_id,
        label_id=label_id,
        deleted=False
    )
    test_db.add(item_label)
    test_db.commit()
    
    # Verify association exists
    association = test_db.query(ItemLabel).filter(ItemLabel.item_id == item_id, ItemLabel.label_id == label_id).first()
    assert association is not None
    
    # Delete the item
    event = api_gateway_event("DELETE", path_params={"item_id": str(item_id)}, auth_user=str(user_id))
    response = lambda_handler(event, {}, db_session=test_db)
    
    assert response["statusCode"] == 204
    
    # Verify item is deleted
    assert test_db.query(Item).filter(Item.id == item_id).first() is None
    
    # Verify association is deleted but label still exists
    assert test_db.query(ItemLabel).filter(ItemLabel.item_id == item_id, ItemLabel.label_id == label_id).first() is None
    assert test_db.query(Label).filter(Label.id == label_id).first() is not None

def test_delete_item_not_found(api_gateway_event, test_db, seed_claim):
    """Test attempting to delete an item that doesn't exist."""
    claim_id, user_id, file_id = seed_claim
    
    # Generate a random item ID that doesn't exist
    nonexistent_item_id = uuid.uuid4()
    
    event = api_gateway_event("DELETE", path_params={"item_id": str(nonexistent_item_id)}, auth_user=str(user_id))
    response = lambda_handler(event, {}, db_session=test_db)
    
    assert response["statusCode"] == 404
    response_body = json.loads(response["body"])
    assert "Item not found" in response_body["message"]

def test_delete_item_invalid_id_format(api_gateway_event, test_db, seed_claim):
    """Test attempting to delete an item with an invalid ID format."""
    claim_id, user_id, file_id = seed_claim
    
    event = api_gateway_event("DELETE", path_params={"item_id": "not-a-uuid"}, auth_user=str(user_id))
    response = lambda_handler(event, {}, db_session=test_db)
    
    assert response["statusCode"] == 400
    response_body = json.loads(response["body"])
    assert "Invalid item ID format" in response_body["message"]

def test_delete_item_missing_id(api_gateway_event, test_db, seed_claim):
    """Test attempting to delete an item without providing an ID."""
    claim_id, user_id, file_id = seed_claim
    
    event = api_gateway_event("DELETE", path_params={}, auth_user=str(user_id))
    response = lambda_handler(event, {}, db_session=test_db)
    
    assert response["statusCode"] == 400
    response_body = json.loads(response["body"])
    assert "Item ID is required" in response_body["message"]

def test_delete_item_unauthorized(api_gateway_event, test_db, seed_claim):
    """Test attempting to delete an item without authentication."""
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
    
    # Attempt to delete without authentication (no user_id)
    event = api_gateway_event("DELETE", path_params={"item_id": str(item_id)}, auth_user=None)  # Explicitly set auth_user to None
    response = lambda_handler(event, {}, db_session=test_db)
    
    # Check that the response indicates unauthorized access
    assert response["statusCode"] == 400
    response_body = json.loads(response["body"])
    assert "Invalid authentication" in response_body["message"]
    
    # Verify item still exists
    assert test_db.query(Item).filter(Item.id == item_id).first() is not None

@patch("items.delete_item.get_db_session")
def test_delete_item_database_error(mock_get_db, api_gateway_event, test_db, seed_item):
    """Test handling of database errors when deleting an item."""
    item_id, user_id, file_id = seed_item
    
    # Mock the database session to raise an exception
    mock_session = MagicMock()
    mock_session.query.side_effect = SQLAlchemyError("Database error")
    mock_get_db.return_value = mock_session
    
    event = api_gateway_event("DELETE", path_params={"item_id": str(item_id)}, auth_user=str(user_id))
    response = lambda_handler(event, {})
    
    assert response["statusCode"] == 500
    response_body = json.loads(response["body"])
    assert "Database error" in response_body["message"]
