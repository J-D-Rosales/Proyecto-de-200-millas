# 📊 Analytics - 200 Millas

Sistema de analytics usando AWS Glue, Athena y S3 para análisis de datos de pedidos.

## Arquitectura

```
DynamoDB Tables
    ↓
Lambda (Export)
    ↓
S3 Bucket (bucket-analytic)
    ↓
Glue Crawlers
    ↓
Glue Database
    ↓
Athena Queries
    ↓
API Endpoints
```

## Componentes

### 1. Exportación de Datos
- **Función**: `ExportDynamoDBToS3`
- **Descripción**: Exporta datos de DynamoDB a S3 en formato JSON
- **Tablas**: `Millas-Pedidos`, `Millas-Historial-Estados`
- **Destino**: `s3://bucket-analytic-{account-id}/`

### 2. Glue Crawlers
- **millas-pedidos-crawler**: Escanea `s3://bucket-analytic-{account-id}/pedidos/`
- **millas-historial-crawler**: Escanea `s3://bucket-analytic-{account-id}/historial_estados/`
- **Database**: `millas_analytics_db`

### 3. Queries de Athena

#### Query 1: Total de Pedidos por Local
- **Endpoint**: `GET /analytics/pedidos-por-local`
- **Descripción**: Cuenta el total de pedidos agrupados por local
- **Tabla**: `pedidos`

**Ejemplo de respuesta:**
```json
{
  "query": "Total de pedidos por local",
  "data": [
    {
      "local_id": "LOCAL-001",
      "total_pedidos": 150
    },
    {
      "local_id": "LOCAL-002",
      "total_pedidos": 120
    }
  ]
}
```

#### Query 2: Ganancias Totales por Local
- **Endpoint**: `GET /analytics/ganancias-por-local`
- **Descripción**: Calcula ganancias totales y promedio por local
- **Tabla**: `pedidos`

**Ejemplo de respuesta:**
```json
{
  "query": "Ganancias totales por local",
  "data": [
    {
      "local_id": "LOCAL-001",
      "total_pedidos": 150,
      "ganancias_totales": 4500.50,
      "ganancia_promedio": 30.00
    }
  ]
}
```

#### Query 3: Tiempo Total de Pedido
- **Endpoint**: `GET /analytics/tiempo-pedido`
- **Descripción**: Calcula el tiempo desde "procesando" hasta "recibido"
- **Tabla**: `historial_estados`

**Ejemplo de respuesta:**
```json
{
  "query": "Tiempo total de pedido (procesado -> recibido)",
  "data": [
    {
      "pedido_id": "abc-123",
      "inicio": "2024-11-23T10:00:00",
      "fin": "2024-11-23T11:30:00",
      "tiempo_total_minutos": 90,
      "tiempo_total_horas": 1
    }
  ]
}
```

#### Query 4: Promedio de Tiempo por Estado
- **Endpoint**: `GET /analytics/promedio-por-estado`
- **Descripción**: Calcula el tiempo promedio que los pedidos pasan en cada estado
- **Tabla**: `historial_estados`

**Ejemplo de respuesta:**
```json
{
  "query": "Promedio de tiempo por estado",
  "data": [
    {
      "estado": "procesando",
      "total_pedidos": 100,
      "tiempo_promedio_minutos": 15.5,
      "tiempo_minimo_minutos": 5,
      "tiempo_maximo_minutos": 30,
      "desviacion_estandar": 5.2
    }
  ]
}
```

## Despliegue

### Automático (con setup_backend.sh)
```bash
./setup_backend.sh
# Seleccionar opción 1 (Desplegar todo)
```

### Manual
```bash
cd analytics
bash setup_analytics.sh
```

## Uso

### 1. Exportar Datos

#### Opción A: Mediante API (Recomendado)
```bash
# Usando curl
curl -X POST https://your-api-id.execute-api.us-east-1.amazonaws.com/analytics/export

# Usando Postman
POST https://your-api-id.execute-api.us-east-1.amazonaws.com/analytics/export
```

