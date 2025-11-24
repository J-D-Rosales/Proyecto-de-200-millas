import os
import json
import re
from datetime import datetime
import boto3
from botocore.exceptions import ClientError
from auth_helper import get_bearer_token, validate_token_via_lambda

TABLE_PEDIDOS = os.environ["TABLE_PEDIDOS"]
TOKENS_TABLE = os.environ.get("TOKENS_TABLE_USERS", "TOKENS_TABLE_USERS")

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
    if method != "POST":
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

    body = _parse_body(event)
    local_id = (body.get("local_id") or "").strip()
    pedido_id = (body.get("pedido_id") or "").strip()
    if not local_id or not pedido_id:
        return _resp(400, {"error": "Faltan campos local_id y/o pedido_id"})

    # Verificar propiedad y actualizar estado a 'recibido'
    tenant_id = os.getenv("TENANT_ID", "millas")
    expected_tenant_usuario = f"{tenant_id}#{correo_token}"
    
    try:
        # Condición: el pedido existe y pertenece al usuario del token
        resp = pedidos_table.update_item(
            Key={"local_id": local_id, "pedido_id": pedido_id},
            UpdateExpression="SET #estado = :recibido",
            ConditionExpression="attribute_exists(local_id) AND attribute_exists(pedido_id) AND tenant_id_usuario = :tenant_usuario",
            ExpressionAttributeNames={"#estado": "estado"},
            ExpressionAttributeValues={
                ":recibido": "recibido",
                ":tenant_usuario": expected_tenant_usuario
            },
            ReturnValues="ALL_NEW"
        )
        item = resp.get("Attributes", {})
    except ClientError as e:
        code = e.response["Error"]["Code"]
        if code == "ConditionalCheckFailedException":
            # Puede ser que no exista o que no pertenezca al usuario
            # Revisemos si existe para dar mejor mensaje (opcional, simple: 403 genérico)
            try:
                r = pedidos_table.get_item(Key={"local_id": local_id, "pedido_id": pedido_id})
                if not r.get("Item"):
                    return _resp(404, {"error": "Pedido no encontrado"})
                return _resp(403, {"error": "No autorizado a confirmar este pedido"})
            except Exception:
                return _resp(403, {"error": "No autorizado a confirmar este pedido"})
        print(f"Error update_item pedidos: {e}")
        return _resp(500, {"error": "Error actualizando el pedido"})

    # Publicar evento ConfirmarPedidoCliente (bus por defecto) con id_pedido
    try:
        eventbridge.put_events(Entries=[{
            "Source": "service-clientes",
            "DetailType": "ConfirmarPedidoCliente",
            "Detail": json.dumps({"id_pedido": pedido_id}, ensure_ascii=False)
        }])
    except Exception as e:
        # No bloquea la confirmación; solo loguea
        print(f"Error publicando evento ConfirmarPedidoCliente: {e}")

    return _resp(200, {
        "message": "Recepción confirmada",
        "local_id": local_id,
        "pedido_id": pedido_id,
        "estado": item.get("estado", "recibido")
    })
