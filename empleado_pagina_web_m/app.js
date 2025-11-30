// ==================== Global State ====================
let authToken = null;
let currentUser = null;
let allOrders = [];
let currentFilter = 'todos';
let selectedOrder = null;
let isAdmin = false;

// ==================== DOM Elements ====================
const loginSection = document.getElementById('loginSection');
const mainContent = document.getElementById('mainContent');
const userName = document.getElementById('userName');
const btnLogout = document.getElementById('btnLogout');
const btnRefresh = document.getElementById('btnRefresh');
const filterEstado = document.getElementById('filterEstado');
const ordersGrid = document.getElementById('ordersGrid');
const emptyState = document.getElementById('emptyState');
const statusModal = document.getElementById('statusModal');
const modalClose = document.getElementById('modalClose');
const btnCancelModal = document.getElementById('btnCancelModal');
const btnConfirmStatus = document.getElementById('btnConfirmStatus');
const orderDetails = document.getElementById('orderDetails');
const newStatus = document.getElementById('newStatus');
const statusNote = document.getElementById('statusNote');

// ==================== Initialize ====================
document.addEventListener('DOMContentLoaded', () => {
    console.log('App initialized');
    setupEventListeners();
    checkAuth();
});

// ==================== Event Listeners ====================
function setupEventListeners() {
    const loginForm = document.getElementById('loginForm');
    const registerForm = document.getElementById('registerForm');
    const toggleFormBtn = document.getElementById('toggleFormBtn');
    
    if (loginForm) {
        loginForm.addEventListener('submit', handleLogin);
    }
    
    if (registerForm) {
        registerForm.addEventListener('submit', handleRegister);
    }
    
    if (toggleFormBtn) {
        toggleFormBtn.addEventListener('click', function(e) {
            e.preventDefault();
            e.stopPropagation();
            toggleForm();
        });
    }
    
    if (btnLogout) btnLogout.addEventListener('click', handleLogout);
    if (btnRefresh) btnRefresh.addEventListener('click', loadOrders);
    if (filterEstado) filterEstado.addEventListener('change', handleFilterChange);
    if (modalClose) modalClose.addEventListener('click', closeModal);
    if (btnCancelModal) btnCancelModal.addEventListener('click', closeModal);
    if (btnConfirmStatus) btnConfirmStatus.addEventListener('click', handleStatusChange);
    
    const changeStatusForm = document.getElementById('changeStatusForm');
    if (changeStatusForm) {
        changeStatusForm.addEventListener('submit', handleChangeStatusForm);
    }
    
    const consultStatusForm = document.getElementById('consultStatusForm');
    if (consultStatusForm) {
        consultStatusForm.addEventListener('submit', handleConsultStatusForm);
    }
    
    if (statusModal) {
        statusModal.addEventListener('click', (e) => {
            if (e.target === statusModal) {
                closeModal();
            }
        });
    }
}

// ==================== Authentication ====================
function checkAuth() {
    const savedToken = localStorage.getItem('authToken');
    const savedUser = localStorage.getItem('currentUser');
    const savedIsAdmin = localStorage.getItem('isAdmin');
    
    if (savedToken && savedUser) {
        authToken = savedToken;
        currentUser = JSON.parse(savedUser);
        isAdmin = savedIsAdmin === 'true';
        showMainContent();
        if (isAdmin) {
            showAnalytics();
        } else {
            loadOrders();
        }
    } else {
        showLoginSection();
    }
}

