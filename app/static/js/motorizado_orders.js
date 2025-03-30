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
  
    // **Función para marcar como entregado**
    window.marcarEntregado = orderId => {
      console.log("Marcando pedido:", orderId);
      fetch(`/marcar_entregado/${orderId}`, {
        method: 'POST',
        headers: {
          'X-Requested-With': 'XMLHttpRequest',
          'Content-Type': 'application/json'
        }
      })
        .then(response => response.json())
        .then(data => {
          if (data.success) {
            const pedido = document.querySelector(`.pedido[data-order-id="${orderId}"]`);
            if (pedido) {
              pedido.dataset.estado = 'entregado';
              const spanStatus = pedido.querySelector('span');
              if (spanStatus) {
                spanStatus.textContent = 'Entregado';
              }
              const actionButton = pedido.querySelector('button');
              if (actionButton) {
                actionButton.remove();
              }
              filtrarPedidos(estadoActual);
            }
            alert(data.message || '¡Pedido marcado como entregado!');
          } else {
            alert(data.message || 'Error al marcar como entregado');
          }
        })
        .catch(error => {
          console.error('Error en la petición:', error);
          alert('Error al conectar con el servidor');
        });
    };
  
    // **Delegación de eventos para botones**
    tabContent.addEventListener('click', event => {
      if (event.target.matches('button')) {
        const orderId = event.target.getAttribute('data-order-id');
        if (orderId) {
          window.marcarEntregado(orderId);
        }
      }
    });
  
    // **Función para filtrar pedidos**
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
  
    // **Función para formatear el estado**
    function formatearEstado(estado) {
      const formateo = {
        'en-camino': 'En Camino',
        'entregado': 'Entregado'
      };
      return formateo[estado] || estado;
    }
  
    // **Función para actualizar el indicador**
    function updateIndicator(activeTab) {
      if (!activeTab) return;
      
      // Obtener las dimensiones y posición del botón activo
      const tabRect = activeTab.getBoundingClientRect();
      const containerRect = tabsContainer.getBoundingClientRect();
      
      // Calcular la posición relativa al contenedor
      const leftPosition = activeTab.offsetLeft;
      
      // Configurar el indicador
      tabIndicator.style.width = `${tabRect.width}px`;
      tabIndicator.style.left = `${leftPosition}px`;
      
      // Hacer visible el indicador
      tabIndicator.style.display = 'block';
    }
  
    // **Actualizar estilos de pestañas**
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
      
      // Actualizar el indicador
      setTimeout(() => updateIndicator(activeTab), 100);
    }
  
    // **Eventos de pestañas**
    tabButtons.forEach(btn => {
      btn.addEventListener('click', function () {
        const estado = this.id.replace('tab-', '');
        actualizarTabs(estado);
        filtrarPedidos(estado);
      });
    });
  
    // **Solicitud de permiso para notificaciones**
    if (Notification.permission === 'default') {
      Notification.requestPermission().then(permission => {
        console.log(permission === 'granted' ? 'Notificaciones permitidas' : 'Notificaciones denegadas');
      });
    }
  
    // **Manejo de notificaciones vía socket**
    socket.on('new_delivery', function(order) {
      addOrderToList(order);
      
      if (Notification.permission === 'granted') {
        new Notification('Nuevo Pedido Asignado', {
          body: `Tienes un nuevo pedido #${order.order_id} para entregar`,
          icon: '/static/img/logo.png'
        });
      }
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
    });
  
    // **Inicialización**
    window.addEventListener('load', function() {
      actualizarTabs('todos');
      filtrarPedidos('todos');
      
      // Asegurar que el indicador se actualice cuando todo esté cargado
      setTimeout(() => {
        updateIndicator(document.getElementById(`tab-${estadoActual}`));
      }, 200);
    });
    
    // Actualizar el indicador cuando se redimensiona la ventana
    window.addEventListener('resize', function() {
      updateIndicator(document.getElementById(`tab-${estadoActual}`));
    });
  
    // **Función para agregar pedido a la lista**
    function addOrderToList(order) {
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
            ${order.status === 'en-camino' ? `
            <div class="mt-4 flex justify-end">
              <button data-order-id="${order.order_id}" onclick="marcarEntregado(${order.order_id})" class="bg-primary text-white py-2 px-4 rounded-lg hover:bg-primary-600 transition">
                Marcar como Entregado
              </button>
            </div>` : ''}
          </div>
        </div>
      `;
      tabContent.insertBefore(newOrder, tabContent.firstChild);
      updateCounter();
    }
  
    // **Función para actualizar el contador**
    function updateCounter() {
      const visiblePedidos = Array.from(document.querySelectorAll('.pedido')).filter(p => p.style.display !== 'none');
      contador.innerHTML = estadoActual === 'todos'
        ? `Mostrando todos los pedidos <span class="font-bold">${visiblePedidos.length}</span>`
        : `Mostrando pedidos con estado <span class="font-medium text-primary">${formatearEstado(estadoActual)}</span> <span class="font-bold">${visiblePedidos.length}</span>`;
      noOrdersMessage.classList.toggle('hidden', visiblePedidos.length > 0);
    }
  });