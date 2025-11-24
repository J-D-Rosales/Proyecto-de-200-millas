# Guía de Pruebas - Step Functions Workflow

## 1. Despliegue Inicial

### Paso 1: Desplegar el servicio de Step Functions
```bash
cd stepFunction
serverless deploy
```

Esto desplegará:
- ✅ Todas las funciones Lambda
- ✅ Tabla DynamoDB `t_historial_estados`
- ✅ Colas SQS: `Cola_Cocina` y `Cola_Delivery`
- ✅ Reglas de EventBridge

### Paso 2: Crear el Step Functions en AWS Console

**IMPORTANTE:** AWS Academy no permite crear Step Functions mediante IaC, debes hacerlo manualmente.

1. Ve a **AWS Console** → **Step Functions**
2. Click en **"Create state machine"**
3. Selecciona **"Write your workflow in code"**
4. Copia y pega el contenido de `step_function_definition.json`
5. Nombre: `Millas` (o el que prefieras)
6. Click en **"Create"**

### Paso 3: Desplegar el servicio de empleados
```bash
cd ../servicio-empleados
serverless deploy
```

Guarda la URL del API Gateway que aparece en el output.

---

## 2. Visualización en AWS Console

### Opción A: Step Functions Console (RECOMENDADO)

1. **Ir a Step Functions:**
   - AWS Console → Step Functions → State machines
   - Click en tu state machine `Millas`

2. **Ver Ejecuciones:**
   - Tab **"Executions"** muestra todas las ejecuciones
   - Estados: Running, Succeeded, Failed, Timed out

3. **Ver Detalles de una Ejecución:**
   - Click en cualquier ejecución
   - Verás un **diagrama visual** del flujo
   - Los estados completados aparecen en **verde**
   - El estado actual aparece en **azul**
   - Los estados fallidos aparecen en **rojo**

4. **Inspeccionar Estado Individual:**
   - Click en cualquier estado del diagrama
   - Panel derecho muestra:
     - **Input:** Datos de entrada
     - **Output:** Datos de salida
     - **Exception:** Errores (si los hay)

### Opción B: CloudWatch Logs

1. **Logs de Lambda:**
   - AWS Console → CloudWatch → Log groups
   - Busca: `/aws/lambda/service-orders-200-millas-dev-{functionName}`
   - Cada Lambda tiene su propio log group

2. **Filtrar Logs por Order ID:**
   ```
   { $.order_id = "tu-order-id-aqui" }
   ```

### Opción C: DynamoDB

1. **Ver Historial de Estados:**
   - AWS Console → DynamoDB → Tables
   - Selecciona `t_historial_estados`
   - Click en **"Explore table items"**
   - Filtra por `id_pedido` para ver todos los estados de un pedido

---

## 3. Prueba del Flujo Completo

### Método 1: Usando EventBridge (Inicio Automático)

1. **Publicar evento CrearPedido:**
   ```bash
   aws events put-events --entries '[
     {
       "Source": "200millas.pedidos",
       "DetailType": "CrearPedido",
       "Detail": "{\"order_id\":\"test-order-001\",\"empleado_id\":\"EMP-001\",\"productos\":[{\"producto_id\":\"prod-123\",\"cantidad\":2}]}"
     }
   ]'
   ```

2. **Verificar en Step Functions:**
   - Ve a Step Functions Console
   - Deberías ver una nueva ejecución iniciada
   - El flujo estará en estado **"ProcesarPedido"** (verde)
   - Luego pasará a **"PedidoEnCocina"** (azul - esperando)

### Método 2: Inicio Manual desde Console

1. **Ir a Step Functions Console**
2. Click en tu state machine
3. Click en **"Start execution"**
4. Pega este JSON como input:
   ```json
   {
     "detail": {
       "order_id": "test-order-001",
       "empleado_id": "EMP-001",
       "productos": [
         {
           "producto_id": "085f51bb-d0b3-4871-b9ca-fd82fc657802",
           "local_id": "LOCAL-007",
           "cantidad": 2
         }
       ]
     }
   }
   ```
5. Click en **"Start execution"**

---

## 4. Avanzar el Flujo con API Endpoints

Una vez iniciado el flujo, usa los endpoints del servicio de empleados para avanzar:

