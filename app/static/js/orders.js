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
  // Aplicar estilos personalizados para mejorar scroll táctil y animaciones
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

  // Request notification permission on page load
  function requestNotificationPermission() {
    if (Notification.permission === 'default') {
      Notification.requestPermission().then(permission => {
        if (permission === 'granted') {
          console.log('Permiso de notificación concedido');
        } else {
          console.log('Permiso de notificación denegado');
        }
      });
    }
  }
  requestNotificationPermission();

  // Handle new order event
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
    } else {
      alert(`Nuevo pedido #${order.order_id} de ${order.client_name} por RD$${order.total_amount.toFixed(2)}`);
    }

    const tabContent = document.getElementById('tab-content');
    const newOrder = document.createElement('div');
    newOrder.className = 'pedido bg-white rounded-lg shadow-md overflow-hidden pedido-animate';
    newOrder.dataset.estado = order.status;
    newOrder.innerHTML = `
      <div class="border-l-4 border-primary">
        <div class="p-3 sm:p-5">
          <div class="flex flex-col sm:flex-row sm:justify-between sm:items-start gap-2 sm:gap-0">
            <div>
              <h3 class="text-base sm:text-lg font-bold text-gray-800">Pedido #${order.order_id}</h3>
              <p class="text-xs sm:text-sm text-gray-500">Cliente: ${order.client_name}</p>
            </div>
            <span class="px-2 py-1 bg-primary-50 text-primary-700 rounded-full text-xs sm:text-sm font-medium w-fit">${order.status.charAt(0).toUpperCase() + order.status.slice(1)}</span>
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
  });

  const tabButtons = document.querySelectorAll('.tab-btn');
  const pedidos = document.querySelectorAll('.pedido');
  const contador = document.getElementById('contador');
  const tabContent = document.getElementById('tab-content');
  const tabsContainer = document.querySelector('.tab-scroll');
  const tabIndicator = document.querySelector('.tab-indicator');
  
  // Variables para el manejo de deslizamiento táctil
  let startX, scrollLeft, isDragging = false;

  // Añadir eventos de interacción táctil mejorados
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
    const walk = (x - startX) * 2; // Velocidad de desplazamiento aumentada
    tabsContainer.scrollLeft = scrollLeft - walk;
  });
  
  // Implementar eventos de mouse para compatibilidad
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
    const walk = (x - startX) * 1.5; // Velocidad de desplazamiento
    tabsContainer.scrollLeft = scrollLeft - walk;
  });
  
  // Updated states list without 'pagado' and 'despachado'
  const estados = ['todos', 'pendiente', 'en-camino', 'entregado'];
  const noOrdersMessage = document.getElementById('no-orders-message');

  let estadoActual = 'todos';
  
  function updateIndicator(activeTab) {
    if (!activeTab) return;
    tabIndicator.style.display = 'block';
    const tabRect = activeTab.getBoundingClientRect();
    const containerRect = tabsContainer.getBoundingClientRect();
    tabIndicator.style.width = `${tabRect.width}px`;
    const tabLeft = activeTab.offsetLeft;
    tabIndicator.style.transform = `translateX(${tabLeft}px)`;
    
    // Make sure the active tab is visible by scrolling if needed
    if (tabLeft < tabsContainer.scrollLeft) {
      tabsContainer.scrollLeft = tabLeft;
    } else if (tabLeft + tabRect.width > tabsContainer.scrollLeft + containerRect.width) {
      tabsContainer.scrollLeft = tabLeft + tabRect.width - containerRect.width;
    }
  }

  function updateCounter() {
    const visiblePedidos = Array.from(document.querySelectorAll('.pedido')).filter(p => p.style.display !== 'none');
    contador.innerHTML = estadoActual === 'todos' 
      ? `Mostrando todos los pedidos <span class="font-bold">${visiblePedidos.length}</span>`
      : `Mostrando pedidos con estado <span class="font-medium text-primary">${formatearEstado(estadoActual)}</span> <span class="font-bold">${visiblePedidos.length}</span>`;
  }

  function filtrarPedidos(estado) {
    const allPedidos = document.querySelectorAll('.pedido');
    let contadorVisible = 0;

    // Mostrar mensaje cuando no hay pedidos
    
    
    allPedidos.forEach((pedido, index) => {
      if (estado === 'todos' || pedido.dataset.estado === estado) {
        pedido.style.display = 'block';
        pedido.style.opacity = '0';
        pedido.style.transform = 'translateX(20px)';
        
        // Aplicar animación con retraso secuencial
        setTimeout(() => {
          pedido.style.opacity = '1';
          pedido.style.transform = 'translateX(0)';
        }, index * 50); // Retraso secuencial para efecto cascada
        
        contadorVisible++;
      } else {
        pedido.style.display = 'none';
      }
    });

    if (contadorVisible === 0) {
        noOrdersMessage.classList.remove('hidden');
    } else {
        noOrdersMessage.classList.add('hidden');
    }
    updateCounter();
  }
  
  function formatearEstado(estado) {
    const formateo = {
      'pendiente': 'Pendiente',
      'en-camino': 'En Camino',
      'entregado': 'Entregado'
    };
    return formateo[estado] || estado;
  }

  
  
  function actualizarTabs(estado) {
    estadoActual = estado;
    tabButtons.forEach(btn => {
      const isActive = btn.id === `tab-${estado}`;
      btn.classList.toggle('text-primary', isActive);
      btn.classList.toggle('text-gray-500', !isActive);
      
      // Animar botones de pestañas
      if (isActive) {
        btn.style.transform = 'translateY(-2px)';
        setTimeout(() => {
          btn.style.transform = 'translateY(0)';
        }, 200);
      }
      
      // Ensure the active tab is visible in the scroll area
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
  
  tabButtons.forEach(btn => {
    btn.addEventListener('click', function() {
      const estado = this.id.replace('tab-', '');
      actualizarTabs(estado);
      filtrarPedidos(estado);
    });
  });
  
  // Responsive handling for tab indicator on window resize
  window.addEventListener('resize', function() {
    const activeTab = document.getElementById(`tab-${estadoActual}`);
    if (activeTab) updateIndicator(activeTab);
  });
  
  window.addEventListener('load', function() {
    // Iniciar con cursor grab para indicar capacidad de desplazamiento
    tabsContainer.style.cursor = 'grab';
    
    // Configurar animación inicial
    actualizarTabs('todos');
    
    // Aplicar filtro con animación
    filtrarPedidos('todos');
  });
});