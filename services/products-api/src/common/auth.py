import os, json, boto3

VALIDAR_TOKEN_FN = os.environ.get("VALIDAR_TOKEN_FN", "millas-200-dev-ValidarTokenAcceso")
_lambda = boto3.client("lambda")

def get_token_from_headers(event):
    headers = event.get("headers") or {}
    token = (headers.get("authorization") or headers.get("Authorization") or "").strip()
    if token.lower().startswith("bearer "):
        token = token[7:].strip()
    return token

def validate_token_and_get_claims(token: str) -> dict:
    if not token:
        return {"statusCode": 403, "error": "Falta token"}
    resp = _lambda.invoke(
        FunctionName=VALIDAR_TOKEN_FN,
        InvocationType="RequestResponse",
        Payload=json.dumps({"token": token})
    )
    data = json.loads(resp["Payload"].read() or "{}")
    return data
