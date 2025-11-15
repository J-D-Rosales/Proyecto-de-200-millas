import os
import boto3
from datetime import datetime, timezone

TOKENS_TABLE_USERS = os.environ["TOKENS_TABLE_USERS"]

def lambda_handler(event, context):
    # Entrada (json)
    token = event.get('token')
    if not token:
        return {"statusCode": 403, "body": "Token faltante"}

    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table(TOKENS_TABLE_USERS)
    try:
        response = table.get_item(Key={'token': token})
    except Exception as e:
        print(f"Error get_item: {e}")
        return {"statusCode": 403, "body": "Error verificando token"}

    item = response.get('Item')
    if not item:
        return {"statusCode": 403, "body": "Token no existe"}

    expires_str = item.get('expires')
    if not expires_str:
        return {"statusCode": 403, "body": "Token sin fecha de expiración"}

    try:
        expires_dt = datetime.strptime(expires_str, "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
    except ValueError:
        return {"statusCode": 403, "body": "Formato de expiración inválido"}

    now_utc = datetime.now(timezone.utc)
    if now_utc > expires_dt:
        return {"statusCode": 403, "body": "Token expirado"}

    return {"statusCode": 200, "body": "Token válido"}
