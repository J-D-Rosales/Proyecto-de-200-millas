# Solución al Problema de CORS en Analytics

## Problema Detectado

```
Access to fetch at 'https://9chtp1assj.execute-api.us-east-1.amazonaws.com/analytics/pedidos-por-local' 
from origin 'http://0.0.0.0:8080' has been blocked by CORS policy: 
Response to preflight request doesn't pass access control check: 
No 'Access-Control-Allow-Origin' header is present on the requested resource.
```

## ¿Qué es CORS?

CORS (Cross-Origin Resource Sharing) es una política de seguridad del navegador que bloquea peticiones HTTP desde un dominio diferente al del servidor.

Cuando la página web (http://0.0.0.0:8080) intenta hacer una petición POST a la API de AWS (https://9chtp1assj.execute-api.us-east-1.amazonaws.com), el navegador primero envía una petición OPTIONS (preflight) para verificar si el servidor permite esta petición cross-origin.

## Causa del Problema

El endpoint de analytics está configurado para:
```
access-control-allow-methods: POST,OPTIONS
```

Pero falta:
1. **GET** en los métodos permitidos
2. O el backend no responde correctamente a las peticiones OPTIONS

## Solución 1: Configurar CORS en el Backend (RECOMENDADO)

Necesitas modificar el `serverless.yml` del servicio de analytics:

```yaml
provider:
  name: aws
  runtime: python3.13
  region: us-east-1
  httpApi:
    cors:
      allowedOrigins:
        - '*'  # O especifica tu dominio: 'http://localhost:8080'
      allowedHeaders:
        - Content-Type
        - Authorization
        - X-Amz-Date
        - X-Api-Key
        - X-Amz-Security-Token
      allowedMethods:
        - GET
        - POST
        - OPTIONS
      maxAge: 300
```

### O en cada Lambda:

Agregar headers CORS en las respuestas de cada función:

```python
def lambda_handler(event, context):
    # Tu código aquí
    result = {...}
    
    return {
        'statusCode': 200,
        'headers': {
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Headers': 'Content-Type,Authorization',
            'Access-Control-Allow-Methods': 'GET,POST,OPTIONS'
        },
        'body': json.dumps(result)
    }
```

## Solución 2: Usar GET en lugar de POST

Si cambias los endpoints de analytics para aceptar GET con query parameters:

**Antes (POST con body):**
```javascript
fetch('https://api.com/analytics/pedidos-por-local', {
    method: 'POST',
    body: JSON.stringify({ local_id: 'LOCAL-001' })
})
```

**Después (GET con query params - evita preflight):**
```javascript
fetch('https://api.com/analytics/pedidos-por-local?local_id=LOCAL-001')
```

Los GET requests no requieren preflight, entonces evitan el problema de CORS.

## Solución 3: Desplegar la Página en el Mismo Dominio

Si despliegas la página web en el mismo dominio que la API (por ejemplo, ambos en AWS), no habrá problema de CORS porque será same-origin.

## Solución Temporal (SOLO PARA DESARROLLO)

Instalar una extensión del navegador que deshabilite CORS:
- Chrome: "CORS Unblock" o "Allow CORS: Access-Control-Allow-Origin"
- Firefox: "CORS Everywhere"

⚠️ **ADVERTENCIA**: Esto solo funciona en tu navegador local y NO es una solución para producción.

## Comandos para Redesplegar Analytics

```bash
cd /ruta/al/proyecto/analytics
serverless deploy
```

O si usas serverless-compose:

```bash
cd /ruta/al/proyecto
serverless deploy --stage dev
```

## Verificar los Headers CORS

Puedes verificar si los headers están correctos con curl:

```bash
curl -X OPTIONS \
  https://9chtp1assj.execute-api.us-east-1.amazonaws.com/analytics/pedidos-por-local \
  -H "Origin: http://localhost:8080" \
  -H "Access-Control-Request-Method: POST" \
  -H "Access-Control-Request-Headers: Content-Type" \
  -v
```

Deberías ver en la respuesta:
```
Access-Control-Allow-Origin: *
Access-Control-Allow-Methods: GET,POST,OPTIONS
Access-Control-Allow-Headers: Content-Type,Authorization
```

## Estado Actual de la Aplicación

### ✅ Funcionando:
- Registro de usuarios
- Login
- Cerrar sesión
- Cambiar estado de pedidos (empleados)
- Consultar estado de pedidos

### ❌ Con Error de CORS:
- Analytics (pedidos-por-local)
- Analytics (ganancias-por-local)

### Solución Aplicada:
La página ahora muestra un mensaje claro cuando hay error de CORS y no rompe la aplicación.

## Recomendación Final

**Opción A - Rápida**: Modificar el serverless.yml de analytics para agregar CORS y redesplegar

**Opción B - Mejor**: Cambiar los endpoints de analytics para que acepten GET con query parameters (no requiere preflight)

**Opción C - Desplegar**: Subir la página web a S3 + CloudFront y usar el mismo dominio o configurar CORS correctamente
