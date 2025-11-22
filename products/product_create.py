import os
import json
import base64
from decimal import Decimal, InvalidOperation

import boto3
from botocore.exceptions import ClientError

# ---------- Config ----------
CORS_HEADERS = {"Access-Control-Allow-Origin": "*"}
PRODUCTS_TABLE = os.environ.get("PRODUCTS_TABLE", "PRODUCTS_TABLE")
IMAGES_BUCKET = os.environ.get("PRODUCT_IMAGES_BUCKET", "PRODUCT_IMAGES_BUCKET")
TOKEN_VALIDATOR_FUNCTION = os.environ.get("TOKEN_VALIDATOR_FUNCTION", "")

dynamodb = boto3.resource("dynamodb")
lambda_client = boto3.client("lambda")
s3 = boto3.client("s3")
region = os.environ.get("AWS_REGION") or os.environ.get("AWS_DEFAULT_REGION") or "us-east-1"

productos_table = dynamodb.Table(PRODUCTS_TABLE)

CATEGORIA_ENUM = [
    "Promos Fast","Express","Promociones","Sopas Power","Bowls Del Tigre",
    "Leche de Tigre","Ceviches","Fritazo","Mostrimar","Box Marino",
    "Duos Marinos","Trios Marinos","Dobles","Rondas Marinas","Mega Marino","Familiares"
]

# ---------- Helpers ----------
def _resp(code, payload=None):
    return {
        "statusCode": code,
        "headers": {"Content-Type": "application/json", **CORS_HEADERS},
        "body": json.dumps(payload or {}, ensure_ascii=False)
    }

def _parse_body(event):
    body = event.get("body", {})
    if isinstance(body, str):
        body = json.loads(body) if body.strip() else {}
    elif not isinstance(body, dict):
        body = {}
    return body

def _extract_bearer_token(headers: dict) -> str:
    auth_header = headers.get("Authorization") or headers.get("authorization") or ""
    return auth_header.split(" ", 1)[1].strip() if auth_header.lower().startswith("bearer ") else auth_header.strip()

def _validate_token_with_lambda(token: str) -> tuple[bool, str]:
    """Invoca la Lambda de validación: espera statusCode 200 si es válido."""
    if not TOKEN_VALIDATOR_FUNCTION:
        return False, "TOKEN_VALIDATOR_FUNCTION no configurado"
    try:
        resp = lambda_client.invoke(
            FunctionName=TOKEN_VALIDATOR_FUNCTION,
            InvocationType="RequestResponse",
            Payload=json.dumps({"token": token}).encode("utf-8"),
        )
        payload = resp.get("Payload")
        data = json.loads(payload.read().decode("utf-8")) if payload else {}
    except Exception as e:
        return False, f"Error invocando validador: {e}"
    return (data.get("statusCode") == 200, data.get("body", "Token inválido"))

def _to_decimal(n):
    if isinstance(n, Decimal):
        return n
    if isinstance(n, (int, float, str)):
        try:
            return Decimal(str(n))
        except (InvalidOperation, ValueError, TypeError):
            pass
    raise InvalidOperation("No es un número válido")

def _to_int(n):
    if isinstance(n, bool):
        raise ValueError("bool no permitido")
    try:
        return int(str(n))
    except Exception as e:
        raise ValueError("No es un entero válido") from e

def _slug(s: str) -> str:
    return "".join(ch.lower() if ch.isalnum() else "-" for ch in s).strip("-")

def _strip_data_uri(b64s: str):
    """Devuelve (base64_puro, mime_hint) si viene como data URI."""
    if "," in b64s and "base64" in b64s[:64].lower():
        header, content = b64s.split(",", 1)
        if ";base64" in header and ":" in header:
            mime = header.split(":", 1)[1].split(";")[0].strip()
            return content, mime
    return b64s, None

def _map_file_type(file_type: str) -> tuple[str, str]:
    """
    Convierte file_type a (content_type, ext).
    Acepta: png | jpg | jpeg | image/png | image/jpeg
    """
    ft = (file_type or "").strip().lower()
    if ft in ("png", "image/png"):
        return "image/png", "png"
    if ft in ("jpg", "jpeg", "image/jpg", "image/jpeg"):
        return "image/jpeg", "jpg"
    raise ValueError("file_type debe ser 'png' o 'jpg/jpeg'")

