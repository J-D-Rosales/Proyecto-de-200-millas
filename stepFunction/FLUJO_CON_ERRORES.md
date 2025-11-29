# 🔄 Flujo Completo del Step Function con Manejo de Errores

## 📊 Diagrama de Flujo

```
┌─────────────────┐
│ ProcesarPedido  │ (15 min timeout)
└────────┬────────┘
         │ ✅ Success
         ↓
┌─────────────────┐
│ PedidoEnCocina  │ (15 min timeout)
└────────┬────────┘
         │ ✅ Success
         ↓
┌─────────────────┐
│ EvaluarCocina   │ (Choice)
└────────┬────────┘
         │
    ┌────┴────┐
    │         │
ACEPTADO  RECHAZADO
    │         │
    │         ↓
    │    ┌──────────────┐
    │    │ReintentarCocina│
    │    └──────┬─────────┘
    │           │
    │           ↓
    │    ┌──────────────────┐
    │    │EvaluarReintento  │
    │    └──────┬───────────┘
    │           │
    │      ┌────┴────┐
    │      │         │
    │   retry≤3   retry>3
    │      │         │
    │      └─────┐   │
    │            │   ↓
    │            │ PedidoFallido ❌
    │            │
    ↓            ↓
┌─────────────────┐
│ CocinaCompleta  │ (15 min timeout)
└────────┬────────┘
         │
         ↓
┌─────────────────┐
│  Empaquetado    │ (15 min timeout)
└────────┬────────┘
         │
         ↓
┌─────────────────┐
│    Delivery     │ (15 min timeout)
└────────┬────────┘
         │
         ↓
┌─────────────────┐
│ EvaluarDelivery │ (Choice)
└────────┬────────┘
         │
    ┌────┴────┐
    │         │
ACEPTADO  RECHAZADO
    │         │
    │         ↓
    │    ┌──────────────────┐
    │    │ReintentarDelivery│
    │    └──────┬───────────┘
    │           │
    │           ↓
    │    ┌──────────────────┐
    │    │EvaluarReintento  │
    │    └──────┬───────────┘
    │           │
    │      ┌────┴────┐
    │      │         │
    │   retry≤3   retry>3
    │      │         │
    │      └─────┐   │
    │            │   ↓
    │            │ PedidoFallido ❌
    │            │
    ↓            ↓
┌─────────────────┐
│   Entregado     │ (15 min timeout)
└────────┬────────┘
         │
         ↓
┌─────────────────┐
│ EntregaCompleta │ ✅ SUCCESS
└─────────────────┘
```

## 🎯 Estados y Transiciones

### Estados Normales (Happy Path)

| Estado | Timeout | Siguiente | Actualiza Pedidos |
|--------|---------|-----------|-------------------|
| ProcesarPedido | 15 min | PedidoEnCocina | `procesando` |
| PedidoEnCocina | 15 min | EvaluarCocina | `en_preparacion` |
| CocinaCompleta | 15 min | Empaquetado | `cocina_completa` |
| Empaquetado | 15 min | Delivery | `empaquetando` |
| Delivery | 15 min | EvaluarDelivery | `pedido_en_camino` |
| Entregado | 15 min | EntregaCompleta | `entrega_delivery` |
| EntregaCompleta | - | END | `recibido` |

### Estados de Error

| Estado | Trigger | Acción |
|--------|---------|--------|
| PedidoFallido | Timeout o retry>3 | Actualiza a `fallido`, notifica usuario |

## ⏱️ Manejo de Timeouts

Cada estado con `waitForTaskToken` tiene un timeout de **15 minutos (900 segundos)**.

### ¿Qué pasa si hay timeout?

1. **Step Function detecta timeout** (15 min sin respuesta)
2. **Catch captura el error** → `"ErrorEquals": ["States.Timeout"]`
3. **Va al estado PedidoFallido**
4. **Lambda pedido_fallido.py ejecuta:**
   - ✅ Actualiza tabla Pedidos: `estado = 'fallido'`
   - ✅ Guarda en Historial Estados
   - ✅ Publica evento `PedidoFallido` a EventBridge
   - ✅ Notifica al usuario (email/SMS)

### Ejemplo de Timeout

```
Usuario crea pedido → ProcesarPedido → PedidoEnCocina
                                            ↓
                                    (espera 15 minutos)
                                            ↓
                                    ❌ TIMEOUT
                                            ↓
                                    PedidoFallido
                                            ↓
                        - Pedidos.estado = 'fallido'
                        - Historial: nuevo registro 'fallido'
                        - EventBridge: evento 'PedidoFallido'
                        - Usuario recibe notificación
```

