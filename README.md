# API Documentation - Proyecto 200 Millas

Documentación de endpoints para desarrollo frontend.

---

## 🔐 Autenticación

**Endpoints públicos**: No requieren token  
**Endpoints protegidos**: Header `Authorization: Bearer <token>`

---

# URL
servicio clientes -> https://96189ls6ki.execute-api.us-east-1.amazonaws.com

servicio productos -> https://j30x9cucu2.execute-api.us-east-1.amazonaws.com

servicio usuarios -> https://02vk0b0dll.execute-api.us-east-1.amazonaws.com

servicio empleados -> https://uou7ashhbl.execute-api.us-east-1.amazonaws.com


---

## 1. Usuarios y Autenticación

### Públicos

#### POST `/users/register`
Registrar nuevo usuario
```json
Request: {
  "nombre": "string",
  "correo": "email",
  "contrasena": "string",
  "role": "Cliente|Gerente|Admin"
}
Response: {
  "message": "string",
  "correo": "email"
}
```

#### POST `/users/login`
Iniciar sesión
```json
Request: {
  "correo": "email",
  "contrasena": "string"
}
Response: {
  "token": "string",
  "expires_iso": "ISO8601"
}
```

### Protegidos (Requieren Token)

#### GET `/users/me`
Obtener datos del usuario autenticado
```json
Response: {
  "nombre": "string",
  "correo": "email",
  "role": "string"
}
```

#### PUT `/users/me`
Actualizar datos del usuario
```json
Request: {
  "nombre": "string (opcional)",
  "contrasena": "string (opcional)"
}
Response: {
  "message": "string"
}
```

#### DELETE `/users/me`
Eliminar cuenta del usuario
```json
Response: {
  "message": "string"
}
```

#### POST `/users/password/change`
Cambiar contraseña
```json
Request: {
  "contrasena_actual": "string",
  "contrasena_nueva": "string"
}
Response: {
  "message": "string"
}
```

---

## 2. Empleados

**Permisos**: Admin o Gerente

#### POST `/users/employee`
Crear empleado
```json
Request: {
  "local_id": "string",
  "dni": "string",
  "nombre": "string",
  "apellido": "string",
  "role": "Repartidor|Cocinero|Despachador",
  "ocupado": boolean
}
Response: {
  "message": "string",
  "employee": {...}
}
```

#### PUT `/users/employee`
Actualizar empleado
```json
Request: {
  "local_id": "string",
  "dni": "string",
  "nombre": "string (opcional)",
  "apellido": "string (opcional)",
  "role": "string (opcional)"
}
Response: {
  "message": "string"
}
```

#### DELETE `/users/employee`
Eliminar empleado
```json
Request: {
  "local_id": "string",
  "dni": "string"
}
Response: {
  "message": "string"
}
```

#### POST `/users/employees/list`
Listar empleados de un local
```json
Request: {
  "local_id": "string",
  "limit": number (opcional),
  "start_key": object (opcional, para paginación)
}
Response: {
  "empleados": [...],
  "count": number,
  "last_evaluated_key": object (si hay más páginas)
}
```

---

## 3. Productos

**Permisos**: Todos los endpoints requieren token

#### POST `/productos/create`
Crear producto
```json
Request: {
  "local_id": "string",
  "producto_id": "UUID",
  "nombre": "string",
  "precio": number,
  "descripcion": "string",
  "categoria": "string",
  "cantidad": number,
  "imagen_url": "string (opcional)"
}
Response: {
  "message": "string",
  "producto": {...}
}
```

#### PUT `/productos/update`
Actualizar producto
```json
Request: {
  "local_id": "string",
  "producto_id": "UUID",
  "nombre": "string (opcional)",
  "precio": number (opcional)",
  "descripcion": "string (opcional)",
  "categoria": "string (opcional)",
  "cantidad": number (opcional)",
  "imagen_url": "string (opcional)"
}
Response: {
  "message": "string"
}
```

#### POST `/productos/id`
Obtener producto por ID
```json
Request: {
  "local_id": "string",
  "producto_id": "UUID"
}
Response: {
  "producto": {
    "local_id": "string",
    "producto_id": "UUID",
    "nombre": "string",
    "precio": number,
    "descripcion": "string",
    "categoria": "string",
    "cantidad": number,
    "imagen_url": "string"
  }
}
```

#### POST `/productos/list`
Listar productos de un local
```json
Request: {
  "local_id": "string",
  "limit": number (opcional, default: 50),
  "start_key": object (opcional, para paginación)
}
Response: {
  "productos": [...],
  "count": number,
  "last_evaluated_key": object (si hay más páginas)
}
```

#### DELETE `/productos/delete`
Eliminar producto
```json
Request: {
  "local_id": "string",
  "producto_id": "UUID"
}
Response: {
  "message": "string"
}
```

---

## 4. Pedidos (Clientes)

**Permisos**: Requieren token

#### POST `/pedido/create`
Crear nuevo pedido
```json
Request: {
  "tenant_id": "string",
  "local_id": "string",
  "usuario_correo": "email",
  "direccion": "string",
  "costo": number,
  "estado": "string",
  "productos": [
    {
      "producto_id": "UUID",
      "nombre": "string",
      "cantidad": number,
      "precio": number
    }
  ],
  "fecha_entrega_aproximada": "ISO8601 (opcional)"
}
Response: {
  "message": "string",
  "pedido": {
    "pedido_id": "UUID",
    "tenant_id": "string",
    ...
  }
}
```

