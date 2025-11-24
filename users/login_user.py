import os
import json
import uuid
import re
import boto3
from datetime import datetime, timedelta
from common import hash_password

USERS_TABLE = os.environ.get("USERS_TABLE", "USERS_TABLE")
TOKENS_TABLE_USERS = os.environ.get("TOKENS_TABLE_USERS", "TOKENS_TABLE_USERS")

CORS_HEADERS = {"Access-Control-Allow-Origin": "*"}

dynamodb = boto3.resource("dynamodb")
t_users = dynamodb.Table(USERS_TABLE)
t_tokens = dynamodb.Table(TOKENS_TABLE_USERS)

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

def _resp(code, body):
    return {
        "statusCode": code,
        "headers": {"Content-Type": "application/json", **CORS_HEADERS},
        "body": json.dumps(body, ensure_ascii=False)
    }

def _normalize_email(value: str) -> str:
    return (value or "").strip().lower()

def lambda_handler(event, context):
    try:
        # Parsear body
        body = json.loads(event.get("body") or "{}")
        
        correo_in = body.get("correo")
        password_in = body.get("contrasena")
        
        correo = _normalize_email(correo_in)
        
        # Validaciones
        if not (correo and password_in):
            return _resp(400, {"error": "correo y contrasena son requeridos"})
        if not EMAIL_RE.match(correo):
            return _resp(400, {"error": "correo inválido"})
        
        # Buscar usuario
        response = t_users.get_item(Key={"correo": correo})
        
        if 'Item' not in response:
            return _resp(403, {"error": "Usuario no existe"})
        
        user = response['Item']
        hashed_password_bd = user.get("contrasena")
        
        # Verificar contraseña (soporta tanto hasheada como texto plano)
        hashed_password = hash_password(password_in)
        # Comparar: hasheada o texto plano (para compatibilidad con datos generados)
        if hashed_password != hashed_password_bd and password_in != hashed_password_bd:
            return _resp(403, {"error": "Password incorrecto"})
        
        # Generar token
        token = str(uuid.uuid4())
        fecha_hora_exp = datetime.now() + timedelta(minutes=60)
        
        # Obtener rol del usuario
        rol = user.get("rol") or user.get("role") or "Cliente"
        
        # Guardar token en la tabla
        registro = {
            'token': token,
            'user_id': correo,
            'rol': rol,
            'expires': fecha_hora_exp.strftime('%Y-%m-%d %H:%M:%S')
        }
        
        t_tokens.put_item(Item=registro)
        
        # Retornar token
        return _resp(200, {
            "token": token,
            "expires": fecha_hora_exp.strftime('%Y-%m-%d %H:%M:%S'),
            "correo": correo,
            "rol": rol
        })
        
    except Exception as e:
        return _resp(500, {"error": str(e)})
