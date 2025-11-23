import json
import os
import boto3
from datetime import datetime

dynamodb = boto3.resource('dynamodb')
TABLE_HISTORIAL = os.environ['TABLE_HISTORIAL']

def handler(event, context):
    print(f"Entregado Event: {json.dumps(event)}")
    
    task_token = event.get('taskToken')
    input_data = event.get('input', {})
    order_id = input_data.get('order_id')
    
    table = dynamodb.Table(TABLE_HISTORIAL)
    timestamp = datetime.utcnow().isoformat()
    
    item = {
        'id_pedido': order_id,
        'createdAt': timestamp,
        'status': 'ENTREGADO',
        'taskToken': task_token,
        'details': input_data
    }
    table.put_item(Item=item)
    
    return {
        "status": "PEDIDO_ENTREGADO",
        "order_id": order_id
    }
