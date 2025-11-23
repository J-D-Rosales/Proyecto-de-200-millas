import json
import os
import boto3
import uuid
from datetime import datetime

dynamodb = boto3.resource('dynamodb')
sqs = boto3.client('sqs')
TABLE_HISTORIAL = os.environ['TABLE_HISTORIAL']
QUEUE_COCINA_URL = os.environ['QUEUE_COCINA_URL']

def handler(event, context):
    print(f"ProcesarPedido Event: {json.dumps(event)}")
    
    # Event comes from SF: { "taskToken": "...", "input": { ... } }
    task_token = event.get('taskToken')
    input_data = event.get('input', {})
    order_id = input_data.get('detail', {}).get('order_id') or input_data.get('order_id') or str(uuid.uuid4())
    
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
    table = dynamodb.Table(TABLE_HISTORIAL)
    timestamp = datetime.utcnow().isoformat()
    
    item = {
        'id_pedido': order_id,
        'createdAt': timestamp,
        'status': 'PROCESANDO_PEDIDO',
        'taskToken': task_token,
        'history': input_data
    }
    table.put_item(Item=item)
    
    return {
        "status": "EN_COLA_COCINA",
        "order_id": order_id
    }
