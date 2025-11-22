import os
import json
from datetime import datetime, timezone
import boto3
from botocore.exceptions import ClientError

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
    "Access-Control-Allow-Methods": "OPTIONS,GET"
}

def _resp(code, body):
    return {
        "statusCode": code,
        "headers": {"Content-Type": "application/json", **CORS_HEADERS},
        "body": json.dumps(body, ensure_ascii=False, default=str)
    }

def _get_auth_token(event):
    headers = event.get("headers") or {}
    auth = headers.get("Authorization") or headers.get("authorization") or ""
    auth = auth.strip()
    if not auth:
        return None
    if auth.lower().startswith("bearer "):
        return auth[7:].strip()
    return auth

def _invoke_token_validator(token):
    if not TOKEN_VALIDATOR_FUNCTION:
        return False
    try:
        lambda_client = boto3.client('lambda')
        payload_string = '{ "token": "' + token + '" }'
        invoke_response = lambda_client.invoke(
            FunctionName=TOKEN_VALIDATOR_FUNCTION,
            InvocationType='RequestResponse',
            Payload=payload_string
        )
        response = json.loads(invoke_response['Payload'].read())
        if response.get('statusCode') == 200:
            return True
        return False
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

def lambda_handler(event, context):
    # CORS preflight
    method = event.get("httpMethod", event.get("requestContext", {}).get("http", {}).get("method"))
    if method == "OPTIONS":
        return _resp(200, {"ok": True})

    # Solo GET
    if method != "GET":
        return _resp(405, {"error": "Método no permitido"})

    # Auth
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
