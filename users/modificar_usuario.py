import os
import json
import boto3
from botocore.exceptions import ClientError

ALLOWED_ROLES = {"Admin", "Gerente", "Cliente"}

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

# ---------- Helpers ----------
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

def _solo_campos_schema(usuario_dict: dict) -> dict:
    """
    Enforce schema Usuarios (additionalProperties: false).
    Campos permitidos: nombre, correo, contrasena, rol.
    """
    permitido = {"nombre", "correo", "contrasena", "rol"}
    return {k: v for k, v in usuario_dict.items() if k in permitido}

# ---------- Handler ----------
def lambda_handler(event, context):
    # 1) Extraer y validar token con Lambda externo
    token = _get_bearer_token(event)
    if not token:
        return _resp(401, {"message": "Token requerido"})

    valid = _invocar_lambda_validar_token(token)
    if not valid.get("valido"):
        return _resp(401, {"message": valid.get("error", "Token inválido")})

    # 2) Resolver usuario autenticado (correo y rol)
    correo_aut, rol_solicitante, err = _resolver_usuario_desde_token(token)
    if err:
        return _resp(401, {"message": err})
    if not rol_solicitante:
        return _resp(401, {"message": "No se pudo resolver el rol del usuario"})

    body = _parse_body(event)

    # target: por defecto, yo mismo
    correo_objetivo = body.get("correo") or correo_aut

    # 3) Obtener usuario objetivo
    try:
        r = usuarios_table.get_item(Key={"correo": correo_objetivo})
    except Exception as e:
        return _resp(500, {"message": f"Error al obtener usuario: {str(e)}"})

    if "Item" not in r:
        return _resp(404, {"message": "Usuario no encontrado"})

    usuario_actual = r["Item"]
    rol_objetivo = usuario_actual.get("rol") or usuario_actual.get("role") or "Cliente"

    # 4) Autorización:
    #    - self: permitido
    #    - Admin: puede modificar a cualquiera
    #    - Gerente: puede modificar solo a Clientes
    soy_mismo = (correo_aut == correo_objetivo)
    permitido = False
    if soy_mismo:
        permitido = True
    elif rol_solicitante == "Admin":
        permitido = True
    elif rol_solicitante == "Gerente" and rol_objetivo == "Cliente":
        permitido = True

    if not permitido:
        return _resp(403, {"message": "No tienes permiso para modificar este usuario"})

    # 5) Construir modificaciones permitidas (cumpliendo schema)
    usuario_mod = {
        "nombre": usuario_actual.get("nombre"),
        "correo": usuario_actual.get("correo"),
        "contrasena": usuario_actual.get("contrasena"),
        "rol": usuario_actual.get("rol") or usuario_actual.get("role") or "Cliente",
    }
    hubo_cambios = False
    campos_cambiados = []

    # nombre
    if "nombre" in body and body["nombre"] != usuario_mod.get("nombre"):
        usuario_mod["nombre"] = body["nombre"]
        hubo_cambios = True
        campos_cambiados.append("nombre")

    # contrasena (self / Admin / Gerente)
    if "contrasena" in body:
        nueva = body["contrasena"]
        if not isinstance(nueva, str) or len(nueva) < 6:
            return _resp(400, {"message": "La contraseña debe tener al menos 6 caracteres"})
        if nueva != usuario_mod.get("contrasena"):
            usuario_mod["contrasena"] = nueva
            hubo_cambios = True
            campos_cambiados.append("contrasena")

    # rol (solo Admin)
    if "rol" in body:
        nuevo_rol = body["rol"]
        if rol_solicitante != "Admin":
            return _resp(403, {"message": "No tienes permiso para cambiar el rol"})
        if nuevo_rol not in ALLOWED_ROLES:
            return _resp(400, {"message": "Rol inválido"})
        if nuevo_rol != usuario_mod.get("rol"):
            usuario_mod["rol"] = nuevo_rol
            hubo_cambios = True
            campos_cambiados.append("rol")

    # cambio de correo (PK) — permitido según regla general
    nuevo_correo = body.get("nuevo_correo")
    cambio_pk = False
    if nuevo_correo and nuevo_correo != correo_objetivo:
        if "@" not in nuevo_correo or "." not in nuevo_correo.split("@")[-1]:
            return _resp(400, {"message": "Correo electrónico inválido"})
        try:
            exists_new = usuarios_table.get_item(Key={"correo": nuevo_correo})
        except Exception as e:
            return _resp(500, {"message": f"Error al validar correo: {str(e)}"})
        if "Item" in exists_new:
            return _resp(400, {"message": "El nuevo correo ya está registrado"})

        usuario_mod["correo"] = nuevo_correo
        hubo_cambios = True
        cambio_pk = True
        campos_cambiados.append("correo")

    if not hubo_cambios:
        return _resp(400, {"message": "No hay campos para actualizar"})

    # 6) Persistencia (enforce schema)
    usuario_mod = _solo_campos_schema(usuario_mod)
    try:
        if cambio_pk:
            usuarios_table.put_item(
                Item=usuario_mod,
                ConditionExpression="attribute_not_exists(correo)"
            )
            usuarios_table.delete_item(Key={"correo": correo_objetivo})
        else:
            usuarios_table.put_item(Item=usuario_mod)
    except ClientError as e:
        if e.response.get("Error", {}).get("Code") == "ConditionalCheckFailedException":
            return _resp(400, {"message": "El nuevo correo ya está registrado"})
        return _resp(500, {"message": f"Error al actualizar usuario: {str(e)}"})
    except Exception as e:
        return _resp(500, {"message": f"Error al actualizar usuario: {str(e)}"})

    # nunca devolver password
    usuario_mod.pop("contrasena", None)

    return _resp(200, {
        "message": "Usuario actualizado correctamente",
        "usuario": usuario_mod,
        "campos_cambiados": campos_cambiados
    })
