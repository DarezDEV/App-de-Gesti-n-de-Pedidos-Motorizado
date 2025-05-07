// background-tracking.js
// Script para integrar el Service Worker y el seguimiento en segundo plano

// Variables de estado
let serviceWorkerRegistration = null;
let backgroundTrackingActive = false;
let lastPosition = null;
let orderId = null;
let userRole = null;
let backgroundSyncStatus = 'inactive';
let lastBackgroundSync = null;

// Inicialización del módulo
function initBackgroundTracking(_orderId, _userRole) {
    orderId = _orderId;
    userRole = _userRole;
    
    // Mostrar indicador de estado del seguimiento en segundo plano
    addBackgroundTrackingIndicator();
    
    // Registrar Service Worker si es compatible
    if ('serviceWorker' in navigator && 'PushManager' in window) {
        registerServiceWorker();
        setupBeforeUnloadHandler();
        setupVisibilityChangeHandler();
    } else {
        console.warn('Este navegador no soporta Service Workers o notificaciones Push');
        updateBackgroundStatus('no-support', 'Este navegador no soporta seguimiento en segundo plano');
    }
}

// Registrar el Service Worker
function registerServiceWorker() {
    navigator.serviceWorker.register('/service-worker.js')
        .then(registration => {
            serviceWorkerRegistration = registration;
            console.log('Service Worker registrado correctamente');
            
            // Comprobar permisos de notificación
            checkNotificationPermission();
            
            // Escuchar mensajes del Service Worker
            navigator.serviceWorker.addEventListener('message', event => {
                const data = event.data;
                if (data && data.type === 'syncSuccess') {
                    lastBackgroundSync = new Date(data.timestamp);
                    updateBackgroundStatus('active', `Última sincronización: ${formatTime(lastBackgroundSync)}`);
                }
            });
            
            updateBackgroundStatus('registered', 'Service Worker registrado');
        })
        .catch(error => {
            console.error('Error al registrar el Service Worker:', error);
            updateBackgroundStatus('error', 'Error al registrar el Service Worker');
        });
}

// Comprobar y solicitar permisos de notificación
function checkNotificationPermission() {
    if (Notification.permission === 'granted') {
        updateBackgroundStatus('permission-granted', 'Notificaciones permitidas');
    } else if (Notification.permission !== 'denied') {
        Notification.requestPermission().then(permission => {
            if (permission === 'granted') {
                updateBackgroundStatus('permission-granted', 'Notificaciones permitidas');
            } else {
                updateBackgroundStatus('permission-denied', 'Notificaciones denegadas');
                console.warn('Las notificaciones han sido denegadas');
            }
        });
    } else {
        updateBackgroundStatus('permission-denied', 'Notificaciones denegadas');
        console.warn('Las notificaciones ya fueron denegadas previamente');
    }
}

// Actualizar la posición y enviar al Service Worker
function updatePositionInBackground(position) {
    if (!backgroundTrackingActive) return;
    
    lastPosition = {
        lat: position.coords.latitude,
        lon: position.coords.longitude,
        accuracy: position.coords.accuracy
    };
    
    // Enviar la posición al Service Worker
    if (navigator.serviceWorker.controller) {
        navigator.serviceWorker.controller.postMessage({
            action: 'updatePosition',
            position: lastPosition
        });
    }
}

// Iniciar seguimiento en segundo plano
function startBackgroundTracking(initialPosition) {
    if (!serviceWorkerRegistration || backgroundTrackingActive) return;
    
    if (initialPosition) {
        lastPosition = {
            lat: initialPosition[0],
            lon: initialPosition[1],
            accuracy: initialPosition[2] || null
        };
    }
    
    // Notificar al Service Worker que inicie el seguimiento
    navigator.serviceWorker.controller.postMessage({
        action: 'startTracking',
        orderId: orderId,
        role: userRole,
        position: lastPosition
    });
    
    backgroundTrackingActive = true;
    updateBackgroundStatus('active', 'Seguimiento en segundo plano activo');
    
    // Mostrar notificación al usuario
    showBackgroundTrackingNotification();
}

// Detener seguimiento en segundo plano
function stopBackgroundTracking() {
    if (!serviceWorkerRegistration || !backgroundTrackingActive) return;
    
    navigator.serviceWorker.controller.postMessage({
        action: 'stopTracking'
    });
    
    backgroundTrackingActive = false;
    updateBackgroundStatus('inactive', 'Seguimiento en segundo plano desactivado');
}

// Mostrar notificación de seguimiento activo
function showBackgroundTrackingNotification() {
    if (Notification.permission === 'granted' && serviceWorkerRegistration) {
        serviceWorkerRegistration.showNotification('Seguimiento GPS activo', {
            body: `Se está compartiendo tu ubicación para el pedido #${orderId}`,
            icon: '/static/img/logo.png',
            requireInteraction: false
        });
    }
}

