# ack_status.py
import json

def lambda_handler(event, context):
    # 'event' llega con el $.detail del evento original (tenant_id, order_id, status, at, mensaje)
    return {
        "statusCode": 200,
        "body": json.dumps({
            "ok": True,
            "message": "Estado recibido por Step Functions",
            "received": event
        }),
        "headers": {"Content-Type": "application/json"}
    }
