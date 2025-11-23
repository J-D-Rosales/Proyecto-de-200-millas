import os
import json
import boto3
from botocore.exceptions import ClientError

# === ENV ===
TABLE_USUARIOS_NAME       = os.getenv("USERS_TABLE", "USERS_TABLE")
TOKENS_TABLE_USERS        = os.getenv("TOKENS_TABLE_USERS", "TOKENS_TABLE_USERS")

CORS_HEADERS = {"Access-Control-Allow-Origin": "*"}

# === AWS ===
dynamodb = boto3.resource("dynamodb")

usuarios_table = dynamodb.Table(TABLE_USUARIOS_NAME)
tokens_table   = dynamodb.Table(TOKENS_TABLE_USERS)

# ---------- helpers ----------
def _resp(code, payload):
    return {"statusCode": code, "headers": CORS_HEADERS, "body": json.dumps(payload)}

def _get_bearer_token(event):
    headers = event.get("headers") or {}
    auth_header = headers.get("Authorization") or headers.get("authorization") or ""
    if isinstance(auth_header, str) and auth_header.lower().startswith("bearer "):
        return auth_header.split(" ", 1)[1].strip()
    return None

def _resolver_usuario_desde_token(token: str):
    """
    Con el token válido (ya validado por el authorizer), resolvemos correo y rol:
    TOKENS_TABLE_USERS (token -> user_id) -> TABLE_USUARIOS (user_id=correo -> rol).
    """
    try:
        r = tokens_table.get_item(Key={"token": token})
        item = r.get("Item")
        if not item:
            return None, None, "Token no encontrado"
        correo = item.get("user_id")  # en login guardas user_id = correo
        if not correo:
            return None, None, "Token sin usuario"

        u = usuarios_table.get_item(Key={"correo": correo}).get("Item")
        if not u:
            return None, None, "Usuario no encontrado"
        rol = u.get("rol") or u.get("role") or "Cliente"
        return correo, rol, None
    except Exception as e:
        return None, None, f"Error resolviendo usuario: {str(e)}"

# ---------- handler ----------
def lambda_handler(event, context):
    # 1) Obtener token (ya validado por el authorizer de API Gateway)
    token = _get_bearer_token(event)
    if not token:
        return _resp(401, {"message": "Token requerido"})

    # 2) Resolver usuario autenticado (correo y rol)
    correo_aut, rol_aut, err = _resolver_usuario_desde_token(token)
    if err:
        return _resp(401, {"message": err})

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
