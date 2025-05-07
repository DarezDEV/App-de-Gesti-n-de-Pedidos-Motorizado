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

document.addEventListener('DOMContentLoaded', () => {
  const socket = io('/motorizado');
  const tabButtons = document.querySelectorAll('.tab-btn');
  const contador = document.getElementById('contador');
  const tabContent = document.getElementById('tab-content');
  const tabsContainer = document.querySelector('.tab-container');
  const tabScroll = document.querySelector('.tab-scroll');
  const tabIndicator = document.querySelector('.tab-indicator');
  const noOrdersMessage = document.getElementById('no-orders-message');

  let estadoActual = 'todos';

  // Función para filtrar pedidos
  function filtrarPedidos(estado) {
    const allPedidos = document.querySelectorAll('.pedido');
    let visibleCount = 0;

    console.log("Filtrando por estado:", estado);

    allPedidos.forEach((pedido, index) => {
      const pedidoEstado = pedido.dataset.estado;
      console.log("Pedido:", pedido.dataset.orderId, "Estado:", pedidoEstado);

      if (estado === 'todos' || pedidoEstado === estado) {
        pedido.style.display = 'block';
        pedido.style.opacity = '0';
        pedido.style.transform = 'translateX(20px)';
        setTimeout(() => {
          pedido.style.opacity = '1';
          pedido.style.transform = 'translateX(0)';
        }, index * 50);
        visibleCount++;
      } else {
        pedido.style.display = 'none';
      }
    });

    contador.innerHTML = estado === 'todos'
      ? `Mostrando todos los pedidos <span class="font-bold">${visibleCount}</span>`
      : `Mostrando pedidos con estado <span class="font-medium text-primary">${formatearEstado(estado)}</span> <span class="font-bold">${visibleCount}</span>`;

    noOrdersMessage.classList.toggle('hidden', visibleCount > 0);
  }

  // Función para formatear el estado
  function formatearEstado(estado) {
    const formateo = {
      'en-camino': 'En Camino',
      'entregado': 'Entregado'
    };
    return formateo[estado] || estado;
  }

  // Función para actualizar el indicador
  function updateIndicator(activeTab) {
    if (!activeTab) return;

    const tabRect = activeTab.getBoundingClientRect();
    const containerRect = tabsContainer.getBoundingClientRect();

    const leftPosition = activeTab.offsetLeft;

    tabIndicator.style.width = `${tabRect.width}px`;
    tabIndicator.style.left = `${leftPosition}px`;

    tabIndicator.style.display = 'block';
  }

  // Actualizar estilos de pestañas
  function actualizarTabs(estado) {
    estadoActual = estado;

    tabButtons.forEach(btn => {
      const isActive = btn.id === `tab-${estado}`;
      btn.classList.toggle('text-primary', isActive);
      btn.classList.toggle('text-gray-500', !isActive);
      btn.classList.toggle('font-semibold', isActive);
    });

    const activeTab = document.getElementById(`tab-${estado}`);
    if (activeTab && window.innerWidth < 640) {
      tabScroll.scrollTo({
        left: activeTab.offsetLeft - (tabScroll.clientWidth / 2) + (activeTab.clientWidth / 2),
        behavior: 'smooth'
      });
    }

    setTimeout(() => updateIndicator(activeTab), 100);
  }

  // Eventos de pestañas
  tabButtons.forEach(btn => {
    btn.addEventListener('click', function () {
      const estado = this.id.replace('tab-', '');
      actualizarTabs(estado);
      filtrarPedidos(estado);
    });
  });

  // Solicitud de permiso para notificaciones
  function requestNotificationPermission() {
    if (Notification.permission === 'default') {
      Notification.requestPermission().then(permission => {
        console.log(permission === 'granted' ? 'Notificaciones permitidas' : 'Notificaciones denegadas');
      });
    }
  }
  requestNotificationPermission();

  // Manejo de notificaciones vía socket
  socket.on('new_delivery', function(order) {
    addOrderToList(order);

    if (Notification.permission === 'granted') {
      new Notification('Nuevo Pedido Asignado', {
        body: `Tienes un nuevo pedido #${order.order_id} para entregar`,
        icon: '/static/img/logo.png'
      });
    }

    showNotification('Éxito', `Nuevo pedido #${order.order_id} asignado`, 'success');
  });

  socket.on('order_delivered', order => {
    const pedido = document.querySelector(`.pedido[data-order-id="${order.order_id}"]`);
    if (pedido) {
      pedido.dataset.estado = 'entregado';
      const statusSpan = pedido.querySelector('span');
      if (statusSpan) statusSpan.textContent = 'Entregado';
      filtrarPedidos(estadoActual);
    }
    if (Notification.permission === 'granted') {
      new Notification('Entrega Confirmada', {
        body: `El pedido #${order.order_id} ha sido marcado como entregado`,
        icon: '/static/img/logo.png'
      });
    }
    showNotification('Éxito', `Pedido #${order.order_id} marcado como entregado`, 'success');
  });

  // Inicialización
  window.addEventListener('load', function() {
    actualizarTabs('todos');
    filtrarPedidos('todos');

    setTimeout(() => {
      updateIndicator(document.getElementById(`tab-${estadoActual}`));
    }, 200);
  });

  // Actualizar el indicador cuando se redimensiona la ventana
  window.addEventListener('resize', function() {
    updateIndicator(document.getElementById(`tab-${estadoActual}`));
  });

  // Función para agregar pedido a la lista
  function addOrderToList(order) {
    const existingOrder = document.querySelector(`.pedido[data-order-id="${order.order_id}"]`);
    if (existingOrder) {
      console.log(`El pedido #${order.order_id} ya existe en la lista.`);
      return;
    }

    const newOrder = document.createElement('div');
    newOrder.className = 'pedido bg-white rounded-lg shadow-md overflow-hidden pedido-animate';
    newOrder.dataset.estado = order.status.toLowerCase().replace(/\s+/g, '-');
    newOrder.dataset.orderId = order.order_id;
    newOrder.innerHTML = `
      <div class="border-l-4 border-primary">
        <div class="p-4 sm:p-5">
          <div class="flex justify-between items-start">
            <div>
              <h3 class="text-lg font-bold text-gray-800">Pedido #${order.order_id}</h3>
              <p class="text-sm text-gray-500">Cliente: ${order.client_name || 'N/A'}</p>
            </div>
            <span class="px-3 py-1 bg-primary-50 text-primary-700 rounded-full text-sm font-medium">
              ${formatearEstado(order.status)}
            </span>
          </div>
          <div class="mt-4 border-t pt-4">
            <div class="flex flex-wrap justify-between text-sm gap-y-3">
              <div>
                <p class="text-gray-500">Fecha de pedido:</p>
                <p class="font-medium">${order.created_at}</p>
              </div>
              <div>
                <p class="text-gray-500">Dirección:</p>
                <p class="font-medium">${order.address}</p>
              </div>
              <div>
                <p class="text-gray-500">Monto:</p>
                <p class="font-medium">RD$${order.total_amount.toFixed(2)}</p>
              </div>
            </div>
          </div>
          <div class="mt-4 flex justify-end">
            <a href="/dashboard/motorizad/ordenes/orden/${order.order_id}" class="text-primary hover:text-primary-700 text-sm font-medium flex items-center">
              Ver detalles
              <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="w-4 h-4 ml-1">
                <path stroke-linecap="round" stroke-linejoin="round" d="M8.25 4.5l7.5 7.5-7.5 7.5" />
              </svg>
            </a>
          </div>
        </div>
      </div>
    `;
    tabContent.insertBefore(newOrder, tabContent.firstChild);
    updateCounter();
  }

  // Función para actualizar el contador
  function updateCounter() {
    const visiblePedidos = Array.from(document.querySelectorAll('.pedido')).filter(p => p.style.display !== 'none');
    contador.innerHTML = estadoActual === 'todos'
      ? `Mostrando todos los pedidos <span class="font-bold">${visiblePedidos.length}</span>`
      : `Mostrando pedidos con estado <span class="font-medium text-primary">${formatearEstado(estadoActual)}</span> <span class="font-bold">${visiblePedidos.length}</span>`;
    noOrdersMessage.classList.toggle('hidden', visiblePedidos.length > 0);
  }

  // Función para mostrar notificaciones estandarizadas
  function showNotification(title, message, type) {
    const notification = document.createElement('div');
    notification.setAttribute('role', 'alert');
    notification.id = 'flash';

    if (type === 'error') {
      notification.className = 'flash-message slide-in fixed top-4 right-4 z-50';
      notification.innerHTML = `
        <svg class="flash-icon" aria-hidden="true" xmlns="http://www.w3.org/2000/svg" fill="currentColor" viewBox="0 0 20 20">
          <path d="M10 .5a9.5 9.5 0 1 0 9.5 9.5A9.51 9.51 0 0 0 10 .5ZM9.5 4a1.5 1.5 0 1 1 0 3 1.5 1.5 0 0 1 0-3ZM12 15H8a1 1 0 0 1 0-2h1v-3H8a1 1 0 0 1 0-2h2a1 1 0 1 1 1 1v4h1a1 1 0 0 1 0 2Z"/>
        </svg>
        <div class="message-container">
          <span class="message">Advertencia:</span> ${message}
        </div>
        <button onclick="closeFlash()" class="flash-close">×</button>
      `;
    } else if (type === 'success') {
      notification.className = 'flash-message-success slide-in fixed top-4 right-4 z-50';
      notification.innerHTML = `
        <svg class="flash-icon-success" aria-hidden="true" xmlns="http://www.w3.org/2000/svg" fill="currentColor" viewBox="0 0 20 20">
          <path d="M10 0.5a9.5 9.5 0 1 0 9.5 9.5A9.51 9.51 0 0 0 10 0.5ZM8.293 10.293a1 1 0 0 1 1.414 0L10 10.586l2.293-2.293a1 1 0 1 1 1.414 1.414l-3 3a1 1 0 0 1-1.414 0l-2-2a1 1 0 0 1 1.414-1.414Z"/>
        </svg>
        <div class="message-container-success">
          <span class="message-success">Éxito:</span> ${message}
        </div>
        <button onclick="closeFlash()" class="flash-close-success">×</button>
      `;
    } else {
      notification.className = 'flash-message slide-in fixed top-4 right-4 z-50';
      notification.innerHTML = `
        <div class="message-container">
          <span class="message"><strong>${title}:</strong></span> ${message}
        </div>
        <button onclick="closeFlash()" class="flash-close">×</button>
      `;
    }

  }
});