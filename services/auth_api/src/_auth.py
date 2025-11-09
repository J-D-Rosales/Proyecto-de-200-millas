# src/_auth.py
import os, boto3
from datetime import datetime

TOKENS_TABLE = os.environ.get("TOKENS_TABLE", "t_tokens_acceso")
dynamodb = boto3.resource("dynamodb")
t_tokens = dynamodb.Table(TOKENS_TABLE)

def validate_token(token: str):
    if not token:
        return None
    r = t_tokens.get_item(Key={"token": token})
    item = r.get("Item")
    if not item:
        return None
    if datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S") > item["expires"]:
        return None
    return {
        "tenant_id": item["tenant_id"],
        "user_id": item["user_id"],
        "role": item.get("role", "customer")
    }