async function handleLogin(e) {
    e.preventDefault();
    
    const email = document.getElementById('loginEmail').value.trim();
    const password = document.getElementById('loginPassword').value;
    const loginError = document.getElementById('loginError');
    
    // Validaciones básicas
    if (!email || !password) {
        loginError.textContent = 'Por favor ingresa email y contraseña';
        loginError.classList.add('show');
        return;
    }
    
    loginError.classList.remove('show');
    loginError.textContent = '';
    
    // Disable submit button
    const submitBtn = loginForm.querySelector('button[type="submit"]');
    const originalText = submitBtn.textContent;
    submitBtn.disabled = true;
    submitBtn.textContent = 'Iniciando sesión...';
    
    try {
        // Llamada real a la API de users/login
        const response = await fetch(`${API_CONFIG.usersUrl}${API_CONFIG.endpoints.login}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ 
                correo: email, 
                contrasena: password 
            })
        });
        
        if (!response.ok) {
            const errorData = await response.json().catch(() => ({}));
            throw new Error(errorData.message || errorData.error || 'Credenciales inválidas');
        }
        
        const data = await response.json();
        
        // Response: {token, rol, correo, expires, message}
        if (data.token) {
            authToken = data.token;
            currentUser = { 
                email: data.correo,
                rol: data.rol,
                nombre: data.nombre || email.split('@')[0]
            };
            
            // Verificar si es Gerente para mostrar analytics
            isAdmin = (data.rol === 'Gerente' || data.rol === 'Admin');
            
            // Save to localStorage
            localStorage.setItem('authToken', authToken);
            localStorage.setItem('currentUser', JSON.stringify(currentUser));
            localStorage.setItem('isAdmin', isAdmin ? 'true' : 'false');
            
            showMainContent();
            
            if (isAdmin) {
                // Gerente: cargar analytics desde API
                await loadAnalytics();
                showNotification(`¡Bienvenido ${currentUser.nombre}! (${currentUser.rol})`, 'success');
            } else {
                // Empleado: cargar pedidos reales
                await loadOrders();
                showNotification(`¡Bienvenido ${currentUser.nombre}! (${currentUser.rol})`, 'success');
            }
        } else {
            throw new Error('Respuesta inválida del servidor');
        }
    } catch (error) {
        console.error('Error en login:', error);
        loginError.textContent = error.message || 'Error al iniciar sesión. Intenta de nuevo.';
        loginError.classList.add('show');
    } finally {
        submitBtn.disabled = false;
        submitBtn.textContent = originalText;
    }
}

async function handleRegister(e) {
    e.preventDefault();
    
    const nombre = document.getElementById('registerNombre').value.trim();
    const email = document.getElementById('registerEmail').value.trim();
    const password = document.getElementById('registerPassword').value;
    const role = document.getElementById('registerRole').value;
    const registerError = document.getElementById('registerError');
    
    // Validaciones básicas
    if (!nombre || !email || !password || !role) {
        registerError.textContent = 'Por favor completa todos los campos';
        registerError.classList.add('show');
        return;
    }
    
    registerError.classList.remove('show');
    registerError.textContent = '';
    
    // Disable submit button
    const submitBtn = registerForm.querySelector('button[type="submit"]');
    const originalText = submitBtn.textContent;
    submitBtn.disabled = true;
    submitBtn.textContent = 'Registrando...';
    
    try {
        // Llamada real a la API de users/register
        const response = await fetch(`${API_CONFIG.usersUrl}${API_CONFIG.endpoints.register}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ 
                nombre: nombre,
                correo: email, 
                contrasena: password,
                role: role
            })
        });
        
        if (!response.ok) {
            const errorData = await response.json().catch(() => ({}));
            throw new Error(errorData.message || errorData.error || 'Error al registrar');
        }
        
        const data = await response.json();
        
        // Response: {token, rol, correo, expires, message}
        if (data.token) {
            // Auto-login después del registro
            authToken = data.token;
            currentUser = { 
                email: data.correo,
                rol: data.rol,
                nombre: nombre
            };
            
            isAdmin = (data.rol === 'Gerente' || data.rol === 'Admin');
            
            // Save to localStorage
            localStorage.setItem('authToken', authToken);
            localStorage.setItem('currentUser', JSON.stringify(currentUser));
            localStorage.setItem('isAdmin', isAdmin ? 'true' : 'false');
            
            showMainContent();
            
            if (isAdmin) {
                await loadAnalytics();
                showNotification(`¡Registro exitoso! Bienvenido ${currentUser.nombre} (${currentUser.rol})`, 'success');
            } else {
                await loadOrders();
                showNotification(`¡Registro exitoso! Bienvenido ${currentUser.nombre} (${currentUser.rol})`, 'success');
            }
        } else {
            throw new Error('Respuesta inválida del servidor');
        }
    } catch (error) {
        console.error('Error en registro:', error);
        registerError.textContent = error.message || 'Error al registrar. Intenta de nuevo.';
        registerError.classList.add('show');
    } finally {
        submitBtn.disabled = false;
        submitBtn.textContent = originalText;
    }
}

function toggleForm() {
    const loginForm = document.getElementById('loginForm');
    const registerForm = document.getElementById('registerForm');
    const formTitle = document.getElementById('formTitle');
    const toggleBtn = document.getElementById('toggleFormBtn');
    
    if (!loginForm || !registerForm || !formTitle || !toggleBtn) {
        return;
    }
    
    const isLoginVisible = window.getComputedStyle(loginForm).display !== 'none';
    
    if (isLoginVisible) {
        loginForm.style.display = 'none';
        registerForm.style.display = 'block';
        formTitle.textContent = 'Registrarse';
        toggleBtn.textContent = '¿Ya tienes cuenta? Inicia sesión';
    } else {
        loginForm.style.display = 'block';
        registerForm.style.display = 'none';
        formTitle.textContent = 'Iniciar Sesión';
        toggleBtn.textContent = '¿No tienes cuenta? Regístrate';
    }
}

