# Reporte de Pruebas de Endpoints

## Resumen
Se han probado los endpoints desplegados para los servicios `service-users`, `service-products` y `service-clientes`.

**Estado General:**
- ✅ **service-users**: Autenticación (Registro/Login) funciona correctamente.
- ✅ **service-products**: Listado y consulta de productos funciona correctamente.
- ❌ **service-clientes**: Creación de pedidos falla (403 Forbidden).
- ❌ **service-users (Perfil)**: Consulta de perfil (`/users/me`) falla (500 Internal Server Error).

## Detalles de Endpoints

### 1. Service Users
**Base URL:** `https://wp4cigovo1.execute-api.us-east-1.amazonaws.com`

#### POST /users/register
- **Estado:** ✅ Funciona (200 OK - Usuario ya existe / 201 Created)
- **Descripción:** Registra un nuevo usuario.
- **Body Request:**
  ```json
  {
    "nombre": "Test User",
    "correo": "test_client_v2@200millas.com",
    "contrasena": "password123",
    "role": "Cliente"
  }
  ```
- **Response:**
  ```json
  {
    "message": "Usuario ya existe",
    "correo": "test_client_v2@200millas.com"
  }
  ```

#### POST /users/login
- **Estado:** ✅ Funciona (200 OK)
- **Descripción:** Inicia sesión y devuelve un token JWT.
- **Body Request:**
  ```json
  {
    "correo": "test_client_v2@200millas.com",
    "contrasena": "password123"
  }
  ```
- **Response:**
  ```json
  {
    "token": "...",
    "expires": "...",
    "correo": "test_client_v2@200millas.com",
    "role": "Cliente"
  }
  ```

#### GET /users/me
- **Estado:** ❌ Falla (500 Internal Server Error)
- **Causa Identificada:**
  1.  En `users/serverless.yml`, la variable `TOKEN_VALIDATOR_FUNCTION` tenía el nombre corto `ValidarUserTokenAcceso`, lo que causa que la invocación manual falle.
  2.  El endpoint estaba configurado con `authorizer: userTokenAuthorizer`. El autorizador `ValidarUserTokenAcceso` devuelve un JSON simple `{statusCode: 200...}`, lo cual NO es válido para un Lambda Authorizer de tipo REQUEST (que espera una política IAM). Esto causa que API Gateway devuelva 500 o 401 antes de llegar al handler.

### 2. Service Products
**Base URL:** `https://bd1dxxt4yh.execute-api.us-east-1.amazonaws.com`

#### POST /productos/list
- **Estado:** ✅ Funciona (200 OK)
- **Descripción:** Lista productos de un local.
- **Body Request:**
  ```json
  {
    "local_id": "LOCAL-005"
  }
  ```
- **Response:** Lista de productos.

#### POST /productos/id
- **Estado:** ✅ Funciona (200 OK)
- **Descripción:** Obtiene el detalle de un producto específico.
- **Body Request:**
  ```json
  {
    "local_id": "LOCAL-005",
    "nombre": "Ceviches 39"
  }
  ```
- **Response:** Detalle del producto.

### 3. Service Clientes (Pedidos)
**Base URL:** `https://s371uf7p37.execute-api.us-east-1.amazonaws.com`

#### POST /pedido/create
- **Estado:** ❌ Falla (403 Forbidden)
- **Error:** `{"error": "Token inválido o expirado"}`
- **Causa Identificada:**
  1.  La validación del token fallaba. Se ha corregido el código para usar el patrón de invocación manual proporcionado.
  2.  **Problema de Roles:** El usuario se registra con rol "Cliente" (Mayúscula), pero el código validaba `rol != "cliente"` (Minúscula). Esto causaría un error de permisos incluso si el token fuera válido.

## Correcciones Aplicadas (Pendientes de Despliegue)
Se han realizado las siguientes correcciones en el código fuente:

1.  **`users/serverless.yml`**:
    -   Se actualizó `TOKEN_VALIDATOR_FUNCTION` al nombre completo: `service-users-dev-ValidarUserTokenAcceso`.
    -   **Se eliminó** la configuración `authorizer: userTokenAuthorizer` de las funciones protegidas (`MiUsuario`, etc.). Dado que el código realiza la validación manualmente invocando a la lambda, el autorizador a nivel de API Gateway era redundante y estaba mal configurado (retorno incorrecto).

2.  **`clientes/pedido_create.py`** (y otros endpoints de clientes):
    -   Se corrigió la validación de rol para ser insensible a mayúsculas/minúsculas (`.lower()`).
    -   Se mantiene el uso del patrón de invocación manual para validar el token.

3.  **`users/mi_usuario.py`**:
    -   Se mantiene el uso del patrón de invocación manual.

Una vez desplegados estos cambios, los errores 500 y 403 deberían resolverse.
