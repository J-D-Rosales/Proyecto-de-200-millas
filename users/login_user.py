import os, json, uuid, re, boto3, time
from datetime import datetime, timedelta
from common import hash_password, response

USERS_TABLE         = os.environ["USERS_TABLE"]
TOKENS_TABLE_USERS  = os.environ["TOKENS_TABLE_USERS"]

dynamodb = boto3.resource("dynamodb")
t_users  = dynamodb.Table(USERS_TABLE)
t_tokens = dynamodb.Table(TOKENS_TABLE_USERS)

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

def _normalize_email(value: str) -> str:
    return (value or "").strip().lower()

def lambda_handler(event, context):
    try:
        body = json.loads(event.get("body") or "{}")

        correo_in   = body.get("correo")
        password_in = body.get("contrasena")

        correo = _normalize_email(correo_in)

        # Validaciones mínimas (según schema)
        if not (correo and password_in):
            return response(400, {"error": "correo y contrasena son requeridos"})
        if not EMAIL_RE.match(correo):
            return response(400, {"error": "correo inválido"})

        # Buscar usuario por PK = correo
        db = t_users.get_item(Key={"correo": correo})
        user = db.get("Item")

        # Si no existe o hash no coincide => 403
        if not user:
            return response(403, {"error": "Credenciales inválidas"})

        stored_hash = user.get("contrasena")  # en este diseño guardamos el hash en el mismo campo 'contrasena'
        if not stored_hash or stored_hash != hash_password(password_in):
            return response(403, {"error": "Credenciales inválidas"})

        # Generar token + expiración (60 min)
        token = str(uuid.uuid4())
        expires_dt = datetime.utcnow() + timedelta(minutes=60)

        # Guardar token; incluimos TTL (epoch seg) si configuraste TTL en la tabla.
        # Cambia 'ttl' si tu atributo TTL tiene otro nombre.
        ttl_epoch = int(time.time()) + 60 * 60

        put_item = {
            "token": token,                 # PK de la tabla de tokens
            "correo": correo,
            "role": user.get("role", "Cliente"),
            "expires_iso": expires_dt.isoformat(),  # legible
            "ttl": ttl_epoch                              # útil si activaste TTL
        }

        t_tokens.put_item(Item=put_item)

        return response(200, {
            "token": token,
            "expires": expires_dt.isoformat(),
            "correo": correo,
            "role": user.get("role", "Cliente")
        })

    except Exception as e:
        return response(500, {"error": str(e)})
