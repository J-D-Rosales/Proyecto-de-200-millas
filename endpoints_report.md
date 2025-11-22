# Reporte de Pruebas de Endpoints

## Resumen
Se han probado los endpoints desplegados para los servicios `service-users`, `service-products` y `service-clientes`.

**Estado General:**
- ✅ **service-users**: Autenticación (Registro/Login) funciona correctamente.
- ✅ **service-products**: Listado y consulta de productos funciona correctamente.
- ❌ **service-clientes**: Creación de pedidos falla por error de configuración en AWS (Variables de Entorno).
- ❌ **service-users (Perfil)**: Consulta de perfil (`/users/me`) falla por error interno (posiblemente relacionado con la misma configuración).

## Detalles de Endpoints

### 1. Service Users
**Base URL:** `https://wp4cigovo1.execute-api.us-east-1.amazonaws.com`

#### POST /users/register
- **Estado:** ✅ Funciona (201 Created)
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
    "message": "Usuario registrado",
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
- **Causa Probable:** La función Lambda intenta invocar al validador de tokens usando el nombre corto `ValidarUserTokenAcceso` definido en la variable de entorno `TOKEN_VALIDATOR_FUNCTION`. Al no usar el ARN completo o el nombre físico del recurso, la invocación falla.

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
- **Response:** Lista de productos (ver JSON completo en respuesta).

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
- **Causa Identificada:** El servicio `service-clientes` intenta validar el token invocando a la función Lambda `ValidarUserTokenAcceso` que reside en `service-users`. La variable de entorno `TOKEN_VALIDATOR_FUNCTION` tiene el valor `ValidarUserTokenAcceso`, pero al estar en otro stack/servicio, AWS no puede resolver este nombre. Se requiere el ARN completo de la función para la invocación entre servicios.

## Recomendaciones de Corrección
1. **Actualizar `serverless.yml` en `users` y `clientes`:**
   - Asegurar que `TOKEN_VALIDATOR_FUNCTION` contenga el ARN completo de la función validadora o el nombre físico correcto (`service-users-dev-ValidarUserTokenAcceso`).
   - En `service-clientes`, se debe referenciar el output del stack de usuarios o construir el nombre predeciblemente.

2. **Corregir Case Sensitivity en Roles:**
   - `register_user.py` guarda roles como "Cliente" (Capitalized).
   - `pedido_create.py` valida `rol != "cliente"` (Lowercase). Esto causará fallos de autorización incluso si se arregla la invocación del validador. Se debe unificar el criterio (usar `.lower()` o constantes).

3. **Hashing de Contraseñas:**
   - Los datos poblados inicialmente en `usuarios.json` tienen contraseñas en texto plano, pero el login espera hashes. Estos usuarios iniciales no pueden hacer login. Solo los usuarios nuevos registrados vía API funcionan.
