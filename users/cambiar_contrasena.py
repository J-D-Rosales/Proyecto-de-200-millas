import os
import json
import boto3
from botocore.exceptions import ClientError
from datetime import datetime, timezone
from common import hash_password  # tu hasher

# ===== ENV =====
TABLE_USUARIOS            = os.getenv("TABLE_USUARIOS", "TABLE_USUARIOS")
TOKENS_TABLE_USERS        = os.getenv("TOKENS_TABLE_USERS", "TOKENS_TABLE_USERS")
TOKEN_VALIDATOR_FUNCTION  = os.getenv("TOKEN_VALIDATOR_FUNCTION", "TOKEN_VALIDATOR_FUNCTION")

CORS_HEADERS = {"Access-Control-Allow-Origin": "*"}

# ===== AWS =====
dynamodb   = boto3.resource("dynamodb")
lambda_cli = boto3.client("lambda")

t_usuarios = dynamodb.Table(TABLE_USUARIOS)
t_tokens   = dynamodb.Table(TOKENS_TABLE_USERS)

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

def _get_bearer_token(event):
    headers = event.get("headers") or {}
    auth_header = headers.get("Authorization") or headers.get("authorization") or ""
    if isinstance(auth_header, str) and auth_header.lower().startswith("bearer "):
        return auth_header.split(" ", 1)[1].strip()
    # fallback opcional: token en body
    try:
        body = json.loads(event.get("body") or "{}")
        if body.get("token"):
            return str(body["token"]).strip()
    except Exception:
        pass
    return None

def _invocar_lambda_validar_token(token: str) -> dict:
    """Invoca el Lambda externo que valida el token. Espera {"statusCode":200|403,"body":"..."}."""
    try:
        resp = lambda_cli.invoke(
            FunctionName=TOKEN_VALIDATOR_FUNCTION,
            InvocationType="RequestResponse",
            Payload=json.dumps({"token": token}).encode("utf-8"),
        )
        payload = resp.get("Payload")
        raw = payload.read().decode("utf-8") if payload else ""
        data = json.loads(raw) if raw else {}
        if data.get("statusCode") != 200:
            body = data.get("body")
            msg = body if isinstance(body, str) else (json.dumps(body) if body else "Token inválido")
            return {"valido": False, "error": msg}
        return {"valido": True}
    except Exception as e:
        return {"valido": False, "error": f"Error llamando validador: {str(e)}"}

def _resolver_usuario_desde_token(token: str):
    """
    TOKENS_TABLE_USERS (token -> user_id/correo) -> TABLE_USUARIOS (correo -> rol).
    Devuelve (correo, rol, error).
    """
    try:
        r = t_tokens.get_item(Key={"token": token})
        tok = r.get("Item")
        if not tok:
            return None, None, "Token no encontrado"

        correo = tok.get("user_id")  # en login guardaste user_id = correo
        if not correo:
            return None, None, "Token sin usuario"

        u = t_usuarios.get_item(Key={"correo": correo}).get("Item")
        if not u:
            return None, None, "Usuario no encontrado"

        rol = u.get("rol") or u.get("role") or "Cliente"
        return correo, rol, None
    except Exception as e:
        return None, None, f"Error resolviendo usuario: {str(e)}"

# --------- handler ----------
def lambda_handler(event, context):
    # 1) Validación de token con Lambda externo
    token = _get_bearer_token(event)
    if not token:
        return _resp(401, {"message": "Token requerido"})

    v = _invocar_lambda_validar_token(token)
    if not v.get("valido"):
        return _resp(401, {"message": v.get("error", "Token inválido")})

    correo_aut, rol_aut, err = _resolver_usuario_desde_token(token)
    if err:
        return _resp(401, {"message": err})

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
