import json

def lambda_handler(event, context):
    """
    Placeholder function for GetItems API.
    Returns a hardcoded list of items for now.
    """
    items = [
        {"id": "item-1", "name": "Laptop", "description": "Dell XPS 15"},
        {"id": "item-2", "name": "Smartphone", "description": "iPhone 13"},
    ]

    return {
        "statusCode": 200,
        "body": json.dumps({"items": items}),
        "headers": {
            "Content-Type": "application/json"
        }
    }
