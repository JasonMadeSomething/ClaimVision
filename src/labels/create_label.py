import json
import logging
import re
import uuid

from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from database.database import get_db_session
from models import File, Label, User
from models.file_labels import FileLabel
from utils import response

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger()

# ✅ Set max labels per file & max labels per request
MAX_LABELS_PER_FILE = 50
MAX_LABELS_PER_REQUEST = 10
MAX_LABEL_LENGTH = 255
# ✅ Allowed label format: only letters, numbers, spaces, dashes, underscores
LABEL_REGEX = re.compile(r"^[A-Za-z0-9 _-]+$")


def lambda_handler(event, _context, db_session: Session = None):
    """Handles adding one or multiple user-created labels to a file."""
    db = db_session if db_session else get_db_session()

    try:
        user_id: str = event["requestContext"]["authorizer"]["claims"]["sub"]
        file_id: str = event.get("pathParameters", {}).get("file_id")
        if not file_id:
            return response.api_response(400, message="File ID is required.")

        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            return response.api_response(404, message="User not found.")

        body = json.loads(event.get("body", "{}"))

        # ✅ Detect whether it's a batch or single label request
        labels_to_add = body.get("label_text") or body.get("labels")
        if isinstance(labels_to_add, str):
            labels_to_add = [labels_to_add]
        elif isinstance(labels_to_add, list):
            labels_to_add = labels_to_add
        else:
            return response.api_response(400, message="Invalid label format. Provide 'label_text' or 'labels'.")
        
        # ✅ Ensure at least one valid label remains
        if not labels_to_add:
            return response.api_response(400, message="No valid labels provided.")

        # ✅ Validate format before anything else
        invalid_labels = [label for label in labels_to_add if not LABEL_REGEX.fullmatch(label) or len(label) > MAX_LABEL_LENGTH or '\n' in label or '\t' in label or '\r' in label or '\f' in label or '\v' in label]
        if invalid_labels:
            return response.api_response(400, error_details="Invalid label format. Only letters, numbers, spaces, dashes, and underscores are allowed.")

        # ✅ Strip whitespace before checking duplicates
        labels_to_add = [label.strip() for label in labels_to_add if isinstance(label, str) and label.strip()]


        # ✅ Enforce batch size limit
        if len(labels_to_add) > MAX_LABELS_PER_REQUEST:
            return response.api_response(400, message=f"Cannot add more than {MAX_LABELS_PER_REQUEST} labels at once.")
        print("Labels to add:", labels_to_add)
        # ✅ Ensure file exists and user owns it
        file = db.query(File).filter(File.id == file_id).first()
        if not file or file.household_id != db.query(User.household_id).filter(User.id == user_id).scalar():
            return response.api_response(404, message="File not found.")

        # ✅ Check max label count
        existing_label_count = (
            db.query(FileLabel)
            .join(Label, Label.id == FileLabel.label_id)
            .filter(FileLabel.file_id == file_id)
            .count()
        )
        print("Existing label count:", existing_label_count)
        if existing_label_count + len(labels_to_add) > MAX_LABELS_PER_FILE:
            return response.api_response(400, message="Too many labels on this file.")

        # ✅ Insert labels
        created_labels = []
        failed_labels = []

        for label_text in labels_to_add:
            # ✅ Strip whitespace before checking duplicates
            label_text = label_text.strip()

            # ✅ Validate format (reject special characters)
            if not LABEL_REGEX.match(label_text):
                failed_labels.append({"label_text": label_text, "reason": "Invalid label format."})
                continue

            # ✅ Check for duplicates before adding new labels
            existing_label = (
                db.query(Label)
                .join(FileLabel, FileLabel.label_id == Label.id)
                .filter(FileLabel.file_id == file_id, Label.label_text.ilike(label_text))
                .first()
            )
            if existing_label:
                failed_labels.append({"label_text": label_text, "reason": "Duplicate label."})
                continue
            print("Existing label:", existing_label)
            # ✅ Only add new labels
            new_label = Label(label_text=label_text, is_ai_generated=False, household_id=user.household_id)
            db.add(new_label)
            created_labels.append(new_label)
            try:
                db.commit()  # ✅ Attempt DB commit
            except (IntegrityError, SQLAlchemyError):
                db.rollback()  # ✅ Ensure rollback
                return response.api_response(500, message="Database error occurred.")
            file_label = FileLabel(file_id=file_id, label_id=new_label.id)
            db.add(file_label)
            try:
                db.commit()  # ✅ Attempt DB commit
            except (IntegrityError, SQLAlchemyError):
                db.rollback()  # ✅ Ensure rollback
                return response.api_response(500, message="Database error occurred.")

        # ✅ Construct response
        response_data = {
            "labels_created": [{"label_id": str(label.id), "label_text": label.label_text} for label in created_labels],
            "labels_failed": failed_labels
        }

        # ✅ If some labels failed, return 207 Multi-Status
        if failed_labels and created_labels:
            return response.api_response(207, message="Some labels failed to create.", data=response_data)
        elif created_labels:
            return response.api_response(201, message="Labels created successfully.", data=response_data)
        else:
            return response.api_response(409, message="All labels failed due to duplicates or errors.", data=response_data)

    except IntegrityError:
        db.rollback()
        logger.error("Database integrity error occurred.")
        return response.api_response(500, message="Database error occurred.")

    except Exception as e:
        db.rollback()
        logger.exception("Unexpected error creating labels")
        return response.api_response(500, message="Internal Server Error", error_details=str(e))

    finally:
        db.close()
