"""
File Metadata Retrieval Handler

This module handles retrieving metadata for a single file from PostgreSQL.
It ensures the authenticated user has access to the file before returning its metadata.

Features:
- Authenticates the user and fetches only their file.
- Uses SQLAlchemy for database interactions.
- Handles potential database errors gracefully.
- Returns standardized API responses.

Example Usage:
    ```
    GET /files/{file_id}
    ```
"""

from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from models.file import File
from database.database import get_db_session
from utils import response

def lambda_handler(event: dict, _context: dict) -> dict:
    """
    Retrieves metadata for a single file from PostgreSQL.

    This function:
    1. Extracts the authenticated user ID from the request.
    2. Retrieves the file from the PostgreSQL database using the file ID.
    3. Ensures that the requesting user owns the file.
    4. Returns the file metadata if the user has access.

    Parameters
    ----------
    event : dict
        The API Gateway event payload.
    _context : dict
        The AWS Lambda execution context (unused).

    Returns
    -------
    dict
        Standardized API response containing the file metadata.
    """
    session: Session = get_db_session()

    try:
        user_id: str = event["requestContext"]["authorizer"]["claims"]["sub"]
        file_id: str = event["pathParameters"]["id"]

        # ✅ Step 1: Retrieve file from PostgreSQL
        session = get_db_session()
        try:
            file_data = session.query(File).filter(File.id == file_id).first()
        finally:
            session.close()  # ✅ Closes session safely

        # ✅ Step 2: Ensure file exists
        if not file_data:
            return response.api_response(404, message="File Not Found")

        # ✅ Step 3: Ensure user owns the file
        if file_data.user_id != user_id:
            return response.api_response(404, message="File Not Found")

        return response.api_response(
            200,
            message="File found",
            data=file_data.to_dict()
        )

    except SQLAlchemyError as e:
        return response.api_response(
            500,
            message="Database error",
            error_details=str(e)
        )

    except Exception as e:
        return response.api_response(
            400,
            message="Bad request",
            error_details=str(e)
        )

    finally:
        session.close()
