import os, json, re, boto3
from common import hash_password, response

USERS_TABLE = os.environ["USERS_TABLE"]
dynamodb = boto3.resource("dynamodb")
t_users = dynamodb.Table(USERS_TABLE)

ALLOWED_ROLES = {"Cliente", "Gerente", "Admin"}
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

def lambda_handler(event, context):
    try:
        body = json.loads(event.get("body") or "{}")

        nombre      = (body.get("nombre") or "").strip()
        correo_raw  = (body.get("correo") or "").strip()
        contrasena  = (body.get("contrasena") or "")
        role        = (body.get("role") or "").strip()

        # Normalizar correo (PK)
        correo = correo_raw.lower()

        # Validaciones según schema
        if not (nombre and correo and contrasena and role):
            return response(400, {"error": "nombre, correo, contrasena y role son requeridos"})

        if not EMAIL_RE.match(correo):
            return response(400, {"error": "correo inválido"})

        if len(contrasena) < 6:
            return response(400, {"error": "contrasena debe tener al menos 6 caracteres"})

        if role not in ALLOWED_ROLES:
            return response(400, {"error": f"role inválido. Permitidos: {sorted(ALLOWED_ROLES)}"})

        # Insertar estrictamente los 4 campos del schema
        t_users.put_item(
            Item={
                "nombre": nombre,
                "correo": correo,                      # PK
                "contrasena": hash_password(contrasena),  # almacenamos el hash en el mismo campo
                "role": role
            },
            ConditionExpression="attribute_not_exists(correo)"
        )

        return response(201, {"message": "Usuario registrado", "correo": correo})

    except dynamodb.meta.client.exceptions.ConditionalCheckFailedException:
        # Ya existe un item con ese 'correo' (PK)
        return response(200, {"message": "Usuario ya existe", "correo": (body.get("correo") or "").strip().lower()})

    except Exception as e:
        return response(500, {"error": str(e)})
