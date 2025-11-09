# Proyecto-de-200-millas
Este proyecto impleemnta el serverless para la gestión de os usuarios y productos.
# Resumen de la arquitectura (MVP Auth)

* **API Gateway (HTTP API)** expone dos endpoints:

  * `POST /usuarios/crear` → Lambda **CrearUsuario**
  * `POST /usuarios/login` → Lambda **LoginUsuario**
  * (Interno) **ValidarTokenAcceso**: se usará desde otras Lambdas para proteger endpoints (productos, pedidos, etc.).

* **Lambdas (Python 3.12)**:

  * **CrearUsuario**: recibe `tenant_id`, `user_id` (email) y `password`.

    * Hash del password (`sha256`), escribe en **DynamoDB t_usuarios** con clave compuesta:

      * `PK: tenant_id`, `SK: user_id` + `password_hash`, `created_at`.
    * Usa condición de “no existe” para idempotencia.
  * **LoginUsuario**: valida credenciales contra **t_usuarios** y crea un **token** (UUID) en **t_tokens_acceso** con `expires` (+60 min, UTC). Devuelve `{ token, expires }`.
  * **ValidarTokenAcceso** (sin endpoint por ahora): busca el `token` en **t_tokens_acceso**, verifica expiración y devuelve `tenant_id` y `user_id` si es válido. Esto permitirá autorizar endpoints como “crear producto”.

* **DynamoDB**:

  * **t_usuarios**: PK `tenant_id`, SK `user_id`; atributos `password_hash`, `created_at`.
  * **t_tokens_acceso**: PK `token`; atributos `tenant_id`, `user_id`, `expires` (UTC `YYYY-MM-DD HH:MM:SS`).

* **Multitenancy**: todos los datos se agrupan por `tenant_id` (misma partición lógica). Un mismo tenant tiene múltiples usuarios.

* **Seguridad (MVP)**: token propio en tabla (no Cognito). Passwords hash (no en claro). Todo vía HTTPS. En producción podrás cambiar a **Cognito** o JWT firmado.

---

# Endpoints activos (dev)

* `POST` — **[https://rgvk752mh6.execute-api.us-east-1.amazonaws.com/usuarios/crear](https://rgvk752mh6.execute-api.us-east-1.amazonaws.com/usuarios/crear)**
* `POST` — **[https://rgvk752mh6.execute-api.us-east-1.amazonaws.com/usuarios/login](https://rgvk752mh6.execute-api.us-east-1.amazonaws.com/usuarios/login)**

---

# JSON para Postman (request bodies)

## Registrar usuario

URL: `POST https://rgvk752mh6.execute-api.us-east-1.amazonaws.com/usuarios/crear`
Headers:

* `Content-Type: application/json`

Body (raw JSON):

```json
{
  "tenant_id": "200millas",
  "user_id": "chef@6200millas.pe",
  "password": "Secreta123"
}
```

**Respuestas típicas**

* 200 (creado): `{"message":"Usuario registrado","tenant_id":"6200millas","user_id":"chef@6200millas.pe"}`
* 200 (ya existe, idempotente): `{"message":"Usuario ya existe"}`
* 400: `{"error":"tenant_id, user_id y password son requeridos"}`
* 500: `{"error":"<detalle>"}`

## Login

URL: `POST https://rgvk752mh6.execute-api.us-east-1.amazonaws.com/usuarios/login`
Headers:

* `Content-Type: application/json`

Body (raw JSON):

```json
{
  "tenant_id": "200millas",
  "user_id": "chef@6200millas.pe",
  "password": "Secreta123"
}
```
