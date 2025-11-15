import os, json, boto3
from datetime import datetime

EVENT_SOURCE = os.environ.get("EVENT_SOURCE", "200millas.delivery")
EVENT_BUS = os.environ.get("EVENT_BUS", "default")

_events = boto3.client("events")

def emit_status(status: str, tenant_id: str, order_id: str, extra: dict | None = None):
    detail = {
        "tenant_id": tenant_id,
        "order_id": order_id,
        "status": status,
        "at": datetime.utcnow().isoformat()
    }
    if extra:
        detail.update(extra)

    _events.put_events(
        Entries=[{
            "Source": EVENT_SOURCE,
            "DetailType": status,          # lo usamos también para EventBridge Rule
            "Detail": json.dumps(detail),
            "EventBusName": EVENT_BUS
        }]
    )
    return detail

def resp(code, body):
    return {"statusCode": code,
            "headers": {"Content-Type":"application/json","Access-Control-Allow-Origin":"*"},
            "body": json.dumps(body)}
