from datetime import datetime
from typing import Any, Dict

def serialize_datetime_values(data: Dict[str, Any]) -> Dict[str, Any]:
    """Convert all datetime values in a dictionary to ISO format strings."""
    serialized_data = {}
    for key, value in data.items():
        if isinstance(value, datetime):
            serialized_data[key] = value.isoformat()
        elif isinstance(value, dict):
            serialized_data[key] = serialize_datetime_values(value)
        else:
            serialized_data[key] = value
    return serialized_data