function handleLogout() {
    authToken = null;
    currentUser = null;
    isAdmin = false;
    allOrders = [];
    
    localStorage.removeItem('authToken');
    localStorage.removeItem('currentUser');
    localStorage.removeItem('isAdmin');
    
    // Limpiar formularios y errores
    const loginEmail = document.getElementById('loginEmail');
    const loginPassword = document.getElementById('loginPassword');
    const loginError = document.getElementById('loginError');
    const registerError = document.getElementById('registerError');
    
    if (loginEmail) loginEmail.value = '';
    if (loginPassword) loginPassword.value = '';
    if (loginError) {
        loginError.classList.remove('show');
        loginError.textContent = '';
        loginError.style.display = 'none';
    }
    if (registerError) {
        registerError.classList.remove('show');
        registerError.textContent = '';
        registerError.style.display = 'none';
    }
    
    showLoginSection();
    showNotification('Sesión cerrada correctamente', 'info');
}

function showLoginSection() {
    loginSection.style.display = 'flex';
    mainContent.style.display = 'none';
    
    // Ocultar ambas secciones
    const analyticsSection = document.getElementById('analyticsSection');
    const ordersSection = document.getElementById('ordersSection');
    if (analyticsSection) analyticsSection.style.display = 'none';
    if (ordersSection) ordersSection.style.display = 'none';
}

function showMainContent() {
    loginSection.style.display = 'none';
    mainContent.style.display = 'block';
    userName.textContent = currentUser?.nombre || currentUser?.email || 'Empleado';
    
    // Mostrar la vista correcta según el tipo de usuario
    if (isAdmin) {
        showAnalytics();
    } else {
        showOrdersView();
    }
}

// ==================== Orders Management ====================
async function loadOrders() {
    // No hacer nada, los empleados usan los formularios directamente
}

function renderOrders() {
    if (!ordersGrid || !emptyState) return;
    
    const filteredOrders = currentFilter === 'todos' 
        ? allOrders 
        : allOrders.filter(order => order.estado === currentFilter);
    
    if (filteredOrders.length === 0) {
        ordersGrid.style.display = 'none';
        emptyState.style.display = 'block';
    } else {
        ordersGrid.style.display = 'grid';
        emptyState.style.display = 'none';
        
        ordersGrid.innerHTML = filteredOrders
            .sort((a, b) => new Date(b.fecha_creacion || b.created_at) - new Date(a.fecha_creacion || a.created_at))
            .map(order => createOrderCard(order))
            .join('');
        
        // Add click listeners to order cards
        document.querySelectorAll('.order-card').forEach(card => {
            card.addEventListener('click', () => {
                const orderId = card.dataset.orderId;
                const order = allOrders.find(o => o.id === orderId || o.pedido_id === orderId);
                if (order) {
                    openStatusModal(order);
                }
            });
        });
    }
    
    // Si es admin, actualizar también el analytics
    if (isAdmin && allOrders.length > 0) {
        calculateAndRenderAnalytics();
    }
}

function createOrderCard(order) {
    const orderId = order.id || order.pedido_id || 'N/A';
    const estado = order.estado || 'pendiente';
    const cliente = order.cliente_nombre || order.usuario_nombre || 'Cliente';
    const total = order.total ? `$${parseFloat(order.total).toFixed(2)}` : 'N/A';
    const productos = order.productos || order.items || [];
    const fecha = order.fecha_creacion || order.created_at;
    
    const productosHTML = productos.length > 0 
        ? productos.slice(0, 3).map(p => 
            `<div>• ${p.nombre || p.producto_nombre || 'Producto'} (x${p.cantidad || 1})</div>`
          ).join('') + (productos.length > 3 ? `<div>• ...y ${productos.length - 3} más</div>` : '')
        : '<div>Sin productos</div>';
    
    const estadoLabel = getEstadoLabel(estado);
    const timeAgo = fecha ? getTimeAgo(new Date(fecha)) : '';
    
    return `
        <div class="order-card" data-order-id="${orderId}">
            <div class="order-header">
                <span class="order-id">Pedido #${orderId}</span>
                <span class="order-status status-${estado}">${estadoLabel}</span>
            </div>
            <div class="order-info">
                <div class="order-info-row">
                    <span class="order-label">Cliente:</span>
                    <span class="order-value">${cliente}</span>
                </div>
                <div class="order-info-row">
                    <span class="order-label">Total:</span>
                    <span class="order-value">${total}</span>
                </div>
            </div>
            <div class="order-products">
                <div class="order-products-title">Productos:</div>
                <div class="order-products-list">${productosHTML}</div>
            </div>
            ${timeAgo ? `<div class="order-time">${timeAgo}</div>` : ''}
        </div>
    `;
}

