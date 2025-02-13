def mock_dynamodb_query(
    table_name,
    records=None,
    invalid_data=False,
    empty_response=False,
    pagination=False
):
    """
    Generate mock DynamoDB query response for any table.

    :param table_name: The name of the table being queried.
    :param records: A list of dictionaries representing items in the table.
    :param invalid_data: If True, injects invalid/malformed data.
    :param empty_response: If True, return an empty item list.
    :param pagination: If True, simulate paginated results.
    :return: Mocked query response.
    """
    if empty_response:
        return {"Items": []}

    if records is None:
        records = []

    items = []

    for i, record in enumerate(records):
        item = record.copy()

        # Introduce invalid data cases
        if invalid_data:
            if i == 0 and "file_name" in item:
                item.pop("file_name")  # ❌ Remove required field
            elif i == 1:
                item["extra_field"] = "unexpected_value"  # ❌ Add extra field
            elif i == 2 and "metadata" in item:
                item["metadata"]["size"] = "not-an-integer"  # ❌ Wrong data type
            elif i == 3:
                item["metadata"] = "corrupted"  # ❌ Metadata should be a dict

        items.append(item)

    response = {"Items": items}

    # Simulate pagination
    if pagination:
        response["LastEvaluatedKey"] = {list(items[-1].keys())[0]: list(items[-1].values())[0]}

    return response
