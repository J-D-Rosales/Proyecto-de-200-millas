import json
import os
import boto3
from botocore.exceptions import ClientError
from auth_helper import get_bearer_token, validate_token_via_lambda

# === ENV ===
TABLE_EMPLEADOS_NAME      = os.getenv("TABLE_EMPLEADOS", "TABLE_EMPLEADOS")
TABLE_USUARIOS_NAME       = os.getenv("USERS_TABLE", "USERS_TABLE")
TOKENS_TABLE_USERS        = os.getenv("TOKENS_TABLE_USERS", "TOKENS_TABLE_USERS")

CORS_HEADERS = {"Access-Control-Allow-Origin": "*"}

# === AWS ===
dynamodb   = boto3.resource("dynamodb")

empleados_table = dynamodb.Table(TABLE_EMPLEADOS_NAME)
usuarios_table  = dynamodb.Table(TABLE_USUARIOS_NAME)
tokens_table    = dynamodb.Table(TOKENS_TABLE_USERS)

# Reglas de negocio (mantengo tus validaciones)
TIPOS_AREA       = {"mantenimiento", "electricidad", "limpieza", "seguridad", "ti", "logistica", "otros"}
ESTADOS_VALIDOS  = {"activo", "inactivo"}
ROLES_PUEDEN_EDITAR = {"Admin", "Gerente"}  # <-- solo estos pueden modificar empleados

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

def _get_correo_from_token(token: str):
    """Obtiene el correo del usuario desde el token en la tabla"""
    try:
        r = tokens_table.get_item(Key={"token": token})
        item = r.get("Item")
        if not item:
            return None
        return item.get("user_id")
    except Exception:
        return None

# ---------- Handler ----------
def lambda_handler(event, context):
    # 1. Validar token mediante Lambda
    token = get_bearer_token(event)
    valido, err, rol_aut = validate_token_via_lambda(token)
    if not valido:
        return _resp(401, {"message": err or "Token inválido"})
    
    # 2. Obtener correo del usuario autenticado
    correo_aut = _get_correo_from_token(token)
    if not correo_aut:
        return _resp(401, {"message": "No se pudo obtener el usuario del token"})

    # 3) Autorización: solo Admin o Gerente pueden modificar empleados
    if rol_aut not in ROLES_PUEDEN_EDITAR:
        return _resp(403, {"message": "No tienes permiso para modificar empleados"})

    # 4) Parse body y validar empleado_id (PK de tu tabla actual)
    body = _parse_body(event)
    empleado_id = body.get("empleado_id")
    if not empleado_id:
        return _resp(400, {"message": "empleado_id es obligatorio"})

    # 5) Obtener empleado
    try:
        resp = empleados_table.get_item(Key={"empleado_id": empleado_id})
    except ClientError as e:
        return _resp(500, {"message": f"Error al obtener empleado: {str(e)}"})

    if "Item" not in resp:
        return _resp(404, {"message": "Empleado no encontrado"})

    empleado = resp["Item"]
    hubo_cambios = False

    # 6) Aplicar cambios permitidos (manteniendo tus validaciones)
    if "nombre" in body and body["nombre"]:
        empleado["nombre"] = body["nombre"]
        hubo_cambios = True

    if "tipo_area" in body:
        tipo_area = body["tipo_area"]
        if tipo_area not in TIPOS_AREA:
            return _resp(400, {"message": "tipo_area inválido"})
        empleado["tipo_area"] = tipo_area
        hubo_cambios = True

    if "estado" in body:
        estado = body["estado"]
        if estado not in ESTADOS_VALIDOS:
            return _resp(400, {"message": "estado inválido"})
        empleado["estado"] = estado
        hubo_cambios = True

    if "contacto" in body:
        contacto = body["contacto"]
        if contacto is not None and not isinstance(contacto, dict):
            return _resp(400, {"message": "contacto debe ser un objeto"})
        empleado["contacto"] = contacto or {}
        hubo_cambios = True

    if not hubo_cambios:
        return _resp(400, {"message": "No hay cambios para aplicar"})

    # 7) Persistir
    try:
        empleados_table.put_item(Item=empleado)
    except ClientError as e:
        return _resp(500, {"message": f"Error al actualizar empleado: {str(e)}"})

    return _resp(200, {
        "message": "Empleado actualizado correctamente",
        "empleado": empleado,
        "modificado_por": correo_aut,
        "rol_solicitante": rol_aut
    })
