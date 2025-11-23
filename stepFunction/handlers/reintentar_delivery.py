import json
import os
import boto3
from datetime import datetime

dynamodb = boto3.resource('dynamodb')
TABLE_HISTORIAL = os.environ['TABLE_HISTORIAL']

def handler(event, context):
    print(f"ReintentarDelivery Event: {json.dumps(event)}")
    
    input_data = event.get('input', {})
    order_id = input_data.get('order_id')
    
    table = dynamodb.Table(TABLE_HISTORIAL)
    timestamp = datetime.utcnow().isoformat()
    
    item = {
        'id_pedido': order_id,
        'createdAt': timestamp,
        'status': 'REINTENTAR_DELIVERY',
        'details': "Re-enqueuing for delivery"
    }
    table.put_item(Item=item)
    
    retry_count = input_data.get('retry_count', 0) + 1
    
    return {
        "order_id": order_id,
        "retry_count": retry_count,
        "status": "RETRYING_DELIVERY"
    }
