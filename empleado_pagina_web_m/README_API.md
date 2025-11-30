# Sistema de Gestión 200 Millas

## 🚀 Inicio Rápido

```bash
./test_local.sh
# Abre http://localhost:8080
```

## 🎯 Descripción

Sistema web integrado con la API real de 200 Millas. Registro, login y gestión de pedidos por rol.

## 🚀 Características

### ✅ Sistema de Autenticación Real
- **Registro de Usuarios**: Los usuarios pueden registrarse seleccionando su rol
- **Login con Token**: Autenticación mediante JWT tokens
- **Roles Disponibles**:
  - **Cliente**: Usuario final (sin acceso a gestión)
  - **Gerente**: Ve dashboard de analytics
  - **Cocinero**: Gestiona estados de cocina
  - **Repartidor**: Gestiona entregas
  - **Despachador**: Gestiona empaquetado

### 🎨 Interfaz de Usuario
- **Vista de Gerente**: Dashboard con KPIs y analytics
- **Vista de Empleado**: Grid de pedidos con cambio de estados
- **Diseño Responsive**: Funciona en móvil, tablet y desktop

### 🔗 Integración con API

#### Endpoints Configurados

**Autenticación (Users Service)**
- `POST /users/register` - Registro de nuevos usuarios
- `POST /users/login` - Inicio de sesión

**Gestión de Pedidos (Empleado Service)**
- `POST /empleados/cocina/iniciar` - Iniciar preparación en cocina
- `POST /empleados/cocina/completar` - Completar cocina
- `POST /empleados/empaque/completar` - Completar empaquetado
- `POST /empleados/delivery/iniciar` - Iniciar entrega
- `POST /empleados/delivery/entregar` - Confirmar entrega

## 📋 Cómo Usar

### 1. Abrir la Aplicación

```bash
# Opción 1: Con servidor Python
cd empleado_pagina_web_m
python3 -m http.server 8080

# Opción 2: Directamente en el navegador
# Abre index.html con tu navegador
```

### 2. Registrarse

1. Haz clic en "¿No tienes cuenta? Regístrate"
2. Completa el formulario:
   - Nombre completo
   - Email
   - Contraseña
   - **Selecciona tu rol** (Gerente, Cocinero, Repartidor, etc.)
3. Haz clic en "Registrarse"
4. Serás redirigido automáticamente a tu panel

### 3. Iniciar Sesión

1. Ingresa tu email y contraseña
2. Haz clic en "Iniciar Sesión"
3. Serás redirigido según tu rol:
   - **Gerente**: Dashboard de analytics
   - **Empleado**: Panel de gestión de pedidos

### 4. Gestionar Pedidos (Empleados)

#### Ver Pedidos
- Los pedidos se muestran en tarjetas con:
  - ID del pedido
  - Estado actual
  - Cliente
  - Total
  - Productos

#### Cambiar Estado
1. Haz clic en una tarjeta de pedido
2. Se abrirá un modal con los detalles
3. Selecciona el nuevo estado:
   - **En Preparación**: Cocina inicia
   - **Cocina Completa**: Cocina terminada
   - **Empaquetado**: Listo para entrega
   - **En Camino**: Delivery en curso
   - **Entregado**: Pedido completado
4. (Opcional) Agrega una nota
5. Haz clic en "Confirmar Cambio"

### 5. Ver Analytics (Gerentes)

Los gerentes ven automáticamente:
- **Total de Pedidos**: Cantidad total
- **Pedidos Entregados**: Completados exitosamente
- **Ingresos Totales**: Suma de todos los pedidos
- **Pedidos Activos**: En proceso
- **Gráfico de Estados**: Distribución visual

## 🔧 Configuración

El archivo `config.js` contiene las URLs de los servicios:

```javascript
const API_CONFIG = {
    usersUrl: 'https://g1m4xkh1u4.execute-api.us-east-1.amazonaws.com',
    empleadoUrl: 'https://v8fwfbvwvb.execute-api.us-east-1.amazonaws.com',
    clientesUrl: 'https://iw3t3dw6qa.execute-api.us-east-1.amazonaws.com',
    localId: 'LOCAL-001',
    // ...
};
```

## 📝 Flujo de Estados de Pedido

```
procesando → en_preparacion → cocina_completa → empaquetado → pedido_en_camino → entregado
```

## ⚠️ Notas Importantes

### Datos Mock
Por ahora, el sistema usa **datos mock** para mostrar los pedidos en el grid porque no existe un endpoint específico para listar todos los pedidos de un local/empleado. Sin embargo, **los cambios de estado SÍ se envían a la API real**.

### Token de Autenticación
El token JWT recibido al hacer login se guarda en `localStorage` y se usa para las peticiones autenticadas.

### Rol de Gerente
Los gerentes ven analytics con datos mock. Para conectar con el endpoint real de analytics, descomenta las líneas en `app.js` y configura la llamada al servicio de analytics.

## 🐛 Solución de Problemas

### Error: "Credenciales inválidas"
- Verifica que el email y contraseña sean correctos
- Asegúrate de haber registrado el usuario previamente

### Error: "Failed to fetch"
- Verifica tu conexión a internet
- Confirma que las URLs de los servicios en `config.js` sean correctas
- Revisa la consola del navegador para más detalles

### Los pedidos no se actualizan
- El sistema usa datos mock para el listado
- Asegúrate de hacer clic en "Refrescar" después de cambiar un estado
- Los cambios de estado SÍ se envían a la API

### Error al cambiar estado
- Verifica que tengas un rol válido (Cocinero, Repartidor, Despachador)
- Asegúrate de que el `empleado_id` (DNI) esté configurado correctamente

## 📱 Compatibilidad

- ✅ Chrome/Edge (Recomendado)
- ✅ Firefox
- ✅ Safari
- ✅ Mobile browsers

## 🎨 Personalización

### Cambiar el Local ID
Edita `config.js`:
```javascript
localId: 'LOCAL-002',  // Cambia según tu local
```

### Modificar Estados Disponibles
Edita `config.js`:
```javascript
const ESTADOS_PEDIDO = {
    // Agrega o quita estados según necesites
};
```

## 📞 Soporte

Para problemas o preguntas sobre la API, consulta la documentación del backend o revisa la colección de Postman del proyecto.

---

**Versión**: 2.0  
**Última actualización**: Nov 2025  
**Estado**: Integración con API Real ✅
