import json
import os
import boto3
from datetime import datetime

dynamodb = boto3.resource('dynamodb')
TABLE_HISTORIAL = os.environ['TABLE_HISTORIAL']
TABLE_PRODUCTOS = os.environ['TABLE_PRODUCTOS']

def handler(event, context):
    print(f"CocinaCompleta Event: {json.dumps(event)}")
    
    task_token = event.get('taskToken')
    input_data = event.get('input', {})
    order_id = input_data.get('order_id')
    
    # Update Products (Mock logic - decrement generic product)
    # In a real app, we'd parse items from input_data
    
    # Save State
    table = dynamodb.Table(TABLE_HISTORIAL)
    timestamp = datetime.utcnow().isoformat()
    
    item = {
        'id_pedido': order_id,
        'createdAt': timestamp,
        'status': 'COCINA_COMPLETA',
        'taskToken': task_token,
        'details': input_data
    }
    table.put_item(Item=item)
    
    return {
        "status": "COCINA_TERMINADA",
        "order_id": order_id
    }
