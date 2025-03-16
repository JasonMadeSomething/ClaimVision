import json
import uuid
from items.update_item import lambda_handler as update_item_handler
from items.create_item import lambda_handler as create_item_handler
from models.room import Room
from models.claim import Claim
from models.household import Household
from models.user import User
from models.item import Item
from datetime import datetime

def test_create_item_with_room(test_db, api_gateway_event):
    """Test creating an item with a room assignment"""
    # Create test data
    household_id = uuid.uuid4()
    claim_id = uuid.uuid4()
    user_id = uuid.uuid4()
    room_id = uuid.uuid4()
    
    # Create household, user, claim, and room
    test_household = Household(id=household_id, name="Test Household")
    test_user = User(id=user_id, email="test@example.com", first_name="Test", last_name="User", household_id=household_id)
    test_claim = Claim(id=claim_id, household_id=household_id, title="Test Claim", date_of_loss=datetime(2024, 1, 10))
    test_room = Room(id=room_id, name="Living Room", description="Main living area", household_id=household_id, claim_id=claim_id)
    
    test_db.add_all([test_household, test_user, test_claim, test_room])
    test_db.commit()
    
    # Create request body
    item_data = {
        "name": "Sofa",
        "description": "Leather sofa",
        "room_id": str(room_id)
    }
    
    # Create event
    event = api_gateway_event(
        http_method="POST",
        path_params={"claim_id": str(claim_id)},
        body=json.dumps(item_data),
        auth_user=str(user_id)
    )
    
    # Call lambda handler
    response = create_item_handler(event, {}, db_session=test_db)
    body = json.loads(response["body"])
    
    # Assertions
    assert response["statusCode"] == 201
    assert body["data"]["name"] == "Sofa"
    assert body["data"]["room_id"] == str(room_id)
    
    # Verify item was created in the database with room association
    item = test_db.query(Item).filter(Item.id == uuid.UUID(body["data"]["id"])).first()
    assert item is not None
    assert item.room_id == room_id

def test_create_item_without_room(test_db, api_gateway_event):
    """Test creating an item without a room assignment"""
    # Create test data
    household_id = uuid.uuid4()
    claim_id = uuid.uuid4()
    user_id = uuid.uuid4()
    
    # Create household, user, and claim
    test_household = Household(id=household_id, name="Test Household")
    test_user = User(id=user_id, email="test@example.com", first_name="Test", last_name="User", household_id=household_id)
    test_claim = Claim(id=claim_id, household_id=household_id, title="Test Claim", date_of_loss=datetime(2024, 1, 10))
    
    test_db.add_all([test_household, test_user, test_claim])
    test_db.commit()
    
    # Create request body without room_id
    item_data = {
        "name": "Sofa",
        "description": "Leather sofa"
    }
    
    # Create event
    event = api_gateway_event(
        http_method="POST",
        path_params={"claim_id": str(claim_id)},
        body=json.dumps(item_data),
        auth_user=str(user_id)
    )
    
    # Call lambda handler
    response = create_item_handler(event, {}, db_session=test_db)
    body = json.loads(response["body"])
    
    # Assertions
    assert response["statusCode"] == 201
    assert body["data"]["name"] == "Sofa"
    assert "room_id" not in body["data"] or body["data"]["room_id"] is None
    
    # Verify item was created in the database without room association
    item = test_db.query(Item).filter(Item.id == uuid.UUID(body["data"]["id"])).first()
    assert item is not None
    assert item.room_id is None

def test_update_item_add_room(test_db, api_gateway_event):
    """Test updating an item to add a room association"""
    # Create test data
    household_id = uuid.uuid4()
    claim_id = uuid.uuid4()
    user_id = uuid.uuid4()
    room_id = uuid.uuid4()
    item_id = uuid.uuid4()
    
    # Create household, user, claim, room, and item (without room)
    test_household = Household(id=household_id, name="Test Household")
    test_user = User(id=user_id, email="test@example.com", first_name="Test", last_name="User", household_id=household_id)
    test_claim = Claim(id=claim_id, household_id=household_id, title="Test Claim", date_of_loss=datetime(2024, 1, 10))
    test_room = Room(id=room_id, name="Living Room", description="Main living area", household_id=household_id, claim_id=claim_id)
    test_item = Item(id=item_id, claim_id=claim_id, name="Sofa", description="Leather sofa")
    
    test_db.add_all([test_household, test_user, test_claim, test_room, test_item])
    test_db.commit()
    
    # Create request body to add room
    update_data = {
        "room_id": str(room_id)
    }
    
    # Create event
    event = api_gateway_event(
        http_method="PUT",
        path_params={"item_id": str(item_id)},
        body=json.dumps(update_data),
        auth_user=str(user_id)
    )
    
    # Call lambda handler
    response = update_item_handler(event, {}, db_session=test_db)
    body = json.loads(response["body"])
    
    # Assertions
    assert response["statusCode"] == 200
    assert body["data"]["room_id"] == str(room_id)
    
    # Verify item was updated in the database with room association
    updated_item = test_db.query(Item).filter(Item.id == item_id).first()
    assert updated_item.room_id == room_id

