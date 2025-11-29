import json
import os
import boto3

events = boto3.client('events')
EVENT_BUS_NAME = os.environ.get('EVENT_BUS_NAME', 'default')

def publish_event(source, detail_type, detail):
    """Helper function to publish events to EventBridge"""
    try:
        events.put_events(
            Entries=[{
                'Source': source,
                'DetailType': detail_type,
                'Detail': json.dumps(detail),
                'EventBusName': EVENT_BUS_NAME
            }]
        )
        return True
    except Exception as e:
        print(f"Error publishing event: {e}")
        return False

def response(status_code, body):
    """Helper function to create HTTP response"""
    return {
        'statusCode': status_code,
        'headers': {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*'
        },
        'body': json.dumps(body)
    }
