import json
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger()

def lambda_handler(event, context):
    """
    Auto-confirms user sign-ups in Cognito.
    """
    logger.info(f"PreSignUp trigger invoked: {json.dumps(event)}")

    # ✅ Auto-confirm the user
    event["response"]["autoConfirmUser"] = True
    event["response"]["autoVerifyEmail"] = True  # ✅ Auto-verify email

    return event
