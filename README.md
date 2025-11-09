# 200 Millas – Auth (Register & Login) • README corto

Este README explica **solo** la parte de **usuarios**: *crear usuario* y *login*.
(La parte de productos e imágenes queda fuera.)

---

## Arquitectura mínima

* **API Gateway (HTTP API)**

  * `POST /usuarios/crear` → Lambda **CrearUsuario**
  * `POST /usuarios/login` → Lambda **LoginUsuario**
* **DynamoDB**

  * `t_usuarios` (PK `tenant_id`, SK `user_id`)
  * `t_tokens_acceso` (PK `token`)
* **Lambdas (Python 3.12)** con Serverless Framework v4.

---

## Variables de entorno (definidas en `serverless.yml`)

```yaml
USERS_TABLE=t_usuarios
TOKENS_TABLE=t_tokens_acceso
```

---

## Modelo de datos

### t_usuarios

```json
{
  "tenant_id": "6200millas",          // PK
  "user_id": "admin@6200millas.pe",   // SK (email)
  "password_hash": "sha256...",
  "role": "admin | customer",         // por defecto "customer"
  "created_at": "2025-11-08T12:34:56Z"
}
```

### t_tokens_acceso

```json
{
  "token": "uuid",                     // PK
  "tenant_id": "6200millas",
  "user_id": "admin@6200millas.pe",
  "role": "admin | customer",
  "expires": "YYYY-MM-DD HH:MM:SS"     // UTC
}
```

---

## Endpoints

### 1) Crear Usuario

* **POST** `/usuarios/crear`
* **Body (JSON)**:

```json
{
  "tenant_id": "6200millas",
  "user_id": "admin@6200millas.pe",
  "password": "Secreta123",
  "role": "admin"
}
```

* **Respuestas**:

  * `200` → `{"message":"Usuario registrado", "tenant_id":"...", "user_id":"...", "role":"admin"}`
  * `200` (si ya existe) → `{"message":"Usuario ya existe"}`
  * `400` → parámetros faltantes o `role` inválido
  * `500` → error interno

> Nota: Para MVP se permite enviar `role`. En producción, **no** permitir autoasignarse `admin`.

---

### 2) Login

* **POST** `/usuarios/login`
* **Body (JSON)**:

```json
{
  "tenant_id": "6200millas",
  "user_id": "admin@6200millas.pe",
  "password": "Secreta123"
}
```

* **Respuestas**:

  * `200` → `{"token":"<uuid>","expires":"<iso8601>","role":"admin"}`
  * `403` → credenciales inválidas
  * `400/500` → error de validación/servidor

El `token` se guarda en `t_tokens_acceso` y se usará para autorizar otros endpoints.

---

## Probar rápido

### Postman

1. **Crear usuario** con el JSON de arriba.
2. **Login** y guarda el `token`.

### cURL

```bash
# Crear usuario
curl -X POST "$BASE/usuarios/crear" \
 -H "Content-Type: application/json" \
 -d '{"tenant_id":"6200millas","user_id":"admin@6200millas.pe","password":"Secreta123","role":"admin"}'

# Login
curl -X POST "$BASE/usuarios/login" \
 -H "Content-Type: application/json" \
 -d '{"tenant_id":"6200millas","user_id":"admin@6200millas.pe","password":"Secreta123"}'
```

---

## Notas de implementación

* **Passwords**: se guardan con `sha256` (campo `password_hash`).
* **Expiración de tokens**: +60 min desde el login (UTC).
* **Multitenancy**: `tenant_id` agrupa a los usuarios por negocio.
* **Compatibilidad**: si un usuario antiguo no tiene `role`, `login` devuelve `"customer"` por defecto.

---
# Cambios para los estados
Para los cambios añadidos, se le añadieron 4 funciones.
serverless.yml  src
:~/r_200_millas/Proyecto-de-200-millas/services/workflow (main) $ sls deploy

✔ Installed Serverless Framework v4.23.0

Deploying "pedidos-workflow" to stage "dev" (us-east-1)

✔ Service deployed to stack pedidos-workflow-dev (93s)

endpoints:
  POST - https://49ootimq6b.execute-api.us-east-1.amazonaws.com/delivery/cocina-asignada
  POST - https://49ootimq6b.execute-api.us-east-1.amazonaws.com/delivery/cocina-completa
  POST - https://49ootimq6b.execute-api.us-east-1.amazonaws.com/delivery/empaquetado-completo
  POST - https://49ootimq6b.execute-api.us-east-1.amazonaws.com/delivery/entrega-delivery
functions:
  CocinaAsignada: pedidos-workflow-dev-CocinaAsignada (3.6 kB)
  CocinaCompleta: pedidos-workflow-dev-CocinaCompleta (3.6 kB)
  EmpaquetadoCompleto: pedidos-workflow-dev-EmpaquetadoCompleto (3.6 kB)
  EntregaDelivery: pedidos-workflow-dev-EntregaDelivery (3.6 kB)
  AckStatus: pedidos-workflow-dev-AckStatus (3.6 kB)

:~/r_200_millas/Proyecto-de-200-millas/services/workflow (main) $ curl -X POST "https://49ootimq6b.execute-api.us-east-1.amazonaws.com/delivery/cocina-asignada" \
  -H "Content-Type: application/json" \
  -d '{"tenant_id":"6200millas","order_id":"ORD-1001"}'
{"message": "Evento publicado", "detail": {"tenant_id": "6200millas", "order_id": "ORD-1001", "status": "COCINA_ASIGNADA", "at": "2025-11-09T03:48:34.274268", "mensaje": "Est\u00e1 en cocina"}}:~/r_200_millas/Proyecto-de-200-millas/services/workflow (main) $ 

POr ahora, solo se manda a un evnet bridge que llama a otra funciton que manda un ok 200.

## Firma de la funcion
Paso 1: Llamar a los endpoints (API Delivery)
Llamada para "Cocina Asignada"

Usa el siguiente comando cURL para hacer la llamada a la API:

curl -X POST "https://49ootimq6b.execute-api.us-east-1.amazonaws.com/delivery/cocina-asignada" \
  -H "Content-Type: application/json" \
  -d '{"tenant_id":"6200millas","order_id":"ORD-1001"}'

Esperado:

La respuesta debería ser algo como:

{
  "message": "Evento publicado",
  "detail": {
    "tenant_id": "6200millas",
    "order_id": "ORD-1001",
    "status": "COCINA_ASIGNADA",
    "at": "2025-11-08T12:34:56.000000",
    "mensaje": "Está en cocina"
  }
}


Esto significa que el evento fue correctamente publicado en EventBridge.

