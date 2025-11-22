import os
import json
import re
import uuid
from datetime import datetime, timezone
import boto3
from botocore.exceptions import ClientError
from decimal import Decimal

TABLE_PEDIDOS = os.environ["TABLE_PEDIDOS"]
TOKENS_TABLE_USERS = os.environ["TOKENS_TABLE_USERS"]
TOKEN_VALIDATOR_FUNCTION = os.environ["TOKEN_VALIDATOR_FUNCTION"]

dynamodb = boto3.resource("dynamodb")
pedidos_table = dynamodb.Table(TABLE_PEDIDOS)
tokens_table = dynamodb.Table(TOKENS_TABLE_USERS)
lambda_client = boto3.client("lambda")

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
        body = json.loads(body) if body.strip() else {}
    elif not isinstance(body, dict):
        body = {}
    return body

def _get_auth_token(event):
    headers = event.get("headers") or {}
    auth = headers.get("Authorization") or headers.get("authorization") or ""
    auth = auth.strip()
    if not auth:
        return None
    if auth.lower().startswith("bearer "):
        return auth[7:].strip()
    return auth

def _validate_payload(p):
    """
    Igual que antes, pero SIN exigir 'pedido_id'.
    """
    required = ["tenant_id","local_id","usuario_correo","direccion","costo","estado"]
    missing = [k for k in required if k not in p]
    if missing:
        return False, f"Faltan campos requeridos: {', '.join(missing)}"

    if not isinstance(p["tenant_id"], str) or not p["tenant_id"].strip():
        return False, "tenant_id debe ser string no vacío"
    if not isinstance(p["local_id"], str) or not p["local_id"].strip():
        return False, "local_id debe ser string"
    if not isinstance(p["usuario_correo"], str) or "@" not in p["usuario_correo"]:
        return False, "usuario_correo debe ser un email válido"
    if not isinstance(p["direccion"], str) or not p["direccion"].strip():
        return False, "direccion debe ser string"
    if not (isinstance(p["costo"], int) or isinstance(p["costo"], float)) or p["costo"] < 0:
        return False, "costo debe ser number >= 0"

    enum_estados = {"procesando","cocinando","empacando","enviando","recibido"}
    if p["estado"] not in enum_estados:
        return False, f"estado inválido. Debe ser uno de: {', '.join(sorted(enum_estados))}"

    if "productos" not in p or p["productos"] is None:
        return False, "productos es requerido y debe ser un array con al menos un item"
    if not isinstance(p["productos"], list) or len(p["productos"]) < 1:
        return False, "productos debe ser un array con al menos un item"
    for i, it in enumerate(p["productos"]):
        if not isinstance(it, dict):
            return False, f"productos[{i}] debe ser objeto"
        if "nombre" not in it or not isinstance(it["nombre"], str) or not it["nombre"].strip():
            return False, f"productos[{i}].nombre debe ser string"
        if "cantidad" not in it or not isinstance(it["cantidad"], int) or it["cantidad"] < 1:
            return False, f"productos[{i}].cantidad debe ser entero >= 1"

    fea = p.get("fecha_entrega_aproximada")
    if fea is not None:
        iso_pattern = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+\-]\d{2}:\d{2})$")
        if not isinstance(fea, str) or not iso_pattern.match(fea):
            return False, "fecha_entrega_aproximada debe ser ISO 8601 o null"

    return True, None

def _invoke_token_validator(token):
    try:
        payload = {"token": token}
        resp = lambda_client.invoke(
            FunctionName=TOKEN_VALIDATOR_FUNCTION,
            InvocationType="RequestResponse",
            Payload=json.dumps(payload).encode("utf-8"),
        )
        raw = resp.get("Payload").read()
        out = json.loads(raw.decode("utf-8")) if raw else {}
        return int(out.get("statusCode", 500)) == 200
    except Exception as e:
        print(f"Error invocando validar_token: {e}")
        return False

def _get_token_item(token):
    try:
        r = tokens_table.get_item(Key={"token": token})
        return r.get("Item")
    except Exception as e:
        print(f"Error get_item tokens: {e}")
        return None

def _now_iso():
    return datetime.now(timezone.utc).isoformat()

def lambda_handler(event, context):
    if event.get("httpMethod", event.get("requestContext", {}).get("http", {}).get("method")) == "OPTIONS":
        return _resp(200, {"ok": True})

    body = _parse_body(event)
    token = _get_auth_token(event)
    if not token:
        return _resp(403, {"error": "Falta header Authorization"})

    if not _invoke_token_validator(token):
        return _resp(403, {"error": "Token inválido o expirado"})

    token_item = _get_token_item(token)
    if not token_item:
        return _resp(403, {"error": "Token no encontrado"})
    rol = token_item.get("rol") or token_item.get("role")
    correo_token = token_item.get("correo") or token_item.get("email") or token_item.get("usuario_correo")
    if rol != "cliente":
        return _resp(403, {"error": "Permiso denegado: se requiere rol 'cliente'"})
    if not correo_token:
        return _resp(403, {"error": "Token sin correo asociado"})

    ok, msg = _validate_payload(body)
    if not ok:
        return _resp(400, {"error": msg})

    if body.get("usuario_correo") != correo_token:
        return _resp(403, {"error": "usuario_correo no coincide con el token"})

    # >>> Generamos el pedido_id aquí (UUID v4) <<<
    pedido_id = str(uuid.uuid4())

    item = {
        "tenant_id": body["tenant_id"],
        "pedido_id": pedido_id,
        "local_id": body["local_id"],
        "usuario_correo": body["usuario_correo"],
        "productos": body["productos"],
        "costo": Decimal(str(body["costo"])),
        "direccion": body["direccion"],
        "fecha_entrega_aproximada": body.get("fecha_entrega_aproximada"),
        "estado": body["estado"],
        "created_at": _now_iso(),
        "updated_at": _now_iso(),
    }

    try:
        pedidos_table.put_item(
            Item=item,
            ConditionExpression="attribute_not_exists(tenant_id) AND attribute_not_exists(pedido_id)"
        )
    except ClientError as e:
        if e.response["Error"]["Code"] == "ConditionalCheckFailedException":
            # Muy improbable porque generamos UUID, pero por si acaso:
            return _resp(409, {"error": "El pedido ya existe (tenant_id, pedido_id)"})
        print(f"Error put_item: {e}")
        return _resp(500, {"error": "Error guardando el pedido"})

    return _resp(201, {"message": "Pedido registrado", "pedido": item})
