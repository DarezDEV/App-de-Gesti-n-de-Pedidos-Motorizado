// app/static/js/admin_orders.js
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
  // Estilos personalizados para mejorar scroll y animaciones
  const style = document.createElement('style');
  style.textContent = `
    .tab-scroll {
      -webkit-overflow-scrolling: touch;
      scroll-behavior: smooth;
      scrollbar-width: none;
      transition: transform 0.3s ease;
      overscroll-behavior-x: contain;
    }
    .tab-scroll::-webkit-scrollbar {
      display: none;
    }
    .tab-btn {
      transition: all 0.3s ease;
    }
    .tab-indicator {
      transition: transform 0.3s ease, width 0.3s ease;
    }
    .pedido {
      transition: all 0.3s ease;
    }
    @keyframes slideIn {
      from {
        opacity: 0;
        transform: translateX(20px);
      }
      to {
        opacity: 1;
        transform: translateX(0);
      }
    }
    .pedido-animate {
      animation: slideIn 0.3s ease forwards;
    }
  `;
  document.head.appendChild(style);

  const socket = io('/admin');

  // Solicitar permiso de notificación al cargar la página
  function requestNotificationPermission() {
    if (Notification.permission === 'default') {
      Notification.requestPermission().then(permission => {
        console.log(permission === 'granted' ? 'Permiso de notificación concedido' : 'Permiso de notificación denegado');
      });
    }
  }
  requestNotificationPermission();

  // Manejar evento de nuevo pedido
  socket.on('new_order', function(order) {
    if (Notification.permission === 'granted') {
      const notification = new Notification('Nuevo Pedido Recibido', {
        body: `Pedido #${order.order_id} de ${order.client_name} por RD$${order.total_amount.toFixed(2)}`,
        icon: '/static/uploads/favicon.ico',
        tag: `order-${order.order_id}`,
        data: { url: `/admin/order/${order.order_id}` }
      });

      notification.onclick = function() {
        window.location.href = notification.data.url;
      };
    }

    // Solo agregar si el filtro actual lo permite
    if (estadoActual === 'todos' || estadoActual === 'pendiente') {
      addOrderToList(order);
    }

    // Actualizar localStorage para el contador global
    let currentCount = parseInt(localStorage.getItem('pendingOrdersCount') || '0');
    if (order.status === 'pendiente') {
      currentCount += 1;
    }
    localStorage.setItem('pendingOrdersCount', currentCount.toString());
    window.dispatchEvent(new Event('recalculate-pending'));
  });

  // Manejar actualización de estado del pedido
  socket.on('order_status_update', function(order) {
    console.log('Evento recibido en admin:', order);
    const pedido = document.querySelector(`.pedido[data-order-id="${order.order_id}"]`);
    if (pedido) {
      const statusSpan = pedido.querySelector('span');
      const newStatus = formatearEstado(order.status);
      statusSpan.textContent = newStatus;
      pedido.dataset.estado = order.status;

      // Filtrar nuevamente para mantener la consistencia
      filtrarPedidos(estadoActual);

      if (Notification.permission === 'granted') {
        const message = order.status === 'en-camino' 
          ? `El pedido #${order.order_id} ha sido asignado a ${order.motorizado_name}`
          : `El pedido #${order.order_id} ha sido entregado`;
        new Notification(order.status === 'en-camino' ? 'Motorizado Asignado' : 'Pedido Entregado', {
          body: message,
          icon: '/static/img/logo.png'
        });
      }

      // Actualizar localStorage para el contador global
      let currentCount = parseInt(localStorage.getItem('pendingOrdersCount') || '0');
      if (order.status !== 'pendiente' && pedido.dataset.estado === 'pendiente') {
        currentCount = Math.max(currentCount - 1, 0);
      }
      localStorage.setItem('pendingOrdersCount', currentCount.toString());
      window.dispatchEvent(new Event('recalculate-pending'));
    }
  });

  // Elementos del DOM
  const tabButtons = document.querySelectorAll('.tab-btn');
  const contador = document.getElementById('contador');
  const tabContent = document.getElementById('tab-content');
  const tabsContainer = document.querySelector('.tab-scroll');
  const tabIndicator = document.querySelector('.tab-indicator');
  const noOrdersMessage = document.getElementById('no-orders-message');

  // Variables para manejo táctil
  let startX, scrollLeft, isDragging = false;

  // Eventos táctiles
  tabsContainer.addEventListener('touchstart', function(e) {
    isDragging = true;
    startX = e.touches[0].pageX - tabsContainer.offsetLeft;
    scrollLeft = tabsContainer.scrollLeft;
  });

  tabsContainer.addEventListener('touchend', function() {
    isDragging = false;
  });

  tabsContainer.addEventListener('touchmove', function(e) {
    if (!isDragging) return;
    const x = e.touches[0].pageX - tabsContainer.offsetLeft;
    const walk = (x - startX) * 2;
    tabsContainer.scrollLeft = scrollLeft - walk;
  });

  // Eventos de mouse
  tabsContainer.addEventListener('mousedown', function(e) {
    isDragging = true;
    startX = e.pageX - tabsContainer.offsetLeft;
    scrollLeft = tabsContainer.scrollLeft;
    tabsContainer.style.cursor = 'grabbing';
  });

  tabsContainer.addEventListener('mouseup', function() {
    isDragging = false;
    tabsContainer.style.cursor = 'grab';
  });

  tabsContainer.addEventListener('mouseleave', function() {
    isDragging = false;
    tabsContainer.style.cursor = 'grab';
  });

  tabsContainer.addEventListener('mousemove', function(e) {
    if (!isDragging) return;
    e.preventDefault();
    const x = e.pageX - tabsContainer.offsetLeft;
    const walk = (x - startX) * 1.5;
    tabsContainer.scrollLeft = scrollLeft - walk;
  });

  // Estados posibles
  const estados = ['todos', 'pendiente', 'en-camino', 'entregado'];
  let estadoActual = 'todos';

  // Función para agregar un pedido a la lista
  function addOrderToList(order) {
    const existingOrder = document.querySelector(`.pedido[data-order-id="${order.order_id}"]`);
    if (existingOrder) {
      console.log(`El pedido #${order.order_id} ya existe en la lista.`);
      return;
    }

    const newOrder = document.createElement('div');
    newOrder.className = 'pedido bg-white rounded-lg shadow-md overflow-hidden pedido-animate';
    newOrder.dataset.estado = order.status;
    newOrder.dataset.orderId = order.order_id;
    newOrder.innerHTML = `
        <div class="border-l-4 border-primary">
            <div class="p-3 sm:p-5">
                <div class="flex flex-col sm:flex-row sm:justify-between sm:items-start gap-2 sm:gap-0">
                    <div>
                        <h3 class="text-base sm:text-lg font-bold text-gray-800">Pedido #${order.order_id}</h3>
                        <p class="text-xs sm:text-sm text-gray-500">Cliente: ${order.client_name}</p>
                    </div>
                    <span class="px-2 py-1 bg-primary-50 text-primary-700 rounded-full text-xs sm:text-sm font-medium w-fit">${formatearEstado(order.status)}</span>
                </div>
                <div class="mt-3 sm:mt-4 border-t pt-3 sm:pt-4">
                    <div class="grid grid-cols-1 sm:grid-cols-3 gap-2 sm:gap-4 text-xs sm:text-sm">
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
                <div class="mt-3 sm:mt-4 flex justify-end">
                    <a href="/admin/order/${order.order_id}" class="text-primary hover:text-primary-700 text-xs sm:text-sm font-medium flex items-center">
                        Ver detalles
                        <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="w-3 h-3 sm:w-4 sm:h-4 ml-1">
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

  // Actualizar el indicador de pestaña
  function updateIndicator(activeTab) {
    if (!activeTab) return;
    tabIndicator.style.display = 'block';
    const tabRect = activeTab.getBoundingClientRect();
    const containerRect = tabsContainer.getBoundingClientRect();
    tabIndicator.style.width = `${tabRect.width}px`;
    const tabLeft = activeTab.offsetLeft;
    tabIndicator.style.transform = `translateX(${tabLeft}px)`;

    if (tabLeft < tabsContainer.scrollLeft) {
      tabsContainer.scrollLeft = tabLeft;
    } else if (tabLeft + tabRect.width > tabsContainer.scrollLeft + containerRect.width) {
      tabsContainer.scrollLeft = tabLeft + tabRect.width - containerRect.width;
    }
  }

  // Actualizar el contador de pedidos visibles
  function updateCounter() {
    const visiblePedidos = Array.from(document.querySelectorAll('.pedido')).filter(p => p.style.display !== 'none');
    contador.innerHTML = estadoActual === 'todos' 
      ? `Mostrando todos los pedidos <span class="font-bold">${visiblePedidos.length}</span>`
      : `Mostrando pedidos con estado <span class="font-medium text-primary">${formatearEstado(estadoActual)}</span> <span class="font-bold">${visiblePedidos.length}</span>`;
    
    if (visiblePedidos.length === 0) {
      noOrdersMessage.classList.remove('hidden');
    } else {
      noOrdersMessage.classList.add('hidden');
    }
  }

  // Filtrar pedidos por estado
  function filtrarPedidos(estado) {
    const allPedidos = document.querySelectorAll('.pedido');
    let contadorVisible = 0;

    allPedidos.forEach((pedido, index) => {
      if (estado === 'todos' || pedido.dataset.estado === estado) {
        pedido.style.display = 'block';
        pedido.style.opacity = '0';
        pedido.style.transform = 'translateX(20px)';
        
        setTimeout(() => {
          pedido.style.opacity = '1';
          pedido.style.transform = 'translateX(0)';
        }, index * 50);
        contadorVisible++;
      } else {
        pedido.style.display = 'none';
      }
    });

    updateCounter();
  }

  // Formatear el estado para mostrarlo
  function formatearEstado(estado) {
    const formateo = {
      'pendiente': 'Pendiente',
      'en-camino': 'En Camino',
      'entregado': 'Entregado'
    };
    return formateo[estado] || estado;
  }

  // Actualizar estilos y posición de las pestañas
  function actualizarTabs(estado) {
    estadoActual = estado;
    tabButtons.forEach(btn => {
      const isActive = btn.id === `tab-${estado}`;
      btn.classList.toggle('text-primary', isActive);
      btn.classList.toggle('text-gray-500', !isActive);

      if (isActive) {
        btn.style.transform = 'translateY(-2px)';
        setTimeout(() => {
          btn.style.transform = 'translateY(0)';
        }, 200);
      }

      if (isActive) {
        setTimeout(() => {
          const rect = btn.getBoundingClientRect();
          const containerRect = tabsContainer.getBoundingClientRect();
          
          if (rect.left < containerRect.left) {
            tabsContainer.scrollLeft += rect.left - containerRect.left - 10;
          } else if (rect.right > containerRect.right) {
            tabsContainer.scrollLeft += rect.right - containerRect.right + 10;
          }
        }, 10);
      }
    });

    setTimeout(() => {
      const activeTab = document.getElementById(`tab-${estado}`);
      if (activeTab) updateIndicator(activeTab);
    }, 50);
  }

  // Añadir eventos a los botones de pestañas
  tabButtons.forEach(btn => {
    btn.addEventListener('click', function() {
      const estado = this.id.replace('tab-', '');
      actualizarTabs(estado);
      filtrarPedidos(estado);
    });
  });

  // Manejo responsivo del indicador al redimensionar
  window.addEventListener('resize', function() {
    const activeTab = document.getElementById(`tab-${estadoActual}`);
    if (activeTab) updateIndicator(activeTab);
  });

  // Inicialización al cargar la página
  window.addEventListener('load', function() {
    tabsContainer.style.cursor = 'grab';
    actualizarTabs('todos');
    filtrarPedidos('todos');
  });
});

// Polyfill para :contains (si es necesario en algunos navegadores)
if (!Element.prototype.matches) {
  Element.prototype.matches = Element.prototype.msMatchesSelector || Element.prototype.webkitMatchesSelector;
}

if (!Element.prototype.closest) {
  Element.prototype.closest = function(s) {
    let el = this;
    do {
      if (el.matches(s)) return el;
      el = el.parentElement || el.parentNode;
    } while (el !== null && el.nodeType === 1);
    return null;
  };
}