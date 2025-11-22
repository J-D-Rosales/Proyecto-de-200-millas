import json
import os
import boto3
from botocore.exceptions import ClientError

# === ENV ===
TABLE_USUARIOS_NAME      = os.getenv("TABLE_USUARIOS", "TABLE_USUARIOS")
TOKENS_TABLE_USERS       = os.getenv("TOKENS_TABLE_USERS", "TOKENS_TABLE_USERS")
TOKEN_VALIDATOR_FUNCTION = os.getenv("TOKEN_VALIDATOR_FUNCTION", "TOKEN_VALIDATOR_FUNCTION")

CORS_HEADERS = {"Access-Control-Allow-Origin": "*"}

# === AWS ===
dynamodb   = boto3.resource("dynamodb")
lambda_cli = boto3.client("lambda")

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
    """
    Invoca el Lambda externo de validación de token.
    Debe retornar {"statusCode": 200|403, "body": "..."}.
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
            body = data.get("body")
            msg = body if isinstance(body, str) else (json.dumps(body) if body else "Token inválido")
            return {"valido": False, "error": msg}
        return {"valido": True}
    except Exception as e:
        return {"valido": False, "error": f"Error llamando validador: {str(e)}"}

def _resolver_usuario_desde_token(token: str):
    """
    Con token válido, resolvemos correo/rol:
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

# ---------------------- handler ----------------------
def lambda_handler(event, context):
    # 1) Autenticación por Bearer y validación por Lambda externo
    token = _get_bearer_token(event)
    if not token:
        return _resp(401, {"message": "Token requerido"})

    valid = _invocar_lambda_validar_token(token)
    if not valid.get("valido"):
        return _resp(401, {"message": valid.get("error", "Token inválido")})

    # 2) Resolver usuario autenticado (correo y rol)
    correo_solicitante, rol_solicitante, err = _resolver_usuario_desde_token(token)
    if err:
        return _resp(401, {"message": err})
    if not rol_solicitante or not correo_solicitante:
        return _resp(401, {"message": "No se pudo resolver el usuario autenticado"})

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
