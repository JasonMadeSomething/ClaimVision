import json
from typing import Any, Dict, List, Optional, Union

# ✅ Predefined status code mappings
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
    500: "Internal Server Error",
}

def api_response(
    status_code: int,
    message: Optional[str] = None,
    data: Optional[Union[Dict[str, Any], List[Any]]] = None,
    missing_fields: Optional[List[str]] = None,
    error_details: Optional[str] = None,
) -> Dict[str, Union[int, str, Dict[str, Any], List[Any]]]:
    """
    Generate a standardized API response.

    - `status_code`: (int) HTTP status code
    - `message`: (str, optional) custom message (defaults to standard message)
    - `data`: (dict, list, optional) successful response payload
    - `missing_fields`: (list, optional) auto-generates a 400 message
    - `error_details`: (str, optional) debugging details for errors
    """

    # Validate status code
    if status_code not in STATUS_MESSAGES:
        raise ValueError(f"Invalid status code: {status_code}")

    # Default message from status code mapping
    message = message or STATUS_MESSAGES[status_code]

    # Handle missing fields (auto-generate a 400 error message)
    if missing_fields and status_code == 400:
        message = f"Missing required field(s): {', '.join(missing_fields)}"

    response: Dict[str, Union[int, str, Dict[str, Any], List[Any]]] = {
        "status": STATUS_MESSAGES[status_code],
        "code": status_code,
        "message": message,
    }

    if data is not None:
        response["data"] = data  # Can be a dict or list
    if error_details:
        response["error_details"] = error_details

    return {
        "statusCode": status_code,
        "body": json.dumps(response),
    }
