"""
Retrieve Labels for a File

This module handles fetching all labels associated with a given file.
Ensures the user has access to the file's labels and filters appropriately.

Example Usage:
    GET /files/{file_id}/labels
"""

import json
import logging
import uuid
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from models import Label, File, User
from models.file_labels import FileLabel
from database.database import get_db_session
from utils import response

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger()

def lambda_handler(event: dict, _context: dict, db_session: Session = None) -> dict:
    """
    Retrieves all labels associated with a given file.

    Ensures:
    - The file exists.
    - The requesting user has access to the file's household.
    - Both AI-generated and user-created labels are returned.
    - Soft-deleted AI labels are included.

    Parameters
    ----------
    event : dict
        The API Gateway event payload.
    _context : dict
        The AWS Lambda execution context (unused).
    db_session : Session, optional
        SQLAlchemy session for testing. Defaults to None.

    Returns
    -------
    dict
        Standardized API response containing the list of labels.
    """
    try:
        db = db_session if db_session else get_db_session()
    except Exception as e:
        logger.error("Database connection failed: %s", str(e))
        return response.api_response(500, message="Database error: " + str(e))

    try:
        user_id = event.get("requestContext", {}).get("authorizer", {}).get("claims", {}).get("sub")
        if not user_id:
            return response.api_response(400, message="Invalid authentication. JWT missing or malformed.")

        try:
            user_uuid = uuid.UUID(user_id)  # Ensure user ID is a UUID
        except ValueError:
            return response.api_response(400, message="Invalid user ID format. Expected UUID.")

        file_id = event.get("pathParameters", {}).get("file_id")
        if not file_id:
            return response.api_response(400, message="Missing file ID in request.")

        try:
            file_uuid = uuid.UUID(file_id)  # Ensure file ID is a valid UUID
        except ValueError:
            return response.api_response(400, message="Invalid file ID format. Expected UUID.")

        # ✅ Step 1: Retrieve file and check household ownership
        file = db.query(File).filter(File.id == file_uuid).first()
        if not file:
            return response.api_response(404, message="File not found.")

        user = db.query(User).filter(User.id == user_uuid).first()
        if not user or user.household_id != file.household_id:
            return response.api_response(404, message="File not found.")  # ✅ Prevents leaking existence

        # ✅ Step 2: Retrieve labels (including soft-deleted AI ones)
        labels = (
            db.query(Label)
            .join(FileLabel, FileLabel.label_id == Label.id)
            .filter(FileLabel.file_id == file_uuid)
            .filter(Label.household_id == user.household_id)
            .filter(
                (Label.is_ai_generated.is_(False))  # User-created labels always appear
                | (Label.deleted.is_(False))        # AI labels must NOT be soft deleted
            )
            .all()
        )

        return response.api_response(
            200,
            message="Labels retrieved successfully.",
            data={"labels": [label.to_dict() for label in labels]}
        )

    except SQLAlchemyError as e:
        logger.error("Database error occurred: %s", str(e))
        return response.api_response(500, message="Database error occurred.", error_details=str(e))

    except Exception as e:
        logger.exception("Unexpected error retrieving labels")
        return response.api_response(500, message="Internal server error.", error_details=str(e))

    finally:
        if db_session is None:
            db.close()
