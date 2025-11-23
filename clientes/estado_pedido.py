import os
import json
from datetime import datetime
import boto3
from botocore.exceptions import ClientError

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
        
        try:
            if 'T' in expires_str:
                if '.' in expires_str:
                    expires_str = expires_str.split('.')[0]
                expires_dt = datetime.strptime(expires_str, '%Y-%m-%dT%H:%M:%S')
            else:
                expires_dt = datetime.strptime(expires_str, '%Y-%m-%d %H:%M:%S')
        except ValueError:
            return False, "Formato de fecha inválido", None, None
        
        now = datetime.now()
        if now > expires_dt:
            return False, "Token expirado", None, None
        
        correo = item.get('user_id') or item.get('correo')
        rol = item.get('rol') or item.get('role') or "Cliente"
        
        return True, None, correo, rol
        
    except Exception as e:
        return False, f"Error al validar token: {str(e)}", None, None



def lambda_handler(event, context):
    # CORS preflight
    method = event.get("httpMethod", event.get("requestContext", {}).get("http", {}).get("method"))
    if method == "OPTIONS":
        return _resp(200, {"ok": True})

    # Solo GET
    if method != "GET":
        return _resp(405, {"error": "Método no permitido"})

    # Validar token
    token = _get_token(event)
    valido, error, correo_token, rol = _validate_token(token)
    if not valido:
        return _resp(403, {"error": error or "Token inválido"})

    # Params: tenant_id y pedido_id por querystring
    qs = event.get("queryStringParameters") or {}
    tenant_id = (qs.get("tenant_id") or "").strip()
    pedido_id = (qs.get("pedido_id") or "").strip()
    if not tenant_id or not pedido_id:
        return _resp(400, {"error": "Faltan parámetros tenant_id y/o pedido_id"})

    # Leer pedido
    try:
        r = pedidos_table.get_item(Key={"tenant_id": tenant_id, "pedido_id": pedido_id})
    except ClientError as e:
        print(f"Error get_item pedidos: {e}")
        return _resp(500, {"error": "Error consultando el pedido"})

    item = r.get("Item")
    if not item:
        return _resp(404, {"error": "Pedido no encontrado"})

    # AutZ: el pedido debe pertenecer al usuario del token
    if item.get("usuario_correo") != correo_token:
        return _resp(403, {"error": "No autorizado a consultar este pedido"})

    # Respuesta mínima (estado del pedido)
    return _resp(200, {
        "tenant_id": tenant_id,
        "pedido_id": pedido_id,
        "estado": item.get("estado"),
    })
