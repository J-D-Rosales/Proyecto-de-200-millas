import os
import json
from datetime import datetime
import boto3
from botocore.exceptions import ClientError
from auth_helper import get_bearer_token, validate_token_via_lambda

TABLE_PEDIDOS = os.environ["TABLE_PEDIDOS"]
TOKENS_TABLE = os.environ.get("TOKENS_TABLE_USERS", "TOKENS_TABLE_USERS")

dynamodb = boto3.resource("dynamodb")
pedidos_table = dynamodb.Table(TABLE_PEDIDOS)
tokens_table = dynamodb.Table(TOKENS_TABLE)

CORS_HEADERS = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Headers": "Content-Type,Authorization",
    "Access-Control-Allow-Methods": "OPTIONS,GET"
}

def _resp(code, body):
    return {
        "statusCode": code,
        "headers": {"Content-Type": "application/json", **CORS_HEADERS},
        "body": json.dumps(body, ensure_ascii=False, default=str)
    }

def _get_correo_from_token(token: str):
    """Obtiene el correo del usuario desde el token en la tabla"""
    try:
        response = tokens_table.get_item(Key={'token': token})
        if 'Item' not in response:
            return None
        item = response['Item']
        return item.get('user_id') or item.get('correo')
    except Exception:
        return None

def lambda_handler(event, context):
    # CORS preflight
    method = event.get("httpMethod", event.get("requestContext", {}).get("http", {}).get("method"))
    if method == "OPTIONS":
        return _resp(200, {"ok": True})

    # Solo GET
    if method != "GET":
        return _resp(405, {"error": "Método no permitido"})

    # Validar token mediante Lambda
    token = get_bearer_token(event)
    valido, error, rol = validate_token_via_lambda(token)
    if not valido:
        return _resp(403, {"error": error or "Token inválido"})
    
    # Obtener correo del usuario autenticado
    correo_token = _get_correo_from_token(token)
    if not correo_token:
        return _resp(401, {"error": "No se pudo obtener el usuario del token"})

    # Params: local_id y pedido_id por querystring
    qs = event.get("queryStringParameters") or {}
    local_id = (qs.get("local_id") or "").strip()
    pedido_id = (qs.get("pedido_id") or "").strip()
    if not local_id or not pedido_id:
        return _resp(400, {"error": "Faltan parámetros local_id y/o pedido_id"})

    # Leer pedido
    try:
        r = pedidos_table.get_item(Key={"local_id": local_id, "pedido_id": pedido_id})
    except ClientError as e:
        print(f"Error get_item pedidos: {e}")
        return _resp(500, {"error": "Error consultando el pedido"})

    item = r.get("Item")
    if not item:
        return _resp(404, {"error": "Pedido no encontrado"})

    # AutZ: el pedido debe pertenecer al usuario del token
    # Verificar usando tenant_id_usuario
    tenant_id = os.getenv("TENANT_ID", "millas")
    expected_tenant_usuario = f"{tenant_id}#{correo_token}"
    if item.get("tenant_id_usuario") != expected_tenant_usuario:
        return _resp(403, {"error": "No autorizado a consultar este pedido"})

    # Respuesta mínima (estado del pedido)
    return _resp(200, {
        "local_id": local_id,
        "pedido_id": pedido_id,
        "estado": item.get("estado"),
    })