### Paso 1: Cocina Inicia Preparación
```bash
curl -X POST https://alkbqjtbdi.execute-api.us-east-1.amazonaws.com/empleados/cocina/iniciar \
  -H "Content-Type: application/json" \
  -d '{
    "order_id": "test-order-001",
    "empleado_id": "EMP-COCINA-001"
  }'
```

**Verificar:** El flujo debe pasar de `ProcesarPedido` → `PedidoEnCocina`

### Paso 2: Cocina Completa
```bash
curl -X POST https://alkbqjtbdi.execute-api.us-east-1.amazonaws.com/empleados/cocina/completar \
  -H "Content-Type: application/json" \
  -d '{
    "order_id": "test-order-001",
    "empleado_id": "EMP-COCINA-001"
  }'
```

**Verificar:** El flujo debe pasar de `PedidoEnCocina` → `CocinaCompleta` → `Empaquetado`

### Paso 3: Empaquetado Completo
```bash
curl -X POST https://alkbqjtbdi.execute-api.us-east-1.amazonaws.com/empleados/empaque/completar \
  -H "Content-Type: application/json" \
  -d '{
    "order_id": "test-order-001",
    "empleado_id": "EMP-EMPAQUE-001"
  }'
```

**Verificar:** El flujo debe pasar de `Empaquetado` → `Delivery`

### Paso 4: Delivery Inicia
```bash
curl -X POST https://alkbqjtbdi.execute-api.us-east-1.amazonaws.com/empleados/delivery/iniciar \
  -H "Content-Type: application/json" \
  -d '{
    "order_id": "test-order-001",
    "empleado_id": "EMP-DELIVERY-001"
  }'
```

**Verificar:** El flujo debe pasar de `Empaquetado` → `Delivery`

### Paso 5: Delivery Entrega
```bash
curl -X POST https://alkbqjtbdi.execute-api.us-east-1.amazonaws.com/empleados/delivery/entregar \
  -H "Content-Type: application/json" \
  -d '{
    "order_id": "test-order-001",
    "empleado_id": "EMP-DELIVERY-001"
  }'
```

**Verificar:** El flujo debe pasar de `Delivery` → `Entregado`

### Paso 6: Cliente Confirma
```bash
curl -X POST https://alkbqjtbdi.execute-api.us-east-1.amazonaws.com/empleados/cliente/confirmar \
  -H "Content-Type: application/json" \
  -d '{
    "order_id": "test-order-001",
    "empleado_id": "CLIENTE"
  }'
```

**Verificar:** El flujo debe pasar de `Entregado` → `EntregaCompleta` (FINALIZADO ✅)

---

## 5. Verificación de Resultados

### En Step Functions Console:
- ✅ Estado final: **"Succeeded"** (verde)
- ✅ Todos los estados deben estar en verde
- ✅ Duración total del flujo

### En DynamoDB:
```bash
aws dynamodb query \
  --table-name t_historial_estados \
  --key-condition-expression "id_pedido = :oid" \
  --expression-attribute-values '{":oid":{"S":"test-order-001"}}'
```

Deberías ver registros para cada estado:
1. `procesando` (ProcesarPedido)
2. `cocinando` (PedidoEnCocina)
3. `cocinando` (CocinaCompleta)
4. `empacando` (Empaquetado)
5. `enviando` (Delivery)
6. `recibido` (Entregado)
7. `recibido` (EntregaCompleta)

### En CloudWatch Logs:
- Busca logs de cada Lambda
- Filtra por `order_id` para seguir el flujo completo

---

## 6. Prueba de Reintentos

### Simular Rechazo en Cocina:

1. **Modificar temporalmente** `cambiar_estado.py` para enviar status RECHAZADO:
   ```python
   output_payload = {
       "order_id": order_id,
       "event": detail_type,
       "status": "RECHAZADO",  # Cambiar a RECHAZADO
       "retry_count": retry_count,
       "empleado_id": detail.get('empleado_id', 'UNKNOWN'),
       "details": detail
   }
   ```

2. **Redesplegar:**
   ```bash
   cd stepFunction
   serverless deploy function -f cambiarEstado
   ```

3. **Ejecutar flujo** y llamar endpoint de cocina

