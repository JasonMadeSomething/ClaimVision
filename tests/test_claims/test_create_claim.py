import json
import uuid
from datetime import datetime, timedelta, timezone
from claims.create_claim import lambda_handler
from models.claim import Claim
from models.household import Household

def test_create_claim_success(test_db, api_gateway_event):
    """✅ Test successful claim creation with real test DB"""

    # ✅ Create a test household before inserting a claim
    household_id = uuid.uuid4()
    test_household = Household(id=household_id, name="Test Household")
    test_db.add(test_household)
    test_db.commit()

    event = api_gateway_event(
        http_method="POST",
        body={"title": "Lost Laptop", "date_of_loss": "2024-01-10", "household_id": str(household_id)},  # ✅ Now a real existing household
    )

    response = lambda_handler(event, {})
    body = json.loads(response["body"])

    claim = test_db.query(Claim).filter_by(title="Lost Laptop").first()

    assert response["statusCode"] == 201
    assert claim is not None  # ✅ Ensure claim was stored
    assert claim.date_of_loss == datetime.strptime("2024-01-10", "%Y-%m-%d")
    assert "id" in body["data"]

def test_create_claim_missing_fields(test_db, api_gateway_event):
    """❌ Test creating a claim with missing required fields"""
    event = api_gateway_event(http_method="POST", body={"title": "Lost Laptop"})  # Missing `date_of_loss`
    response = lambda_handler(event, {})
    body = json.loads(response["body"])

    assert response["statusCode"] == 400
    assert "missing_fields" in body["data"]

def test_create_claim_invalid_date_format(test_db, api_gateway_event):
    """❌ Test creating a claim with an invalid date format"""
    household_id = uuid.uuid4()
    test_household = Household(id=household_id, name="Test Household")
    test_db.add(test_household)
    test_db.commit()

    event = api_gateway_event(http_method="POST", body={"title": "Lost Laptop", "date_of_loss": "10-01-2024", "household_id": str(household_id)})  # Wrong format
    response = lambda_handler(event, {})
    body = json.loads(response["body"])
    print(body)
    assert response["statusCode"] == 400
    assert "Invalid date format" in body["error_details"]

def test_create_claim_dynamodb_failure(test_db, api_gateway_event):
    """❌ Test creating a claim when PostgreSQL fails"""
    # ✅ Simulate DB failure
    test_db.rollback()
    test_db.close()

    event = api_gateway_event(
        http_method="POST",
        body={"title": "Lost Laptop", "date_of_loss": "2024-01-10", "household_id": "household-456"},
    )

    response = lambda_handler(event, {})
    body = json.loads(response["body"])

    assert response["statusCode"] == 500
    assert "Internal Server Error" in body["message"]

def test_create_claim_duplicate_title(test_db, api_gateway_event):
    """❌ Test creating a duplicate claim title in the same household"""
    household_id = uuid.uuid4()
    test_household = Household(id=household_id, name="Test Household")
    test_db.add(test_household)
    test_db.commit()
    
    claim = Claim(id=uuid.uuid4(), household_id=household_id, title="Lost Laptop", date_of_loss=datetime(2024, 1, 10))
    test_db.add(claim)
    test_db.commit()

    event = api_gateway_event(
        http_method="POST",
        body={"title": "Lost Laptop", "date_of_loss": "2024-01-10", "household_id": str(household_id)},
    )

    response = lambda_handler(event, {}, db_session=test_db)
    assert response["statusCode"] == 201  # ✅ Confirm if duplicates are allowed

def test_create_claim_future_date(test_db, api_gateway_event):
    """❌ Test creating a claim with a future date"""

    household_id = uuid.uuid4()
    test_household = Household(id=household_id, name="Test Household")
    test_db.add(test_household)
    test_db.commit()

    future_date = (datetime.now(timezone.utc) + timedelta(days=10)).strftime("%Y-%m-%d")  # ✅ Use timezone-aware UTC
    event = api_gateway_event(
        http_method="POST",
        body={"title": "Lost Laptop", "date_of_loss": future_date, "household_id": str(household_id)},
    )
    response = lambda_handler(event, {}, db_session=test_db)

    assert response["statusCode"] == 400
    assert "Future dates are not allowed" in response["body"]

def test_create_claim_empty_title(test_db, api_gateway_event):
    """❌ Test creating a claim with an empty title"""
    household_id = uuid.uuid4()
    test_household = Household(id=household_id, name="Test Household")
    test_db.add(test_household)
    test_db.commit()

    event = api_gateway_event(
        http_method="POST",
        body={"title": "", "date_of_loss": "2024-01-10", "household_id": str(household_id)},
    )
    response = lambda_handler(event, {}, db_session=test_db)
    assert response["statusCode"] == 400
    assert "Title cannot be empty" in response["body"]

def test_create_claim_sql_injection(test_db, api_gateway_event):
    """❌ Test SQL injection attempt in title field"""
    household_id = uuid.uuid4()
    test_household = Household(id=household_id, name="Test Household")
    test_db.add(test_household)
    test_db.commit()

    malicious_title = "DROP TABLE claims;"
    event = api_gateway_event(
        http_method="POST",
        body={"title": malicious_title, "date_of_loss": "2024-01-10", "household_id": str(household_id)},
    )
    response = lambda_handler(event, {}, db_session=test_db)
    assert response["statusCode"] == 400  # ✅ Ensure injection attempts are blocked
    assert "Invalid characters in title" in response["body"]
