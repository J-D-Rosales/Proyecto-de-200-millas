import os
import json
import logging
from datetime import datetime, timezone

import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger()
logger.setLevel(logging.INFO)

dynamodb = boto3.resource("dynamodb")
TABLE_NAME = os.environ["HIST_TABLE"]
table = dynamodb.Table(TABLE_NAME)

def _now_iso():
    # Timestamp ISO-8601 con zona UTC (ordenable como sort key string)
    return datetime.now(timezone.utc).isoformat(timespec="seconds")

def handler(event, context):
    """
    Evento esperado (desde Step Functions):
      {
        "id_pedido": "PED-00123",
        "estado": "EN_PREPARACION",
        ... (otros campos opcionales)
      }
    Guarda: { id_pedido (PK), createdAt (SK), estado }
    """
    logger.info("Evento recibido: %s", json.dumps(event, ensure_ascii=False))

    if not isinstance(event, dict):
        return {"ok": False, "error": "Input debe ser un objeto JSON"}

    id_pedido = str(event.get("id_pedido", "")).strip()
    estado = str(event.get("estado", "")).strip()

    if not id_pedido or not estado:
        return {"ok": False, "error": "Faltan id_pedido y/o estado"}

    item = {
        "id_pedido": id_pedido,
        "createdAt": _now_iso(),
        "estado": estado,
    }

    try:
        table.put_item(Item=item)
        logger.info("Historial insertado: %s", json.dumps(item, ensure_ascii=False))
        # Devolvemos algo útil a la state machine
        return {"ok": True, "historial": item}
    except ClientError as e:
        logger.exception("Error al escribir en DynamoDB: %s", e)
        return {"ok": False, "error": str(e)}
