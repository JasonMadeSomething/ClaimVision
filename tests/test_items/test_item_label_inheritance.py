import json
import uuid
from items.get_item import lambda_handler as get_item_handler
from items.update_item import lambda_handler as update_item_handler
from models import File, User, Label
from models.item import Item
from models.item_files import ItemFile
from models.claim import Claim
from datetime import datetime, timezone

def test_item_inherits_correct_labels(api_gateway_event, test_db, seed_item_with_file_labels):
    """Test that an item only inherits the labels explicitly associated with it."""
    item_id, user_id, file_id = seed_item_with_file_labels  
    
    # First, update the item with only the "TV" label
    update_payload = {
        "file_id": str(file_id),  # Use the correct file_id
        "labels": ["TV"]
    }
    update_event = api_gateway_event(
        "PATCH", 
        path_params={"item_id": str(item_id)}, 
        body=update_payload, 
        auth_user=str(user_id)
    )
    update_response = update_item_handler(update_event, {}, db_session=test_db)
    assert update_response["statusCode"] == 200  # Check HTTP status code
    response_body = json.loads(update_response["body"])
    assert response_body["status"] == "OK"  # Check status in response body
    
    # Then, get the item to verify the labels
    get_event = api_gateway_event("GET", path_params={"item_id": str(item_id)}, auth_user=str(user_id))
    get_response = get_item_handler(get_event, {}, db_session=test_db)
    
    # Parse the JSON response body
    response_data = json.loads(get_response["body"])
    labels = response_data["data"]["labels"]
    
    # Extract label texts for easier assertion
    label_texts = [label["text"] for label in labels]

    # Ensure only expected labels are inherited
    assert "TV" in label_texts
    assert "Couch" not in label_texts

def test_multiple_items_dont_inherit_wrong_labels(api_gateway_event, test_db, seed_multiple_items_with_labels):
    """Test that items have their own distinct labels when updated."""
    item_ids, user_id = seed_multiple_items_with_labels
    
    # Get the user to update their household_id
    user = test_db.query(User).filter(User.id == user_id).first()
    
    # Create files to associate with items
    file_id_1 = str(uuid.uuid4())
    file_id_2 = str(uuid.uuid4())
    
    # Create files in the database - use the user's existing household_id
    household_id = user.household_id
    
    # Create a claim first with the user's household_id
    claim_id = uuid.uuid4()
    test_claim = Claim(
        id=claim_id,
        household_id=household_id,
        title="Test Claim",
        description="Test Claim Description",
        date_of_loss=datetime.now(timezone.utc)
    )
    test_db.add(test_claim)
    test_db.commit()
    
    # Update the items to use the new claim_id
    for item_id in item_ids:
        item = test_db.query(Item).filter(Item.id == item_id).first()
        if item:
            item.claim_id = claim_id
    test_db.commit()
    
    # Get or create labels for testing
    tv_label = test_db.query(Label).filter(Label.label_text == "TV", Label.is_ai_generated.is_(True)).first()
    if not tv_label:
        tv_label = Label(
            id=uuid.uuid4(),
            label_text="TV",
            is_ai_generated=True,
            household_id=household_id
        )
        test_db.add(tv_label)
        test_db.commit()
    
    laptop_label = test_db.query(Label).filter(Label.label_text == "Laptop", Label.is_ai_generated.is_(True)).first()
    if not laptop_label:
        laptop_label = Label(
            id=uuid.uuid4(),
            label_text="Laptop",
            is_ai_generated=True,
            household_id=household_id
        )
        test_db.add(laptop_label)
        test_db.commit()
    
    file_1 = File(
        id=uuid.UUID(file_id_1), 
        uploaded_by=user_id, 
        household_id=household_id, 
        file_name="file1.jpg", 
        s3_key="file1-key",
        claim_id=claim_id,
        file_hash="unique_hash_1"
    )
    file_2 = File(
        id=uuid.UUID(file_id_2), 
        uploaded_by=user_id, 
        household_id=household_id, 
        file_name="file2.jpg", 
        s3_key="file2-key",
        claim_id=claim_id,
        file_hash="unique_hash_2"
    )
    test_db.add_all([file_1, file_2])
    test_db.commit()
    
    # Associate files with items
    test_db.add_all([
        ItemFile(item_id=item_ids[0], file_id=uuid.UUID(file_id_1)),
        ItemFile(item_id=item_ids[1], file_id=uuid.UUID(file_id_2))
    ])
    test_db.commit()
    
    # Update first item with "TV" label
    update_payload_1 = {
        "file_id": file_id_1,
        "labels": ["TV"]
    }
    update_event_1 = api_gateway_event(
        "PATCH", 
        path_params={"item_id": str(item_ids[0])}, 
        body=update_payload_1, 
        auth_user=str(user_id)
    )
    update_response_1 = update_item_handler(update_event_1, {}, db_session=test_db)
    assert update_response_1["statusCode"] == 200
    
    # Update second item with "Laptop" label
    update_payload_2 = {
        "file_id": file_id_2,
        "labels": ["Laptop"]
    }
    update_event_2 = api_gateway_event(
        "PATCH", 
        path_params={"item_id": str(item_ids[1])}, 
        body=update_payload_2, 
        auth_user=str(user_id)
    )
    update_response_2 = update_item_handler(update_event_2, {}, db_session=test_db)
    assert update_response_2["statusCode"] == 200
    
    # Get first item and verify labels
    get_event_1 = api_gateway_event("GET", path_params={"item_id": str(item_ids[0])}, auth_user=str(user_id))
    get_response_1 = get_item_handler(get_event_1, {}, db_session=test_db)
    response_data_1 = json.loads(get_response_1["body"])
    labels_1 = response_data_1["data"]["labels"]
    label_texts_1 = [label["text"] for label in labels_1]
    
    # Get second item and verify labels
    get_event_2 = api_gateway_event("GET", path_params={"item_id": str(item_ids[1])}, auth_user=str(user_id))
    get_response_2 = get_item_handler(get_event_2, {}, db_session=test_db)
    response_data_2 = json.loads(get_response_2["body"])
    labels_2 = response_data_2["data"]["labels"]
    label_texts_2 = [label["text"] for label in labels_2]
    
    # Verify first item has only "TV" label
    assert "TV" in label_texts_1
    assert "Laptop" not in label_texts_1
    
    # Verify second item has only "Laptop" label
    assert "Laptop" in label_texts_2
    assert "TV" not in label_texts_2
