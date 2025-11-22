import os, json, boto3
from decimal import Decimal, InvalidOperation
from botocore.exceptions import ClientError

PRODUCTS_TABLE = os.environ.get("PRODUCTS_TABLE", "")
TOKEN_VALIDATOR_FUNCTION = os.environ.get("TOKEN_VALIDATOR_FUNCTION", "")

CORS_HEADERS = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Headers": "Content-Type,Authorization",
    "Access-Control-Allow-Methods": "OPTIONS,POST"
}

# Si quieres exigir SIEMPRE rol Admin/Gerente, pon True.
# Si lo dejas en False, solo se verifica rol si el validador lo envía.
REQUIRE_ROLE = False
ALLOWED_ROLES = {"Admin", "Gerente"}

def _resp(code, body):
    return {
        "statusCode": code,
        "headers": {"Content-Type": "application/json", **CORS_HEADERS},
        "body": json.dumps(body, ensure_ascii=False, default=str)
    }

def _parse_body(event):
    body = event.get("body") or "{}"
    if isinstance(body, str):
        body = body if body.strip() else "{}"
        try:
            return json.loads(body)
        except json.JSONDecodeError:
            return {}
    return body if isinstance(body, dict) else {}

def _to_decimal(obj):
    """int/float -> Decimal (recursivo)."""
    if isinstance(obj, dict):
        return {k: _to_decimal(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_to_decimal(x) for x in obj]
    if isinstance(obj, (bool, type(None), Decimal, str)):
        return obj
    if isinstance(obj, (int, float)):
        return Decimal(str(obj))
    return obj

def _extract_bearer(headers: dict) -> str:
    h = (headers or {}).get("Authorization") or (headers or {}).get("authorization") or ""
    h = h.strip()
    return h.split(" ", 1)[1].strip() if h.lower().startswith("bearer ") else h

def _invoke_token_validator(token: str):
    if not TOKEN_VALIDATOR_FUNCTION:
        return {"ok": False, "error": "TOKEN_VALIDATOR_FUNCTION no configurado"}
    try:
        lambda_client = boto3.client("lambda")
        payload_string = json.dumps({"token": token})
        invoke_response = lambda_client.invoke(
            FunctionName=TOKEN_VALIDATOR_FUNCTION,
            InvocationType="RequestResponse",
            Payload=payload_string.encode("utf-8")
        )
        data = json.loads(invoke_response["Payload"].read().decode("utf-8"))
        return {"ok": data.get("statusCode") == 200, "data": data}
    except Exception as e:
        return {"ok": False, "error": f"Error invocando validador: {e}"}

def _extract_role(validator_data: dict):
    """
    Intenta leer rol/role del body del validador.
    Soporta body string o JSON.
    """
    if not validator_data:
        return None
    body = validator_data.get("body")
    if isinstance(body, dict):
        return body.get("rol") or body.get("role")
    if isinstance(body, str):
        try:
            j = json.loads(body)
            if isinstance(j, dict):
                return j.get("rol") or j.get("role")
        except Exception:
            return None
    return None

def lambda_handler(event, context):
    # CORS preflight
    method = event.get("httpMethod") or event.get("requestContext", {}).get("http", {}).get("method")
    if method == "OPTIONS":
        return _resp(204, {})

    if not PRODUCTS_TABLE:
        return _resp(500, {"error": "PRODUCTS_TABLE no configurado"})

    # --- Auth ---
    token = _extract_bearer(event.get("headers") or {})
    if not token:
        return _resp(401, {"error": "Token requerido"})

    v = _invoke_token_validator(token)
    if not v.get("ok"):
        # Si tu validador devuelve 403 u otro, reflejamos
        return _resp(403, {"error": v.get("error") or v.get("data", {}).get("body") or "Acceso no autorizado"})

    role = _extract_role(v.get("data", {}))
    if REQUIRE_ROLE or role is not None:
        if role not in ALLOWED_ROLES:
            return _resp(403, {"error": "Se requiere rol Admin o Gerente"})

    # --- Body ---
    raw = _parse_body(event)
    data = _to_decimal(raw)

    # Claves admitidas:
    #   esquema legado: tenant_id + product_id
    #   esquema actual: local_id + nombre
    tenant_id = data.pop("tenant_id", None)
    product_id = data.pop("product_id", None)
    local_id   = data.pop("local_id", None)
    nombre     = data.pop("nombre", None)

    # Resolver clave real a usar
    key = None
    if tenant_id and product_id:
        key = {"tenant_id": tenant_id, "product_id": product_id}
        pk_name, sk_name = "tenant_id", "product_id"
    elif local_id and nombre:
        key = {"local_id": local_id, "nombre": nombre}
        pk_name, sk_name = "local_id", "nombre"
    else:
        # Mensaje claro según lo que falte
        return _resp(400, {"error": "Faltan claves. Usa (tenant_id, product_id) o (local_id, nombre)"})

    # No permitir que intenten cambiar PK/SK en el update:
    for forbidden in ("tenant_id", "product_id", "local_id", "nombre"):
        if forbidden in data:
            data.pop(forbidden, None)

    if not data:
        return _resp(400, {"error": "Body vacío; nada que actualizar"})

    # Construir UpdateExpression seguro
    expr_names, expr_values, sets = {}, {}, []
    idx = 0
    for k, v in data.items():
        idx += 1
        name_key = f"#f{idx}"
        value_key = f":v{idx}"
        expr_names[name_key] = k
        expr_values[value_key] = v
        sets.append(f"{name_key} = {value_key}")
    update_expr = "SET " + ", ".join(sets)

    ddb = boto3.resource("dynamodb")
    table = ddb.Table(PRODUCTS_TABLE)

    try:
        res = table.update_item(
            Key=key,
            UpdateExpression=update_expr,
            ExpressionAttributeNames=expr_names,
            ExpressionAttributeValues=expr_values,
            ConditionExpression=f"attribute_exists({pk_name}) AND attribute_exists({sk_name})",
            ReturnValues="ALL_NEW"
        )
    except ClientError as e:
        code = e.response.get("Error", {}).get("Code")
        if code == "ConditionalCheckFailedException":
            return _resp(404, {"error": "Producto no encontrado"})
        return _resp(500, {"error": f"Error al actualizar: {e}"})
    except Exception as e:
        return _resp(500, {"error": f"Error inesperado: {e}"})

    return _resp(200, {"ok": True, "item": res.get("Attributes")})
