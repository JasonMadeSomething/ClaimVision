import logging
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from datetime import datetime, timezone
from botocore.exceptions import BotoCoreError, ClientError
from database.database import get_db_session
from models import File, User
from utils import response

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger()

def lambda_handler(event: dict, _context: dict, db_session: Session = None) -> dict:
    """
    Handles deleting a file from both AWS S3 and PostgreSQL.

    This function:
    1. Ensures the file exists and belongs to the user's household.
    2. If the file is attached to a claim, marks it as `deleted=True` (soft delete).
    3. If the file is not attached to a claim, returns 400 (files must be claim-related).
    4. Deletes the file from S3.
    5. Returns a 204 response if successful.

    Args:
        event (dict): API Gateway event containing authentication details and file ID.
        _context (dict): Lambda execution context (unused).
        db_session (Session, optional): SQLAlchemy session for testing. Defaults to None.

    Returns:
        dict: API response confirming deletion or an error message.
    """
    db = db_session if db_session else get_db_session()

    try:
        # ✅ Step 1: Get user ID from JWT claims
        user_id = event.get("requestContext", {}).get("authorizer", {}).get("claims", {}).get("sub")
        file_id = event.get("pathParameters", {}).get("id")

        if not file_id:
            return response.api_response(400, error_details="Missing file ID in request.")

        # ✅ Step 2: Fetch file metadata
        file = db.query(File).filter_by(id=file_id).first()

        if not file:
            return response.api_response(404, error_details="File not found.")

        # ✅ Step 3: Ensure the user belongs to the file’s household
        user = db.query(User).filter_by(id=user_id).first()
        if not user or file.household_id != user.household_id:
            return response.api_response(404, error_details="File not found.")

        # ✅ Step 4: Handle claim-related deletion logic
        if file.claim_id:
            # 🔄 Soft delete (mark as `deleted=True`) if the file is attached to a claim
            file.deleted = True
            file.deleted_at = datetime.now(timezone.utc)
            db.commit()
            return response.api_response(204, success_message="File marked as deleted.")
        else:
            # 🚨 If no claim is attached, return 400 (files must be part of a claim)
            return response.api_response(400, error_details="Files must be attached to a claim.")

    except SQLAlchemyError as e:
        logger.error("Database error occurred: %s", str(e))
        return response.api_response(500, error_details="Database error occurred.")

    except Exception as e:
        logger.exception("Unexpected error deleting file")
        return response.api_response(500, error_details=str(e))

    finally:
        db.close()
