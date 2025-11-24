import os
import json
import boto3
from datetime import datetime, timezone
from botocore.exceptions import ClientError
from common import response
from auth_helper import get_bearer_token, validate_token_via_lambda

# === Entorno ===
EMPLOYEE_TABLE             = os.environ.get("EMPLOYEE_TABLE", "EMPLOYEE_TABLE")
USERS_TABLE                = os.environ.get("USERS_TABLE", "USERS_TABLE")
TOKENS_TABLE_USERS         = os.environ.get("TOKENS_TABLE_USERS", "TOKENS_TABLE_USERS")

# === AWS ===
dynamodb     = boto3.resource("dynamodb")

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

def _get_correo_from_token(token: str):
    """Obtiene el correo del usuario desde el token en la tabla"""
    try:
        tok = t_tokens.get_item(Key={"token": token})
        item = tok.get("Item")
        if not item:
            return None
        return item.get("user_id")
    except Exception:
        return None

def lambda_handler(event, context):
    try:
        # 1. Validar token mediante Lambda
        token = get_bearer_token(event)
        valido, err, rol = validate_token_via_lambda(token)
        if not valido:
            return response(401, {"message": err or "Token inválido"})
        
        # 2. Obtener correo del usuario autenticado
        correo = _get_correo_from_token(token)
        if not correo:
            return response(401, {"message": "No se pudo obtener el usuario del token"})

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
