import json
import os
import boto3
from datetime import datetime

dynamodb = boto3.resource('dynamodb')
TABLE_HISTORIAL = os.environ['TABLE_HISTORIAL']

def handler(event, context):
    print(f"PedidoEnCocina Event: {json.dumps(event)}")
    
    task_token = event.get('taskToken')
    input_data = event.get('input', {})
    # Input might be the output of previous state or the original input
    # If previous state was ProcesarPedido (Wait), the output is what triggered the success (EnPreparacion event)
    
    # If triggered by 'EnPreparacion', the input to this state is the event detail from CambiarEstado
    # which is { "order_id": "...", "status": "EnPreparacion", ... }
    
    order_id = input_data.get('order_id')
    
    table = dynamodb.Table(TABLE_HISTORIAL)
    timestamp = datetime.utcnow().isoformat()
    
    item = {
        'id_pedido': order_id,
        'createdAt': timestamp,
        'status': 'PEDIDO_EN_COCINA',
        'taskToken': task_token,
        'details': input_data
    }
    table.put_item(Item=item)
    
    return {
        "status": "EN_COCINA",
        "order_id": order_id
    }
