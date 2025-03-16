import json
from utils.logging_utils import get_logger
from utils.logging_utils import get_logger


logger = get_logger(__name__)

# Configure logging
logger = get_logger(__name__)
def lambda_handler(event, context):
    """
    Auto-confirms user sign-ups in Cognito.
    """
    logger.info(f"PreSignUp trigger invoked: {json.dumps(event)}")

    # ✅ Auto-confirm the user
    event["response"]["autoConfirmUser"] = True
    event["response"]["autoVerifyEmail"] = True  # ✅ Auto-verify email

    return event