// Configurar manejador para cuando el usuario abandona la página
function setupBeforeUnloadHandler() {
    window.addEventListener('beforeunload', () => {
        if (lastPosition) {
            // Guardar última posición conocida en localStorage
            localStorage.setItem('lastKnownPosition', JSON.stringify({
                orderId: orderId,
                role: userRole,
                position: lastPosition,
                timestamp: Date.now()
            }));
            
            // Iniciar seguimiento en segundo plano si no está activo
            if (!backgroundTrackingActive) {
                startBackgroundTracking([lastPosition.lat, lastPosition.lon, lastPosition.accuracy]);
            }
        }
    });
}

// Manejar cambios de visibilidad del documento
function setupVisibilityChangeHandler() {
    document.addEventListener('visibilitychange', () => {
        // Si la página se oculta y tenemos posición
        if (document.visibilityState === 'hidden' && lastPosition) {
            if (!backgroundTrackingActive) {
                startBackgroundTracking([lastPosition.lat, lastPosition.lon, lastPosition.accuracy]);
            }
        } 
        // Si la página vuelve a estar visible
        else if (document.visibilityState === 'visible') {
            // Restaurar la interacción normal con la página
            const storedData = localStorage.getItem('lastKnownPosition');
            if (storedData) {
                const data = JSON.parse(storedData);
                if (data.orderId === orderId) {
                    // Si la última sincronización fue hace más de 1 minuto, actualizar estado
                    const timeSinceLastUpdate = Date.now() - data.timestamp;
                    if (timeSinceLastUpdate > 60000) {
                        // Notificar al usuario que los datos pueden estar desactualizados
                        updateBackgroundStatus('outdated', 'Datos de ubicación desactualizados');
                    }
                }
            }
        }
    });
}

// Agregar indicador de estado de seguimiento
function addBackgroundTrackingIndicator() {
    const indicatorHTML = `
        <div id="backgroundTrackingIndicator" class="fixed bottom-4 right-4 bg-white p-3 rounded-lg shadow-lg z-50 border-l-4 border-gray-300 hidden">
            <div class="flex items-center">
                <div id="backgroundStatusIcon" class="w-3 h-3 rounded-full bg-gray-400 mr-2"></div>
                <div>
                    <p class="text-sm font-medium">Seguimiento en segundo plano</p>
                    <p id="backgroundStatusText" class="text-xs text-gray-500">Inactivo</p>
                </div>
            </div>
        </div>
    `;
    
    document.body.insertAdjacentHTML('beforeend', indicatorHTML);
}

// Actualizar estado del seguimiento en segundo plano
function updateBackgroundStatus(status, message) {
    backgroundSyncStatus = status;
    
    const indicator = document.getElementById('backgroundTrackingIndicator');
    const statusIcon = document.getElementById('backgroundStatusIcon');
    const statusText = document.getElementById('backgroundStatusText');
    
    if (!indicator || !statusIcon || !statusText) return;
    
    // Mostrar el indicador
    indicator.classList.remove('hidden');
    
    // Actualizar el icono y mensaje según el estado
    switch (status) {
        case 'active':
            statusIcon.className = 'w-3 h-3 rounded-full bg-green-500 mr-2 pulse-marker';
            indicator.className = 'fixed bottom-4 right-4 bg-white p-3 rounded-lg shadow-lg z-50 border-l-4 border-green-500';
            break;
        case 'registered':
        case 'permission-granted':
            statusIcon.className = 'w-3 h-3 rounded-full bg-blue-500 mr-2';
            indicator.className = 'fixed bottom-4 right-4 bg-white p-3 rounded-lg shadow-lg z-50 border-l-4 border-blue-500';
            break;
        case 'inactive':
            statusIcon.className = 'w-3 h-3 rounded-full bg-gray-400 mr-2';
            indicator.className = 'fixed bottom-4 right-4 bg-white p-3 rounded-lg shadow-lg z-50 border-l-4 border-gray-300';
            break;
        case 'error':
        case 'no-support':
        case 'permission-denied':
            statusIcon.className = 'w-3 h-3 rounded-full bg-red-500 mr-2';
            indicator.className = 'fixed bottom-4 right-4 bg-white p-3 rounded-lg shadow-lg z-50 border-l-4 border-red-500';
            break;
        case 'outdated':
            statusIcon.className = 'w-3 h-3 rounded-full bg-yellow-500 mr-2';
            indicator.className = 'fixed bottom-4 right-4 bg-white p-3 rounded-lg shadow-lg z-50 border-l-4 border-yellow-500';
            break;
    }
    
    statusText.textContent = message;
    
    // Ocultar después de 5 segundos si está activo o registrado
    if (status === 'active' || status === 'registered' || status === 'permission-granted') {
        setTimeout(() => {
            indicator.classList.add('hidden');
        }, 5000);
    }
}

// Formatear hora
function formatTime(date) {
    return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
}

// Exportar funciones para uso global
window.BackgroundTracking = {
    init: initBackgroundTracking,
    start: startBackgroundTracking,
    stop: stopBackgroundTracking,
    updatePosition: updatePositionInBackground
};