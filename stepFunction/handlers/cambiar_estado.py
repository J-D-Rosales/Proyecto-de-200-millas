import json
import os
import boto3
from boto3.dynamodb.conditions import Key

dynamodb = boto3.resource('dynamodb')
stepfunctions = boto3.client('stepfunctions')
TABLE_HISTORIAL = os.environ['TABLE_HISTORIAL']

def handler(event, context):
    print(f"CambiarEstado Event: {json.dumps(event)}")
    
    detail = event.get('detail', {})
    detail_type = event.get('detail-type') # e.g. "EnPreparacion", "CocinaCompleta"
    order_id = detail.get('order_id')
    
    if not order_id:
        print("No order_id in event")
        return
    
    # Map Event Type to Expected Status in DB to find the token
    # We need to find the LATEST token for this order.
    # The table has (id_pedido, createdAt).
    
    table = dynamodb.Table(TABLE_HISTORIAL)
    
    # Query all history for this order
    response = table.query(
        KeyConditionExpression=Key('id_pedido').eq(order_id),
        ScanIndexForward=False, # Descending order (newest first)
        Limit=1
    )
    
    items = response.get('Items', [])
    if not items:
        print(f"No history found for order {order_id}")
        return
    
    latest_item = items[0]
    task_token = latest_item.get('taskToken')
    current_status = latest_item.get('status')
    
    if not task_token:
        print(f"No task token found in latest state ({current_status}) for order {order_id}")
        return
    
    print(f"Found token for order {order_id} in status {current_status}. Triggering SF...")
    
    # Retrieve stored input/details to preserve context (like retry_count)
    # stored_data can be in 'history' (ProcesarPedido) or 'details' (others)
    stored_data = latest_item.get('history') or latest_item.get('details') or {}
    retry_count = stored_data.get('retry_count', 0)
    
    # Determine output status based on event
    output_payload = {
        "order_id": order_id,
        "event": detail_type,
        "status": detail.get('status', 'ACEPTADO'), # Default to Accepted if not specified
        "retry_count": retry_count, # Persist retry count
        "details": detail
    }
    
    try:
        stepfunctions.send_task_success(
            taskToken=task_token,
            output=json.dumps(output_payload)
        )
        print("Successfully sent task success")
    except Exception as e:
        print(f"Error sending task success: {e}")
        # If token is invalid (timeout), we might want to handle it, but for now just log.
