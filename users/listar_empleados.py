import os
import json
import math
import boto3
from botocore.exceptions import ClientError
from boto3.dynamodb.conditions import Key, Attr

TABLE_EMPLEADOS           = os.getenv("TABLE_EMPLEADOS", "TABLE_EMPLEADOS")
TABLE_USUARIOS            = os.getenv("TABLE_USUARIOS", "TABLE_USUARIOS")
TOKENS_TABLE_USERS        = os.getenv("TOKENS_TABLE_USERS", "TOKENS_TABLE_USERS")
TOKEN_VALIDATOR_FUNCTION  = os.getenv("TOKEN_VALIDATOR_FUNCTION", "TOKEN_VALIDATOR_FUNCTION")

CORS_HEADERS = {"Access-Control-Allow-Origin": "*"}

dynamodb   = boto3.resource("dynamodb")
lambda_cli = boto3.client("lambda")

t_empleados = dynamodb.Table(TABLE_EMPLEADOS)
t_usuarios  = dynamodb.Table(TABLE_USUARIOS)
t_tokens    = dynamodb.Table(TOKENS_TABLE_USERS)

ROLES_PUEDEN_LISTAR = {"Admin", "Gerente"}

def _resp(code, payload):
    return {"statusCode": code, "headers": CORS_HEADERS, "body": json.dumps(payload)}

def _safe_int(v, default=0):
    try:
        return int(v)
    except Exception:
        return default

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
    """Invoca el Lambda validador de token (externo). Espera {"statusCode":200|403,"body":"..."}"""
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
    """TOKENS_TABLE_USERS (token -> user_id/correo) -> TABLE_USUARIOS (correo -> rol)"""
    try:
        r = t_tokens.get_item(Key={"token": token})
        tok = r.get("Item")
        if not tok:
            return None, None, "Token no encontrado"
        correo = tok.get("user_id")
        if not correo:
            return None, None, "Token sin usuario"

        u_resp = t_usuarios.get_item(Key={"correo": correo})
        u = u_resp.get("Item")
        if not u:
            return None, None, "Usuario no encontrado"
        rol = u.get("rol") or u.get("role") or "Cliente"
        return correo, rol, None
    except Exception as e:
        return None, None, f"Error resolviendo usuario: {str(e)}"

# ---------- Handler (patrón page/size) ----------
def lambda_handler(event, context):
    # 0) Validación de token
    token = _get_bearer_token(event)
    if not token:
        return _resp(401, {"error": "Token requerido"})

    valid = _invocar_lambda_validar_token(token)
    if not valid.get("valido"):
        return _resp(401, {"error": valid.get("error", "Token inválido")})

    correo_aut, rol_aut, err = _resolver_usuario_desde_token(token)
    if err:
        return _resp(401, {"error": err})
    if rol_aut not in ROLES_PUEDEN_LISTAR:
        return _resp(403, {"error": "No tienes permiso para listar empleados"})

    # 1) Body & parámetros
    body = json.loads(event.get("body") or "{}")
    tenant_id = body.get("tenant_id")
    if not tenant_id:
        return _resp(400, {"error": "Falta tenant_id en el body"})

    page = _safe_int(body.get("page", 0), 0)
    size = _safe_int(body.get("size", body.get("limit", 10)), 10)
    if size <= 0 or size > 100:
        size = 10
    if page < 0:
        page = 0

    # Filtros opcionales (no son claves, van como FilterExpression)
    filtro_estado = body.get("estado")
    filtro_role   = body.get("role") or body.get("rol")     # "Repartidor"/"Cocinero"/"Despachador"
    filtro_local  = body.get("local_id")

    # 2) Contar total por tenant (Query + Select=COUNT paginado por LEK)
    total = 0
    count_args = {
        "KeyConditionExpression": Key("tenant_id").eq(tenant_id),
        "Select": "COUNT"
    }
    lek = None
    while True:
        if lek:
            count_args["ExclusiveStartKey"] = lek
        rcount = t_empleados.query(**count_args)
        total += rcount.get("Count", 0)
        lek = rcount.get("LastEvaluatedKey")
        if not lek:
            break

    total_pages = math.ceil(total / size) if size > 0 else 0
    if total_pages and page >= total_pages:
        return _resp(200, {
            "contents": [],
            "page": page,
            "size": size,
            "totalElements": total,
            "totalPages": total_pages
        })

    # 3) Query base para la página
    qargs = {
        "KeyConditionExpression": Key("tenant_id").eq(tenant_id),
        "Limit": size
    }

    # FilterExpression si se piden filtros
    fe = None
    if filtro_estado in {"activo", "inactivo"}:
        fe = Attr("estado").eq(filtro_estado)
    if filtro_role:
        fe = Attr("role").eq(filtro_role) if fe is None else (fe & Attr("role").eq(filtro_role))
    if filtro_local:
        fe = Attr("local_id").eq(filtro_local) if fe is None else (fe & Attr("local_id").eq(filtro_local))
    if fe is not None:
        qargs["FilterExpression"] = fe

    # 4) “Saltar” páginas previas avanzando con LEK
    lek = None
    for _ in range(page):
        if lek:
            qargs["ExclusiveStartKey"] = lek
        rskip = t_empleados.query(**qargs)
        lek = rskip.get("LastEvaluatedKey")
        if not lek:
            return _resp(200, {
                "contents": [],
                "page": page,
                "size": size,
                "totalElements": total,
                "totalPages": total_pages
            })

    # 5) Ejecutar la página solicitada
    if lek:
        qargs["ExclusiveStartKey"] = lek
    rpage = t_empleados.query(**qargs)
    items = rpage.get("Items", [])

    return _resp(200, {
        "contents": items,
        "page": page,
        "size": size,
        "totalElements": total,
        "totalPages": total_pages
    })
