import os, json, boto3
from datetime import datetime
from .common import hash_password, response

USERS_TABLE = os.environ["USERS_TABLE"]
dynamodb = boto3.resource("dynamodb")
t_users = dynamodb.Table(USERS_TABLE)


def lambda_handler(event, context):
    try:
        body = json.loads(event.get("body") or "{}")
        tenant_id = (body.get("tenant_id") or "").strip()
        user_id   = (body.get("user_id") or "").strip()
        password  = (body.get("password") or "")

        if not (tenant_id and user_id and password):
            return response(400, {"error": "tenant_id, user_id y password son requeridos"})


        t_users.put_item(
            Item={
                "tenant_id": tenant_id,
                "user_id": user_id,
                "password_hash": hash_password(password),
                "created_at": datetime.utcnow().isoformat()
            },
            ConditionExpression="attribute_not_exists(tenant_id) AND attribute_not_exists(user_id)"
        )
        return response(200, {"message": "Usuario registrado", "tenant_id": tenant_id, "user_id": user_id})
    except dynamodb.meta.client.exceptions.ConditionalCheckFailedException:
        return response(200, {"message": "Usuario ya existe", "tenant_id": tenant_id, "user_id": user_id})
    except Exception as e:
        return response(500, {"error": str(e)})
