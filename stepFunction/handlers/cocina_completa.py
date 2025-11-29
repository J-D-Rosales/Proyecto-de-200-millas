import json
import os
import boto3
from datetime import datetime
from boto3.dynamodb.conditions import Key
from decimal import Decimal

dynamodb = boto3.resource('dynamodb')
TABLE_HISTORIAL_ESTADOS = os.environ['TABLE_HISTORIAL_ESTADOS']
TABLE_PRODUCTOS = os.environ['TABLE_PRODUCTOS']
TABLE_PEDIDOS = os.environ.get('TABLE_PEDIDOS')

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
    print(f"CocinaCompleta Event: {json.dumps(event)}")
    
    task_token = event.get('taskToken')
    input_data = event.get('input', {})
    order_id = input_data.get('order_id')
    empleado_id = input_data.get('empleado_id', 'COCINA')
    local_id = input_data.get('details', {}).get('local_id') or input_data.get('local_id', 'UNKNOWN')
    
    # Update Pedidos table
    update_pedido_estado(order_id, local_id, 'cocina_completa')
    
    # Update product inventory
    productos_items = input_data.get('details', {}).get('productos', [])
    if productos_items:
        productos_table = dynamodb.Table(TABLE_PRODUCTOS)
        for item in productos_items:
            producto_id = item.get('producto_id')
            cantidad = item.get('cantidad', 1)
            if producto_id:
                try:
                    # Decrement product quantity
                    productos_table.update_item(
                        Key={'local_id': item.get('local_id', 'default'), 'producto_id': producto_id},
                        UpdateExpression='SET cantidad = cantidad - :val',
                        ExpressionAttributeValues={':val': Decimal(str(cantidad))},
                        ConditionExpression='cantidad >= :val'
                    )
                except Exception as e:
                    print(f"Error updating product {producto_id}: {e}")
    
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
    
    # Save State
    timestamp = datetime.utcnow().isoformat()
    
    item = {
        'pedido_id': order_id,
        'estado_id': timestamp,
        'createdAt': timestamp,
        'estado': 'cocina_completa',
        'taskToken': task_token,
        'hora_inicio': timestamp,
        'empleado': empleado_id,
        'details': input_data
    }
    table.put_item(Item=item)
    
    return {
        "status": "COCINA_TERMINADA",
        "order_id": order_id,
        "empleado_id": empleado_id
    }
