# Panel de Empleado - 200 Millas

Panel web profesional y minimalista para que los empleados gestionen el estado de los pedidos.

## 🚀 Características

- ✅ **Autenticación de empleados** con login seguro
- 📋 **Visualización de pedidos** en tarjetas organizadas
- 🔄 **Actualización de estados** mediante modal interactivo
- 🔍 **Filtrado de pedidos** por estado
- 🔄 **Auto-actualización** cada 30 segundos
- 📱 **Diseño responsive** para móviles y tablets
- 🎨 **Interfaz minimalista** y profesional

## 📁 Estructura de Archivos

```
empleado_pagina_web_m/
├── index.html      # Estructura HTML principal
├── styles.css      # Estilos minimalistas y responsive
├── app.js          # Lógica de la aplicación
├── config.js       # Configuración de endpoints API
└── README.md       # Este archivo
```

## 🚀 Inicio Rápido (Modo Demo)

Para ver la página inmediatamente **sin necesidad de backend o login**:

1. Abre el archivo `app.js`
2. Busca la línea que dice `const DEV_MODE = false;`
3. Cámbiala a `const DEV_MODE = true;`
4. Abre `index.html` en tu navegador

¡Listo! Verás la página con datos de ejemplo funcionando.

### 👤 Tipos de Usuario

El sistema tiene **autenticación diferenciada** por tipo de usuario:

#### **🔧 EMPLEADO** (Vista de Gestión de Pedidos)
```
Login: [cualquier email que NO sea "admin"]
Contraseña: [cualquier contraseña]
Backend: ⚠️ Intenta conectar, si falla usa datos mock
```
- ✅ Vista: Tarjetas de pedidos con filtros
- ✅ Puede: Cambiar estados de pedidos
- ✅ Auto-actualización cada 30 segundos
- ✅ **Modo demo**: Si no hay backend, muestra 15 pedidos de ejemplo

#### **👨‍💼 ADMINISTRADOR** (Vista de Analytics)
```
Login: admin
Contraseña: [cualquier contraseña]
Backend: ❌ NO requiere API (funciona offline)
```
- ✅ Vista: Dashboard con estadísticas y métricas
- ✅ Ve: KPIs, gráficos, distribución de pedidos
- ✅ Datos calculados en tiempo real
- ✅ **15 pedidos de ejemplo** para análisis completo

## ⚙️ Configuración

### 1. Configurar Endpoints

Edita el archivo `config.js` y actualiza la URL de tu API:

```javascript
const API_CONFIG = {
    baseUrl: 'https://tu-api-gateway.amazonaws.com/dev',
    endpoints: {
        login: '/users/login',
        orders: '/pedidos',
        updateStatus: '/pedidos/estado',
        orderDetail: '/pedidos/{id}'
    }
};
```

### 2. Formato de Respuesta de la API

La aplicación espera que los endpoints respondan con el siguiente formato:

#### Login (`POST /users/login`)
```json
{
    "token": "jwt-token-here",
    "user": {
        "email": "empleado@ejemplo.com",
        "nombre": "Juan Pérez"
    }
}
```

#### Lista de Pedidos (`GET /pedidos`)
```json
{
    "pedidos": [
        {
            "id": "123",
            "estado": "en_cocina",
            "cliente_nombre": "María López",
            "total": 25.50,
            "productos": [
                {
                    "nombre": "Pizza Margherita",
                    "cantidad": 2
                }
            ],
            "fecha_creacion": "2025-11-22T10:30:00Z"
        }
    ]
}
```

#### Actualizar Estado (`POST /pedidos/estado`)
```json
{
    "pedido_id": "123",
    "nuevo_estado": "empaquetado",
    "notas": "Pedido listo para delivery"
}
```

## 🎯 Estados de Pedidos

Los siguientes estados están configurados:

- **Pendiente** - Pedido recibido, esperando procesamiento
- **En Preparación** - Pedido siendo preparado
- **En Cocina** - Pedido en proceso de cocción
- **Empaquetado** - Pedido listo y empaquetado
- **En Delivery** - Pedido en camino al cliente
- **Entregado** - Pedido entregado exitosamente
- **Cancelado** - Pedido cancelado

## 🖥️ Uso

### Para Desarrollo Local

1. Abre el archivo `index.html` directamente en un navegador moderno, o
2. Usa un servidor local:

```bash
# Con Python 3
python -m http.server 8000

# Con Node.js (http-server)
npx http-server

# Con PHP
php -S localhost:8000
```

3. Accede a `http://localhost:8000` en tu navegador

### Para Producción

1. Sube los archivos a un hosting web (S3, Netlify, Vercel, etc.)
2. Configura CORS en tu API para permitir peticiones desde tu dominio
3. Asegúrate de usar HTTPS en producción

## 🔐 Seguridad

- El token de autenticación se guarda en `localStorage`
- Las peticiones incluyen el header `Authorization: Bearer <token>`
- La sesión se mantiene entre recargas de página
- El token se elimina al cerrar sesión

## 🎨 Personalización

### Colores

Edita las variables CSS en `styles.css`:

```css
:root {
    --primary-color: #2c3e50;
    --accent-color: #3498db;
    --success-color: #27ae60;
    /* ... más variables ... */
}
```

### Auto-refresh

Cambia el intervalo en `config.js`:

```javascript
const CONFIG = {
    autoRefreshInterval: 30000, // en milisegundos
};
```

O modifica directamente en `app.js`:

```javascript
// Línea final del archivo
setInterval(() => {
    if (authToken && mainContent.style.display !== 'none') {
        loadOrders();
    }
}, 30000); // Cambia este valor
```

## 📱 Compatibilidad

- ✅ Chrome/Edge (últimas 2 versiones)
- ✅ Firefox (últimas 2 versiones)
- ✅ Safari 12+
- ✅ Navegadores móviles modernos

## 🐛 Troubleshooting

### Los pedidos no cargan

1. Verifica que la URL en `config.js` sea correcta
2. Abre la consola del navegador (F12) y revisa los errores
3. Verifica que CORS esté configurado correctamente en tu API
4. Confirma que el token de autenticación sea válido

### Error de autenticación

1. Verifica las credenciales del empleado
2. Confirma que el endpoint de login sea correcto
3. Revisa que la API devuelva un token válido

### Los estilos no se ven correctamente

1. Verifica que los archivos CSS y JS estén en la misma carpeta
2. Limpia la caché del navegador (Ctrl+Shift+R)
3. Confirma que no haya errores en la consola

## 📝 Licencia

Proyecto creado para 200 Millas - Sistema de gestión de pedidos

---

**¿Necesitas ayuda?** Revisa la consola del navegador (F12) para más detalles sobre errores.
