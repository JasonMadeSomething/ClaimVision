import pytest
import json
import uuid
from datetime import datetime, timezone
from items.create_item import lambda_handler
from models.file import File
from models.item_files import ItemFile
from models.user import User
from models.claim import Claim
from models.household import Household

def test_create_item_blank(api_gateway_event, test_db, seed_claim):
    """ Test creating a blank item with no details."""
    claim_id, user_id, file_id = seed_claim
    payload = {}  # No details provided

    event = api_gateway_event("POST", path_params={"claim_id": str(claim_id)}, body=json.dumps(payload), auth_user=str(user_id))
    response = lambda_handler(event, {}, db_session=test_db)

    assert response["statusCode"] == 201

def test_create_item_with_details(api_gateway_event, test_db, seed_claim):
    """ Test creating an item with details."""
    claim_id, user_id, file_id = seed_claim
    payload = {
        "name": "Test Item",
        "description": "A sample item",
        "estimated_value": 250.00,
        "condition": "New"
    }

    event = api_gateway_event("POST", path_params={"claim_id": str(claim_id)}, body=json.dumps(payload), auth_user=str(user_id))
    response = lambda_handler(event, {}, db_session=test_db)

    assert response["statusCode"] == 201

def test_create_item_with_file_association(api_gateway_event, test_db, seed_claim):
    """Test creating an item with an associated file."""
    claim_id, user_id, file_id = seed_claim
    
    # Use the existing file from seed_claim
    payload = {
        "name": "Item with File",
        "description": "An item with a file association",
        "file_id": str(file_id)
    }

    event = api_gateway_event("POST", path_params={"claim_id": str(claim_id)}, body=json.dumps(payload), auth_user=str(user_id))
    response = lambda_handler(event, {}, db_session=test_db)

    assert response["statusCode"] == 201
    response_body = json.loads(response["body"])
    item_id = response_body["data"]["item_id"]
    
    # Verify the file association exists
    association = test_db.query(ItemFile).filter(
        ItemFile.item_id == uuid.UUID(item_id),
        ItemFile.file_id == file_id
    ).first()
    
    assert association is not None

def test_create_item_with_file_from_different_claim(api_gateway_event, test_db, seed_claim):
    """Test attempting to create an item with a file from a different claim."""
    claim_id, user_id, file_id = seed_claim
    
    # Get the user to get their household_id
    user = test_db.query(User).filter(User.id == user_id).first()
    household_id = user.household_id
    
    # Create a new claim
    new_claim_id = uuid.uuid4()
    new_claim = Claim(
        id=new_claim_id,
        household_id=household_id,
        title="Another Claim",
        description="Another Test Claim",
        date_of_loss=datetime.now(timezone.utc)
    )
    test_db.add(new_claim)
    
    # Create a new file associated with the new claim
    new_file_id = uuid.uuid4()
    new_file = File(
        id=new_file_id,
        uploaded_by=user_id,
        household_id=household_id,
        file_name="different_claim_file.jpg",
        s3_key="different-claim-key",
        claim_id=new_claim_id,
        file_hash="unique_hash_different_claim"
    )
    test_db.add(new_file)
    test_db.commit()
    
    # Try to create an item in the original claim but with a file from the new claim
    payload = {
        "name": "Invalid File Item",
        "file_id": str(new_file_id)
    }
    
    event = api_gateway_event("POST", path_params={"claim_id": str(claim_id)}, body=json.dumps(payload), auth_user=str(user_id))
    response = lambda_handler(event, {}, db_session=test_db)
    
    # Should fail with a 400 status code
    assert response["statusCode"] == 400
    response_body = json.loads(response["body"])
    assert "File must belong to the same claim" in response_body["message"]

def test_create_item_with_file_not_owned(api_gateway_event, test_db, seed_claim):
    """Test attempting to create an item with a file not owned by the user's household."""
    claim_id, user_id, file_id = seed_claim
    
    # Create a new household
    other_household_id = uuid.uuid4()
    other_household = Household(
        id=other_household_id,
        name="Other Test Household"
    )
    test_db.add(other_household)
    test_db.commit()
    
    # Create a new user in the other household
    other_user_id = uuid.uuid4()
    other_user = User(
        id=other_user_id,
        email="other_user@example.com",
        first_name="Other",
        last_name="User",
        household_id=other_household_id
    )
    test_db.add(other_user)
    
    # Create a new claim for the other household
    other_claim_id = uuid.uuid4()
    other_claim = Claim(
        id=other_claim_id,
        household_id=other_household_id,
        title="Other Household Claim",
        description="Claim from another household",
        date_of_loss=datetime.now(timezone.utc)
    )
    test_db.add(other_claim)
    
    # Create a file owned by the other household
    other_file_id = uuid.uuid4()
    other_file = File(
        id=other_file_id,
        uploaded_by=other_user_id,
        household_id=other_household_id,
        file_name="other_household_file.jpg",
        s3_key="other-household-key",
        claim_id=other_claim_id,
        file_hash="unique_hash_other_household"
    )
    test_db.add(other_file)
    test_db.commit()
    
    # Try to create an item with a file from another household
    payload = {
        "name": "Unauthorized File Item",
        "file_id": str(other_file_id)
    }
    
    event = api_gateway_event("POST", path_params={"claim_id": str(claim_id)}, body=json.dumps(payload), auth_user=str(user_id))
    response = lambda_handler(event, {}, db_session=test_db)
    
    # Should fail with a 404 status code (file not found for security reasons)
    assert response["statusCode"] == 404
    response_body = json.loads(response["body"])
    assert "File not found" in response_body["message"]

def test_create_item_with_invalid_claim(api_gateway_event, test_db, seed_claim):
    """Test attempting to create an item with a claim that doesn't exist."""
    claim_id, user_id, file_id = seed_claim
    
    # Generate a random claim ID that doesn't exist
    nonexistent_claim_id = uuid.uuid4()
    
    payload = {
        "name": "Invalid Claim Item"
    }
    
    event = api_gateway_event("POST", path_params={"claim_id": str(nonexistent_claim_id)}, body=json.dumps(payload), auth_user=str(user_id))
    response = lambda_handler(event, {}, db_session=test_db)
    
    # Should fail with a 404 status code
    assert response["statusCode"] == 404
    response_body = json.loads(response["body"])
    assert "Claim not found" in response_body["message"]

def test_create_item_with_claim_from_different_household(api_gateway_event, test_db, seed_claim):
    """Test attempting to create an item with a claim from a different household."""
    claim_id, user_id, file_id = seed_claim
    
    # Create a new household
    other_household_id = uuid.uuid4()
    other_household = Household(
        id=other_household_id,
        name="Other Test Household"
    )
    test_db.add(other_household)
    test_db.commit()
    
    # Create a new claim for the other household
    other_claim_id = uuid.uuid4()
    other_claim = Claim(
        id=other_claim_id,
        household_id=other_household_id,
        title="Other Household Claim",
        description="Claim from another household",
        date_of_loss=datetime.now(timezone.utc)
    )
    test_db.add(other_claim)
    test_db.commit()
    
    # Try to create an item with a claim from another household
    payload = {
        "name": "Unauthorized Claim Item"
    }
    
    event = api_gateway_event("POST", path_params={"claim_id": str(other_claim_id)}, body=json.dumps(payload), auth_user=str(user_id))
    response = lambda_handler(event, {}, db_session=test_db)
    
    # Should fail with a 404 status code (claim not found for security reasons)
    assert response["statusCode"] == 404
    response_body = json.loads(response["body"])
    assert "Claim not found" in response_body["message"]
