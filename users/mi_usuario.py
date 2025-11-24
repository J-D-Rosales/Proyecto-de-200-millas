import os
import json
import boto3
from datetime import datetime
from botocore.exceptions import ClientError
from auth_helper import get_bearer_token, validate_token_via_lambda

# === ENV ===
TABLE_USUARIOS_NAME = os.getenv("USERS_TABLE", "USERS_TABLE")
TOKENS_TABLE = os.environ.get("TOKENS_TABLE_USERS", "TOKENS_TABLE_USERS")

CORS_HEADERS = {"Access-Control-Allow-Origin": "*"}

# === AWS ===
dynamodb = boto3.resource("dynamodb")

usuarios_table = dynamodb.Table(TABLE_USUARIOS_NAME)
tokens_table = dynamodb.Table(TOKENS_TABLE)

# ---------- helpers ----------
def _resp(code, payload):
    return {"statusCode": code, "headers": CORS_HEADERS, "body": json.dumps(payload)}

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

# ---------- handler ----------
def lambda_handler(event, context):
    # 1. Validar token mediante Lambda
    token = get_bearer_token(event)
    valido, err, rol_aut = validate_token_via_lambda(token)
    if not valido:
        return _resp(401, {"message": err or "Token inválido"})
    
    # 2. Obtener correo del usuario autenticado
    correo_aut = _get_correo_from_token(token)
    if not correo_aut:
        return _resp(401, {"message": "No se pudo obtener el usuario del token"})

    # 3) Target (query param ?correo=...), por defecto yo mismo
    qp = event.get("queryStringParameters") or {}
    correo_target = qp.get("correo", correo_aut)

    # 4) Obtener usuario target
    try:
        r = usuarios_table.get_item(Key={"correo": correo_target})
    except Exception as e:
        return _resp(500, {"message": f"Error al obtener usuario: {str(e)}"})

    if "Item" not in r:
        return _resp(404, {"message": "Usuario no encontrado"})

    user_target = r["Item"]
    rol_target  = user_target.get("rol") or user_target.get("role") or "Cliente"

    # 5) Autorización:
    #    - self: siempre ok
    #    - Admin: puede ver a cualquiera
    #    - Gerente: solo puede ver a Clientes
    permitido = (correo_aut == correo_target)
    if not permitido:
        if rol_aut == "Admin":
            permitido = True
        elif rol_aut == "Gerente" and rol_target == "Cliente":
            permitido = True

    if not permitido:
        return _resp(403, {"message": "No tienes permiso para ver este usuario"})

    # 6) Sanitizar salida
    user_sanit = dict(user_target)
    user_sanit.pop("contrasena", None)
    user_sanit.pop("password", None)
    user_sanit.pop("password_hash", None)

    return _resp(200, {"message": "Usuario encontrado", "usuario": user_sanit})
