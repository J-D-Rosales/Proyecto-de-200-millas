import json
import os
import boto3
from botocore.exceptions import ClientError
from auth_helper import get_bearer_token, validate_token_via_lambda

# === ENV ===
TABLE_USUARIOS_NAME      = os.getenv("USERS_TABLE", "USERS_TABLE")
TOKENS_TABLE_USERS       = os.getenv("TOKENS_TABLE_USERS", "TOKENS_TABLE_USERS")

CORS_HEADERS = {"Access-Control-Allow-Origin": "*"}

# === AWS ===
dynamodb   = boto3.resource("dynamodb")

usuarios_table = dynamodb.Table(TABLE_USUARIOS_NAME)
tokens_table   = dynamodb.Table(TOKENS_TABLE_USERS)

# ---------------------- helpers ----------------------
def _resp(code, payload):
    return {"statusCode": code, "headers": CORS_HEADERS, "body": json.dumps(payload)}

def _parse_body(event):
    body = {}
    if isinstance(event, dict) and "body" in event:
        raw_body = event.get("body")
        if isinstance(raw_body, str):
            body = json.loads(raw_body) if raw_body else {}
        elif isinstance(raw_body, dict):
            body = raw_body
    elif isinstance(event, dict):
        body = event
    elif isinstance(event, str):
        body = json.loads(event)
    return body if isinstance(body, dict) else {}

def _get_correo_from_token(token: str):
    """Obtiene el correo del usuario desde el token en la tabla"""
    try:
        r = tokens_table.get_item(Key={"token": token})
        item = r.get("Item")
        if not item:
            return None
        return item.get("user_id")
    except Exception:
        return None

# ---------------------- handler ----------------------
def lambda_handler(event, context):
    # 1. Validar token mediante Lambda
    token = get_bearer_token(event)
    valido, err, rol_solicitante = validate_token_via_lambda(token)
    if not valido:
        return _resp(401, {"message": err or "Token inválido"})
    
    # 2. Obtener correo del usuario autenticado
    correo_solicitante = _get_correo_from_token(token)
    if not correo_solicitante:
        return _resp(401, {"message": "No se pudo obtener el usuario del token"})

    # 3) Body y correo a eliminar (requerido)
    body = _parse_body(event)
    correo_a_eliminar = body.get("correo")
    if not correo_a_eliminar:
        return _resp(400, {"message": "correo es obligatorio"})

    # 4) Buscar usuario objetivo
    try:
        resp = usuarios_table.get_item(Key={"correo": correo_a_eliminar})
    except Exception as e:
        return _resp(500, {"message": f"Error al obtener usuario: {str(e)}"})

    if "Item" not in resp:
        return _resp(404, {"message": "Usuario no encontrado"})

    usuario_objetivo = resp["Item"]
    rol_objetivo = usuario_objetivo.get("role") or usuario_objetivo.get("rol") or "Cliente"

    # 5) Autorización:
    #    - self-delete: permitido
    #    - Admin: puede eliminar a cualquiera
    #    - Gerente: puede eliminar solo a Cliente
    es_mismo_usuario = (correo_solicitante == correo_a_eliminar)
    permitido = es_mismo_usuario or (rol_solicitante == "Admin") or (rol_solicitante == "Gerente" and rol_objetivo == "Cliente")

    if not permitido:
        return _resp(403, {"message": "No tienes permiso para eliminar este usuario"})

    # 6) Eliminar con condición de existencia
    try:
        usuarios_table.delete_item(
            Key={"correo": correo_a_eliminar},
            ConditionExpression="attribute_exists(correo)"
        )
    except dynamodb.meta.client.exceptions.ConditionalCheckFailedException:
        return _resp(404, {"message": "Usuario no encontrado"})
    except ClientError as e:
        return _resp(500, {"message": f"Error al eliminar usuario: {str(e)}"})
    except Exception as e:
        return _resp(500, {"message": f"Error al eliminar usuario: {str(e)}"})

    return _resp(200, {"message": "Usuario eliminado correctamente"})
