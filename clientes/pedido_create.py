import os
import json
import re
import uuid
from datetime import datetime, timedelta
import boto3
from botocore.exceptions import ClientError
from decimal import Decimal

# ==== Variables de entorno ====
TABLE_PEDIDOS = os.environ["TABLE_PEDIDOS"]
TOKENS_TABLE = os.environ.get("TOKENS_TABLE_USERS", "TOKENS_TABLE_USERS")

# ==== Clientes AWS ====
dynamodb = boto3.resource("dynamodb")
pedidos_table = dynamodb.Table(TABLE_PEDIDOS)
tokens_table = dynamodb.Table(TOKENS_TABLE)
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

def _get_token(event):
    """Extrae el token del header Authorization"""
    headers = event.get("headers") or {}
    for key, value in headers.items():
        if key.lower() == "authorization":
            token = value.strip()
            if token.lower().startswith("bearer "):
                return token.split(" ", 1)[1].strip()
            return token
    return None

def _validate_token(token):
    """Valida el token consultando la tabla de tokens"""
    if not token:
        return False, "Token requerido", None, None
    
    try:
        response = tokens_table.get_item(Key={'token': token})
        
        if 'Item' not in response:
            return False, "Token no existe", None, None
        
        item = response['Item']
        expires_str = item.get('expires')
        
        if not expires_str:
            return False, "Token sin fecha de expiración", None, None
        
        # Parsear fecha de expiración
        try:
            if 'T' in expires_str:
                if '.' in expires_str:
                    expires_str = expires_str.split('.')[0]
                expires_dt = datetime.strptime(expires_str, '%Y-%m-%dT%H:%M:%S')
            else:
                expires_dt = datetime.strptime(expires_str, '%Y-%m-%d %H:%M:%S')
        except ValueError:
            return False, "Formato de fecha inválido", None, None
        
        # Comparar con fecha actual
        now = datetime.now()
        if now > expires_dt:
            return False, "Token expirado", None, None
        
        # Obtener datos del usuario
        correo = item.get('user_id') or item.get('correo')
        rol = item.get('rol') or item.get('role') or "Cliente"
        
        return True, None, correo, rol
        
    except Exception as e:
        return False, f"Error al validar token: {str(e)}", None, None



def _validate_payload(p):
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



def _now_iso():
    return datetime.now().isoformat()

def _publish_crear_pedido_event(item):
    """
    Publica 'CrearPedido' en el bus por defecto con:
    - pedido_id
    - local_id
    - productos: lista de {nombre, cantidad}
    """
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
            # Sin EventBusName -> usa el bus por defecto
        }])
    except Exception as e:
        # No bloquea el flujo de creación; solo loguea
        print(f"Error publicando evento CrearPedido: {e}")

def lambda_handler(event, context):
    # Preflight CORS
    if event.get("httpMethod", event.get("requestContext", {}).get("http", {}).get("method")) == "OPTIONS":
        return _resp(200, {"ok": True})

    body = _parse_body(event)
    
    # Validar token
    token = _get_token(event)
    valido, error, correo_token, rol = _validate_token(token)
    if not valido:
        return _resp(403, {"error": error or "Token inválido"})

    ok, msg = _validate_payload(body)
    if not ok:
        return _resp(400, {"error": msg})
    if body.get("usuario_correo") != correo_token:
        return _resp(403, {"error": "usuario_correo no coincide con el token"})

    # Generamos el pedido_id (UUID v4)
    pedido_id = str(uuid.uuid4())
    now_iso = _now_iso()

    # Item a persistir (sin updated_at)
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
        "created_at": now_iso
    }

    # Claves derivadas para GSIs multi-tenant (si ya adaptaste el esquema propuesto)
    item["tenant_id_local"]   = f'{item["tenant_id"]}#{item["local_id"]}'
    item["tenant_id_usuario"] = f'{item["tenant_id"]}#{item["usuario_correo"]}'
    item["tenant_id_estado"]  = f'{item["tenant_id"]}#{item["estado"]}'

    # Guardar en DynamoDB con condición de unicidad
    try:
        pedidos_table.put_item(
            Item=item,
            ConditionExpression="attribute_not_exists(tenant_id) AND attribute_not_exists(pedido_id)"
        )
    except ClientError as e:
        if e.response["Error"]["Code"] == "ConditionalCheckFailedException":
            return _resp(409, {"error": "El pedido ya existe (tenant_id, pedido_id)"})
        print(f"Error put_item: {e}")
        return _resp(500, {"error": "Error guardando el pedido"})

    # Publicar evento 'CrearPedido' (bus por defecto)
    _publish_crear_pedido_event(item)

    return _resp(201, {"message": "Pedido registrado", "pedido": item})