#### GET `/pedido/status?tenant_id=X&pedido_id=Y`
Obtener estado del pedido
```json
Response: {
  "tenant_id": "string",
  "pedido_id": "UUID",
  "estado": "string",
  "detalles": {...}
}
```

#### POST `/pedido/confirmar`
Confirmar recepción del pedido
```json
Request: {
  "tenant_id": "string",
  "pedido_id": "UUID"
}
Response: {
  "message": "string",
  "estado": "recibido"
}
```

---

## 5. Workflow de Empleados

**Permisos**: Endpoints para empleados (no requieren token, son internos)

Estos endpoints gatillan eventos en el flujo de Step Functions.

#### POST `/empleados/cocina/iniciar`
Cocina inicia preparación
```json
Request: {
  "order_id": "UUID",
  "empleado_id": "string"
}
Response: {
  "message": "EnPreparacion event published",
  "order_id": "UUID"
}
```

#### POST `/empleados/cocina/completar`
Cocina completa preparación
```json
Request: {
  "order_id": "UUID",
  "empleado_id": "string"
}
Response: {
  "message": "CocinaCompleta event published",
  "order_id": "UUID"
}
```

#### POST `/empleados/empaque/completar`
Empaquetado completo
```json
Request: {
  "order_id": "UUID",
  "empleado_id": "string"
}
Response: {
  "message": "Empaquetado event published",
  "order_id": "UUID"
}
```

#### POST `/empleados/delivery/iniciar`
Delivery inicia entrega
```json
Request: {
  "order_id": "UUID",
  "empleado_id": "string"
}
Response: {
  "message": "PedidoEnCamino event published",
  "order_id": "UUID"
}
```

#### POST `/empleados/delivery/entregar`
Delivery entrega pedido
```json
Request: {
  "order_id": "UUID",
  "empleado_id": "string"
}
Response: {
  "message": "EntregaDelivery event published",
  "order_id": "UUID"
}
```

#### POST `/empleados/cliente/confirmar`
Cliente confirma recepción
```json
Request: {
  "order_id": "UUID",
  "empleado_id": "CLIENTE (opcional)"
}
Response: {
  "message": "ConfirmarPedidoCliente event published",
  "order_id": "UUID"
}
```

---

## 📊 Modelos de Datos

### Usuario
```typescript
{
  correo: string (PK)
  nombre: string
  contrasena: string (hashed)
  role: "Cliente" | "Gerente" | "Admin"
}
```

### Empleado
```typescript
{
  local_id: string (PK)
  dni: string (SK)
  nombre: string
  apellido: string
  role: "Repartidor" | "Cocinero" | "Despachador"
  ocupado: boolean
}
```

### Producto
```typescript
{
  local_id: string (PK)
  producto_id: UUID (SK)
  nombre: string
  precio: number
  descripcion: string
  categoria: string
  cantidad: number
  imagen_url?: string
}
```

### Pedido
```typescript
{
  tenant_id: string (PK)
  pedido_id: UUID (SK)
  local_id: string
  usuario_correo: string
  direccion: string
  costo: number
  estado: string
  productos: Array<{
    producto_id: UUID
    nombre: string
    cantidad: number
    precio: number
  }>
  fecha_creacion: ISO8601
  fecha_entrega_aproximada?: ISO8601
}
```

---

## 🔄 Estados del Pedido

1. **procesando** - Pedido creado, en cola para cocina
2. **cocinando** - En preparación en cocina
3. **empacando** - Siendo empaquetado
4. **enviando** - En camino con delivery
5. **recibido** - Entregado y confirmado

---

## ⚠️ Códigos de Error Comunes

- `400` - Bad Request (datos inválidos)
- `401` - Unauthorized (token inválido/expirado)
- `403` - Forbidden (sin permisos)
- `404` - Not Found (recurso no existe)
- `409` - Conflict (recurso ya existe)
- `500` - Internal Server Error

---

## 🔑 Categorías de Productos

- Promos Fast
- Express
- Promociones
- Sopas Power
- Bowls Del Tigre
- Leche de Tigre
- Ceviches
- Fritazo
- Mostrimar
- Box Marino
- Duos Marinos
- Trios Marinos
- Dobles
- Rondas Marinas
- Mega Marino
- Familiares

---

## 💡 Notas para Frontend

### Autenticación
1. Guardar token en localStorage/sessionStorage
2. Incluir en header: `Authorization: Bearer ${token}`
3. Renovar token antes de expiración
4. Limpiar token al logout

### Paginación
- Usar `start_key` del response anterior para siguiente página
- `limit` controla items por página
- Si no hay `last_evaluated_key`, es la última página

### Manejo de Errores
```javascript
try {
  const response = await fetch(url, options);
  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.message || 'Error desconocido');
  }
  return await response.json();
} catch (error) {
  // Manejar error
}
```

### Workflow de Pedido
```
Cliente crea pedido
  ↓
Empleado cocina inicia (/empleados/cocina/iniciar)
  ↓
Empleado cocina completa (/empleados/cocina/completar)
  ↓
Empleado empaque completa (/empleados/empaque/completar)
  ↓
Empleado delivery inicia (/empleados/delivery/iniciar)
  ↓
Empleado delivery entrega (/empleados/delivery/entregar)
  ↓
Cliente confirma (/empleados/cliente/confirmar)
```
