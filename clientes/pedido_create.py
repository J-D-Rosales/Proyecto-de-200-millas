import os
import json
import re
import uuid
from datetime import datetime, timezone
import boto3
from botocore.exceptions import ClientError
from decimal import Decimal
from auth_helper import get_bearer_token, validate_token_via_lambda

# ==== Variables de entorno ====
TABLE_PEDIDOS = os.environ["TABLE_PEDIDOS"]
TOKENS_TABLE_USERS = os.environ["TOKENS_TABLE_USERS"]

# ==== Clientes AWS ====
dynamodb = boto3.resource("dynamodb")
pedidos_table = dynamodb.Table(TABLE_PEDIDOS)
tokens_table = dynamodb.Table(TOKENS_TABLE_USERS)
lambda_client = boto3.client("lambda")
eventbridge = boto3.client("events")  # bus por defecto

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

def _validate_payload(p):
    required = ["local_id","direccion","costo","estado"]
    missing = [k for k in required if k not in p]
    if missing:
        return False, f"Faltan campos requeridos: {', '.join(missing)}"

    if not isinstance(p["local_id"], str) or not p["local_id"].strip():
        return False, "local_id debe ser string"
    if not isinstance(p["direccion"], str) or not p["direccion"].strip():
        return False, "dirección debe ser string"
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
        if "producto_id" not in it or not isinstance(it["producto_id"], str) or len(it["producto_id"]) < 3:
            return False, f"productos[{i}].producto_id debe ser string con mínimo 3 caracteres"
        if "cantidad" not in it or not isinstance(it["cantidad"], int) or it["cantidad"] < 1:
            return False, f"productos[{i}].cantidad debe ser entero >= 1"

    return True, None

def _get_correo_from_token(token: str):
    """Obtiene el correo del usuario desde el token en la tabla"""
    try:
        r = tokens_table.get_item(Key={"token": token})
        item = r.get("Item")
        if not item:
            return None
        return item.get("correo") or item.get("email") or item.get("usuario_correo") or item.get("user_id")
    except Exception:
        return None

def _now_iso():
    return datetime.now(timezone.utc).isoformat()

def _publish_crear_pedido_event(item):
    productos_simple = [
        {"nombre": p.get("nombre"), "cantidad": p.get("cantidad")}
        for p in item.get("productos", [])
        if isinstance(p, dict) and "nombre" in p and "cantidad" in p
    ]
    detail = {
        "pedido_id": item["pedido_id"],
        "local_id": item["local_id"],
        "productos": productos_simple
    }
    try:
        eventbridge.put_events(Entries=[{
            "Source": "service-pedidos",
            "DetailType": "CrearPedido",
            "Detail": json.dumps(detail, ensure_ascii=False)
        }])
    except Exception as e:
        print(f"Error publicando evento CrearPedido: {e}")

def lambda_handler(event, context):
    # Preflight CORS
    method = event.get("httpMethod", event.get("requestContext", {}).get("http", {}).get("method"))
    if method == "OPTIONS":
        return _resp(200, {"ok": True})

    body = _parse_body(event)

    # ======== Validar token mediante Lambda ========
    token = get_bearer_token(event)
    valido, error, rol = validate_token_via_lambda(token)
    if not valido:
        return _resp(403, {"status": "Forbidden - Acceso No Autorizado", "error": error})
    
    # Obtener correo del token
    correo_token = _get_correo_from_token(token)
    if not correo_token:
        return _resp(403, {"error": "Token sin correo asociado"})
    
    # Verificar que sea Cliente
    if rol.lower() != "cliente":
        return _resp(403, {"error": "Permiso denegado: se requiere rol 'cliente'"})

    # Validación de payload
    ok, msg = _validate_payload(body)
    if not ok:
        return _resp(400, {"error": msg})

    # Generar ID y timestamps
    pedido_id = str(uuid.uuid4())
    now_iso = _now_iso()
    tenant_id = os.getenv("TENANT_ID", "millas")

    # Construir item con nueva estructura
    item = {
        "local_id": body["local_id"],                           # PK (cambió de tenant_id)
        "pedido_id": pedido_id,                                  # SK
        "tenant_id_usuario": f"{tenant_id}#{correo_token}",     # GSI by_usuario_v2
        "productos": body["productos"],                         # Ahora usa producto_id
        "costo": Decimal(str(body["costo"])),
        "direccion": body["direccion"],
        "estado": body["estado"],
        "created_at": now_iso                                    # Nuevo campo requerido
    }

    # Persistir en DynamoDB (unicidad por PK compuesta)
    try:
        pedidos_table.put_item(
            Item=item,
            ConditionExpression="attribute_not_exists(local_id) AND attribute_not_exists(pedido_id)"
        )
    except ClientError as e:
        if e.response["Error"]["Code"] == "ConditionalCheckFailedException":
            return _resp(409, {"error": "El pedido ya existe (local_id, pedido_id)"})
        print(f"Error put_item: {e}")
        return _resp(500, {"error": "Error guardando el pedido"})

    # Publicar evento
    _publish_crear_pedido_event(item)

    return _resp(201, {"message": "Pedido registrado", "pedido": item})
