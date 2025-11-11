import os, json, boto3
from datetime import datetime, timezone

TOKENS_TABLE = os.environ["TOKENS_TABLE"]

VALIDAR_TOKEN_FN = os.environ.get("VALIDAR_TOKEN_FN")
_lambda = boto3.client("lambda")

def get_token_from_headers(event):
    headers = event.get("headers") or {}
    token = (headers.get("authorization") or headers.get("Authorization") or "").strip()
    if token.lower().startswith("bearer "):
        token = token[7:].strip()
    return token

def validate_token_and_get_claims(token: str) -> dict:
    if not token:
        return {"statusCode": 403, "body": json.dumps({"error": "Falta token"})}
    resp = _lambda.invoke(
        FunctionName=VALIDAR_TOKEN_FN,
        InvocationType="RequestResponse",
        Payload=json.dumps({"token": token})
    )
    data = json.loads(resp["Payload"].read() or "{}")
    if "body" not in data:
        data["body"] = {}
    return data

def require_admin(token: str) -> dict:
    if not token:
        return {"statusCode": 403, "body": {"error": "Falta token"}}

    ddb = boto3.resource("dynamodb")
    table = ddb.Table(TOKENS_TABLE)
    try:
        res = table.get_item(Key={"token": token})
    except Exception:
        return {"statusCode": 403, "body": {"error": "Error verificando token"}}

    item = (res or {}).get("Item")
    if not item:
        return {"statusCode": 403, "body": {"error": "Token no existe"}}

    role = (item.get("role") or "").strip().lower()
    if not role and item.get("roles") is not None:
        roles_legacy = item["roles"]
        if isinstance(roles_legacy, dict) and "SS" in roles_legacy:
            roles_legacy = list(roles_legacy["SS"])
        if isinstance(roles_legacy, list) and roles_legacy:
            role = str(roles_legacy[0]).strip().lower()
        elif isinstance(roles_legacy, str):
            role = roles_legacy.strip().lower()

    if role == "admin":
        return {"statusCode": 200, "body": {"is_admin": True, "role": "admin"}}

    return {"statusCode": 403, "body": {"error": "Role no autorizado"}}
