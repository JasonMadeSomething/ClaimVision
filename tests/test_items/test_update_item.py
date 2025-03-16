import pytest
import json
import uuid
from items.update_item import lambda_handler
from models.claim import Claim
from models.user import User
from models.household import Household
from models.file import File

def test_update_item_name(api_gateway_event, test_db, seed_item):
    """ Test updating an item's name."""
    item_id, user_id, file_id = seed_item

    payload = {"name": "Updated Item Name"}
    event = api_gateway_event("PATCH", path_params={"item_id": str(item_id)}, body=json.dumps(payload), auth_user=str(user_id))
    response = lambda_handler(event, {}, db_session=test_db)

    assert response["statusCode"] == 200
    
def test_update_item_multiple_properties(api_gateway_event, test_db, seed_item):
    """ Test updating multiple item properties at once."""
    item_id, user_id, file_id = seed_item

    payload = {
        "name": "Multi-Updated Item",
        "description": "This is an updated description",
        "estimated_value": 299.99,
        "condition": "Good"
    }
    event = api_gateway_event("PATCH", path_params={"item_id": str(item_id)}, body=json.dumps(payload), auth_user=str(user_id))
    response = lambda_handler(event, {}, db_session=test_db)

    assert response["statusCode"] == 200
    
    # Verify the item was updated correctly
    from items.get_item import lambda_handler as get_item_handler
    get_event = api_gateway_event("GET", path_params={"item_id": str(item_id)}, auth_user=str(user_id))
    get_response = get_item_handler(get_event, {}, db_session=test_db)
    
    item_data = json.loads(get_response["body"])["data"]
    assert item_data["name"] == "Multi-Updated Item"
    assert item_data["description"] == "This is an updated description"
    assert item_data["estimated_value"] == 299.99
    assert item_data["condition"] == "Good"

def test_update_item_no_auth(api_gateway_event, test_db, seed_item):
    """ Test updating an item without authentication."""
    item_id, _, _ = seed_item

    payload = {"name": "Unauthorized Update"}
    # Explicitly set auth_user to None to test no authentication
    event = api_gateway_event("PATCH", path_params={"item_id": str(item_id)}, body=json.dumps(payload), auth_user=None)
    response = lambda_handler(event, {}, db_session=test_db)

    assert response["statusCode"] == 401
    response_body = json.loads(response["body"])
    assert "Authentication required" in response_body["message"]

def test_update_item_invalid_id(api_gateway_event, test_db, seed_item):
    """ Test updating an item with an invalid ID."""
    _, user_id, _ = seed_item

    payload = {"name": "Invalid ID Update"}
    event = api_gateway_event("PATCH", path_params={"item_id": "not-a-uuid"}, body=json.dumps(payload), auth_user=str(user_id))
    response = lambda_handler(event, {}, db_session=test_db)

    assert response["statusCode"] == 400
    response_body = json.loads(response["body"])
    assert "Invalid item ID format" in response_body["message"]

def test_update_nonexistent_item(api_gateway_event, test_db, seed_item):
    """ Test updating an item that doesn't exist."""
    _, user_id, _ = seed_item
    
    # Generate a random UUID that doesn't exist in the database
    nonexistent_id = str(uuid.uuid4())
    
    payload = {"name": "Nonexistent Item Update"}
    event = api_gateway_event("PATCH", path_params={"item_id": nonexistent_id}, body=json.dumps(payload), auth_user=str(user_id))
    response = lambda_handler(event, {}, db_session=test_db)

    assert response["statusCode"] == 404
    response_body = json.loads(response["body"])
    assert "Item not found" in response_body["message"]

def test_update_item_with_invalid_file_id(api_gateway_event, test_db, seed_item):
    """ Test updating an item with an invalid file ID."""
    item_id, user_id, _ = seed_item

    payload = {
        "name": "Invalid File Update",
        "file_id": "not-a-uuid"
    }
    event = api_gateway_event("PATCH", path_params={"item_id": str(item_id)}, body=json.dumps(payload), auth_user=str(user_id))
    response = lambda_handler(event, {}, db_session=test_db)

    assert response["statusCode"] == 400
    response_body = json.loads(response["body"])
    assert "Invalid file ID format" in response_body["message"]

def test_update_item_with_nonexistent_file(api_gateway_event, test_db, seed_item):
    """ Test updating an item with a file that doesn't exist."""
    item_id, user_id, _ = seed_item
    
    # Generate a random UUID that doesn't exist in the database
    nonexistent_file_id = str(uuid.uuid4())
    
    payload = {
        "name": "Nonexistent File Update",
        "file_id": nonexistent_file_id
    }
    event = api_gateway_event("PATCH", path_params={"item_id": str(item_id)}, body=json.dumps(payload), auth_user=str(user_id))
    response = lambda_handler(event, {}, db_session=test_db)

    assert response["statusCode"] == 404
    response_body = json.loads(response["body"])
    assert "File not found" in response_body["message"]

def test_update_item_unauthorized_user(api_gateway_event, test_db, seed_item):
    """ Test updating an item with an unauthorized user."""
    item_id, _, _ = seed_item
    
    # Create a new household
    new_household = Household(name="Test Household 2")
    test_db.add(new_household)
    test_db.commit()
    
    # Create a different user in a different household
    unauthorized_user = User(
        email="unauthorized@example.com",
        first_name="Unauthorized",
        last_name="User",
        household_id=new_household.id
    )
    test_db.add(unauthorized_user)
    test_db.commit()
    
    payload = {"name": "Unauthorized User Update"}
    event = api_gateway_event("PATCH", path_params={"item_id": str(item_id)}, body=json.dumps(payload), auth_user=str(unauthorized_user.id))
    response = lambda_handler(event, {}, db_session=test_db)

    assert response["statusCode"] == 404
    response_body = json.loads(response["body"])
    assert "Item not found" in response_body["message"]

def test_update_item_with_file_from_different_claim(api_gateway_event, test_db, seed_item):
    """ Test updating an item with a file from a different claim."""
    item_id, user_id, _ = seed_item
    
    # Get the user from the database
    user = test_db.query(User).filter(User.id == user_id).first()
    
    # Create a new claim for the same household
    new_claim = Claim(
        household_id=user.household_id,
        title="Another Test Claim",
        description="This is another test claim",
        date_of_loss="2023-01-01"
    )
    test_db.add(new_claim)
    test_db.commit()
    
    # Create a file for the new claim
    different_claim_file = File(
        claim_id=new_claim.id,
        uploaded_by=user_id,
        household_id=user.household_id,
        file_name="different_claim_file.jpg",
        s3_key="different_claim_file.jpg",
        file_hash="different_claim_file_hash"
    )
    test_db.add(different_claim_file)
    test_db.commit()
    
    payload = {
        "name": "Different Claim File Update",
        "file_id": str(different_claim_file.id)
    }
    event = api_gateway_event("PATCH", path_params={"item_id": str(item_id)}, body=json.dumps(payload), auth_user=str(user_id))
    response = lambda_handler(event, {}, db_session=test_db)

    assert response["statusCode"] == 404
    response_body = json.loads(response["body"])
    assert "File not found" in response_body["message"]
