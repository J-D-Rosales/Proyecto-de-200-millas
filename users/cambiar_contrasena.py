import os
import json
import boto3
from botocore.exceptions import ClientError
from datetime import datetime
from common import hash_password

# ===== ENV =====
TABLE_USUARIOS = os.getenv("USERS_TABLE", "USERS_TABLE")
TOKENS_TABLE = os.environ.get("TOKENS_TABLE_USERS", "TOKENS_TABLE_USERS")

CORS_HEADERS = {"Access-Control-Allow-Origin": "*"}

# ===== AWS =====
dynamodb = boto3.resource("dynamodb")

t_usuarios = dynamodb.Table(TABLE_USUARIOS)
tokens_table = dynamodb.Table(TOKENS_TABLE)

# --------- helpers ----------
def _resp(code, payload):
    return {"statusCode": code, "headers": CORS_HEADERS, "body": json.dumps(payload)}

def _parse_body(event):
    body = event.get("body", {})
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

# --------- handler ----------
def lambda_handler(event, context):
    # Validar token
    token = _get_token(event)
    valido, err, correo_aut, rol_aut = _validate_token(token)
    if not valido:
        return _resp(401, {"message": err or "Token inválido"})

    # 2) Body y validaciones básicas
    body = _parse_body(event)

    correo_objetivo = body.get("correo") or correo_aut
    if not correo_objetivo:
        return _resp(400, {"message": "correo es obligatorio"})

    nueva_contrasena = body.get("nueva_contrasena")
    if not nueva_contrasena or len(nueva_contrasena) < 6:
        return _resp(400, {"message": "La nueva contraseña debe tener al menos 6 caracteres"})

    # Permisos:
    # - Self puede cambiar su propia contraseña (requiere contrasena_actual).
    # - Admin / Gerente pueden cambiar la de cualquiera (no requieren contrasena_actual).
    is_self = (correo_objetivo == correo_aut)
    is_admin_or_gerente = rol_aut in ("Admin", "Gerente")

    if not (is_self or is_admin_or_gerente):
        return _resp(403, {"message": "No tienes permiso para cambiar la contraseña de este usuario"})

    requiere_actual = is_self
    contrasena_actual = body.get("contrasena_actual") if requiere_actual else None
    if requiere_actual and not contrasena_actual:
        return _resp(400, {"message": "Debes proporcionar la contraseña actual"})

    # 3) Obtener usuario objetivo
    try:
        resp = t_usuarios.get_item(Key={"correo": correo_objetivo})
    except Exception as e:
        return _resp(500, {"message": f"Error al obtener usuario: {str(e)}"})

    if "Item" not in resp:
        return _resp(404, {"message": "Usuario no encontrado"})

    usuario_obj = resp["Item"]
    almacenada = usuario_obj.get("contrasena")

    # 4) Verificación de contraseña actual (solo para self)
    if requiere_actual:
        hash_actual = hash_password(contrasena_actual)
        # Soporta transición: si en DB está en claro (legacy) o ya hasheada.
        ok_actual = (almacenada == hash_actual) or (almacenada == contrasena_actual)
        if not ok_actual:
            return _resp(400, {"message": "La contraseña actual no coincide"})

    # 5) Guardar nueva contraseña hasheada
    nuevo_hash = hash_password(nueva_contrasena)

    try:
        t_usuarios.update_item(
            Key={"correo": correo_objetivo},
            UpdateExpression="SET contrasena = :h",
            ExpressionAttributeValues={":h": nuevo_hash},
            ConditionExpression="attribute_exists(correo)"
        )
    except ClientError as e:
        # Si la condición falla o hay otro error de DDB
        return _resp(500, {"message": f"Error al actualizar contraseña: {str(e)}"})
    except Exception as e:
        return _resp(500, {"message": f"Error al actualizar contraseña: {str(e)}"})

    return _resp(200, {"message": "Contraseña actualizada correctamente"})
