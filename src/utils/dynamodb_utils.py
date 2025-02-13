"""
DynamoDB Utility Module

Provides a reusable function for retrieving DynamoDB tables.
"""

import os
import boto3

def get_dynamodb_table(table_env_var):
    """
    Retrieves a DynamoDB table based on an environment variable.

    Args:
        table_env_var (str): The environment variable name storing the table name.

    Returns:
        boto3.Table: The requested DynamoDB table instance.
    """
    table_name = os.getenv(table_env_var)
    if not table_name:
        raise ValueError(f"Missing environment variable: {table_env_var}")

    dynamodb = boto3.resource("dynamodb")
    return dynamodb.Table(table_name)
