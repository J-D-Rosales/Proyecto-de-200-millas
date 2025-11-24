import os
import json
import boto3
from decimal import Decimal
from datetime import datetime
from urllib.parse import urlparse

from botocore.exceptions import ClientError
from auth_helper import get_bearer_token, validate_token_via_lambda

PRODUCTS_TABLE = os.environ.get("PRODUCTS_TABLE")
PRODUCTS_BUCKET = os.environ.get("PRODUCTS_BUCKET", "")
TOKENS_TABLE = os.environ.get("TOKENS_TABLE_USERS", "TOKENS_TABLE_USERS")

CORS_HEADERS = {"Access-Control-Allow-Origin": "*"}

dynamodb = boto3.resource("dynamodb")
s3 = boto3.client("s3")
table = dynamodb.Table(PRODUCTS_TABLE)
tokens_table = dynamodb.Table(TOKENS_TABLE)


def _resp(code, body):
    return {
        "statusCode": code,
        "headers": {"Content-Type": "application/json", **CORS_HEADERS},
        "body": json.dumps(body, ensure_ascii=False),
    }

def _parse_body(event):
    body = event.get("body") or {}
    if isinstance(body, str):
        body = json.loads(body) if body.strip() else {}
    elif not isinstance(body, dict):
        body = {}
    return body

def _convert_decimal(obj):
    if isinstance(obj, Decimal):
        return float(obj)
    if isinstance(obj, dict):
        return {k: _convert_decimal(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_convert_decimal(i) for i in obj]
    return obj

def _parse_s3_from_url(url: str):
    """
    Soporta:
      - s3://bucket/key
      - https://bucket.s3.<region>.amazonaws.com/key
      - https://s3.<region>.amazonaws.com/bucket/key  (path-style)
    Devuelve (bucket, key) o (None, None) si no se pudo.
    """
    if not isinstance(url, str) or not url:
        return (None, None)
    u = urlparse(url)
    if u.scheme == "s3":
        return (u.netloc, u.path.lstrip("/"))
    if u.scheme in ("http", "https"):
        host = u.netloc or ""
        path = u.path or ""
        # virtual-hosted-style: bucket.s3.region.amazonaws.com/key
        if ".s3." in host and host.count(".") >= 3:
            bucket = host.split(".s3.", 1)[0]
            key = path.lstrip("/")
            return (bucket, key)
        # path-style: s3.region.amazonaws.com/bucket/key
        if host.startswith("s3.") and path.count("/") >= 2:
            parts = path.split("/", 2)  # ['', 'bucket', 'key...']
            bucket = parts[1]
            key = parts[2] if len(parts) > 2 else ""
            return (bucket, key)
    return (None, None)

def lambda_handler(event, context):
    # Validar token y rol mediante Lambda
    token = get_bearer_token(event)
    valido, error, rol = validate_token_via_lambda(token)
    if not valido:
        return _resp(403, {"message": error or "Token inválido"})
    
    # Verificar que sea Admin o Gerente
    if rol not in ("Admin", "Gerente"):
        return _resp(403, {"message": "Permiso denegado: se requiere rol Admin o Gerente"})

    # ----- Body -----
    data = _parse_body(event)

    # Acepta ambos contratos:
    # (1) actual: local_id + nombre
    local_id = data.get("local_id")
    nombre = data.get("nombre")
    # (2) legado: tenant_id + product_id
    if not (local_id and nombre):
        local_id = local_id or data.get("tenant_id")
        nombre = nombre or data.get("product_id")

    if not local_id:
        return _resp(400, {"error": "Falta local_id en el body"})
    if not nombre:
        return _resp(400, {"error": "Falta nombre en el body"})

    # ----- Buscar item -----
    try:
        res = table.get_item(Key={"local_id": local_id, "nombre": nombre})
    except ClientError as e:
        return _resp(500, {"error": f"Error al obtener producto: {e}"})

    if "Item" not in res:
        return _resp(404, {"error": "Producto no encontrado"})

    product = res["Item"]
    # soporta 'imagen_url' (schema actual) o 'image_url' (posible legado)
    image_url = product.get("imagen_url") or product.get("image_url")
    bucket, key = _parse_s3_from_url(image_url) if image_url else (None, None)

    # Si solo guardaste key y no URL completa, intenta usar env PRODUCTS_BUCKET
    if not bucket and image_url and image_url == image_url.strip() and "/" in image_url and not image_url.startswith(("http://", "https://", "s3://")):
        bucket = PRODUCTS_BUCKET or None
        key = image_url

    if bucket and key:
        try:
            s3.delete_object(Bucket=bucket, Key=key)
        except ClientError as e:
            # Log y continúa (o devuelve 500 si quieres que sea estrictamente transaccional)
            return _resp(500, {"error": f"Error al eliminar la imagen de S3: {e}"})

    # ----- Borrar item DDB con condición -----
    try:
        del_res = table.delete_item(
            Key={"local_id": local_id, "nombre": nombre},
            ConditionExpression="attribute_exists(local_id) AND attribute_exists(nombre)",
            ReturnValues="ALL_OLD"
        )
    except ClientError as e:
        code = e.response.get("Error", {}).get("Code")
        if code == "ConditionalCheckFailedException":
            return _resp(404, {"error": "Producto no encontrado"})
        return _resp(500, {"error": f"Error al eliminar producto: {e}"})

    deleted_attributes = _convert_decimal(del_res.get("Attributes") or {})
    return _resp(200, {"ok": True, "deleted": deleted_attributes})
