import json

# ✅ Mock files stored in DynamoDB
test_files = [
    {"id": "file-1", "user_id": "user-123", "file_name": "test.jpg"},
    {"id": "file-2", "user_id": "user-123", "file_name": "another.jpg"},
]

# ✅ Expected response for GET /files
expected_files_response = {
    "statusCode": 200,
    "body": {
        "status": "OK",
        "code": 200,
        "message": "Files retrieved successfully",
        "data": {
            "files": test_files,
            "last_key": None
        }
    }
}

# ✅ Mock update metadata payload
test_update_payload = {
    "description": "Updated description",
    "labels": ["new-label"],
    "status": "review"
}

# ✅ Mock file replacement payload (New Base64-encoded image)
test_replace_payload = {
    "file_name": "test.jpg",
    "file_data": "iVBORw0KGgoAAAANSUhEUgAAAAUA",
    "s3_key": "uploads/user-123/test.jpg"
}

# ✅ Expected response when updating a file
expected_update_response = {
    "statusCode": 200,
    "body": {
        "status": "OK",
        "code": 200,
        "message": "File metadata updated successfully",
        "data": {
            "description": "Updated description",
            "labels": ["new-label"],
            "status": "review"
        }
    }
}

# ✅ Expected response when replacing a file
expected_replace_response = {
    "statusCode": 200,
    "body": {
        "status": "OK",
        "code": 200,
        "message": "File replaced successfully",
    }
}

# ✅ Expected response for failed operations (e.g., unauthorized, missing file)
expected_not_found_response = {
    "statusCode": 404,
    "body": {
        "status": "Not Found",
        "code": 404,
        "message": "File not found"
    }
}

# ✅ Mock Basic Upload Payload
test_upload_payload = {
    "files": [
        {"file_name": "test.jpg", "file_data": "iVBORw0KGgoAAAANSUhEUgAAABAAAA=="},
        {"file_name": "another.png", "file_data": "iVBORw0KGgoAAAANSUhEUgAAABAAAA=="}
    ]
}

# ✅ Mock Large File Upload Payload
test_large_file_payload = {
    "files": [
        {"file_name": "large_image.jpg", "file_data": "A" * (5 * 1024 * 1024)}  # 5MB file
    ]
}

# ❌ Mock Missing Fields Payload
test_missing_fields_payload = {
    "files": [
        {"file_data": "iVBORw0KGgoAAAANSUhEUgAAABAAAA=="}  # Missing file_name
    ]
}

# ❌ Mock Invalid File Type Payload
test_invalid_file_payload = {
    "files": [
        {"file_name": "test.exe", "file_data": "iVBORw0KGgoAAAANSUhEUgAAABAAAA=="}
    ]
}

duplicate_payload = {
        "files": [
            {"file_name": "test.jpg", "file_data": "iVBORw0KGgoAAAANSUhEUgAAABAAAA=="},
            {"file_name": "test.jpg", "file_data": "iVBORw0KGgoAAAANSUhEUgAAABAAAA=="}  # Duplicate
        ]
    }
