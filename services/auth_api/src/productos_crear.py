import os, json, uuid, boto3
from datetime import datetime
from decimal import Decimal, InvalidOperation
from ._auth import validate_token  # si no usas paquetes, quita el punto

dynamodb = boto3.resource("dynamodb")
t = dynamodb.Table(os.environ["PRODUCTS_TABLE"])

def _to_decimal(n, default="0"):
    """
    Convierte int/float/str a Decimal con precisión segura.
    Acepta "38.5", 38.5, 38 -> Decimal('38.5').
    """
    if n is None:
        return Decimal(str(default))
    # si ya es Decimal
    if isinstance(n, Decimal):
        return n
    # si viene como int/float/str, conviértelo desde str para no heredar binario
    try:
        return Decimal(str(n))
    except (InvalidOperation, ValueError, TypeError):
        raise ValueError("Valor numérico inválido")

def lambda_handler(event, context):
    try:
        body = json.loads(event.get("body") or "{}")
        token = (body.get("token") or "").strip()
        name  = (body.get("name") or "").strip()
        price = body.get("price")
        offer = body.get("offer", 0)
        image_key = (body.get("image_key") or "").strip()
        product_id = (body.get("product_id") or "") or str(uuid.uuid4())

        auth = validate_token(token)
        if not auth:
            return _resp(403, {"error": "Token inválido"})
        tenant_id = auth["tenant_id"]

        if not (name and image_key):
            return _resp(400, {"error": "name e image_key son requeridos"})
        # convierte a Decimal (clave del fix)
        price_dec = _to_decimal(price)
        offer_dec = _to_decimal(offer, default="0")

        item = {
            "tenant_id": tenant_id,
            "product_id": product_id,
            "name": name,
            "price": price_dec,
            "offer": offer_dec,
            "image_key": image_key,
            "created_at": datetime.utcnow().isoformat()
        }
        t.put_item(Item=item)
        return _resp(200, {"message": "Producto creado", "product_id": product_id})
    except ValueError as e:
        return _resp(400, {"error": str(e)})
    except Exception as e:
        return _resp(500, {"error": str(e)})

def _resp(code, body):
    return {
        "statusCode": code,
        "headers": {"Content-Type": "application/json","Access-Control-Allow-Origin":"*"},
        "body": json.dumps(body)
    }
