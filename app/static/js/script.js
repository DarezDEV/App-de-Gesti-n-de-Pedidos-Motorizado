
window.onload = function () {
    let flash = document.getElementById('flash');
    if (flash) {
        flash.classList.add('slide-in');  // Agregar animación de entrada
        setTimeout(() => {
            closeFlash();
        }, 3000);
    }
};

function closeFlash() {
    let flash = document.getElementById('flash');
    if (flash) {
        flash.classList.remove('slide-in'); // Eliminar animación de entrada
        flash.classList.add('slide-out');  // Agregar animación de salida
        setTimeout(() => {
            flash.style.display = 'none';
        }, 500);
    }
}

function previewImage(userId) {
    const fileInput = document.getElementById(`photoInput${userId}`);
    const preview = document.getElementById(`preview${userId}`);
    
    const file = fileInput.files[0];
    if (file) {
        const reader = new FileReader();
        reader.onload = function(e) {
            preview.src = e.target.result;
        };
        reader.readAsDataURL(file);
    }
}

// static/js/global_counter.js
document.addEventListener('DOMContentLoaded', function() {
  const pendingOrdersBadge = document.getElementById('pending-orders-badge');
  
  if (!pendingOrdersBadge) return;
  
  // Verificar si estamos en la página de admin_orders
  const isOrdersPage = window.location.pathname.includes('/admin/orders') || 
                       window.location.pathname.includes('/motorizado/pedidos');
  
  if (isOrdersPage) {
    // Si estamos en la página de pedidos, el contador se actualizará 
    // a través del código existente en admin_orders.js
    return;
  }
  
  // Para otras páginas, usar localStorage para obtener el conteo
  const pendingCount = localStorage.getItem('pendingOrdersCount') || '0';
  updateBadge(parseInt(pendingCount, 10));
  
  // Conectar a socket.io para recibir actualizaciones en tiempo real
  try {
    const socket = io('/admin');
    
    // Escuchar nueva orden
    socket.on('new_order', function(order) {
      if (order.status === 'pendiente') {
        const currentCount = parseInt(localStorage.getItem('pendingOrdersCount') || '0', 10);
        const newCount = currentCount + 1;
        localStorage.setItem('pendingOrdersCount', newCount.toString());
        updateBadge(newCount);
      }
    });
    
    // Escuchar actualización de estado
    socket.on('order_status_update', function(order) {
      // Como solo tenemos la información del pedido actualizado,
      // solicitar a la página principal que recalcule el conteo
      window.dispatchEvent(new CustomEvent('recalculate-pending'));
    });
  } catch (error) {
    console.error('Error al conectar con socket.io:', error);
  }
  
  function updateBadge(count) {
    if (count > 0) {
      pendingOrdersBadge.textContent = count;
      pendingOrdersBadge.classList.remove('hidden');
    } else {
      pendingOrdersBadge.classList.add('hidden');
    }
  }
});






// spinner 

