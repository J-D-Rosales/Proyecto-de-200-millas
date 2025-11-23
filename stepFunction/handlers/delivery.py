import json
import os
import boto3
from datetime import datetime

dynamodb = boto3.resource('dynamodb')
sqs = boto3.client('sqs')
TABLE_HISTORIAL = os.environ['TABLE_HISTORIAL']
QUEUE_DELIVERY_URL = os.environ['QUEUE_DELIVERY_URL']

def handler(event, context):
    print(f"Delivery Event: {json.dumps(event)}")
    
    task_token = event.get('taskToken')
    input_data = event.get('input', {})
    order_id = input_data.get('order_id')
    
    # Enqueue to SQS Delivery
    message_body = {
        "order_id": order_id,
        "action": "DELIVERY",
        "details": input_data
    }
    sqs.send_message(
        QueueUrl=QUEUE_DELIVERY_URL,
        MessageBody=json.dumps(message_body)
    )
    
    table = dynamodb.Table(TABLE_HISTORIAL)
    timestamp = datetime.utcnow().isoformat()
    
    item = {
        'id_pedido': order_id,
        'createdAt': timestamp,
        'status': 'EN_DELIVERY',
        'taskToken': task_token,
        'details': input_data
    }
    table.put_item(Item=item)
    
    return {
        "status": "DELIVERY_EN_CURSO",
        "order_id": order_id
    }
