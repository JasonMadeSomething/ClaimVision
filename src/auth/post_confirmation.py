import os
import boto3
import uuid


cognito_client = boto3.client("cognito-idp")

def lambda_handler(event, _context):
    """
    Post Confirmation Lambda to assign a household_id to new users.

    Parameters
    ----------
    event : dict
        The event data from Cognito.
    _context : dict
        The Lambda execution context (unused).

    Returns
    -------
    dict
        The original event to allow Cognito to proceed.
    """
    user_pool_id = os.getenv("USER_POOL_ID")
    user_sub = event["request"]["userAttributes"]["sub"]

    # Check if household_id already exists
    existing_household_id = event["request"]["userAttributes"].get("custom:household_id")

    if not existing_household_id:
        # Generate a new Household ID
        new_household_id = str(uuid.uuid4())

        # Update the user with the generated household ID
        cognito_client.admin_update_user_attributes(
            UserPoolId=user_pool_id,
            Username=user_sub,
            UserAttributes=[{"Name": "custom:household_id", "Value": new_household_id}]
        )

    return event  # Return event to allow Cognito to proceed
