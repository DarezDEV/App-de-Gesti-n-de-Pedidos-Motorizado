 tailwind.config = {
        theme: {
            extend: {
                colors: {
                    primary: {
                        DEFAULT: '#F49A13',
                        50: '#FEF0DC',
                        100: '#FDE6C3',
                        200: '#FCD192',
                        300: '#FBBD60',
                        400: '#F9A82E',
                        500: '#F49A13',
                        600: '#CF7F08',
                        700: '#9E6006',
                        800: '#6C4204',
                        900: '#3B2402',
                }
            }
        }
    }
}

document.addEventListener('DOMContentLoaded', function() {
    const tabButtons = document.querySelectorAll('.tab-btn');
    const pedidos = document.querySelectorAll('.pedido');
    const contador = document.getElementById('contador');
    const tabContent = document.getElementById('tab-content');
    const tabsContainer = document.querySelector('.tab-container');
    const tabScroll = document.querySelector('.tab-scroll');
    const tabIndicator = document.querySelector('.tab-indicator');
    const noOrdersMessage = document.getElementById('no-orders-message');
    const notificationContainer = document.getElementById('notification-container');

    const estados = ['todos', 'pendiente', 'en-camino', 'entregado'];
    let estadoActual = 'todos';

    // Formatear estado para mostrar
    function formatearEstado(estado) {
      const formateo = {
        'pendiente': 'Pendiente',
        'en-camino': 'En Camino',
        'entregado': 'Entregado'
      };
      return formateo[estado] || estado;
    }

    // Función mejorada para actualizar el indicador
    function updateIndicator(activeTab) {
      if (!activeTab) return;
      
      // Obtener las dimensiones y posición del botón activo
      const tabRect = activeTab.getBoundingClientRect();
      
      // Calcular la posición relativa al contenedor
      const leftPosition = activeTab.offsetLeft;
      
      // Configurar el indicador
      tabIndicator.style.width = `${tabRect.width}px`;
      tabIndicator.style.left = `${leftPosition}px`;
      
      // Hacer visible el indicador
      tabIndicator.style.display = 'block';
    }

    // Filtrar pedidos por estado
    function filtrarPedidos(estado) {
      let contadorVisible = 0;
      pedidos.forEach(pedido => {
        const estadoNormalizado = pedido.dataset.estado.toLowerCase().replace(/\s+/g, '-');
        const estadoSeleccionado = estado.toLowerCase().replace(/\s+/g, '-');
        if (estadoSeleccionado === 'todos' || estadoNormalizado === estadoSeleccionado) {
          pedido.style.display = 'block';
          contadorVisible++;
        } else {
          pedido.style.display = 'none';
        }
      });
      
      // Actualizar contador
      contador.innerHTML = estado === 'todos' 
        ? `Mostrando todos los pedidos <span class="font-bold">${contadorVisible}</span>`
        : `Mostrando pedidos con estado <span class="font-medium text-primary">${formatearEstado(estado)}</span> <span class="font-bold">${contadorVisible}</span>`;
      
      // Mostrar mensaje cuando no hay pedidos
      if (contadorVisible === 0) {
        noOrdersMessage.classList.remove('hidden');
      } else {
        noOrdersMessage.classList.add('hidden');
      }
    }

    // Actualizar pestañas activas y aplicar estilos
    function actualizarTabs(estado) {
      estadoActual = estado;
      
      // Actualizar clases de los botones
      tabButtons.forEach(btn => {
        const isActive = btn.id === `tab-${estado}`;
        btn.classList.toggle('text-primary', isActive);
        btn.classList.toggle('text-gray-500', !isActive);
        btn.classList.toggle('font-semibold', isActive);
      });
      
      // Hacer scroll al botón activo en dispositivos móviles
      const activeTab = document.getElementById(`tab-${estado}`);
      if (activeTab && window.innerWidth < 640) {
        tabScroll.scrollTo({
          left: activeTab.offsetLeft - (tabScroll.clientWidth / 2) + (activeTab.clientWidth / 2),
          behavior: 'smooth'
        });
      }
      
      // Actualizar el indicador con un pequeño retraso para asegurar que los cambios de DOM se hayan aplicado
      setTimeout(() => updateIndicator(activeTab), 100);
    }

    // Mostrar notificación en pantalla
    function showNotification(title, message, duration = 5000) {
      const notification = document.createElement('div');
      notification.className = 'notification';
      notification.innerHTML = `
        <div class="notification-title">${title}</div>
        <div class="notification-body">${message}</div>
      `;
      
      notificationContainer.appendChild(notification);
      
      // Aplicar la transición después de un breve retraso para que se active correctamente
      setTimeout(() => {
        notification.classList.add('show');
      }, 10);
      
      // Eliminar la notificación después del tiempo especificado
      setTimeout(() => {
        notification.classList.remove('show');
        setTimeout(() => {
          notification.remove();
        }, 300);
      }, duration);
    }

    // Crear o actualizar el pedido dinámicamente
    function actualizarPedido(orderData) {
      let pedido = document.querySelector(`.pedido[data-order-id="${orderData.order_id}"]`);
      
      // Si no existe el pedido, crearlo
      if (!pedido) {
        pedido = document.createElement('div');
        pedido.className = 'pedido bg-white rounded-lg shadow-md overflow-hidden';
        pedido.dataset.orderId = orderData.order_id;
        tabContent.prepend(pedido);
      }
      
      // Actualizar estado en el dataset
      pedido.dataset.estado = orderData.status.toLowerCase().replace(/\s+/g, '-');
      
      // Formatear fecha si está disponible
      let fechaFormateada = orderData.created_at || new Date().toLocaleDateString('es-ES');
      
      // Construir HTML interno del pedido
      const statusDisplay = formatearEstado(orderData.status);
      
      pedido.innerHTML = `
        <div class="border-l-4 border-primary">
          <div class="p-4 sm:p-5">
            <div class="flex justify-between items-start">
              <div>
                <h3 class="text-lg font-bold text-gray-800">Pedido #${orderData.order_id}</h3>
                <p class="text-sm text-gray-500">Fecha: ${fechaFormateada}</p>
              </div>
              <span class="px-3 py-1 bg-primary-50 text-primary-700 rounded-full text-sm font-medium">
                ${statusDisplay}
              </span>
            </div>
            <div class="mt-4 border-t pt-4">
              <div class="flex flex-wrap justify-between text-sm gap-y-3">
                <div>
                  <p class="text-gray-500">Dirección:</p>
                  <p class="font-medium">${orderData.address || 'No especificada'}</p>
                </div>
                <div>
                  <p class="text-gray-500">Monto:</p>
                  <p class="font-medium">RD$${orderData.total_amount ? parseFloat(orderData.total_amount).toFixed(2) : '0.00'}</p>
                </div>
                ${(orderData.status === 'en-camino' || orderData.status === 'entregado') && orderData.motorizado_name ? `
                <div class="motorizado-info">
                  <p class="text-gray-500">Motorizado:</p>
                  <p class="font-medium">${orderData.motorizado_name} ${orderData.motorizado_last_name || ''}</p>
                </div>
                ` : ''}
              </div>
            </div>
            <div class="mt-4 flex justify-end">
              <a href="/order_details/${orderData.order_id}" class="text-primary hover:text-primary-700 text-sm font-medium flex items-center">
                Ver detalles
                <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="w-4 h-4 ml-1">
                  <path stroke-linecap="round" stroke-linejoin="round" d="M8.25 4.5l7.5 7.5-7.5 7.5" />
                </svg>
              </a>
            </div>
          </div>
        </div>
      `;
      
      // Actualizar la lista de pedidos
      filtrarPedidos(estadoActual);
    }

    // Añadir eventos a los botones de pestañas
    tabButtons.forEach(btn => {
      btn.addEventListener('click', function() {
        const estado = this.id.replace('tab-', '');
        actualizarTabs(estado);
        filtrarPedidos(estado);
      });
    });

    // Manejar el scroll horizontal para actualizar el indicador
    tabScroll.addEventListener('scroll', function() {
      updateIndicator(document.getElementById(`tab-${estadoActual}`));
    });

    // Inicializar la vista al cargar la página
    actualizarTabs('todos');
    filtrarPedidos('todos');
    
    // Asegurar que el indicador se actualice cuando todo esté cargado
    setTimeout(() => {
      updateIndicator(document.getElementById(`tab-${estadoActual}`));
    }, 200);

    // Actualizar el indicador cuando se redimensiona la ventana
    window.addEventListener('resize', function() {
      updateIndicator(document.getElementById(`tab-${estadoActual}`));
    });

    // Configuración de notificaciones push
    function setupPushNotifications() {
      if ('serviceWorker' in navigator && 'PushManager' in window) {
        // Registrar el Service Worker si no existe
        navigator.serviceWorker.register('/service-worker.js')
          .then(registration => {
            console.log('Service Worker registrado con éxito:', registration);
            requestNotificationPermission();
          })
          .catch(error => {
            console.error('Error al registrar el Service Worker:', error);
          });
      } else {
        console.warn('Las notificaciones push no son soportadas por este navegador');
      }
    }

    // Solicitar permiso para notificaciones
    function requestNotificationPermission() {
      if (Notification.permission !== 'granted' && Notification.permission !== 'denied') {
        Notification.requestPermission().then(permission => {
          if (permission === 'granted') {
            console.log('Permiso de notificaciones concedido');
            subscribeToPushNotifications();
          }
        });
      } else if (Notification.permission === 'granted') {
        subscribeToPushNotifications();
      }
    }

    // Suscribirse a notificaciones push (implementación básica)
    function subscribeToPushNotifications() {
      navigator.serviceWorker.ready.then(registration => {
        // Aquí se implementaría la suscripción real a un servidor de push
        console.log('Listo para recibir notificaciones push');
      });
    }

    // Mostrar notificación nativa
    function showNativeNotification(title, options) {
      if (Notification.permission === 'granted') {
        navigator.serviceWorker.ready.then(registration => {
          registration.showNotification(title, options);
        });
      } else {
        // Fallback a la notificación en pantalla
        showNotification(title, options.body);
      }
    }

    // Iniciar configuración de notificaciones
    setupPushNotifications();

    // Socket IO para actualizaciones en tiempo real
    const socket = io('/client');
    
    socket.on('connect', () => {
      console.log('Conectado al namespace /client');
    });
    
    socket.on('connect_error', (error) => {
      console.error('Error de conexión:', error);
    });

    socket.on('order_status_update', function(order) {
      console.log('Evento recibido:', order);
      
      // Actualizar el pedido en la interfaz
      actualizarPedido(order);
      
      // Preparar notificaciones según el estado
      let title, message;
      
      if (order.status === 'en-camino') {
        title = 'Pedido en Camino';
        message = `Tu pedido #${order.order_id} ha sido asignado a ${order.motorizado_name || 'un motorizado'}`;
      } else if (order.status === 'entregado') {
        title = 'Pedido Entregado';
        message = `Tu pedido #${order.order_id} ha sido entregado exitosamente`;
      } else {
        title = 'Actualización de Pedido';
        message = `Tu pedido #${order.order_id} ha cambiado a estado ${formatearEstado(order.status)}`;
      }
      
      // Mostrar notificación en pantalla siempre
      showNotification(title, message);
      
      // Intentar mostrar notificación nativa si está permitido
      if (Notification.permission === 'granted') {
        showNativeNotification(title, {
          body: message,
          icon: '/static/img/logo.png',
          badge: '/static/img/badge.png',
          vibrate: [200, 100, 200],
          tag: `order-${order.order_id}`
        });
      }
    });
  });