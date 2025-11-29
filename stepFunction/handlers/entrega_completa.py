import json
import os
import boto3
from datetime import datetime
from boto3.dynamodb.conditions import Key

dynamodb = boto3.resource('dynamodb')
events = boto3.client('events')
TABLE_HISTORIAL_ESTADOS = os.environ['TABLE_HISTORIAL_ESTADOS']
TABLE_PEDIDOS = os.environ.get('TABLE_PEDIDOS')
EVENT_BUS_NAME = os.environ.get('EVENT_BUS_NAME', 'default')

def update_pedido_estado(pedido_id, local_id, nuevo_estado):
    """Updates the estado field in the Pedidos table"""
    if not TABLE_PEDIDOS:
        return False
    try:
        table = dynamodb.Table(TABLE_PEDIDOS)
        table.update_item(
            Key={'local_id': local_id, 'pedido_id': pedido_id},
            UpdateExpression='SET estado = :estado',
            ExpressionAttributeValues={':estado': nuevo_estado}
        )
        print(f"✅ Updated pedido {pedido_id} estado to: {nuevo_estado}")
        return True
    except Exception as e:
        print(f"❌ Error updating pedido estado: {e}")
        return False

def handler(event, context):
    print(f"EntregaCompleta Event: {json.dumps(event)}")
    
    input_data = event.get('input', {})
    order_id = input_data.get('order_id')
    empleado_id = input_data.get('empleado_id', 'SYSTEM')
    
    # Get local_id from multiple possible locations
    local_id = (
        input_data.get('local_id') or
        input_data.get('details', {}).get('local_id') or
        'UNKNOWN'
    )
    
    print(f"📍 local_id: {local_id}, order_id: {order_id}")
    
    # Update Pedidos table
    update_pedido_estado(order_id, local_id, 'recibido')
    
    # Update previous state's hora_fin
    # Update previous state's hora_fin
    table = dynamodb.Table(TABLE_HISTORIAL_ESTADOS)
    response = table.query(
        KeyConditionExpression=Key('pedido_id').eq(order_id),
        ScanIndexForward=False,
        Limit=1
    )
    if response.get('Items'):
        prev_item = response['Items'][0]
        table.update_item(
            Key={'pedido_id': order_id, 'estado_id': prev_item['estado_id']},
            UpdateExpression='SET hora_fin = :hf',
            ExpressionAttributeValues={':hf': datetime.utcnow().isoformat()}
        )
    
    # Save final state
    timestamp = datetime.utcnow().isoformat()
    item = {
        'pedido_id': order_id,
        'estado_id': timestamp,
        'createdAt': timestamp,
        'estado': 'recibido',
        'hora_inicio': timestamp,
        'hora_fin': timestamp,
        'empleado': empleado_id,
        'details': 'Pedido completado exitosamente'
    }
    table.put_item(Item=item)
    
    # Publish CorreoAgradecimiento event to EventBridge
    try:
        events.put_events(
            Entries=[{
                'Source': '200millas.pedidos',
                'DetailType': 'CorreoAgradecimiento',
                'Detail': json.dumps({
                    'order_id': order_id,
                    'timestamp': timestamp,
                    'message': 'Gracias por tu pedido'
                }),
                'EventBusName': EVENT_BUS_NAME
            }]
        )
        print(f"Published CorreoAgradecimiento event for order {order_id}")
    except Exception as e:
        print(f"Error publishing event: {e}")
    
    return {
        "status": "COMPLETED",
        "order_id": order_id,
        "message": "Pedido completado y email enviado"
    }
