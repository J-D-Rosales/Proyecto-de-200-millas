import json
from .emit import emit_status, resp

def lambda_handler(event, context):
    body = json.loads(event.get("body") or "{}")
    tenant_id = (body.get("tenant_id") or "").strip()
    order_id  = (body.get("order_id") or "").strip()
    if not (tenant_id and order_id):
        return resp(400, {"error": "tenant_id y order_id son requeridos"})

    detail = emit_status("EMPAQUETADO_COMPLETO", tenant_id, order_id, {"mensaje": "Empaquetado listo"})
    return resp(200, {"message": "Evento publicado", "detail": detail})
