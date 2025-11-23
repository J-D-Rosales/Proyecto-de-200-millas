import os
import json
import boto3
from datetime import datetime
from botocore.exceptions import ClientError

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

# ---------- handler ----------
def lambda_handler(event, context):
    # Validar token
    token = _get_token(event)
    valido, err, correo_aut, rol_aut = _validate_token(token)
    if not valido:
        return _resp(401, {"message": err or "Token inválido"})

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
