import json
from datetime import datetime


def create_startup_record(name, employee_count, source_url):

    record = {
        "schemaVersion": "1.0",
        "recordType": "STARTUP",

        "source": {
            "name": name,
            "url": source_url
        },

        "content": {
            "entityName": name,
            "data": {
                "employeeCount": employee_count
            }
        },

        "collectedAt": datetime.now().astimezone().isoformat()
    }

    return record


record = create_startup_record(
    "Example Startup",
    50,
    "https://example.com"
)

print(json.dumps(record, indent=4))