# ---------- Handler ----------
def lambda_handler(event, context):
    # Preflight
    method = event.get("httpMethod") or event.get("requestContext", {}).get("http", {}).get("method")
    if method == "OPTIONS":
        return _resp(204, {})

    if not IMAGES_BUCKET:
        return _resp(500, {"message": "PRODUCT_IMAGES_BUCKET no configurado"})
    if not PRODUCTS_TABLE:
        return _resp(500, {"message": "PRODUCTS_TABLE no configurado"})

    # 1) Validación de token via Lambda
    headers = event.get("headers") or {}
    token = _extract_bearer_token(headers)
    if not token:
        return _resp(401, {"message": "Token requerido"})
    ok, msg = _validate_token_with_lambda(token)
    if not ok:
        return _resp(403, {"message": msg})

    # 2) Body + validaciones (imagen_b64 + file_type + resto del schema)
    body = _parse_body(event)

    required = ["local_id", "nombre", "precio", "categoria", "stock", "imagen_b64", "file_type"]
    for f in required:
        if f not in body:
            return _resp(400, {"message": f"Falta el campo obligatorio: {f}"})

    nombre = body["nombre"]
    if not isinstance(nombre, str) or not nombre.strip():
        return _resp(400, {"message": "El campo 'nombre' debe ser string no vacío"})

    local_id = body["local_id"]
    if not isinstance(local_id, str) or not local_id.strip():
        return _resp(400, {"message": "El campo 'local_id' debe ser string no vacío"})

    try:
        precio = _to_decimal(body["precio"])
        if precio < 0:
            return _resp(400, {"message": "El campo 'precio' debe ser >= 0"})
    except InvalidOperation:
        return _resp(400, {"message": "El campo 'precio' debe ser numérico"})

    descripcion = body.get("descripcion")
    if descripcion is not None and not isinstance(descripcion, str):
        return _resp(400, {"message": "El campo 'descripcion' debe ser string"})

    categoria = body["categoria"]
    if categoria not in CATEGORIA_ENUM:
        return _resp(400, {"message": "Valor de 'categoria' no válido"})

    try:
        stock = _to_int(body["stock"])
    except ValueError:
        return _resp(400, {"message": "El campo 'stock' debe ser un entero"})
    if stock < 0:
        return _resp(400, {"message": "El campo 'stock' debe ser un entero >= 0"})

    imagen_b64 = body["imagen_b64"]
    if not isinstance(imagen_b64, str) or not imagen_b64.strip():
        return _resp(400, {"message": "El campo 'imagen_b64' es requerido"})

    # Tipo de archivo explícito -> content-type/ext
    try:
        content_type, ext = _map_file_type(body["file_type"])
    except ValueError as e:
        return _resp(400, {"message": str(e)})

    # 3) Decodificar base64 (admite data URI)
    b64_clean, _hint = _strip_data_uri(imagen_b64)
    try:
        image_bytes = base64.b64decode(b64_clean)
    except Exception as e:
        return _resp(400, {"message": f"imagen_b64 inválida: {e}"})

    # 4) Subir imagen a S3 con código interno <local_id>-<slug(nombre)>.<ext>
    codigo_producto = f"{local_id.strip()}-{_slug(nombre)}"
    object_key = f"{codigo_producto}.{ext}"

    try:
        s3.put_object(
            Bucket=IMAGES_BUCKET,
            Key=object_key,
            Body=image_bytes,
            ContentType=content_type,
        )
    except ClientError as e:
        code = e.response.get("Error", {}).get("Code")
        if code == "AccessDenied":
            return _resp(403, {"message": "Acceso denegado al bucket"})
        if code == "NoSuchBucket":
            return _resp(400, {"message": f"El bucket {IMAGES_BUCKET} no existe"})
        return _resp(500, {"message": f"Error S3: {e}"})
    except Exception as e:
        return _resp(500, {"message": f"Error al subir imagen: {e}"})

    # HTTPS URL (no s3://). Requiere que el objeto sea público o que generes URL firmada aparte.
    imagen_url_https = f"https://{IMAGES_BUCKET}.s3.{region}.amazonaws.com/{object_key}"

    # 5) Guardar producto en DynamoDB
    item = {
        "local_id": local_id.strip(),
        "nombre": nombre.strip(),
        "precio": precio,                # Decimal -> DDB Number
        "descripcion": descripcion or "",
        "categoria": categoria,
        "stock": stock,
        "imagen_url": imagen_url_https
    }

    try:
        productos_table.put_item(
            Item=item,
            ConditionExpression="attribute_not_exists(#pk) AND attribute_not_exists(#sk)",
            ExpressionAttributeNames={"#pk": "local_id", "#sk": "nombre"}
        )
    except ClientError as e:
        code = e.response.get("Error", {}).get("Code")
        if code == "ConditionalCheckFailedException":
            return _resp(409, {"message": "Ya existe un producto con ese local_id y nombre"})
        return _resp(500, {"message": f"Error al crear el producto: {e}"})

    return _resp(201, {
        "message": "Producto creado correctamente",
        "producto": {
            "local_id": item["local_id"],
            "nombre": item["nombre"],
            "categoria": item["categoria"],
            "precio": str(item["precio"]),
            "stock": item["stock"],
            "imagen_url": item["imagen_url"]
        }
    })