**Respuesta:**
```json
{
  "message": "Exportación completada exitosamente",
  "timestamp": "2024-11-23T10:30:00",
  "duration_seconds": 12.5,
  "exports": {
    "pedidos": {
      "s3_key": "pedidos/data_20241123_103000.json",
      "total_items": 150,
      "crawler_started": true
    },
    "historial_estados": {
      "s3_key": "historial_estados/data_20241123_103000.json",
      "total_items": 450,
      "crawler_started": true
    }
  },
  "next_steps": [
    "Los crawlers están procesando los datos (1-2 minutos)",
    "Las tablas estarán disponibles en Glue Database: millas_analytics_db",
    "Puedes consultar los endpoints de analytics después"
  ]
}
```

#### Opción B: Mediante AWS CLI
```bash
aws lambda invoke \
  --function-name service-analytics-dev-ExportDynamoDBToS3 \
  --region us-east-1 \
  /tmp/response.json

cat /tmp/response.json
```

#### Opción C: Automática (Programada)
Para habilitar la exportación automática diaria a las 2 AM:

1. Editar `analytics/serverless.yml`
2. Cambiar `enabled: false` a `enabled: true` en el schedule
3. Redesplegar: `cd analytics && serverless deploy`

```yaml
- schedule:
    rate: cron(0 2 * * ? *)
    enabled: true  # ← Cambiar a true
```

### 2. Ejecutar Crawlers Manualmente
```bash
# Crawler de pedidos
aws glue start-crawler --name millas-pedidos-crawler --region us-east-1

# Crawler de historial
aws glue start-crawler --name millas-historial-crawler --region us-east-1
```

### 3. Verificar Tablas en Glue
```bash
aws glue get-tables \
  --database-name millas_analytics_db \
  --region us-east-1
```

### 4. Consultar Endpoints

**Todos los endpoints ahora son POST y aceptan `local_id` opcional en el body:**

```bash
# Total de pedidos por local (todos los locales)
curl -X POST https://your-api-id.execute-api.us-east-1.amazonaws.com/analytics/pedidos-por-local

# Total de pedidos para un local específico
curl -X POST https://your-api-id.execute-api.us-east-1.amazonaws.com/analytics/pedidos-por-local \
  -H "Content-Type: application/json" \
  -d '{"local_id": "LOCAL-001"}'

# Ganancias por local (todos)
curl -X POST https://your-api-id.execute-api.us-east-1.amazonaws.com/analytics/ganancias-por-local \
  -H "Content-Type: application/json" \
  -d '{}'

# Ganancias para un local específico
curl -X POST https://your-api-id.execute-api.us-east-1.amazonaws.com/analytics/ganancias-por-local \
  -H "Content-Type: application/json" \
  -d '{"local_id": "LOCAL-001"}'

# Tiempo de pedido por local (agregado por local)
curl -X POST https://your-api-id.execute-api.us-east-1.amazonaws.com/analytics/tiempo-pedido \
  -H "Content-Type: application/json" \
  -d '{}'

# Tiempo de pedido para un local específico (detalle por pedido)
curl -X POST https://your-api-id.execute-api.us-east-1.amazonaws.com/analytics/tiempo-pedido \
  -H "Content-Type: application/json" \
  -d '{"local_id": "LOCAL-001"}'

# Promedio por estado (todos)
curl -X POST https://your-api-id.execute-api.us-east-1.amazonaws.com/analytics/promedio-por-estado \
  -H "Content-Type: application/json" \
  -d '{}'

# Promedio por estado para un local específico
curl -X POST https://your-api-id.execute-api.us-east-1.amazonaws.com/analytics/promedio-por-estado \
  -H "Content-Type: application/json" \
  -d '{"local_id": "LOCAL-001"}'
```

## Estructura de Archivos

```
analytics/
├── serverless.yml                      # Configuración de Serverless
├── export_to_s3.py                     # Exporta DynamoDB a S3
├── query_pedidos_por_local.py          # Query 1
├── query_ganancias_por_local.py        # Query 2
├── query_tiempo_pedido.py              # Query 3
├── query_promedio_por_estado.py        # Query 4
├── setup_analytics.sh                  # Script de setup
└── README.md                           # Este archivo
```

## Recursos Creados

### S3 Buckets
- `bucket-analytic-{account-id}` - Almacena datos exportados
- `athena-results-{account-id}` - Almacena resultados de Athena

