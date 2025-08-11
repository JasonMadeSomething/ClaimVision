from utils.logging_utils import get_logger
from sqlalchemy.exc import SQLAlchemyError
from models.file_labels import FileLabel
from utils import response
from utils.lambda_utils import enhanced_lambda_handler

# Configure logging
logger = get_logger(__name__)
@enhanced_lambda_handler(
    requires_auth=True,
    path_params=['file_id', 'label_id'],
    permissions={'resource_type': 'file', 'action': 'write', 'path_param': 'file_id'},
    auto_load_resources={'file_id': 'File', 'label_id': 'Label'}
)
def lambda_handler(event, context, db_session, user, path_params, resources):
    """
    Handles restoring an AI-generated label for a file.
    
    - If the label is AI-generated and was soft deleted, it is reactivated.
    - User-created labels **cannot** be restored (must be recreated manually).
    
    Parameters:
        event (dict): API Gateway event with file ID and label ID.
        context (dict): Lambda execution context.
        db_session (Session): SQLAlchemy session (provided by decorator).
        user (User): Authenticated user object (provided by decorator).
        path_params (dict): Path parameters (provided by decorator).
        resources (dict): Auto-loaded resources (provided by decorator).

    Returns:
        dict: API response confirming restoration or error.
    """
    file = resources['file']
    label = resources['label']
    file_uuid = file.id
    label_uuid = label.id

    try:
        # 🚨 Prevent restoring user-created labels (must be recreated)
        if not label.is_ai_generated:
            return response.api_response(403, error_details='User labels cannot be restored.')

        # ✅ Check if the file-label relationship exists
        file_label = db_session.query(FileLabel).filter(
            FileLabel.file_id == file_uuid,
            FileLabel.label_id == label_uuid
        ).first()
        if not file_label:
            return response.api_response(404, error_details='Label was never associated with this file.')

        # ✅ If already active, return 200 (no change)
        if not file_label.deleted:
            return response.api_response(200, success_message='Label is already active.')

        # ✅ Restore label by setting `deleted = False`
        file_label.deleted = False
        db_session.commit()

        logger.info(f"Restored AI label {label_uuid} for file {file_uuid}")
        return response.api_response(200, success_message='Label restored successfully.')

    except SQLAlchemyError as e:
        db_session.rollback()
        logger.error(f"Database error restoring label: {str(e)}")
        return response.api_response(500, error_details='Database error.')

    except Exception as e:
        logger.exception("Unexpected error restoring label")
        return response.api_response(500, error_details='Internal Server Error')
