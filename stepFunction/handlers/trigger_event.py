import json
import os
import boto3
from datetime import datetime

events = boto3.client('events')
EVENT_BUS_NAME = os.environ.get('EVENT_BUS_NAME', 'default')

def handler(event, context):
    print(f"TriggerEvent: {json.dumps(event)}")
    
    try:
        body = json.loads(event.get('body', '{}'))
    except:
        body = {}
        
    event_type = body.get('type') # e.g. "CrearPedido", "EnPreparacion"
    source = body.get('source', '200millas.manual')
    detail = body.get('detail', {})
    
    if not event_type:
        return {"statusCode": 400, "body": "Missing 'type'"}
        
    # Add timestamp
    detail['at'] = datetime.utcnow().isoformat()
    
    response = events.put_events(
        Entries=[
            {
                'Source': source,
                'DetailType': event_type,
                'Detail': json.dumps(detail),
                'EventBusName': EVENT_BUS_NAME
            }
        ]
    )
    
    return {
        "statusCode": 200,
        "body": json.dumps({
            "message": "Event published",
            "response": response
        })
    }