### Glue
- Database: `millas_analytics_db`
- Crawlers: `millas-pedidos-crawler`, `millas-historial-crawler`
- Tables: `pedidos`, `historial_estados`

### Athena
- Workgroup: `millas-analytics-workgroup`

### Lambda Functions
- `service-analytics-dev-ExportDynamoDBToS3`
- `service-analytics-dev-TotalPedidosPorLocal`
- `service-analytics-dev-GananciasPorLocal`
- `service-analytics-dev-TiempoPedido`
- `service-analytics-dev-PromedioPedidosPorEstado`

## Troubleshooting

### Error: "Table not found"
- Ejecutar los crawlers manualmente
- Esperar 1-2 minutos para que terminen
- Verificar que las tablas existan en Glue

### Error: "No data"
- Verificar que hay datos en DynamoDB
- Ejecutar la exportación manualmente
- Verificar que los archivos JSON estén en S3

### Error: "Query timeout"
- Aumentar el timeout en las funciones Lambda
- Verificar que Athena tenga permisos correctos

## Notas

- La exportación se puede programar con EventBridge (actualmente deshabilitado)
- Los crawlers detectan automáticamente el esquema de los datos
- Athena cobra por datos escaneados (~$5 por TB)
- Los resultados se cachean en S3 para consultas repetidas


---

## 🔧 Solución de Problemas

### ❌ Error: "COLUMN_NOT_FOUND" o datos aparecen como arrays

**Síntoma:** Al ejecutar queries en Athena ves errores como:
```
COLUMN_NOT_FOUND: line 5:19: Column 'local_id' cannot be resolved
```

O cuando haces `SELECT * FROM pedidos` solo ves 6 filas con arrays en lugar de 40 filas individuales.

**Causa:** Los datos se exportaron en formato JSON array en lugar de JSON Lines (JSONL). Athena necesita un objeto JSON por línea.

**Solución:**
```bash
cd analytics
bash fix_and_reexport.sh
```

Este script:
1. ✅ Limpia los datos antiguos en S3
2. ✅ Recrea las tablas de Glue con el schema correcto
3. ✅ Re-exporta los datos en formato JSON Lines (un objeto por línea)
4. ✅ Espera a que los crawlers procesen los datos

**Tiempo estimado:** 2-3 minutos

---

### ❌ Error: "No output location provided"

**Síntoma:** Al hacer preview de una tabla en Athena ves:
```
No output location provided. You did not provide an output location for your query results.
```

**Causa:** Athena no tiene configurado dónde guardar los resultados de las queries.

**Solución automática:**
```bash
cd analytics
bash configure_athena.sh
```

**Solución manual:**
1. Ve a la consola de Athena
2. Click en "Settings" (arriba a la derecha)
3. En "Query result location", ingresa: `s3://athena-results-{tu-account-id}/results/`
4. Click "Save"

---

## 📋 Schema de Tablas

### Tabla: `pedidos`
```sql
local_id              STRING
pedido_id             STRING
tenant_id_usuario     STRING
productos             ARRAY<STRUCT<producto_id:STRING, cantidad:DOUBLE>>
costo                 DOUBLE
direccion             STRING
estado                STRING
created_at            STRING
```

### Tabla: `historial_estados`
```sql
estado_id             STRING
pedido_id             STRING
estado                STRING
hora_inicio           STRING
hora_fin              STRING
empleado              STRING
```

---

## 🧪 Verificación

### 1. Verificar datos en S3
```bash
aws s3 ls s3://bucket-analytic-{account-id}/pedidos/ --recursive
aws s3 ls s3://bucket-analytic-{account-id}/historial_estados/ --recursive
```

### 2. Verificar tablas en Glue
```bash
aws glue get-tables --database-name millas_analytics_db --region us-east-1
```

### 3. Probar query en Athena
```sql
SELECT COUNT(*) as total FROM pedidos;
SELECT local_id, COUNT(*) as total FROM pedidos GROUP BY local_id;
```

### 4. Probar endpoints
```bash
# Obtener API Gateway URL
sls info

# Probar endpoints
curl https://YOUR-API-ID.execute-api.us-east-1.amazonaws.com/analytics/pedidos-por-local
curl https://YOUR-API-ID.execute-api.us-east-1.amazonaws.com/analytics/ganancias-por-local
```