def test_update_item_change_room(test_db, api_gateway_event):
    """Test updating an item to change its room association"""
    # Create test data
    household_id = uuid.uuid4()
    claim_id = uuid.uuid4()
    user_id = uuid.uuid4()
    room1_id = uuid.uuid4()
    room2_id = uuid.uuid4()
    item_id = uuid.uuid4()
    
    # Create household, user, claim, rooms, and item (with room1)
    test_household = Household(id=household_id, name="Test Household")
    test_user = User(id=user_id, email="test@example.com", first_name="Test", last_name="User", household_id=household_id)
    test_claim = Claim(id=claim_id, household_id=household_id, title="Test Claim", date_of_loss=datetime(2024, 1, 10))
    test_room1 = Room(id=room1_id, name="Living Room", description="Main living area", household_id=household_id, claim_id=claim_id)
    test_room2 = Room(id=room2_id, name="Bedroom", description="Master bedroom", household_id=household_id, claim_id=claim_id)
    test_item = Item(id=item_id, claim_id=claim_id, name="Sofa", description="Leather sofa", room_id=room1_id)
    
    test_db.add_all([test_household, test_user, test_claim, test_room1, test_room2, test_item])
    test_db.commit()
    
    # Create request body to change room
    update_data = {
        "room_id": str(room2_id)
    }
    
    # Create event
    event = api_gateway_event(
        http_method="PUT",
        path_params={"item_id": str(item_id)},
        body=json.dumps(update_data),
        auth_user=str(user_id)
    )
    
    # Call lambda handler
    response = update_item_handler(event, {}, db_session=test_db)
    body = json.loads(response["body"])
    
    # Assertions
    assert response["statusCode"] == 200
    assert body["data"]["room_id"] == str(room2_id)
    
    # Verify item was updated in the database with new room association
    updated_item = test_db.query(Item).filter(Item.id == item_id).first()
    assert updated_item.room_id == room2_id

def test_update_item_remove_room(test_db, api_gateway_event):
    """Test updating an item to remove its room association"""
    # Create test data
    household_id = uuid.uuid4()
    claim_id = uuid.uuid4()
    user_id = uuid.uuid4()
    room_id = uuid.uuid4()
    item_id = uuid.uuid4()
    
    # Create household, user, claim, room, and item (with room)
    test_household = Household(id=household_id, name="Test Household")
    test_user = User(id=user_id, email="test@example.com", first_name="Test", last_name="User", household_id=household_id)
    test_claim = Claim(id=claim_id, household_id=household_id, title="Test Claim", date_of_loss=datetime(2024, 1, 10))
    test_room = Room(id=room_id, name="Living Room", description="Main living area", household_id=household_id, claim_id=claim_id)
    test_item = Item(id=item_id, claim_id=claim_id, name="Sofa", description="Leather sofa", room_id=room_id)
    
    test_db.add_all([test_household, test_user, test_claim, test_room, test_item])
    test_db.commit()
    
    # Create request body to remove room
    update_data = {
        "room_id": None
    }
    
    # Create event
    event = api_gateway_event(
        http_method="PUT",
        path_params={"item_id": str(item_id)},
        body=json.dumps(update_data),
        auth_user=str(user_id)
    )
    
    # Call lambda handler
    response = update_item_handler(event, {}, db_session=test_db)
    body = json.loads(response["body"])
    
    # Assertions
    assert response["statusCode"] == 200
    assert "room_id" not in body["data"] or body["data"]["room_id"] is None
    
    # Verify item was updated in the database with room association removed
    updated_item = test_db.query(Item).filter(Item.id == item_id).first()
    assert updated_item.room_id is None
