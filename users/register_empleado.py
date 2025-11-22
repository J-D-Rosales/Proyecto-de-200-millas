import os
import json
import boto3
from datetime import datetime, timezone
from botocore.exceptions import ClientError
from common import response

# === Entorno ===
EMPLOYEE_TABLE             = os.environ["EMPLOYEE_TABLE"]
USERS_TABLE                = os.environ["USERS_TABLE"]
TOKENS_TABLE_USERS         = os.environ["TOKENS_TABLE_USERS"]
TOKEN_VALIDATOR_FUNCTION   = os.environ["TOKEN_VALIDATOR_FUNCTION"]  # nombre del Lambda validador

# === AWS ===
dynamodb     = boto3.resource("dynamodb")
lambda_cli   = boto3.client("lambda")

t_employee = dynamodb.Table(EMPLOYEE_TABLE)
t_users    = dynamodb.Table(USERS_TABLE)
t_tokens   = dynamodb.Table(TOKENS_TABLE_USERS)

# === Reglas ===
ROLES_VALIDOS = {"Repartidor", "Cocinero", "Despachador"}
ROLES_PUEDEN_CREAR = {"Admin", "Gerente"}

def _as_bool(val):
    if isinstance(val, bool):
        return val
    if isinstance(val, (int, float)):
        return bool(val)
    if isinstance(val, str):
        v = val.strip().lower()
        if v in ("true", "1", "yes", "si"): return True
        if v in ("false", "0", "no"):       return False
    return None

def _get_bearer_token(event):
    headers = event.get("headers") or {}
    auth_header = headers.get("Authorization") or headers.get("authorization") or ""
    if isinstance(auth_header, str) and auth_header.lower().startswith("bearer "):
        return auth_header.split(" ", 1)[1].strip()
    # fallback opcional desde body
    try:
        body = json.loads(event.get("body") or "{}")
        if body.get("token"):
            return str(body["token"]).strip()
    except Exception:
        pass
    return None

def _parse_expiry(expires_str: str):
    try:
        return datetime.strptime(expires_str, "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
    except Exception:
        try:
            s = (expires_str or "").strip()
            if s.endswith("Z"):
                return datetime.fromisoformat(s[:-1]).replace(tzinfo=timezone.utc)
            return datetime.fromisoformat(s).replace(tzinfo=timezone.utc)
        except Exception:
            return None

def _invocar_lambda_validar_token(token: str) -> dict:
    """
    Invoca el Lambda externo que valida el token.
    Espera que devuelva un JSON con al menos: {"statusCode": 200|403, "body": "..."}.
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
        status_code = data.get("statusCode")
        if status_code != 200:
            # intenta leer mensaje de body
            body = data.get("body")
            msg = body if isinstance(body, str) else (json.dumps(body) if body else "Token inválido")
            return {"valido": False, "error": msg}
        return {"valido": True}
    except Exception as e:
        return {"valido": False, "error": f"Error llamando validador: {str(e)}"}

def _resolver_usuario_desde_token(token: str):
    """
    Una vez validado el token por el otro Lambda, resolvemos correo y rol
    consultando nuestra tabla de tokens y la tabla de usuarios.
    """
    try:
        tok = t_tokens.get_item(Key={"token": token})
        item = tok.get("Item")
        if not item:
            return None, None, "Token no encontrado tras validación"
        exp = _parse_expiry(item.get("expires"))
        if not exp or datetime.now(timezone.utc) > exp:
            return None, None, "Token expirado"
        correo = item.get("user_id")  # en login guardamos user_id = correo
        if not correo:
            return None, None, "Token sin usuario"
        dbu = t_users.get_item(Key={"correo": correo})
        u = dbu.get("Item")
        if not u:
            return None, None, "Usuario no encontrado"
        return correo, u.get("role"), None
    except Exception as e:
        return None, None, f"Error resolviendo usuario: {str(e)}"

def lambda_handler(event, context):
    try:
        # === 1) Leer token (Bearer) y validarlo con OTRO Lambda ===
        token = _get_bearer_token(event)
        if not token:
            return response(401, {"message": "Token requerido"})

        res = _invocar_lambda_validar_token(token)
        if not res.get("valido"):
            return response(401, {"message": res.get("error", "Token inválido")})

        # === 2) Resolver correo y rol a partir del token localmente ===
        correo, rol, err = _resolver_usuario_desde_token(token)
        if err:
            return response(401, {"message": err})

        if rol not in ROLES_PUEDEN_CREAR:
            return response(403, {"message": "No tienes permisos para crear empleados"})

        # === 3) Body y validaciones ===
        body = json.loads(event.get("body") or "{}")
        local_id = (body.get("local_id") or "").strip()
        dni      = (body.get("dni") or "").strip()
        nombre   = (body.get("nombre") or "").strip()
        apellido = (body.get("apellido") or "").strip()
        emp_role = (body.get("role") or "").strip()
        ocupado  = _as_bool(body.get("ocupado", False))

        faltantes = [k for k, v in {
            "local_id": local_id, "dni": dni, "nombre": nombre, "apellido": apellido, "role": emp_role
        }.items() if not v]
        if faltantes:
            return response(400, {"error": f"Faltan campos requeridos: {', '.join(faltantes)}"})

        if emp_role not in ROLES_VALIDOS:
            return response(400, {"error": f"role debe ser uno de {sorted(ROLES_VALIDOS)}"})

        if ocupado is None:
            return response(400, {"error": "ocupado debe ser booleano"})

        # === 4) Insertar empleado (PK=local_id, SK=dni) ===
        item = {
            "local_id": local_id,
            "dni": dni,
            "nombre": nombre,
            "apellido": apellido,
            "role": emp_role,
            "ocupado": ocupado,
        }

        t_employee.put_item(
            Item=item,
            ConditionExpression="attribute_not_exists(local_id) AND attribute_not_exists(dni)"
        )

        return response(200, {
            "message": "Empleado registrado",
            "local_id": local_id,
            "dni": dni,
            "created_by": correo,
            "creator_role": rol
        })

    except dynamodb.meta.client.exceptions.ConditionalCheckFailedException:
        # idempotencia "amable"
        try:
            body = json.loads(event.get("body") or "{}")
        except Exception:
            body = {}
        return response(200, {
            "message": "Empleado ya existe",
            "local_id": body.get("local_id"),
            "dni": body.get("dni")
        })
    except ClientError as e:
        return response(500, {"error": f"Error de cliente AWS: {str(e)}"})
    except Exception as e:
        return response(500, {"error": str(e)})
