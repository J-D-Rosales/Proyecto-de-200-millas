import json
import os
import boto3
import uuid
from datetime import datetime

dynamodb = boto3.resource('dynamodb')
sqs = boto3.client('sqs')
TABLE_HISTORIAL_ESTADOS = os.environ['TABLE_HISTORIAL_ESTADOS']
QUEUE_COCINA_URL = os.environ['QUEUE_COCINA_URL']

def handler(event, context):
    print(f"ProcesarPedido Event: {json.dumps(event)}")
    
    # Event comes from SF: { "taskToken": "...", "input": { ... } }
    task_token = event.get('taskToken')
    input_data = event.get('input', {})
    order_id = (
        input_data.get('detail', {}).get('order_id') or 
        input_data.get('order_id') or 
        input_data.get('pedido_id') or  # ← NUEVO: también buscar pedido_id
        str(uuid.uuid4())
    )
    empleado_id = input_data.get('detail', {}).get('empleado_id') or input_data.get('empleado_id', 'SYSTEM')
    
    # 1. Enqueue to SQS Cocina
    message_body = {
        "order_id": order_id,
        "action": "COCINAR",
        "details": input_data
    }
    sqs.send_message(
        QueueUrl=QUEUE_COCINA_URL,
        MessageBody=json.dumps(message_body)
    )
    
    # 2. Save Token and Status to DynamoDB
    table = dynamodb.Table(TABLE_HISTORIAL_ESTADOS)
    timestamp = datetime.utcnow().isoformat()
    
    item = {
        'pedido_id': order_id,
        'estado_id': timestamp,
        'createdAt': timestamp,
        'estado': 'procesando',
        'taskToken': task_token,
        'hora_inicio': timestamp,
        'empleado': empleado_id,
        'details': input_data
    }
    table.put_item(Item=item)
    
    return {
        "status": "EN_COLA_COCINA",
        "order_id": order_id,
        "empleado_id": empleado_id
    }
