import os, json, boto3
from decimal import Decimal
from src.common.auth import get_token_from_headers, validate_token_and_get_claims

PRODUCTS_TABLE = os.environ["PRODUCTS_TABLE"]

def _resp(code, body):
    return {"statusCode": code, "body": json.dumps(body, ensure_ascii=False, default=str)}

def lambda_handler(event, context):
    # 1) token válido
    token = get_token_from_headers(event)
    auth = validate_token_and_get_claims(token)
    if auth.get("statusCode") == 403:
        return _resp(403, {"error": "Acceso no autorizado"})

    # 2) body (permitir números como Decimal)
    body = json.loads(event.get("body") or "{}", parse_float=Decimal)
    tenant_id = body.get("tenant_id")
    product_id = body.get("product_id")
    if not tenant_id:
        return _resp(400, {"error": "Falta tenant_id en el body"})
    if not product_id:
        return _resp(400, {"error": "Falta product_id en el body"})

    ddb = boto3.resource("dynamodb")
    table = ddb.Table(PRODUCTS_TABLE)
    try:
        table.put_item(
            Item=body,  # incluye todos los campos extra (name, price, stock, key, etc.)
            ConditionExpression="attribute_not_exists(tenant_id) AND attribute_not_exists(product_id)"
        )
    except ddb.meta.client.exceptions.ConditionalCheckFailedException:
        return _resp(409, {"error": "El producto ya existe"})

    return _resp(201, {"ok": True, "item": body})
