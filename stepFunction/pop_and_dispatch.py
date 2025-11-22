import json
import os
import logging
import boto3

logger = logging.getLogger()
logger.setLevel(logging.INFO)

sqs = boto3.client("sqs")
sf = boto3.client("stepfunctions")

QUEUE_URL = os.environ["QUEUE_URL"]
STATE_MACHINE_ARN = os.environ["STATE_MACHINE_ARN"]

def _parse_http_body(event):
    body = event.get("body", "") or ""
    if event.get("isBase64Encoded"):
        import base64
        body = base64.b64decode(body).decode("utf-8")
    if not body:
        return {}
    try:
        return json.loads(body)
    except Exception:
        raise ValueError("El body del request debe ser JSON")

def _parse_sqs_body(body_str):
    """
    Esperado en la cola:
      JSON: {"id_pedido":"...", "estado":"..."}
      o texto: "id_pedido,estado" (| : ; también)
    Devuelve (id_pedido, estado).
    """
    try:
        data = json.loads(body_str)
        if isinstance(data, dict) and "estado" in data:
            return str(data.get("id_pedido", "")), str(data["estado"])
    except Exception:
        pass
    for sep in [",", "|", ":", ";"]:
        if sep in body_str:
            left, right = [s.strip() for s in body_str.split(sep, 1)]
            if right:
                return left, right
    raise ValueError("Mensaje SQS inválido. Se espera {'id_pedido','estado'} o 'id,estado'.")

def handler(event, context):
    """
    HTTP POST /pedidos/pop
    Body opcional:
      { "max_messages": 5, "wait_seconds": 5, "visibility_timeout": 45 }
    """
    try:
        req = _parse_http_body(event)
        max_messages = int(req.get("max_messages", 1))
        wait_seconds = int(req.get("wait_seconds", 5))
        visibility_timeout = int(req.get("visibility_timeout", 30))

        # límites seguros de SQS
        if max_messages < 1: max_messages = 1
        if max_messages > 10: max_messages = 10
        if wait_seconds < 0: wait_seconds = 0
        if wait_seconds > 20: wait_seconds = 20

        # 1) Recibir mensajes (pop)
        recv = sqs.receive_message(
            QueueUrl=QUEUE_URL,
            MaxNumberOfMessages=max_messages,
            WaitTimeSeconds=wait_seconds,
            VisibilityTimeout=visibility_timeout,
            AttributeNames=["All"],
            MessageAttributeNames=["All"],
        )

        messages = recv.get("Messages", [])
        if not messages:
            return {
                "statusCode": 200,
                "headers": {"content-type": "application/json"},
                "body": json.dumps({"popped": 0, "executions": [], "note": "No hay mensajes"}),
            }

        executions = []
        failures = []

        for m in messages:
            receipt = m["ReceiptHandle"]
            body_str = m.get("Body", "")

            try:
                id_pedido, estado = _parse_sqs_body(body_str)

                # 2) Invocar Step Functions con SOLO el string 'estado' como input
                #    (input debe ser JSON, por eso lo serializamos)
                input_json = json.dumps(estado)
                resp = sf.start_execution(
                    stateMachineArn=STATE_MACHINE_ARN,
                    input=input_json
                )
                exec_arn = resp.get("executionArn")
                executions.append({"messageId": m.get("MessageId"), "id_pedido": id_pedido, "estado": estado, "executionArn": exec_arn})

                # 3) Borrar mensaje de la cola SOLO si la invocación fue OK
                sqs.delete_message(QueueUrl=QUEUE_URL, ReceiptHandle=receipt)

            except Exception as e:
                logger.exception("Error con messageId=%s: %s", m.get("MessageId"), e)
                failures.append({"messageId": m.get("MessageId"), "error": str(e)})

        status = 207 if failures else 200
        return {
            "statusCode": status,
            "headers": {"content-type": "application/json"},
            "body": json.dumps({
                "popped": len(messages),
                "executions": executions,
                "failures": failures
            }),
        }

    except ValueError as e:
        return {"statusCode": 400, "headers": {"content-type": "application/json"}, "body": json.dumps({"error": str(e)})}
    except Exception as e:
        logger.exception("Fallo inesperado: %s", e)
        return {"statusCode": 500, "headers": {"content-type": "application/json"}, "body": json.dumps({"error": "Internal Server Error"})}
