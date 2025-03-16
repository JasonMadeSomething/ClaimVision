import pytest
import json
from items.update_item import lambda_handler
from models.item_labels import ItemLabel
from models.label import Label
from models.item_files import ItemFile

def test_associate_file_to_item(api_gateway_event, test_db, seed_item):
    """ Test associating a file to an item."""
    item_id, user_id, file_id = seed_item

    payload = {"file_id": str(file_id)}
    event = api_gateway_event("PATCH", path_params={"item_id": str(item_id)}, body=json.dumps(payload), auth_user=str(user_id))
    response = lambda_handler(event, {}, db_session=test_db)

    assert response["statusCode"] == 200
    response_body = json.loads(response["body"])
    assert response_body["status"] == "OK"

    #  Verify the association exists
    assert test_db.query(ItemFile).filter(ItemFile.item_id == item_id, ItemFile.file_id == file_id).first() is not None


def test_associate_file_with_selected_labels(api_gateway_event, test_db, seed_item, seed_file):
    """ Test associating a file to an item with specific labels."""
    item_id, user_id, file_id = seed_item
    # Get household_id from the seed_file fixture
    _, _, household_id = seed_file

    # First create the labels in the database
    tv_label = Label(label_text="TV", is_ai_generated=True, household_id=household_id)
    electronics_label = Label(label_text="Electronics", is_ai_generated=True, household_id=household_id)
    couch_label = Label(label_text="Couch", is_ai_generated=True, household_id=household_id)
    test_db.add_all([tv_label, electronics_label, couch_label])
    test_db.commit()

    payload = {
        "file_id": str(file_id),
        "labels": ["TV", "Electronics"]
    }

    event = api_gateway_event("PATCH", path_params={"item_id": str(item_id)}, body=json.dumps(payload), auth_user=str(user_id))
    response = lambda_handler(event, {}, db_session=test_db)

    assert response["statusCode"] == 200
    response_body = json.loads(response["body"])
    assert response_body["status"] == "OK"

    #  Verify only selected labels are applied
    label_ids = [l.label_id for l in test_db.query(ItemLabel).filter(ItemLabel.item_id == item_id).all()]
    applied_labels = [label.label_text for label in test_db.query(Label.label_text).filter(Label.id.in_(label_ids)).all()]

    assert "TV" in applied_labels
    assert "Electronics" in applied_labels
    assert "Couch" not in applied_labels  #  This label wasn't selected

def test_update_item_labels(api_gateway_event, test_db, seed_item, seed_file):
    """ Test updating label selection for an item."""
    item_id, user_id, file_id = seed_item
    # Get household_id from the seed_file fixture
    _, _, household_id = seed_file

    # Create labels in the database
    tv_label = Label(label_text="TV", is_ai_generated=True, household_id=household_id)
    smart_tv_label = Label(label_text="Smart TV", is_ai_generated=True, household_id=household_id)
    test_db.add_all([tv_label, smart_tv_label])
    test_db.commit()

    #  Initial association with TV label
    test_db.add(ItemLabel(item_id=item_id, label_id=tv_label.id))
    test_db.commit()

    #  Update labels to remove TV and add Smart TV
    payload = {
        "file_id": str(file_id),
        "labels": ["Smart TV"]
    }

    event = api_gateway_event("PATCH", path_params={"item_id": str(item_id)}, body=json.dumps(payload), auth_user=str(user_id))
    response = lambda_handler(event, {}, db_session=test_db)

    assert response["statusCode"] == 200
    response_body = json.loads(response["body"])
    assert response_body["status"] == "OK"

    #  Verify updated labels
    label_ids = [l.label_id for l in test_db.query(ItemLabel).filter(ItemLabel.item_id == item_id).all()]
    applied_labels = [label.label_text for label in test_db.query(Label.label_text).filter(Label.id.in_(label_ids)).all()]

    assert "Smart TV" in applied_labels
    assert "TV" not in applied_labels  #  TV label should be removed
