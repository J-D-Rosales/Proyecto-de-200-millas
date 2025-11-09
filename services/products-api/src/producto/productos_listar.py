import os, json, boto3
from boto3.dynamodb.conditions import Key

PRODUCTS_TABLE = os.environ["PRODUCTS_TABLE"]

def _resp(code, body):
    return {"statusCode": code, "body": json.dumps(body, ensure_ascii=False, default=str)}

def lambda_handler(event, context):
    body = json.loads(event.get("body") or "{}")
    tenant_id = body.get("tenant_id")
    if not tenant_id:
        return _resp(400, {"error":"Falta tenant_id en el body"})

    # paginación
    limit = body.get("limit", 10)
    try:
        limit = int(limit)
    except Exception:
        limit = 10
    if limit <= 0 or limit > 100:
        limit = 10

    last_key = body.get("next")  # dict o None

    ddb = boto3.resource("dynamodb")
    table = ddb.Table(PRODUCTS_TABLE)

    qargs = {"KeyConditionExpression": Key("tenant_id").eq(tenant_id), "Limit": limit}
    if last_key:
        qargs["ExclusiveStartKey"] = last_key

    r = table.query(**qargs)
    items = r.get("Items", [])
    next_key = r.get("LastEvaluatedKey")

    return _resp(200, {"items": items, "next": next_key})
