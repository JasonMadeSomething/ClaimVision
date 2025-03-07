import json
import logging
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from database.database import get_db_session
from models import File, User
from utils import response

logger = logging.getLogger()

def lambda_handler(event, _context, db_session: Session = None):
    """
    Retrieves a paginated list of files for the authenticated user's household.

    Parameters:
        event (dict): API Gateway event payload containing authentication and query parameters.
        _context (dict): AWS Lambda context (unused).
        db_session (Session, optional): SQLAlchemy session, for testing purposes.

    Returns:
        dict: Standardized API response.
    """
    db = db_session if db_session else get_db_session()

    try:
        # Get authenticated user ID from JWT claims
        user_id = event.get("requestContext", {}).get("authorizer", {}).get("claims", {}).get("sub")
        if not user_id:
            return response.api_response(401, error_details="Authentication required")

        # Validate query parameters
        query_params = event.get("queryStringParameters") or {}
        try:
            limit = int(query_params.get("limit", 10))
            offset = int(query_params.get("offset", 0))
            if limit <= 0 or offset < 0:
                return response.api_response(400, error_details="Invalid pagination parameters",
                                            data={
                                                "details": "Limit must be positive and offset cannot be negative"
                                            })
        except ValueError:
            return response.api_response(400, error_details="Invalid pagination parameters",
                                        data={
                                            "details": "Limit and offset must be valid integers"
                                        })

        # Fetch user to get household_id
        user = db.query(User).filter_by(id=user_id).first()
        if not user:
            return response.api_response(404, error_details="User not found")

        # Query files based on user's household_id with pagination
        files_query = db.query(File).filter_by(
            household_id=user.household_id
        ).order_by(File.file_name).limit(limit).offset(offset)
        files = files_query.all()

        # Prepare response data
        files_data = [file.to_dict() for file in files]

        return response.api_response(
            200,
            success_message="Files retrieved successfully",
            data={
                "files": files_data,
                "pagination": {
                    "limit": limit,
                    "offset": offset,
                    "count": len(files_data)
                }
            }
        )

    except SQLAlchemyError as e:
        logger.error("Database error occurred: %s", str(e))
        return response.api_response(500, error_details="Database connection failed")

    except Exception as e:
        logger.exception("Unexpected error retrieving files")
        return response.api_response(500, error_details="Internal server error")

    finally:
        if db_session is None:
            db.close()
