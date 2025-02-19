import json
from unittest.mock import patch
import pytest
from claims.create_claim import lambda_handler

@pytest.mark.skip(reason="Stub - To be implemented")
@patch("claims.create_claim.claims_table.put_item")
def test_create_claim_success(mock_dynamodb, api_gateway_event):
    """✅ Test successful claim creation"""
    event = api_gateway_event(
        http_method="POST",
        body={"title": "Lost Laptop", "loss_date": "2024-01-10"},
        auth_user="user-123",
    )

    response = lambda_handler(event, {})
    assert response["statusCode"] == 201

@pytest.mark.skip(reason="Stub - To be implemented")
def test_create_claim_missing_fields(api_gateway_event):
    """❌ Test creating a claim with missing required fields"""
    pass  # TODO: Implement

@pytest.mark.skip(reason="Stub - To be implemented")
def test_create_claim_invalid_date_format(api_gateway_event):
    """❌ Test creating a claim with an invalid date format"""
    pass  # TODO: Implement
