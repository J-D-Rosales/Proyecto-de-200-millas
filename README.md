# 🚀 200 Millas - Sistema de Delivery Serverless

Sistema completo de gestión de pedidos con arquitectura serverless en AWS, diseñado para restaurantes con múltiples locales.

## 📋 Tabla de Contenidos

- [Arquitectura](#-arquitectura)
- [Servicios](#-servicios)
- [Instalación y Despliegue](#-instalación-y-despliegue)
- [Flujo de Pedidos](#-flujo-de-pedidos)
- [API Endpoints](#-api-endpoints)
- [Analytics](#-analytics)
- [Variables de Entorno](#-variables-de-entorno)

## 🏗 Arquitectura

### Servicios AWS Utilizados

- **DynamoDB**: Base de datos NoSQL para almacenamiento de datos
- **Lambda**: Funciones serverless para lógica de negocio
- **API Gateway**: Endpoints HTTP para los microservicios
- **Step Functions**: Orquestación del flujo de estados de pedidos
- **EventBridge**: Bus de eventos para comunicación entre servicios
- **SQS**: Colas para procesamiento asíncrono (Cocina y Delivery)
- **S3**: Almacenamiento de imágenes de productos y datos de analytics
- **Glue + Athena**: Catálogo de datos y consultas SQL para analytics

### Tablas DynamoDB

| Tabla | Descripción | Partition Key | Sort Key |
|-------|-------------|---------------|----------|
| `Millas-Usuarios` | Usuarios del sistema | `correo` | - |
| `Millas-Empleados` | Empleados por local | `local_id` | `dni` |
| `Millas-Locales` | Información de locales | `local_id` | - |
| `Millas-Productos` | Catálogo de productos | `local_id` | `producto_id` |
| `Millas-Pedidos` | Pedidos activos | `local_id` | `pedido_id` |
| `Millas-Historial-Estados` | Historial de cambios de estado | `pedido_id` | `timestamp` |
| `Millas-Tokens-Usuarios` | Tokens de autenticación | `token` | - |

## 🔧 Servicios

### 1. Servicio de Usuarios (`users/`)
Gestión de usuarios y autenticación.

**Endpoints:**
- `POST /users/register` - Registrar usuario (Cliente, Gerente, Admin)
- `POST /users/login` - Iniciar sesión (retorna JWT)
- `GET /users/me` - Obtener perfil del usuario autenticado
- `PUT /users/me` - Actualizar perfil
- `DELETE /users/me` - Eliminar cuenta
- `POST /users/password/change` - Cambiar contraseña
- `POST /users/employee` - Crear empleado (Admin/Gerente)
- `PUT /users/employee` - Actualizar empleado
- `DELETE /users/employee` - Eliminar empleado
- `POST /users/employees/list` - Listar empleados de un local

### 2. Servicio de Productos (`products/`)
Gestión del catálogo de productos por local.

**Endpoints:**
- `POST /productos/create` - Crear producto
- `PUT /productos/update` - Actualizar producto
- `POST /productos/id` - Obtener producto por ID
- `POST /productos/list` - Listar productos de un local (con paginación)
- `DELETE /productos/delete` - Eliminar producto

### 3. Servicio de Clientes (`clientes/`)
Gestión de pedidos desde la perspectiva del cliente.

**Endpoints:**
- `POST /pedido/create` - Crear nuevo pedido
- `GET /pedido/status` - Consultar estado del pedido
- `POST /pedido/confirmar` - Confirmar recepción del pedido

### 4. Servicio de Empleados (`servicio-empleados/`)
Endpoints para que empleados actualicen el estado de los pedidos.

**Endpoints:**
- `POST /empleados/cocina/iniciar` - Cocina inicia preparación
- `POST /empleados/cocina/completar` - Cocina completa preparación
- `POST /empleados/empaque/completar` - Empaquetado completo
- `POST /empleados/delivery/iniciar` - Delivery inicia entrega
- `POST /empleados/delivery/entregar` - Delivery entrega pedido

### 5. Step Functions (`stepFunction/`)
Orquestación del flujo de estados de pedidos con manejo de errores y timeouts.

**Estados:**
1. `procesando` - Pedido creado, esperando cocina
2. `en_preparacion` - Cocina preparando
3. `cocina_completa` - Cocina terminó
4. `empaquetando` - Siendo empaquetado
5. `pedido_en_camino` - En camino con delivery
6. `entrega_delivery` - Entregado al cliente
7. `recibido` - Cliente confirmó recepción ✅
8. `fallido` - Pedido falló (timeout o rechazos) ❌

**Características:**
- Timeout de 15 minutos por estado
- Máximo 3 rechazos antes de marcar como fallido
- Publicación de eventos a EventBridge
- Registro completo en tabla de historial

### 6. Servicio de Analytics (`analytics/`)
Consultas y reportes sobre pedidos y rendimiento.

**Endpoints:**
- `POST /analytics/export` - Exportar datos de DynamoDB a S3
- `POST /analytics/pedidos-por-local` - Total de pedidos por local
- `POST /analytics/ganancias-por-local` - Ganancias totales por local
- `POST /analytics/tiempo-pedido` - Tiempo de procesamiento de pedidos
- `POST /analytics/promedio-por-estado` - Tiempo promedio por estado

## 🚀 Instalación y Despliegue

### Requisitos Previos

1. **AWS CLI** configurado con credenciales
   ```bash
   aws configure
   ```

2. **Serverless Framework**
   ```bash
   npm install -g serverless
   ```

3. **Python 3.9+** y **pip3**

4. **Node.js 18+** (para Serverless Framework)

### Configuración

1. Clonar el repositorio y copiar variables de entorno:
   ```bash
   cp .env.example .env
   ```

2. Editar `.env` con tus valores:
   ```bash
   AWS_ACCOUNT_ID=123456789012
   AWS_REGION=us-east-1
   ORG_NAME=millas

   TABLE_USUARIOS=Millas-Usuarios
   TABLE_EMPLEADOS=Millas-Empleados
   TABLE_LOCALES=Millas-Locales
   TABLE_PRODUCTOS=Millas-Productos
   TABLE_PEDIDOS=Millas-Pedidos
   TABLE_HISTORIAL_ESTADOS=Millas-Historial-Estados
   TABLE_TOKENS_USUARIOS=Millas-Tokens-Usuarios

   S3_BUCKET_NAME=bucket-imagenes-productos-123456789012
   VALIDAR_TOKEN_LAMBDA_NAME=service-users-dev-ValidarToken
   ```

### Despliegue Completo

Ejecutar el script de setup:

```bash
bash setup_backend.sh
```

**Opciones del menú:**

1. **🏗️ Desplegar todo** - Crea infraestructura y despliega todos los servicios
   - Crea tablas DynamoDB
   - Crea buckets S3
   - Genera y pobla datos de prueba
   - Despliega todos los microservicios
   - Configura Step Functions y EventBridge
   - Despliega servicio de analytics
   - **Tiempo estimado:** 5-7 minutos

2. **🗑️ Eliminar todo** - Elimina todos los recursos
   - Elimina microservicios
   - Elimina tablas DynamoDB
   - Vacía y elimina buckets S3

3. **📊 Solo infraestructura** - Crea tablas y pobla datos

4. **🚀 Solo microservicios** - Despliega servicios sin tocar infraestructura

5. **❌ Salir**

### Verificación del Despliegue

Después del despliegue, verifica que todo esté funcionando:

```bash
# Ver tablas creadas
aws dynamodb list-tables

# Ver funciones Lambda
aws lambda list-functions --query 'Functions[?contains(FunctionName, `millas`)].FunctionName'

# Ver APIs desplegadas
aws apigatewayv2 get-apis --query 'Items[].Name'
```

## 🔄 Flujo de Pedidos

### Diagrama de Estados

```
Cliente crea pedido
    ↓
[procesando] ← Esperando cocina
    ↓
Cocina acepta → [en_preparacion]
    ↓
Cocina completa → [cocina_completa]
    ↓
Empaquetado → [empaquetando]
    ↓
Delivery acepta → [pedido_en_camino]
    ↓
Delivery entrega → [entrega_delivery]
    ↓
Cliente confirma → [recibido] ✅
```

### Manejo de Errores

**Timeout (15 minutos por estado):**
- Si un pedido no avanza en 15 minutos → Estado: `fallido`
- Se publica evento `PedidoFallido` a EventBridge

**Rechazos (máximo 3):**
- Si cocina o delivery rechazan 3 veces → Estado: `fallido`
- Se publica evento `PedidoFallido` a EventBridge

## 📡 API Endpoints

### Autenticación

Todos los endpoints protegidos requieren header:
```
Authorization: Bearer <token>
```

### Ejemplo: Crear Pedido

```bash
curl -X POST https://API_URL/pedido/create \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "tenant_id": "TENANT-001",
    "local_id": "LOCAL-001",
    "usuario_correo": "cliente@example.com",
    "direccion": "Av. Principal 123",
    "costo": 45.50,
    "estado": "procesando",
    "productos": [
      {
        "producto_id": "uuid-producto",
        "nombre": "Ceviche Clásico",
        "cantidad": 2,
        "precio": 22.75
      }
    ]
  }'
```

### Ejemplo: Consultar Estado

```bash
curl -X GET "https://API_URL/pedido/status?tenant_id=TENANT-001&pedido_id=uuid-pedido" \
  -H "Authorization: Bearer <token>"
```

### Ejemplo: Empleado Actualiza Estado

```bash
# Cocina inicia preparación
curl -X POST https://API_URL/empleados/cocina/iniciar \
  -H "Content-Type: application/json" \
  -d '{
    "order_id": "uuid-pedido",
    "empleado_id": "EMP-001"
  }'
```

## 📊 Analytics

### Configuración

El servicio de analytics utiliza:
- **S3** para almacenar datos exportados
- **Glue** para catalogar datos
- **Athena** para consultas SQL

### Exportar Datos

```bash
# Exportar datos de DynamoDB a S3
curl -X POST https://API_URL/analytics/export
```

Esto exporta:
- Tabla `Millas-Pedidos` → `s3://bucket-analytic-{account}/pedidos/`
- Tabla `Millas-Historial-Estados` → `s3://bucket-analytic-{account}/historial_estados/`

### Consultas Disponibles

```bash
# Total de pedidos por local
curl -X POST https://API_URL/analytics/pedidos-por-local

# Ganancias por local
curl -X POST https://API_URL/analytics/ganancias-por-local

# Tiempo de procesamiento (paginado)
curl -X POST https://API_URL/analytics/tiempo-pedido \
  -d '{"page": 1, "page_size": 10}'

# Tiempo promedio por estado
curl -X POST https://API_URL/analytics/promedio-por-estado
```

### Ejecutar Glue Crawlers

Después de exportar datos, ejecuta los crawlers para actualizar el catálogo:

```bash
aws glue start-crawler --name millas-pedidos-crawler
aws glue start-crawler --name millas-historial-crawler
```

## 🔐 Variables de Entorno

### Requeridas

| Variable | Descripción | Ejemplo |
|----------|-------------|---------|
| `AWS_ACCOUNT_ID` | ID de cuenta AWS | `123456789012` |
| `AWS_REGION` | Región de AWS | `us-east-1` |
| `ORG_NAME` | Nombre de organización | `millas` |
| `TABLE_USUARIOS` | Nombre tabla usuarios | `Millas-Usuarios` |
| `TABLE_EMPLEADOS` | Nombre tabla empleados | `Millas-Empleados` |
| `TABLE_LOCALES` | Nombre tabla locales | `Millas-Locales` |
| `TABLE_PRODUCTOS` | Nombre tabla productos | `Millas-Productos` |
| `TABLE_PEDIDOS` | Nombre tabla pedidos | `Millas-Pedidos` |
| `TABLE_HISTORIAL_ESTADOS` | Nombre tabla historial | `Millas-Historial-Estados` |
| `TABLE_TOKENS_USUARIOS` | Nombre tabla tokens | `Millas-Tokens-Usuarios` |
| `S3_BUCKET_NAME` | Bucket de imágenes | `bucket-imagenes-productos-{account}` |
| `VALIDAR_TOKEN_LAMBDA_NAME` | Nombre Lambda validación | `service-users-dev-ValidarToken` |

## 🧪 Datos de Prueba

El script de setup genera automáticamente:
- 3 locales de ejemplo
- 50+ productos por local
- 10 usuarios de prueba
- 15 empleados (cocineros, despachadores, repartidores)

Los datos se generan en `DataGenerator/example-data/` y se cargan automáticamente.

## 🛠 Comandos Útiles

### Ver logs de una función

```bash
aws logs tail /aws/lambda/service-orders-200-millas-dev-cambiarEstado --follow
```

### Ver estado de un pedido

```bash
aws dynamodb get-item \
  --table-name Millas-Pedidos \
  --key '{"local_id":{"S":"LOCAL-001"},"pedido_id":{"S":"<pedido_id>"}}'
```

### Ver historial completo de un pedido

```bash
aws dynamodb query \
  --table-name Millas-Historial-Estados \
  --key-condition-expression "pedido_id = :pid" \
  --expression-attribute-values '{":pid":{"S":"<pedido_id>"}}'
```

### Listar Step Functions

```bash
aws stepfunctions list-state-machines
```

## 📚 Documentación Adicional

- [Postman Collection](./200%20Millas%20-%20API%20Collection%20COMPLETA.postman_collection.json) - Colección completa de endpoints
- [Analytics README](./analytics/README.md) - Documentación detallada de analytics
- [Servicio Empleados README](./servicio-empleados/README.md) - Endpoints de empleados
- [Step Functions Flow](./stepFunction/FLUJO_CON_ERRORES.md) - Diagrama de flujo con errores

## 🤝 Contribuir

1. Fork el proyecto
2. Crea una rama para tu feature (`git checkout -b feature/AmazingFeature`)
3. Commit tus cambios (`git commit -m 'Add some AmazingFeature'`)
4. Push a la rama (`git push origin feature/AmazingFeature`)
5. Abre un Pull Request

## 📄 Licencia

Este proyecto es privado y confidencial.

---

**Proyecto:** 200 Millas - Sistema de Delivery Serverless  
**Última actualización:** Noviembre 2024