function getEstadoLabel(estado) {
    const labels = {
        'pendiente': 'Pendiente',
        'en_preparacion': 'En Preparación',
        'en_cocina': 'En Cocina',
        'empaquetado': 'Empaquetado',
        'en_delivery': 'En Delivery',
        'entregado': 'Entregado',
        'cancelado': 'Cancelado'
    };
    return labels[estado] || estado;
}

function getTimeAgo(date) {
    const seconds = Math.floor((new Date() - date) / 1000);
    
    if (seconds < 60) return 'Hace un momento';
    if (seconds < 3600) return `Hace ${Math.floor(seconds / 60)} min`;
    if (seconds < 86400) return `Hace ${Math.floor(seconds / 3600)} hrs`;
    return `Hace ${Math.floor(seconds / 86400)} días`;
}

function handleFilterChange(e) {
    currentFilter = e.target.value;
    renderOrders();
}

// ==================== Status Modal ====================
function openStatusModal(order) {
    selectedOrder = order;
    const orderId = order.id || order.pedido_id || 'N/A';
    const estado = order.estado || 'pendiente';
    const cliente = order.cliente_nombre || order.usuario_nombre || 'Cliente';
    const total = order.total ? `$${parseFloat(order.total).toFixed(2)}` : 'N/A';
    
    orderDetails.innerHTML = `
        <div class="order-details-row">
            <span class="order-details-label">Pedido ID:</span>
            <span class="order-details-value">#${orderId}</span>
        </div>
        <div class="order-details-row">
            <span class="order-details-label">Cliente:</span>
            <span class="order-details-value">${cliente}</span>
        </div>
        <div class="order-details-row">
            <span class="order-details-label">Estado Actual:</span>
            <span class="order-details-value">${getEstadoLabel(estado)}</span>
        </div>
        <div class="order-details-row">
            <span class="order-details-label">Total:</span>
            <span class="order-details-value">${total}</span>
        </div>
    `;
    
    newStatus.value = '';
    statusNote.value = '';
    modalError.classList.remove('show');
    modalError.textContent = '';
    
    statusModal.classList.add('show');
}

function closeModal() {
    statusModal.classList.remove('show');
    selectedOrder = null;
}

async function handleStatusChange() {
    const newStatusValue = newStatus.value;
    const modalError = document.getElementById('modalError');
    
    if (!newStatusValue) {
        modalError.textContent = 'Por favor selecciona un estado';
        modalError.classList.add('show');
        return;
    }
    
    if (!selectedOrder) {
        modalError.textContent = 'Error: pedido no seleccionado';
        modalError.classList.add('show');
        return;
    }
    
    modalError.classList.remove('show');
    btnConfirmStatus.disabled = true;
    btnConfirmStatus.classList.add('loading');
    
    try {
        const orderId = selectedOrder.id || selectedOrder.pedido_id;
        
        // Determinar el endpoint correcto según el nuevo estado
        let endpoint = '';
        let payload = {
            order_id: orderId,
            empleado_id: currentUser.dni || '12345678' // Usar DNI del empleado si está disponible
        };
        
        // Mapear estado a endpoint correcto de la API
        switch (newStatusValue) {
            case 'en_preparacion':
                endpoint = `${API_CONFIG.empleadoUrl}${API_CONFIG.endpoints.cocinaIniciar}`;
                break;
            case 'cocina_completa':
                endpoint = `${API_CONFIG.empleadoUrl}${API_CONFIG.endpoints.cocinaCompletar}`;
                break;
            case 'empaquetado':
                endpoint = `${API_CONFIG.empleadoUrl}${API_CONFIG.endpoints.empaqueCompletar}`;
                break;
            case 'pedido_en_camino':
                endpoint = `${API_CONFIG.empleadoUrl}${API_CONFIG.endpoints.deliveryIniciar}`;
                break;
            case 'entregado':
                endpoint = `${API_CONFIG.empleadoUrl}${API_CONFIG.endpoints.deliveryEntregar}`;
                break;
            default:
                throw new Error('Estado no válido para cambio');
        }
        
        const response = await fetch(endpoint, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(payload)
        });
        
        if (!response.ok) {
            const errorData = await response.json().catch(() => ({}));
            throw new Error(errorData.message || 'Error al actualizar el estado');
        }
        
        const data = await response.json();
        showNotification(data.message || 'Estado actualizado correctamente', 'success');
        closeModal();
        
        // Actualizar el pedido localmente
        const orderIndex = allOrders.findIndex(o => 
            (o.id || o.pedido_id) === orderId
        );
        if (orderIndex !== -1) {
            allOrders[orderIndex].estado = newStatusValue;
            renderOrders();
        }
    } catch (error) {
        console.error('Error updating status:', error);
        modalError.textContent = error.message || 'Error al actualizar el estado';
        modalError.classList.add('show');
    } finally {
        btnConfirmStatus.disabled = false;
        btnConfirmStatus.classList.remove('loading');
    }
}