## 🔄 Manejo de Rechazos

### Cocina Rechaza el Pedido

```
PedidoEnCocina → EvaluarCocina
                      ↓
                status = RECHAZADO
                      ↓
                ReintentarCocina
                      ↓
                retry_count++
                      ↓
            EvaluarReintentoCocina
                      ↓
            ┌─────────┴─────────┐
            │                   │
      retry_count ≤ 3     retry_count > 3
            │                   │
            ↓                   ↓
      PedidoEnCocina      PedidoFallido ❌
      (reintenta)         (falla definitivo)
```

### Delivery Rechaza el Pedido

Mismo flujo que cocina, pero con `ReintentarDelivery`.

## 📧 Notificaciones al Usuario

### Evento: PedidoFallido

Cuando un pedido falla, se publica este evento a EventBridge:

```json
{
  "Source": "200millas.pedidos",
  "DetailType": "PedidoFallido",
  "Detail": {
    "order_id": "xxx",
    "local_id": "LOCAL-001",
    "timestamp": "2025-11-29T...",
    "error": "States.Timeout",
    "message": "Tu pedido no pudo ser procesado. Por favor contacta con el restaurante."
  }
}
```

### Cómo Implementar Notificaciones

Puedes crear un Lambda que escuche el evento `PedidoFallido` y:
- Envíe email con SES
- Envíe SMS con SNS
- Envíe notificación push
- Actualice el frontend en tiempo real

## 🚀 Triggers que Funcionan

Tus triggers actuales **SÍ funcionan** con este flujo:

| Endpoint | Evento | Avanza de → a |
|----------|--------|---------------|
| POST /empleados/cocina/iniciar | EnPreparacion | PedidoEnCocina → CocinaCompleta |
| POST /empleados/cocina/completar | CocinaCompleta | CocinaCompleta → Empaquetado |
| POST /empleados/empaque/completar | Empaquetado | Empaquetado → Delivery |
| POST /empleados/delivery/iniciar | PedidoEnCamino | Delivery → Entregado |
| POST /empleados/delivery/entregar | EntregaDelivery | Entregado → EntregaCompleta |
| POST /clientes/confirmar-recepcion | ConfirmarPedidoCliente | (opcional) |

## 📝 Cambios Implementados

### 1. Nuevo Lambda: `pedido_fallido.py`
- Maneja todos los casos de fallo (timeout, rechazos múltiples)
- Actualiza estado a `fallido`
- Notifica al usuario

### 2. Step Function Actualizado
- Todos los estados con timeout tienen `Catch` → `PedidoFallido`
- Estados `CocinaFallida` y `DeliveryFallido` reemplazados por `PedidoFallido`
- Flujo unificado de manejo de errores

### 3. Archivo: `step_function_definition_v2.json`
- Nueva definición con manejo completo de errores
- Listo para desplegar

## 🔧 Cómo Desplegar

```bash
# 1. Redesplegar Step Functions con nuevo Lambda
cd stepFunction
sls deploy

# 2. Actualizar la definición del Step Function en AWS Console
# O usar AWS CLI:
aws stepfunctions update-state-machine \
  --state-machine-arn arn:aws:states:us-east-1:YOUR_ACCOUNT:stateMachine:DoscientasMillas \
  --definition file://step_function_definition_v2.json
```

## ✅ Verificación

### Probar Timeout (opcional)

Para probar que el timeout funciona, puedes:
1. Crear un pedido
2. NO llamar a ningún trigger
3. Esperar 15 minutos
4. El Step Function debe ir a `PedidoFallido` automáticamente

### Verificar Estado Fallido

```bash
# Ver el pedido en DynamoDB
aws dynamodb get-item \
  --table-name Millas-Pedidos \
  --key '{"local_id":{"S":"LOCAL-001"},"pedido_id":{"S":"<pedido_id>"}}'

# Deberías ver: "estado": "fallido"
```

### Ver Evento de Notificación

```bash
# Ver logs del Lambda pedidoFallido
aws logs tail /aws/lambda/service-orders-200-millas-dev-pedidoFallido --follow
```

Deberías ver:
```
📧 Published PedidoFallido event for order xxx
```

---

**Fecha:** 29 de Noviembre, 2025
**Versión:** 4.0 - Manejo completo de errores y timeouts
