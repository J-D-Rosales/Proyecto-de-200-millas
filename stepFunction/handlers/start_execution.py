import json
import os
import boto3
import uuid

stepfunctions = boto3.client('stepfunctions')
STATE_MACHINE_ARN = os.environ['STATE_MACHINE_ARN']

def handler(event, context):
    print(f"StartExecution Event: {json.dumps(event)}")
    
    # Event detail contains the order info
    detail = event.get('detail', {})
    order_id = detail.get('order_id', str(uuid.uuid4()))
    
    # Start SF Execution
    try:
        response = stepfunctions.start_execution(
            stateMachineArn=STATE_MACHINE_ARN,
            name=f"Order-{order_id}-{uuid.uuid4().hex[:4]}",
            input=json.dumps(detail)
        )
        print(f"Started execution: {response['executionArn']}")
        return {
            "statusCode": 200,
            "body": json.dumps({"executionArn": response['executionArn']})
        }
    except Exception as e:
        print(f"Error starting execution: {e}")
        return {
            "statusCode": 500,
            "body": json.dumps({"error": str(e)})
        }