// Agregar el HTML del spinner al final del body (puedes colocarlo donde prefieras)
document.addEventListener('DOMContentLoaded', function() {
    // Crear el elemento spinner si no existe
    if (!document.getElementById('loading-spinner')) {
        const spinnerHTML = `
          <div id="loading-spinner" class="fixed inset-0 z-[900] flex items-center justify-center bg-black bg-opacity-50 hidden">
            <div class="bg-white p-6 rounded-lg shadow-xl flex flex-col items-center z-[1000]">
              <div class="relative">
                <!-- Círculo exterior giratorio -->
                <div class="w-16 h-16 border-4 border-[#F49A13] border-t-transparent rounded-full animate-spin"></div>
                <!-- Ícono de motocicleta en el centro -->
                <div class="absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2">
                  <i class="fas fa-motorcycle text-[#F49A13] text-xl"></i>
                </div>
              </div>
              <p class="mt-4 text-gray-700 font-medium">Procesando...</p>
            </div>
          </div>
        `;
        
        const spinnerContainer = document.createElement('div');
        spinnerContainer.innerHTML = spinnerHTML;
        document.body.appendChild(spinnerContainer.firstChild);
      }
      
      const spinner = document.getElementById('loading-spinner');
      
      // Asegurar que el spinner esté oculto al cargar la página
      spinner.classList.add('hidden');
    
      // Variable para rastrear si la página se está cargando inicialmente
      let isInitialPageLoad = true;
      
      // Después de un breve retraso, marca que la carga inicial ha terminado
      setTimeout(() => {
        isInitialPageLoad = false;
      }, 500);
    
      // Modificar función addProductToCart para mostrar el spinner
      const originalAddToCart = window.addProductToCart;
      if (originalAddToCart) {
        window.addProductToCart = function(productId, quantity, button) {
          if (button) button.disabled = true; // Deshabilitar botón
          spinner.classList.remove('hidden'); // Mostrar spinner
          
          fetch('/add_to_cart/', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ product_id: productId, quantity: quantity })
          })
          .then(response => response.json())
          .then(data => {
            if (data.success) {
              updateCartCounter(data.cart_count);
              showFlash();
            }
          })
          .catch(error => console.error('Error:', error))
          .finally(() => {
            if (button) button.disabled = false; // Rehabilitar botón
            spinner.classList.add('hidden'); // Ocultar spinner
          });
        };
      }
      
      // Resto de las funciones permanecen igual...
      
      // Interceptar fetch con control para evitar mostrar en carga inicial
      const originalFetch = window.fetch;
      window.fetch = function(url, options = {}) {
        // No mostrar el spinner durante la carga inicial de la página
        if (isInitialPageLoad) {
          return originalFetch.apply(this, arguments);
        }
        
        // No mostrar el spinner para peticiones específicas
        const excludedUrls = ['/api/status', '/heartbeat']; 
        const shouldShowSpinner = !excludedUrls.some(excluded => url.includes(excluded));
        
        if (shouldShowSpinner) {
          spinner.classList.remove('hidden'); // Mostrar spinner
        }
        
        return originalFetch.apply(this, arguments)
          .finally(() => {
            if (shouldShowSpinner) {
              spinner.classList.add('hidden'); // Ocultar spinner
            }
          });
      };
      
      // Interceptar XMLHttpRequest con control para evitar mostrar en carga inicial
      const originalXHROpen = XMLHttpRequest.prototype.open;
      const originalXHRSend = XMLHttpRequest.prototype.send;
      
      XMLHttpRequest.prototype.open = function() {
        this._url = arguments[1]; // Guardar la URL
        return originalXHROpen.apply(this, arguments);
      };
      
      XMLHttpRequest.prototype.send = function() {
        // No mostrar el spinner durante la carga inicial de la página
        if (isInitialPageLoad) {
          return originalXHRSend.apply(this, arguments);
        }
        
        // No mostrar el spinner para peticiones específicas
        const excludedUrls = ['/api/status', '/heartbeat'];
        const shouldShowSpinner = !excludedUrls.some(excluded => this._url && this._url.includes(excluded));
        
        if (shouldShowSpinner) {
          spinner.classList.remove('hidden'); // Mostrar spinner
        }
        
        this.addEventListener('loadend', function() {
          if (shouldShowSpinner) {
            spinner.classList.add('hidden'); // Ocultar spinner
          }
        });
        
        return originalXHRSend.apply(this, arguments);
      };
    
    // Para formularios que envían datos con AJAX
    const forms = document.querySelectorAll('form');
    forms.forEach(form => {
      // Solo si el formulario no tiene el atributo noajax
      if (!form.hasAttribute('noajax')) {
        form.addEventListener('submit', function(event) {
          // Verificar si el formulario tiene validación HTML5 y si es válido
          if (!form.hasAttribute('novalidate') && !form.checkValidity()) {
            return; // No mostrar spinner si el formulario no es válido
          }
          
          // Si el formulario tiene la clase ajax-form o data-ajax=true, 
          // asumimos que ya está manejado por otro código AJAX
          if (!form.classList.contains('ajax-form') && !form.getAttribute('data-ajax')) {
            // Mostrar el spinner
            spinner.classList.remove('hidden');
          }
        });
      }
    });
  });