import os, json, boto3
from decimal import Decimal
from src.common.auth import get_token_from_headers, validate_token_and_get_claims

PRODUCTS_TABLE = os.environ["PRODUCTS_TABLE"]

def _resp(code, body):
    return {"statusCode": code, "body": json.dumps(body, ensure_ascii=False, default=str)}

def lambda_handler(event, context):
    token = get_token_from_headers(event)
    auth = validate_token_and_get_claims(token)
    if auth.get("statusCode") == 403:
        return _resp(403, {"error":"Acceso no autorizado"})

    data = json.loads(event.get("body") or "{}", parse_float=Decimal)
    tenant_id = data.pop("tenant_id", None)
    product_id = data.pop("product_id", None)
    if not tenant_id:
        return _resp(400, {"error":"Falta tenant_id en el body"})
    if not product_id:
        return _resp(400, {"error":"Falta product_id en el body"})
    if not data:
        return _resp(400, {"error":"Body vacío; nada que actualizar"})

    expr_names, expr_values, sets = {}, {}, []
    for i, (k, v) in enumerate(data.items(), start=1):
        expr_names[f"#f{i}"] = k
        expr_values[f":v{i}"] = v
        sets.append(f"#f{i} = :v{i}")
    update_expr = "SET " + ", ".join(sets)

    ddb = boto3.resource("dynamodb")
    table = ddb.Table(PRODUCTS_TABLE)
    res = table.update_item(
        Key={"tenant_id": tenant_id, "product_id": product_id},
        UpdateExpression=update_expr,
        ExpressionAttributeNames=expr_names,
        ExpressionAttributeValues=expr_values,
        ConditionExpression="attribute_exists(tenant_id) AND attribute_exists(product_id)",
        ReturnValues="ALL_NEW"
    )
    return _resp(200, {"ok": True, "item": res.get("Attributes")})
