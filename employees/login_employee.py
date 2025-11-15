import os, json, uuid, boto3
from datetime import datetime, timedelta
from .common import hash_password, response

EMPLOYEE_TABLE  = os.environ["EMPLOYEE_TABLE"]
TOKENS_TABLE_EMPLOYEES = os.environ["TOKENS_TABLE_EMPLOYEES"]
dynamodb = boto3.resource("dynamodb")
t_employee = dynamodb.Table(EMPLOYEE_TABLE)
t_tokens_employee   = dynamodb.Table(TOKENS_TABLE_EMPLOYEES)

def lambda_handler(event, context):
    try:
        body = json.loads(event.get("body") or "{}")
        tenant_id = (body.get("tenant_id") or "").strip()
        user_id   = (body.get("user_id") or "").strip()
        password  = (body.get("password") or "")

        if not (tenant_id and user_id and password):
            return response(400, {"error": "tenant_id, user_id y password son requeridos"})

        db = t_employee.get_item(Key={"tenant_id": tenant_id, "user_id": user_id})
        item = db.get("Item")
        if not item or hash_password(password) != item.get("password_hash"):
            return response(403, {"error": "Credenciales inválidas"})

        token = str(uuid.uuid4())
        expires_dt = datetime.utcnow() + timedelta(minutes=60)

        t_employee.put_item(Item={
            "token": token,
            "tenant_id": tenant_id,
            "user_id": user_id,
            "expires": expires_dt.strftime("%Y-%m-%d %H:%M:%S")
        })

        return response(200, {"token": token, "expires": expires_dt.isoformat()})
    except Exception as e:
        return response(500, {"error": str(e)})
