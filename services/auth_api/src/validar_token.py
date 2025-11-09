import os, json, boto3
from datetime import datetime
from .common import response

TOKENS_TABLE = os.environ["TOKENS_TABLE"]
dynamodb = boto3.resource("dynamodb")
t_tokens = dynamodb.Table(TOKENS_TABLE)

def lambda_handler(event, context):
    try:
        body = event.get("body")
        token = None
        if isinstance(body, str):
            token = (json.loads(body).get("token") or "").strip()
        elif isinstance(event, dict) and "token" in event:
            token = (event.get("token") or "").strip()

        if not token:
            return response(400, {"error": "token requerido"})

        db = t_tokens.get_item(Key={"token": token})
        item = db.get("Item")
        if not item:
            return response(403, {"error": "Token no existe"})

        now = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
        if now > item.get("expires"):
            return response(403, {"error": "Token expirado"})

        return response(200, {
            "message": "Token válido",
            "tenant_id": item.get("tenant_id"),
            "user_id": item.get("user_id"),
            "role": item.get("role", "customer")
        })
    except Exception as e:
        return response(500, {"error": str(e)})
