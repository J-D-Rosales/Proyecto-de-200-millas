import json
import os
import boto3
import uuid
from datetime import datetime

dynamodb = boto3.resource('dynamodb')
sqs = boto3.client('sqs')
TABLE_HISTORIAL_ESTADOS = os.environ['TABLE_HISTORIAL_ESTADOS']
TABLE_PEDIDOS = os.environ.get('TABLE_PEDIDOS')
QUEUE_COCINA_URL = os.environ['QUEUE_COCINA_URL']

def update_pedido_estado(pedido_id, local_id, nuevo_estado):
    """Updates the estado field in the Pedidos table"""
    if not TABLE_PEDIDOS:
        print("Warning: TABLE_PEDIDOS not configured")
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
    local_id = input_data.get('local_id', 'UNKNOWN')
    
    # 0. Update Pedidos table
    update_pedido_estado(order_id, local_id, 'procesando')
    
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