4. **Verificar en Step Functions:**
   - Debe pasar a `ReintentarCocina`
   - Luego volver a `PedidoEnCocina`
   - Máximo 3 reintentos antes de `CocinaFallida`

---

## 7. Diagrama Visual en AWS

Cuando veas la ejecución en Step Functions Console, verás algo así:

```
┌─────────────────┐
│ ProcesarPedido  │ ✅ Verde (completado)
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ PedidoEnCocina  │ ✅ Verde (completado)
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ EvaluarCocina   │ ✅ Verde (completado)
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ CocinaCompleta  │ 🔵 Azul (en progreso) o ✅ Verde
└────────┬────────┘
         │
        ...
```

---

## 8. Troubleshooting

### Problema: El flujo no avanza después de llamar endpoint

**Solución:**
1. Verifica que el `order_id` sea exactamente el mismo
2. Revisa CloudWatch Logs de `cambiarEstado`
3. Verifica que el evento se publicó en EventBridge:
   - AWS Console → EventBridge → Event buses → default
   - Tab "Monitoring" para ver eventos

### Problema: Lambda timeout

**Solución:**
1. Aumenta el timeout en `serverless.yml`:
   ```yaml
   provider:
     timeout: 30  # Aumentar de 20 a 30
   ```

### Problema: No encuentro el Step Functions

**Solución:**
- Verifica que creaste el state machine manualmente en la consola
- AWS Academy no permite crear Step Functions via CloudFormation/Serverless

---

## 9. Script de Prueba Completo

Guarda esto como `test_workflow.sh`:

```bash
#!/bin/bash

API_URL="TU-API-GATEWAY-URL"  # Reemplazar con tu URL
ORDER_ID="test-order-$(date +%s)"

echo "🚀 Iniciando flujo para pedido: $ORDER_ID"

# Iniciar Step Functions manualmente o via EventBridge
echo "📝 Crea la ejecución manualmente en AWS Console con order_id: $ORDER_ID"
read -p "Presiona Enter cuando hayas iniciado la ejecución..."

echo "1️⃣ Cocina inicia preparación..."
curl -X POST $API_URL/empleados/cocina/iniciar \
  -H "Content-Type: application/json" \
  -d "{\"order_id\":\"$ORDER_ID\",\"empleado_id\":\"EMP-COCINA-001\"}"
sleep 2

echo "2️⃣ Cocina completa..."
curl -X POST $API_URL/empleados/cocina/completar \
  -H "Content-Type: application/json" \
  -d "{\"order_id\":\"$ORDER_ID\",\"empleado_id\":\"EMP-COCINA-001\"}"
sleep 2

echo "3️⃣ Empaquetado completo..."
curl -X POST $API_URL/empleados/empaque/completar \
  -H "Content-Type: application/json" \
  -d "{\"order_id\":\"$ORDER_ID\",\"empleado_id\":\"EMP-EMPAQUE-001\"}"
sleep 2

echo "4️⃣ Delivery inicia..."
curl -X POST $API_URL/empleados/delivery/iniciar \
  -H "Content-Type: application/json" \
  -d "{\"order_id\":\"$ORDER_ID\",\"empleado_id\":\"EMP-DELIVERY-001\"}"
sleep 2

echo "5️⃣ Delivery entrega..."
curl -X POST $API_URL/empleados/delivery/entregar \
  -H "Content-Type: application/json" \
  -d "{\"order_id\":\"$ORDER_ID\",\"empleado_id\":\"EMP-DELIVERY-001\"}"
sleep 2

echo "6️⃣ Cliente confirma..."
curl -X POST $API_URL/empleados/cliente/confirmar \
  -H "Content-Type: application/json" \
  -d "{\"order_id\":\"$ORDER_ID\",\"empleado_id\":\"CLIENTE\"}"

echo "✅ Flujo completado! Verifica en Step Functions Console"
```

**Uso:**
```bash
chmod +x test_workflow.sh
./test_workflow.sh
```

---

## 10. Recursos Útiles

- **Step Functions Console:** https://console.aws.amazon.com/states/
- **CloudWatch Logs:** https://console.aws.amazon.com/cloudwatch/
- **DynamoDB Console:** https://console.aws.amazon.com/dynamodb/
- **EventBridge Console:** https://console.aws.amazon.com/events/
