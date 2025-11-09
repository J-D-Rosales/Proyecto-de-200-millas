import os, json, boto3
from datetime import datetime
from .common import hash_password, response

USERS_TABLE = os.environ["USERS_TABLE"]
dynamodb = boto3.resource("dynamodb")
t_usuarios = dynamodb.Table(USERS_TABLE)

ALLOWED_ROLES = {"admin", "customer"}

def lambda_handler(event, context):
    try:
        body = json.loads(event.get("body") or "{}")
        tenant_id = (body.get("tenant_id") or "").strip()
        user_id   = (body.get("user_id") or "").strip()
        password  = (body.get("password") or "")
        role      = (body.get("role") or "customer").strip().lower()

        if not (tenant_id and user_id and password):
            return response(400, {"error": "tenant_id, user_id y password son requeridos"})

        if role not in ALLOWED_ROLES:
            return response(400, {"error": "role inválido (usa: admin | customer)"})

        t_usuarios.put_item(
            Item={
                "tenant_id": tenant_id,
                "user_id": user_id,
                "password_hash": hash_password(password),
                "role": role,
                "created_at": datetime.utcnow().isoformat()
            },
            ConditionExpression="attribute_not_exists(tenant_id) AND attribute_not_exists(user_id)"
        )
        return response(200, {"message": "Usuario registrado", "tenant_id": tenant_id, "user_id": user_id, "role": role})
    except dynamodb.meta.client.exceptions.ConditionalCheckFailedException:
        return response(200, {"message": "Usuario ya existe", "tenant_id": tenant_id, "user_id": user_id})
    except Exception as e:
        return response(500, {"error": str(e)})
