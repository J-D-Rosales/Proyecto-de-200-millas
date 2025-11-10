import os, json, boto3
from decimal import Decimal

PRODUCTS_TABLE = os.environ["PRODUCTS_TABLE"]

def _resp(code, body):
    return {"statusCode": code, "body": json.dumps(body, ensure_ascii=False, default=str)}

def convert_decimal(obj):
    """Convierte objetos Decimal a float de manera recursiva."""
    if isinstance(obj, Decimal):
        return float(obj)
    elif isinstance(obj, dict):
        return {k: convert_decimal(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [convert_decimal(i) for i in obj]
    return obj

def lambda_handler(event, context):
    body = json.loads(event.get("body") or "{}")
    tenant_id = body.get("tenant_id")
    product_id = body.get("product_id")

    if not tenant_id:
        return _resp(400, {"error":"Falta tenant_id en el body"})
    if not product_id:
        return _resp(400, {"error":"Falta product_id en el body"})

    ddb = boto3.resource("dynamodb")
    table = ddb.Table(PRODUCTS_TABLE)
    r = table.get_item(Key={"tenant_id": tenant_id, "product_id": product_id})
    item = r.get("Item")
    if not item:
        return _resp(404, {"error":"Producto no encontrado"})
    
    item = convert_decimal(item)
    return _resp(200, {"item": item})
