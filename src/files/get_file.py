from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
import uuid
import logging
from models import File, User
from database.database import get_db_session
from utils import response

logger = logging.getLogger()

def lambda_handler(event, _context, db_session: Session = None):
    db = db_session if db_session else get_db_session()

    try:
        user_id = event.get("requestContext", {}).get("authorizer", {}).get("claims", {}).get("sub")
        file_id = event.get("pathParameters", {}).get("id")

        # Validate UUID formats
        try:
            user_uuid = uuid.UUID(user_id)
            file_uuid = uuid.UUID(file_id)
        except ValueError:
            return response.api_response(400, error_details="Invalid UUID format")

        # Retrieve user first for ownership validation
        user = db.query(User).filter_by(id=user_uuid).first()
        if not user:
            return response.api_response(404, error_details="User not found")

        # Retrieve the file, ensuring it belongs to user's household
        file_data = db.query(File).filter(
            File.id == file_uuid,
            File.household_id == user.household_id
        ).first()

        if not file_data:
            return response.api_response(404, error_details="File not found")

        return response.api_response(
            200,
            data=file_data.to_dict()
        )

    except SQLAlchemyError as e:
        logging.error(f"Database error occurred: {e}")
        return response.api_response(500, error_details=str(e))

    except Exception as e:
        logging.exception("Unexpected error during file retrieval")
        return response.api_response(500, error_details=str(e))

    finally:
        if db_session is None:
            db.close()
