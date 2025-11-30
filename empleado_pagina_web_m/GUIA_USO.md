# Guía de Uso - Página Web de Empleados 200 Millas

## Descripción
Página web para empleados del sistema 200 Millas que permite gestionar estados de pedidos y visualizar analytics.

## Funcionalidades Implementadas

### 1. Autenticación

#### Registro de Usuario
1. En la página de login, haz clic en "¿No tienes cuenta? Regístrate"
2. Completa el formulario:
   - Nombre completo
   - Email
   - Contraseña
   - Rol: Cliente, Gerente, Cocinero, Repartidor, o Despachador
3. Haz clic en "Registrarse"
4. Si es exitoso, automáticamente iniciarás sesión

**Endpoint usado**: `POST /users/register`
```json
{
  "nombre": "string",
  "correo": "email",
  "contrasena": "string",
  "role": "Cliente|Gerente|Cocinero|Repartidor|Despachador"
}
```

#### Iniciar Sesión
1. Ingresa tu email y contraseña
2. Haz clic en "Iniciar Sesión"
3. Serás redirigido según tu rol

**Endpoint usado**: `POST /users/login`
```json
{
  "correo": "email",
  "contrasena": "string"
}
```

#### Cerrar Sesión
- Haz clic en el botón "Cerrar Sesión" en la esquina superior derecha
- Serás redirigido a la página de login

---

### 2. Vista según Rol de Usuario

#### ROL: Gerente
**Vista**: Dashboard de Analytics

Muestra estadísticas en tiempo real:
- Total de pedidos
- Pedidos entregados
- Pedidos en proceso
- Ingresos totales
- Gráficos de distribución por estado
- Rendimiento operativo

**Endpoints usados**:
- `POST /analytics/pedidos-por-local` - Total de pedidos por local
- `POST /analytics/ganancias-por-local` - Ganancias por local
- `POST /analytics/tiempo-pedido` - Tiempo promedio de pedidos

**Formato de petición**:
```json
{
  "local_id": "LOCAL-001"
}
```

---

#### ROL: Cocinero, Repartidor, Despachador
**Vista**: Panel de Gestión de Pedidos

Permite cambiar el estado de los pedidos según el flujo:

**Estados disponibles y endpoints**:

1. **En Preparación** (Cocinero inicia)
   - Endpoint: `POST /empleados/cocina/iniciar`
   - Body: `{"order_id": "xxx", "empleado_id": "dni"}`

2. **Cocina Completa** (Cocinero completa)
   - Endpoint: `POST /empleados/cocina/completar`
   - Body: `{"order_id": "xxx", "empleado_id": "dni"}`

3. **Empaquetado** (Despachador)
   - Endpoint: `POST /empleados/empaque/completar`
   - Body: `{"order_id": "xxx", "empleado_id": "dni"}`

4. **En Delivery** (Repartidor inicia)
   - Endpoint: `POST /empleados/delivery/iniciar`
   - Body: `{"order_id": "xxx", "empleado_id": "dni"}`

5. **Entregado** (Repartidor completa)
   - Endpoint: `POST /empleados/delivery/entregar`
   - Body: `{"order_id": "xxx", "empleado_id": "dni"}`

---

#### ROL: Cliente
**Vista**: Panel de Pedidos

Funcionalidades para clientes:

1. **Crear Pedido**
   - Endpoint: `POST /pedido/create`
   - Body:
   ```json
   {
     "local_id": "LOCAL-001",
     "user_email": "cliente@email.com",
     "productos": [
       {"producto_id": "P001", "cantidad": 2}
     ]
   }
   ```

2. **Consultar Estado de Pedido**
   - Endpoint: `GET /pedido/status?local_id=LOCAL-001&pedido_id=xxx`

3. **Confirmar Recepción**
   - Endpoint: `POST /pedido/confirmar`
   - Body:
   ```json
   {
     "order_id": "xxx",
     "local_id": "LOCAL-001",
     "usuario_email": "cliente@email.com"
   }
   ```

---

## Flujo de Estados de Pedidos

```
1. Procesando (inicial)
2. En Preparación (cocinero inicia)
3. Pedido en Cocina
4. Cocina Completa (cocinero completa)
5. Empaquetado (despachador)
6. Pedido en Camino (repartidor inicia)
7. Entregado (repartidor completa)
8. Cliente confirma recepción
```

---

## Configuración de APIs

Las URLs de los servicios están configuradas en `config.js`:

```javascript
const API_CONFIG = {
    usersUrl: 'https://zq0fbveqte.execute-api.us-east-1.amazonaws.com',
    empleadoUrl: 'https://cmkk23rz22.execute-api.us-east-1.amazonaws.com',
    clientesUrl: 'https://2tkz55hms1.execute-api.us-east-1.amazonaws.com',
    productsUrl: 'https://y6am9ly97g.execute-api.us-east-1.amazonaws.com',
    analyticUrl: 'https://9chtp1assj.execute-api.us-east-1.amazonaws.com',
    localId: 'LOCAL-001'
};
```

---

## Cómo Ejecutar Localmente

1. Abre una terminal en la carpeta del proyecto
2. Ejecuta: `./test_local.sh`
3. Abre tu navegador en: `http://localhost:8080`

---

## Notas Importantes

- **Token de autenticación**: Se guarda automáticamente en localStorage después del login
- **Sesión persistente**: Tu sesión se mantiene aunque cierres el navegador
- **Local ID**: Por defecto se usa "LOCAL-001", puedes cambiarlo en config.js
- **Empleado ID**: Para cambios de estado, debes ingresar el DNI del empleado

---

## Solución de Problemas

### Error: "Failed to fetch"
- Verifica que las URLs en config.js sean correctas
- Verifica tu conexión a internet
- Comprueba que los servicios de AWS estén activos

### No puedo cambiar el estado de un pedido
- Verifica que el pedido exista en la base de datos
- Asegúrate de estar usando el Order ID correcto
- Verifica que tu rol tenga permisos para ese cambio de estado

### No veo pedidos en el dashboard
- Los pedidos se cargan desde la API de analytics
- Asegúrate de que haya pedidos creados para tu local
- Verifica que el local_id en config.js sea correcto

---

## Próximas Mejoras

- [ ] Formulario para crear pedidos (clientes)
- [ ] Lista automática de pedidos sin necesidad de ID
- [ ] Notificaciones en tiempo real
- [ ] Historial de cambios de estado
- [ ] Validaciones de rol para acciones específicas
