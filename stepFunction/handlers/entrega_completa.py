import json
import os
import boto3

def handler(event, context):
    print(f"EntregaCompleta Event: {json.dumps(event)}")
    
    input_data = event.get('input', {})
    order_id = input_data.get('order_id')
    
    # Mock sending email
    print(f"Sending Thank You Email for Order {order_id}")
    
    return {
        "status": "COMPLETED",
        "order_id": order_id,
        "message": "Email sent"
    }
