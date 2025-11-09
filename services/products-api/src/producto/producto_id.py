import os, json, boto3

PRODUCTS_TABLE = os.environ["PRODUCTS_TABLE"]

def _resp(code, body):
    return {"statusCode": code, "body": json.dumps(body, ensure_ascii=False)}

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
    return _resp(200, {"item": item})
