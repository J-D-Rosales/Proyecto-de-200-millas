import json
import os
import boto3
from datetime import datetime

dynamodb = boto3.resource('dynamodb')
TABLE_HISTORIAL = os.environ['TABLE_HISTORIAL']

def handler(event, context):
    print(f"ReintentarCocina Event: {json.dumps(event)}")
    
    # This is a Task state (not wait), so event is just the input
    input_data = event.get('input', {})
    order_id = input_data.get('order_id')
    
    # Log retry
    table = dynamodb.Table(TABLE_HISTORIAL)
    timestamp = datetime.utcnow().isoformat()
    
    item = {
        'id_pedido': order_id,
        'createdAt': timestamp,
        'status': 'REINTENTAR_COCINA',
        'details': "Re-enqueuing for kitchen"
    }
    table.put_item(Item=item)
    
    # We don't need to enqueue here explicitly if we transition back to ProcesarPedido,
    # because ProcesarPedido handler enqueues.
    # However, if we want to preserve the 'retry' count, we should pass it.
    
    retry_count = input_data.get('retry_count', 0) + 1
    
    return {
        "order_id": order_id,
        "retry_count": retry_count,
        "status": "RETRYING"
    }
