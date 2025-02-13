"""
Models for Standardized API Responses

This module defines the API response schema used across the application.
It ensures all API responses follow a consistent structure, making them
easier to consume by frontend applications and external integrations.

Features:
- Defines `APIResponse`, the standard response format.
- Uses Pydantic for data validation and serialization.
- Overrides `.dict()` and `.json()` to exclude `None` values for cleaner responses.

Example Usage:
    ```
    from models import APIResponse

    response = APIResponse(
        status="OK",
        code=200,
        message="Request successful",
        data={"id": "123"}
    )
    
    print(response.json())
    # {
    #     "status": "OK",
    #     "code": 200,
    #     "message": "Request successful",
    #     "data": {"id": "123"}
    # }
    ```
"""

from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel


class APIResponse(BaseModel):
    """
    Standardized API response model.

    This class ensures a consistent response format across all API endpoints.
    It includes fields for status messages, HTTP status codes, response data, 
    and optional error details.

    Attributes:
        status (str): Human-readable status message (e.g., "OK", "Bad Request").
        code (int): HTTP status code.
        message (str): A descriptive message explaining the response.
        data (Optional[Union[Dict, List]]): Response payload (if applicable).
        error_details (Optional[str]): Additional debugging information (if applicable).
    """

    status: str
    code: int
    message: str
    data: Optional[Union[Dict[str, Any], List[Any]]] = None
    error_details: Optional[str] = None

    def dict(self, **kwargs):
        """
        Convert the API response to a dictionary while ensuring `None` values are excluded.

        Returns:
            dict: Serialized API response without `None` values.
        """
        return super().model_dump(**kwargs, exclude_none=True)

    def json(self, **kwargs):
        """
        Convert the API response to a JSON string while ensuring `None` values are excluded.

        Returns:
            str: JSON-serialized API response.
        """
        return super().model_dump_json(**kwargs, exclude_none=True)
