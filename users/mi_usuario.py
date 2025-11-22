import os
import json
import boto3
from botocore.exceptions import ClientError

# === ENV ===
TABLE_USUARIOS_NAME       = os.getenv("TABLE_USUARIOS", "TABLE_USUARIOS")
TOKENS_TABLE_USERS        = os.getenv("TOKENS_TABLE_USERS", "TOKENS_TABLE_USERS")
TOKEN_VALIDATOR_FUNCTION  = os.getenv("TOKEN_VALIDATOR_FUNCTION", "TOKEN_VALIDATOR_FUNCTION")

CORS_HEADERS = {"Access-Control-Allow-Origin": "*"}

# === AWS ===
dynamodb   = boto3.resource("dynamodb")
lambda_cli = boto3.client("lambda")

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
    # fallback: token en body
    try:
        body = json.loads(event.get("body") or "{}")
        if body.get("token"):
            return str(body["token"]).strip()
    except Exception:
        pass
    return None

def _invocar_lambda_validar_token(token: str) -> dict:
    """
    Invoca el Lambda validador de token.
    Debe responder {"statusCode": 200|403, "body": "..."}.
    """
    try:
        resp = lambda_cli.invoke(
            FunctionName=TOKEN_VALIDATOR_FUNCTION,
            InvocationType="RequestResponse",
            Payload=json.dumps({"token": token}).encode("utf-8"),
        )
        payload = resp.get("Payload")
        if not payload:
            return {"valido": False, "error": "Error interno al validar token"}
        raw = payload.read().decode("utf-8")
        data = json.loads(raw) if raw else {}
        if data.get("statusCode") != 200:
            msg = data.get("body") or "Token inválido"
            return {"valido": False, "error": msg if isinstance(msg, str) else json.dumps(msg)}
        return {"valido": True}
    except Exception as e:
        return {"valido": False, "error": f"Error llamando validador: {str(e)}"}

def _resolver_usuario_desde_token(token: str):
    """
    Con el token válido, resolvemos correo y rol:
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
    # 1) Auth por Bearer
    token = _get_bearer_token(event)
    if not token:
        return _resp(401, {"message": "Token requerido"})

    valid = _invocar_lambda_validar_token(token)
    if not valid.get("valido"):
        return _resp(401, {"message": valid.get("error", "Token inválido")})

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
