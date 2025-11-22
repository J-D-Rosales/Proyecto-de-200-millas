import os
import json
import boto3
from decimal import Decimal
from botocore.exceptions import ClientError

PRODUCTS_TABLE = os.environ.get("PRODUCTS_TABLE", "")

CORS_HEADERS = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Headers": "Content-Type,Authorization",
    "Access-Control-Allow-Methods": "OPTIONS,POST"
}

def _resp(code, body):
    return {
        "statusCode": code,
        "headers": {"Content-Type": "application/json", **CORS_HEADERS},
        "body": json.dumps(body, ensure_ascii=False, default=str)
    }

def _parse_body(event):
    body = event.get("body")
    if isinstance(body, str):
        return json.loads(body) if body.strip() else {}
    return body if isinstance(body, dict) else {}

def _convert_decimal(obj):
    if isinstance(obj, Decimal):
        return float(obj)
    if isinstance(obj, dict):
        return {k: _convert_decimal(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_convert_decimal(i) for i in obj]
    return obj

def lambda_handler(event, context):
    # Preflight CORS
    method = event.get("httpMethod") or event.get("requestContext", {}).get("http", {}).get("method")
    if method == "OPTIONS":
        return _resp(204, {})

    # Solo POST
    if method != "POST":
        return _resp(405, {"error": "Método no permitido. Usa POST."})

    if not PRODUCTS_TABLE:
        return _resp(500, {"error": "PRODUCTS_TABLE no configurado"})

    ddb = boto3.resource("dynamodb")
    table = ddb.Table(PRODUCTS_TABLE)

    # Leer únicamente del body
    body = _parse_body(event)

    # Claves legado
    tenant_id = body.get("tenant_id")
    product_id = body.get("product_id")
    # Claves actuales
    local_id = body.get("local_id")
    nombre   = body.get("nombre")

    if tenant_id and product_id:
        key = {"tenant_id": tenant_id, "product_id": product_id}
    elif local_id and nombre:
        key = {"local_id": local_id, "nombre": nombre}
    else:
        return _resp(400, {
            "error": "Faltan claves. Usa (tenant_id, product_id) o (local_id, nombre) en el body."
        })

    try:
        r = table.get_item(Key=key)
    except ClientError as e:
        return _resp(500, {"error": f"Error al obtener producto: {e}"})

    item = r.get("Item")
    if not item:
        return _resp(404, {"error": "Producto no encontrado"})

    item = _convert_decimal(item)
    return _resp(200, {"item": item})