// ==================== Notifications ====================
function showNotification(message, type = 'info') {
    // Create notification element
    const notification = document.createElement('div');
    notification.className = `notification notification-${type}`;
    notification.textContent = message;
    notification.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        padding: 1rem 1.5rem;
        background: ${type === 'success' ? '#27ae60' : type === 'error' ? '#e74c3c' : '#3498db'};
        color: white;
        border-radius: 8px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        z-index: 10000;
        animation: slideInRight 0.3s ease;
    `;
    
    document.body.appendChild(notification);
    
    setTimeout(() => {
        notification.style.animation = 'slideOutRight 0.3s ease';
        setTimeout(() => notification.remove(), 300);
    }, 3000);
}

// Add CSS animations for notifications
const style = document.createElement('style');
style.textContent = `
    @keyframes slideInRight {
        from {
            transform: translateX(100%);
            opacity: 0;
        }
        to {
            transform: translateX(0);
            opacity: 1;
        }
    }
    
    @keyframes slideOutRight {
        from {
            transform: translateX(0);
            opacity: 1;
        }
        to {
            transform: translateX(100%);
            opacity: 0;
        }
    }
`;
document.head.appendChild(style);

// ==================== Analytics Functions (Admin) ====================
function showAnalytics() {
    const analyticsSection = document.getElementById('analyticsSection');
    const ordersSection = document.getElementById('ordersSection');
    
    if (analyticsSection && ordersSection) {
        analyticsSection.style.display = 'block';
        ordersSection.style.display = 'none';
        calculateAndRenderAnalytics();
    }
}

function showOrdersView() {
    const analyticsSection = document.getElementById('analyticsSection');
    const ordersSection = document.getElementById('ordersSection');
    
    if (analyticsSection && ordersSection) {
        analyticsSection.style.display = 'none';
        ordersSection.style.display = 'block';
    }
}

// ==================== Analytics Management ====================
async function loadAnalytics() {
    try {
        // Usar GET en lugar de POST para evitar CORS preflight
        const [pedidosResp, gananciasResp] = await Promise.all([
            fetch(`${API_CONFIG.analyticUrl}${API_CONFIG.endpoints.analyticsPedidosPorLocal}?local_id=${API_CONFIG.localId}`),
            fetch(`${API_CONFIG.analyticUrl}${API_CONFIG.endpoints.analyticsGananciasPorLocal}?local_id=${API_CONFIG.localId}`)
        ]);

        if (!pedidosResp.ok || !gananciasResp.ok) {
            throw new Error('Error al cargar analytics');
        }

        const pedidosData = await pedidosResp.json();
        const gananciasData = await gananciasResp.json();

        // Extraer datos de las respuestas
        const pedidosInfo = pedidosData.data && pedidosData.data[0] ? pedidosData.data[0] : {};
        const gananciasInfo = gananciasData.data && gananciasData.data[0] ? gananciasData.data[0] : {};

        // Actualizar KPIs con datos reales
        document.getElementById('kpiTotalPedidos').textContent = pedidosInfo.total_pedidos || 0;
        document.getElementById('kpiEntregados').textContent = gananciasInfo.total_pedidos || 0;
        document.getElementById('kpiIngresos').textContent = `$${(gananciasInfo.ganancias_totales || 0).toFixed(2)}`;
        document.getElementById('kpiEnProceso').textContent = '0'; // No hay datos de pedidos en proceso
        
        // Actualizar cambios/detalles
        const promedio = gananciasInfo.ganancia_promedio || 0;
        document.getElementById('kpiIngresosChange').textContent = `$${promedio.toFixed(2)} promedio`;
        document.getElementById('kpiTotalChange').textContent = `${pedidosInfo.total_pedidos || 0} total`;
        document.getElementById('kpiEntregadosChange').textContent = `${gananciasInfo.total_pedidos || 0} completados`;
        
        showNotification('Analytics cargados desde API', 'success');
    } catch (error) {
        console.error('Error loading analytics:', error);
        
        // Mostrar mensaje de error de CORS
        if (error.message.includes('fetch') || error.name === 'TypeError') {
            showNotification('Error de CORS: El backend necesita habilitar CORS para analytics. Configura access-control-allow-methods: GET,POST,OPTIONS', 'error');
            
            // Mostrar valores por defecto para que la UI no esté vacía
            document.getElementById('kpiTotalPedidos').textContent = '-';
            document.getElementById('kpiEntregados').textContent = '-';
            document.getElementById('kpiIngresos').textContent = '$0.00';
            document.getElementById('kpiEnProceso').textContent = '-';
            document.getElementById('kpiIngresosChange').textContent = 'CORS Error';
            document.getElementById('kpiTotalChange').textContent = 'Ver consola';
            document.getElementById('kpiEntregadosChange').textContent = 'Backend issue';
        } else {
            showNotification('Error al cargar analytics', 'error');
        }
    }
}

function calculateAndRenderAnalytics() {
    if (allOrders.length === 0) {
        return;
    }

    // Calcular estadísticas
    const stats = {
        total: allOrders.length,
        entregados: allOrders.filter(o => o.estado === 'entregado').length,
        enProceso: allOrders.filter(o => 
            ['en_preparacion', 'en_cocina', 'empaquetado', 'en_delivery'].includes(o.estado)
        ).length,
        pendientes: allOrders.filter(o => o.estado === 'pendiente').length,
        cancelados: allOrders.filter(o => o.estado === 'cancelado').length,
        ingresoTotal: allOrders
            .filter(o => o.estado === 'entregado')
            .reduce((sum, o) => sum + (parseFloat(o.total) || 0), 0)
    };

    // Distribución por estado
    const estadosCount = {
        pendiente: allOrders.filter(o => o.estado === 'pendiente').length,
        en_preparacion: allOrders.filter(o => o.estado === 'en_preparacion').length,
        en_cocina: allOrders.filter(o => o.estado === 'en_cocina').length,
        empaquetado: allOrders.filter(o => o.estado === 'empaquetado').length,
        en_delivery: allOrders.filter(o => o.estado === 'en_delivery').length,
        entregado: allOrders.filter(o => o.estado === 'entregado').length,
        cancelado: allOrders.filter(o => o.estado === 'cancelado').length
    };

    // Actualizar KPIs
    document.getElementById('kpiTotalPedidos').textContent = stats.total;
    document.getElementById('kpiEntregados').textContent = stats.entregados;
    document.getElementById('kpiEnProceso').textContent = stats.enProceso;
    document.getElementById('kpiEnProcesoDetalle').textContent = `${stats.pendientes} pendientes`;
    document.getElementById('kpiIngresos').textContent = `$${stats.ingresoTotal.toFixed(2)}`;

    // Calcular porcentajes de cambio
    const tasaEntrega = stats.total > 0 ? ((stats.entregados / stats.total) * 100).toFixed(1) : 0;
    document.getElementById('kpiTotalChange').textContent = `${tasaEntrega}% completados`;
    document.getElementById('kpiEntregadosChange').textContent = `${tasaEntrega}% del total`;
    
    const promedioIngresos = stats.entregados > 0 ? (stats.ingresoTotal / stats.entregados).toFixed(2) : 0;
    document.getElementById('kpiIngresosChange').textContent = `$${promedioIngresos} promedio`;

    // Renderizar gráfico de estados
    renderEstadoChart(estadosCount);

    // Renderizar barras de métricas
    renderMetricBars(estadosCount, stats.total);

    // Renderizar detalles
    renderEstadosDetails(estadosCount, stats.total);
}

function renderEstadoChart(estadosCount) {
    const chartContainer = document.getElementById('estadoChart').parentElement;
    const legendContainer = document.getElementById('estadoLegend');

    const estadosInfo = [
        { key: 'pendiente', label: 'Pendiente', color: '#f39c12' },
        { key: 'en_preparacion', label: 'En Preparación', color: '#3498db' },
        { key: 'en_cocina', label: 'En Cocina', color: '#ff8c42' },
        { key: 'empaquetado', label: 'Empaquetado', color: '#17a2b8' },
        { key: 'en_delivery', label: 'En Delivery', color: '#9b59b6' },
        { key: 'entregado', label: 'Entregado', color: '#27ae60' },
        { key: 'cancelado', label: 'Cancelado', color: '#e74c3c' }
    ];

    // Crear gráfico simple con CSS (ya que no tenemos Chart.js)
    const total = Object.values(estadosCount).reduce((a, b) => a + b, 0);
    
    let chartHTML = '<div style="display: flex; flex-direction: column; gap: 1rem; padding: 2rem 1rem;">';
    
    estadosInfo.forEach(estado => {
        const count = estadosCount[estado.key] || 0;
        const percentage = total > 0 ? ((count / total) * 100).toFixed(1) : 0;
        
        if (count > 0) {
            chartHTML += `
                <div style="display: flex; align-items: center; gap: 1rem;">
                    <div style="width: 12px; height: 12px; background-color: ${estado.color}; border-radius: 3px;"></div>
                    <div style="flex: 1;">
                        <div style="display: flex; justify-content: space-between; margin-bottom: 0.25rem; font-size: 0.9rem;">
                            <span style="color: var(--text-primary); font-weight: 500;">${estado.label}</span>
                            <span style="color: var(--text-secondary);">${count} (${percentage}%)</span>
                        </div>
                        <div style="height: 8px; background-color: var(--bg-tertiary); border-radius: 4px; overflow: hidden;">
                            <div style="height: 100%; width: ${percentage}%; background-color: ${estado.color}; transition: width 0.8s ease;"></div>
                        </div>
                    </div>
                </div>
            `;
        }
    });
    
    chartHTML += '</div>';
    chartContainer.innerHTML = chartHTML;

    // Leyenda
    let legendHTML = '';
    estadosInfo.forEach(estado => {
        const count = estadosCount[estado.key] || 0;
        if (count > 0) {
            legendHTML += `
                <div class="legend-item">
                    <div class="legend-color" style="background-color: ${estado.color};"></div>
                    <span class="legend-label">${estado.label}</span>
                    <span class="legend-value">${count}</span>
                </div>
            `;
        }
    });
    legendContainer.innerHTML = legendHTML;
}

function renderMetricBars(estadosCount, total) {
    const container = document.getElementById('metricBars');
    
    const metrics = [
        {
            label: 'Tasa de Entrega',
            value: estadosCount.entregado,
            max: total,
            color: '#27ae60',
            suffix: 'pedidos'
        },
        {
            label: 'En Proceso',
            value: estadosCount.en_preparacion + estadosCount.en_cocina + estadosCount.empaquetado,
            max: total,
            color: '#3498db',
            suffix: 'pedidos'
        },
        {
            label: 'En Delivery',
            value: estadosCount.en_delivery,
            max: total,
            color: '#9b59b6',
            suffix: 'pedidos'
        },
        {
            label: 'Tasa de Cancelación',
            value: estadosCount.cancelado,
            max: total,
            color: '#e74c3c',
            suffix: 'pedidos'
        }
    ];

    let html = '';
    metrics.forEach(metric => {
        const percentage = metric.max > 0 ? ((metric.value / metric.max) * 100).toFixed(1) : 0;
        html += `
            <div class="metric-bar-item">
                <div class="metric-bar-header">
                    <span class="metric-bar-label">${metric.label}</span>
                    <span class="metric-bar-value">${metric.value} ${metric.suffix} (${percentage}%)</span>
                </div>
                <div class="metric-bar-track">
                    <div class="metric-bar-fill" style="width: ${percentage}%; background-color: ${metric.color};"></div>
                </div>
            </div>
        `;
    });

    container.innerHTML = html;
}

function renderEstadosDetails(estadosCount, total) {
    const container = document.getElementById('estadosDetails');
    
    const estadosInfo = [
        { key: 'pendiente', label: 'Pendiente' },
        { key: 'en_preparacion', label: 'En Preparación' },
        { key: 'en_cocina', label: 'En Cocina' },
        { key: 'empaquetado', label: 'Empaquetado' },
        { key: 'en_delivery', label: 'En Delivery' },
        { key: 'entregado', label: 'Entregado' },
        { key: 'cancelado', label: 'Cancelado' }
    ];

    let html = '';
    estadosInfo.forEach(estado => {
        const count = estadosCount[estado.key] || 0;
        const percentage = total > 0 ? ((count / total) * 100).toFixed(1) : 0;
        
        html += `
            <div class="detail-item ${estado.key}">
                <div class="detail-item-label">${estado.label}</div>
                <div class="detail-item-value">${count}</div>
                <div class="detail-item-percentage">${percentage}% del total</div>
            </div>
        `;
    });

    container.innerHTML = html;
}

// ==================== Formulario de cambio de estado ====================
async function handleChangeStatusForm(e) {
    e.preventDefault();
    
    const orderId = document.getElementById('orderIdInput').value.trim();
    const empleadoId = document.getElementById('empleadoIdInput').value.trim();
    const action = document.getElementById('statusActionSelect').value;
    const errorElement = document.getElementById('statusChangeError');
    
    if (!orderId || !empleadoId || !action) {
        errorElement.textContent = 'Por favor completa todos los campos';
        errorElement.classList.add('show');
        return;
    }
    
    errorElement.classList.remove('show');
    errorElement.textContent = '';
    
    const endpoints = {
        'cocina_iniciar': `${API_CONFIG.empleadoUrl}/empleados/cocina/iniciar`,
        'cocina_completar': `${API_CONFIG.empleadoUrl}/empleados/cocina/completar`,
        'empaque_completar': `${API_CONFIG.empleadoUrl}/empleados/empaque/completar`,
        'delivery_iniciar': `${API_CONFIG.empleadoUrl}/empleados/delivery/iniciar`,
        'delivery_entregar': `${API_CONFIG.empleadoUrl}/empleados/delivery/entregar`
    };
    
    const endpoint = endpoints[action];
    
    try {
        const response = await fetch(endpoint, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                order_id: orderId,
                empleado_id: empleadoId
            })
        });
        
        if (!response.ok) {
            const errorData = await response.json().catch(() => ({}));
            throw new Error(errorData.message || errorData.error || 'Error al cambiar estado');
        }
        
        const data = await response.json();
        showNotification('Estado cambiado exitosamente', 'success');
        
        document.getElementById('orderIdInput').value = '';
        document.getElementById('statusActionSelect').value = '';
        
    } catch (error) {
        console.error('Error changing status:', error);
        errorElement.textContent = error.message || 'Error al cambiar el estado del pedido';
        errorElement.classList.add('show');
    }
}

// ==================== Consultar estado de pedido ====================
async function handleConsultStatusForm(e) {
    e.preventDefault();
    
    const orderId = document.getElementById('consultOrderIdInput').value.trim();
    const resultElement = document.getElementById('orderStatusResult');
    
    if (!orderId) {
        resultElement.innerHTML = '<p style="color: #e74c3c;">Por favor ingresa un Order ID</p>';
        return;
    }
    
    resultElement.innerHTML = '<p>Consultando...</p>';
    
    try {
        const response = await fetch(
            `${API_CONFIG.clientesUrl}/pedido/status?local_id=${API_CONFIG.localId}&pedido_id=${orderId}`
        );
        
        if (!response.ok) {
            throw new Error('Pedido no encontrado');
        }
        
        const data = await response.json();
        
        const estadoLabel = getEstadoLabel(data.estado || data.status);
        const productos = data.productos || data.items || [];
        
        let productosHTML = '';
        if (productos.length > 0) {
            productosHTML = '<ul style="margin: 10px 0; padding-left: 20px;">';
            productos.forEach(p => {
                productosHTML += `<li>${p.nombre || p.producto_nombre} x${p.cantidad}</li>`;
            });
            productosHTML += '</ul>';
        }
        
        resultElement.innerHTML = `
            <div style="background: #f8f9fa; padding: 15px; border-radius: 8px; border-left: 4px solid #3498db;">
                <h4 style="margin: 0 0 10px 0;">Pedido #${data.pedido_id || orderId}</h4>
                <p><strong>Estado:</strong> <span class="status-${data.estado || data.status}">${estadoLabel}</span></p>
                <p><strong>Cliente:</strong> ${data.usuario_email || data.cliente || 'N/A'}</p>
                <p><strong>Total:</strong> $${parseFloat(data.total || 0).toFixed(2)}</p>
                ${productos.length > 0 ? '<p><strong>Productos:</strong></p>' + productosHTML : ''}
                <p style="font-size: 12px; color: #7f8c8d; margin-top: 10px;">
                    <strong>Fecha:</strong> ${new Date(data.fecha_creacion || Date.now()).toLocaleString()}
                </p>
            </div>
        `;
        
    } catch (error) {
        console.error('Error consulting status:', error);
        resultElement.innerHTML = `<p style="color: #e74c3c;">Error: ${error.message}</p>`;
    }
}

// ==================== Auto-refresh ====================
// Refresh orders every 30 seconds
setInterval(() => {
    if (authToken && mainContent.style.display !== 'none') {
        loadOrders();
        if (isAdmin && document.getElementById('analyticsSection').style.display !== 'none') {
            calculateAndRenderAnalytics();
        }
    }
}, 30000);
