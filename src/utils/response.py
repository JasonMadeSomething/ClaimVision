"""
Response Utility to Standardize API Responses

This module provides a consistent structure for API responses across the application.
It ensures all HTTP responses follow a predefined format, reducing inconsistencies
between different endpoints.

Features:
- Maps standard HTTP status codes to human-readable messages.
- Ensures a structured JSON format for all API responses.
- Supports error details, missing fields tracking, and data payloads.
- Converts list-based data responses into a dictionary for consistency.

Usage Example:
    ```
    from utils.response import api_response

    response = api_response(200, success_message="User login successful", data={"id": "123"})
    print(response)
    # {
    #     "statusCode": 200,
    #     "body": '{"status": "OK", "code": 200, "message": "User login successful", "data": {"id": "123"}}'
    # }
    ```

The `api_response` function should be used for all API responses to enforce a standardized format.
"""

from typing import Any, Dict, List, Optional, Union
from .models import APIResponse
import os
import json
import logging
# Predefined status code mappings
STATUS_MESSAGES: Dict[int, str] = {
    200: "OK",
    201: "Created",
    204: "No Content",
    207: "Multi-Status",
    400: "Bad Request",
    401: "Unauthorized",
    403: "Forbidden",
    404: "Not Found",
    409: "Conflict",
    429: "Too Many Requests",
    500: "Internal Server Error",
}

def api_response(
    status_code: int,
    message: Optional[str] = None,
    data: Optional[Union[Dict[str, Any], List[Any]]] = None,
    missing_fields: Optional[List[str]] = None,
    error_details: Optional[str] = None,
    success_message: Optional[str] = None,
    event: Optional[Dict[str, Any]] = None,
    origin: Optional[str] = None,
) -> Dict[str, Union[int, str, Dict[str, Any], List[Any]]]:
    """
    Generates a standardized API response for HTTP endpoints.

    Args:
        status_code (int): HTTP status code.
        message (Optional[str]): Custom response message (deprecated, use success_message or error_details).
        data (Optional[Union[Dict, List]]): Payload data (if applicable).
        missing_fields (Optional[List[str]]): Fields missing from request (if applicable).
        error_details (Optional[str]): Debugging details for errors.
        success_message (Optional[str]): Informative message for successful responses.

    Returns:
        Dict[str, Any]: Standardized API response.

    Example:
        ```
        api_response(200, success_message="User login successful", data={"id": "123"})
        # Returns:
        {
            "statusCode": 200,
            "body": '{"status": "OK", "code": 200, "message": "User login successful", "data": {"id": "123"}}'
        }
        ```
    """

    if status_code not in STATUS_MESSAGES:
        raise ValueError(f"Invalid status code: {status_code}")

    # Determine the appropriate message
    if 200 <= status_code < 300 and success_message:
        # For successful responses, use success_message if provided
        response_message = success_message
    else:
        # Otherwise use message if provided, or fall back to the standard status message
        response_message = message or STATUS_MESSAGES[status_code]

    # Ensure missing_fields are explicitly tracked
    extra_info = {}
    if missing_fields and status_code == 400:
        extra_info["missing_fields"] = missing_fields

    # Standardize data format (ensure it's always a dict)
    if isinstance(data, list):
        data = {"results": data}
    elif data is None:
        data = {}

    # Always include error_details, even if None
    response = APIResponse(
        status=STATUS_MESSAGES[status_code],
        code=status_code,
        message=response_message,
        data={**data, **extra_info} if data else extra_info,
        error_details=error_details or None,  # Ensures error_details is explicitly included
    )

    try:
        body = response.json()
    except Exception as e:
        print(f"[ERROR] Failed to serialize response: {e}")
        body = json.dumps({"error": "Internal Server Error"})

    env = os.getenv("ENV")
    # Resolve caller origin from event if provided
    req_headers: Dict[str, Any] = {}
    if event and isinstance(event, dict):
        req_headers = event.get("headers", {}) or {}
    request_origin = origin or req_headers.get("origin") or req_headers.get("Origin")

    # Build allowed origins list
    configured_frontend = os.getenv("FRONTEND_ORIGIN") or ""
    allowed: List[str] = []
    if configured_frontend:
        allowed.append(configured_frontend)
    if env != "prod":
        # Localhosts
        for port in ["3000", "3001", "3002", "8000", "8080", ""]:
            suffix = f":{port}" if port else ""
            allowed.append(f"http://localhost{suffix}")
            allowed.append(f"http://127.0.0.1{suffix}")
        # Dev domains
        allowed.append("https://*.made-something.com")
        allowed.append("https://made-something.com")

    # Default fallback if nothing matches
    fallback_origin = configured_frontend or os.getenv("FRONTEND_ORIGIN_DEV") or "http://localhost:3000"

    # Determine Access-Control-Allow-Origin value
    access_control_origin = fallback_origin
    if request_origin:
        if request_origin in allowed:
            access_control_origin = request_origin
        else:
            for pat in allowed:
                if pat.startswith("https://*.") and request_origin.startswith("https://"):
                    base = pat.replace("https://*.", "")
                    if request_origin.endswith(f".{base}"):
                        access_control_origin = request_origin
                        break

    headers = {
        "Content-Type": "application/json",
        "Access-Control-Allow-Methods": "GET,OPTIONS,POST,PUT,DELETE,PATCH",
        "Access-Control-Allow-Origin": access_control_origin,
        "Access-Control-Allow-Credentials": "true" if access_control_origin and access_control_origin != "*" else "false",
    }
    logging.info(
        "[INFO] Returning response: %s, env=%s, request_origin=%s, resolved_origin=%s",
        body,
        env,
        request_origin,
        headers.get("Access-Control-Allow-Origin"),
    )
    return {
        "statusCode": status_code,
        "headers": headers,
        "body": body,
    }
