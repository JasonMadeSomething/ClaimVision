import json

# ✅ Predefined status code mappings
STATUS_MESSAGES = {
    200: "OK",
    201: "Created",
    204: "No Content",
    400: "Bad Request",
    401: "Unauthorized",
    403: "Forbidden",
    404: "Not Found",
    409: "Conflict",
    500: "Internal Server Error"
}

def api_response(status_code: int, message=None, data=None, missing_fields=None, error_details=None):
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

    response = {
        "status": STATUS_MESSAGES[status_code],
        "code": status_code
    }

    if message:
        response["message"] = message
    if data is not None:
        response["data"] = data
    if error_details:
        response["error_details"] = error_details

    return {
        "statusCode": status_code,
        "body": json.dumps(response)
    }
