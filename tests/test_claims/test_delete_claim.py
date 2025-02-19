import json
from unittest.mock import patch
import pytest
from claims.modify_claims import lambda_handler

@pytest.mark.skip(reason="Stub - To be implemented")
@patch("claims.modify_claims.claims_table.delete_item")
def test_delete_claim_success(mock_dynamodb, api_gateway_event):
    """✅ Test successful claim deletion"""
    pass  # TODO: Implement

@pytest.mark.skip(reason="Stub - To be implemented")
def test_delete_claim_not_found(api_gateway_event):
    """❌ Test deleting a claim that does not exist"""
    pass  # TODO: Implement

@pytest.mark.skip(reason="Stub - To be implemented")
def test_delete_claim_unauthorized(api_gateway_event):
    """❌ Test deleting a claim belonging to another user"""
    pass  # TODO: Implement
