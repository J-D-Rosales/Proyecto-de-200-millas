// ==================== API Configuration ====================
// URLs reales del backend del proyecto 200 Millas

const API_CONFIG = {
    // URLs base por microservicio
    usersUrl: 'https://zq0fbveqte.execute-api.us-east-1.amazonaws.com',
    empleadoUrl: 'https://cmkk23rz22.execute-api.us-east-1.amazonaws.com',
    clientesUrl: 'https://2tkz55hms1.execute-api.us-east-1.amazonaws.com',
    productsUrl: 'https://y6am9ly97g.execute-api.us-east-1.amazonaws.com',
    analyticUrl: 'https://9chtp1assj.execute-api.us-east-1.amazonaws.com',
    
    // ID del local por defecto
    localId: 'LOCAL-001',
    
    // Endpoints específicos
    endpoints: {
        // Users - Autenticación
        login: '/users/login',
        register: '/users/register',
        me: '/users/me',
        
        // Empleados - Cambio de estado pedidos
        cocinaIniciar: '/empleados/cocina/iniciar',
        cocinaCompletar: '/empleados/cocina/completar',
        empaqueCompletar: '/empleados/empaque/completar',
        deliveryIniciar: '/empleados/delivery/iniciar',
        deliveryEntregar: '/empleados/delivery/entregar',
        
        // Pedidos - Cliente
        pedidoCreate: '/pedido/create',
        pedidoStatus: '/pedido/status',
        pedidoConfirmar: '/pedido/confirmar',
        
        // Productos
        productosList: '/productos/list',
        
        // Analytics
        analyticsPedidosPorLocal: '/analytics/pedidos-por-local',
        analyticsGananciasPorLocal: '/analytics/ganancias-por-local',
        analyticsTiempoPedido: '/analytics/tiempo-pedido'
    }
};

// ==================== Configuración de Estados ====================
// Estados del flujo de pedidos según la API
const ESTADOS_PEDIDO = {
    PROCESANDO: 'procesando',
    EN_PREPARACION: 'en_preparacion',
    PEDIDO_EN_COCINA: 'pedido_en_cocina',
    COCINA_COMPLETA: 'cocina_completa',
    EMPAQUETADO: 'empaquetado',
    PEDIDO_EN_CAMINO: 'pedido_en_camino',
    ENTREGADO: 'entregado',
    CANCELADO: 'cancelado'
};

// Roles de usuario
const ROLES = {
    CLIENTE: 'Cliente',
    GERENTE: 'Gerente',
    COCINERO: 'Cocinero',
    REPARTIDOR: 'Repartidor',
    DESPACHADOR: 'Despachador'
};

// ==================== Configuración de Auto-refresh ====================
const CONFIG = {
    // Intervalo de actualización automática en milisegundos (30 segundos por defecto)
    autoRefreshInterval: 30000,
    
    // Tiempo de espera para las peticiones HTTP en milisegundos
    requestTimeout: 10000,
};

// ==================== Instrucciones de Configuración ====================
/*
PASOS PARA CONFIGURAR:

1. Actualiza la URL base (baseUrl) con la URL de tu API Gateway de AWS:
   - Ejemplo: 'https://abc123.execute-api.us-east-1.amazonaws.com/dev'

2. Verifica que los endpoints coincidan con tus lambdas:
   - login: Endpoint para autenticar empleados
   - orders: Endpoint para obtener lista de pedidos
   - updateStatus: Endpoint para cambiar el estado de un pedido
   - orderDetail: Endpoint para obtener detalles de un pedido (opcional)

3. Ajusta los estados según tu flujo de trabajo si es necesario

4. Si tus endpoints requieren un formato diferente, modifica también
   el código en app.js donde se hacen las peticiones fetch()

EJEMPLO DE CONFIGURACIÓN:
const API_CONFIG = {
    baseUrl: 'https://xyz789.execute-api.us-east-1.amazonaws.com/prod',
    endpoints: {
        login: '/api/auth/login',
        orders: '/api/orders/list',
        updateStatus: '/api/orders/update-status',
        orderDetail: '/api/orders/{id}'
    }
};
*/
