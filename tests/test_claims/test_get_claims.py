import json
from unittest.mock import patch
import pytest
from claims.get_claims import lambda_handler

@pytest.mark.skip(reason="Stub - To be implemented")
@patch("claims.get_claims.claims_table.query")
def test_get_claims_success(mock_dynamodb, api_gateway_event):
    """✅ Test retrieving claims successfully"""
    pass  # TODO: Implement

@pytest.mark.skip(reason="Stub - To be implemented")
def test_get_claims_empty(api_gateway_event):
    """✅ Test retrieving claims when the user has none"""
    pass  # TODO: Implement
