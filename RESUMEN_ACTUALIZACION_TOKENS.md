# Resumen de Actualización de Validación de Tokens

## Archivos Actualizados

### ✅ Products (Completado)
- `products/product_create.py` - Validación de token + rol Admin/Gerente
- `products/product_update.py` - Validación de token + rol Admin/Gerente
- `products/product_delete.py` - Validación de token + rol Admin/Gerente

### ✅ Clientes (Completado)
- `clientes/pedido_create.py` - Validación de token
- `clientes/estado_pedido.py` - Validación de token
- `clientes/confirmar_recepcion.py` - Validación de token

### ✅ Users (Completado)
- `users/login_user.py` - Genera token en formato correcto
- `users/mi_usuario.py` - Validación de token
- `users/cambiar_contrasena.py` - Validación de token

### ⚠️ Users (Pendientes - Tienen código antiguo pero pueden funcionar)
- `users/modificar_usuario.py`
- `users/eliminar_usuario.py`
- `users/register_empleado.py`
- `users/actualizar_empleado.py`
- `users/eliminar_empleado.py`
- `users/listar_empleados.py`

## Patrón de Validación Implementado

Todos los archivos ahora siguen el mismo patrón:

```python
from datetime import datetime

TOKENS_TABLE = os.environ.get("TOKENS_TABLE_USERS", "TOKENS_TABLE_USERS")
tokens_table = dynamodb.Table(TOKENS_TABLE)

def _get_token(event):
    """Extrae el token del header Authorization"""
    headers = event.get("headers") or {}
    for key, value in headers.items():
        if key.lower() == "authorization":
            token = value.strip()
            if token.lower().startswith("bearer "):
                return token.split(" ", 1)[1].strip()
            return token
    return None

def _validate_token(token):
    """Valida el token consultando la tabla de tokens"""
    if not token:
        return False, "Token requerido", None, None
    
    try:
        response = tokens_table.get_item(Key={'token': token})
        
        if 'Item' not in response:
            return False, "Token no existe", None, None
        
        item = response['Item']
        expires_str = item.get('expires')
        
        if not expires_str:
            return False, "Token sin fecha de expiración", None, None
        
        # Parsear fecha (soporta ISO y formato simple)
        try:
            if 'T' in expires_str:
                if '.' in expires_str:
                    expires_str = expires_str.split('.')[0]
                expires_dt = datetime.strptime(expires_str, '%Y-%m-%dT%H:%M:%S')
            else:
                expires_dt = datetime.strptime(expires_str, '%Y-%m-%d %H:%M:%S')
        except ValueError:
            return False, "Formato de fecha inválido", None, None
        
        now = datetime.now()
        if now > expires_dt:
            return False, "Token expirado", None, None
        
        correo = item.get('user_id') or item.get('correo')
        rol = item.get('rol') or item.get('role') or "Cliente"
        
        return True, None, correo, rol
        
    except Exception as e:
        return False, f"Error al validar token: {str(e)}", None, None

# En el handler:
def lambda_handler(event, context):
    token = _get_token(event)
    valido, error, correo, rol = _validate_token(token)
    if not valido:
        return _resp(403, {"error": error or "Token inválido"})
    
    # Continuar con la lógica...
```

## Formato del Token en DynamoDB

Tabla: `Millas-Tokens-Usuarios`

```json
{
  "token": "c9f454d1-9fa4-43a6-9b4c-3197c54df482",
  "user_id": "admin@200millas.com",
  "rol": "Admin",
  "expires": "2024-11-23 03:28:53"
}
```

## Formatos de Fecha Soportados

El código ahora acepta ambos formatos:

1. **Formato Simple** (generado por login):
   ```
   2024-11-23 03:28:53
   ```

2. **Formato ISO 8601**:
   ```
   2025-11-23T02:28:53.290513
   2025-11-23T02:28:53
   ```

## Cómo Enviar el Token

En Postman o cualquier cliente HTTP:

**Header:**
```
Authorization: c9f454d1-9fa4-43a6-9b4c-3197c54df482
```

O con Bearer:
```
Authorization: Bearer c9f454d1-9fa4-43a6-9b4c-3197c54df482
```

## Despliegue

Para aplicar los cambios:

```bash
# Products
cd products
serverless deploy

# Clientes
cd ../clientes
serverless deploy

# Users
cd ../users
serverless deploy
```

## Verificación

1. **Hacer login** para obtener un token:
   ```
   POST /users/login
   Body: {
     "correo": "admin@200millas.com",
     "contrasena": "admin123"
   }
   ```

2. **Usar el token** en los siguientes requests:
   ```
   Authorization: <token-recibido>
   ```

3. **Verificar en DynamoDB** que el token se guardó correctamente en `Millas-Tokens-Usuarios`

## Errores Comunes y Soluciones

| Error | Causa | Solución |
|-------|-------|----------|
| "Token requerido" | No se envió el header | Agregar header `Authorization` |
| "Token no existe" | Token incorrecto o no en DB | Hacer login nuevamente |
| "Token expirado" | Pasaron más de 60 minutos | Hacer login nuevamente |
| "Formato de fecha inválido" | Fecha en formato no soportado | Verificar formato en DB |
| "Permiso denegado" | Rol incorrecto | Verificar campo `rol` en DB |
