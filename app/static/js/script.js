document.addEventListener('DOMContentLoaded', function () {
    const forms = document.querySelectorAll('form');
    forms.forEach(form => {
      form.addEventListener('submit', function () {
        showSpinner();
      });
    });
  });

  // Función para mostrar el spinner
  function showSpinner() {
    const spinner = document.getElementById('loading-spinner');
    if (spinner) spinner.classList.remove('hidden');
  }

  // Función para ocultar el spinner (por si la necesitas después)
  function hideSpinner() {
    const spinner = document.getElementById('loading-spinner');
    if (spinner) spinner.classList.add('hidden');
  }

// Función para mostrar notificaciones
function showNotification(title, message, type) {
  const notification = document.createElement('div');
  notification.setAttribute('role', 'alert');

  let className, iconPath, messageClass;
  if (type === 'error') {
      className = 'flash-message slide-in';
      iconPath = 'M10 .5a9.5 9.5 0 1 0 9.5 9.5A9.51 9.51 0 0 0 10 .5ZM9.5 4a1.5 1.5 0 1 1 0 3 1.5 1.5 0 0 1 0-3ZM12 15H8a1 1 0 0 1 0-2h1v-3H8a1 1 0 0 1 0-2h2a1 1 0 1 1 1 1v4h1a1 1 0 0 1 0 2Z';
      messageClass = 'message';
  } else if (type === 'success') {
      className = 'flash-message-success slide-in';
      iconPath = 'M10 0.5a9.5 9.5 0 1 0 9.5 9.5A9.51 9.51 0 0 0 10 0.5ZM8.293 10.293a1 1 0 0 1 1.414 0L10 10.586l2.293-2.293a1 1 0 1 1 1.414 1.414l-3 3a1 1 0 0 1-1.414 0l-2-2a1 1 0 0 1 1.414-1.414Z';
      messageClass = 'message-success';
  } else {
      className = 'flash-message slide-in';
      iconPath = '';
      messageClass = 'message';
  }

  notification.className = className;
  notification.innerHTML = `
      <svg class="${type === 'success' ? 'flash-icon-success' : 'flash-icon'}" aria-hidden="true" xmlns="http://www.w3.org/2000/svg" fill="currentColor" viewBox="0 0 20 20">
          <path d="${iconPath}"/>
      </svg>
      <div class="${type === 'success' ? 'message-container-success' : 'message-container'}">
          <span class="${messageClass}"><strong>${title}:</strong></span> ${message}
      </div>
      <button onclick="this.parentElement.remove()" class="${type === 'success' ? 'flash-close-success' : 'flash-close'}">×</button>
  `;

  document.body.appendChild(notification);
  setTimeout(() => {
      notification.classList.add('fade-out');
      setTimeout(() => notification.remove(), 500);
  }, 5000);
}

// Función para actualizar el contador del carrito
function updateCartCounter(count) {
  const counter = document.getElementById('cart-counter');
  if (counter) {
      counter.textContent = count;
      counter.classList.add('scale-125');
      setTimeout(() => counter.classList.remove('scale-125'), 300);
      console.log("Contador actualizado a:", count);
  }
}

// Función para cerrar el flash message
function closeFlash() {
  const flash = document.getElementById('flash');
  if (flash) {
      flash.classList.remove('slide-in');
      flash.classList.add('slide-out');
      setTimeout(() => flash.style.display = 'none', 500);
  }
}

// Función para previsualizar la imagen
function previewImage(userId) {
  const fileInput = document.getElementById(`photoInput${userId}`);
  const preview = document.getElementById(`preview${userId}`);
  const file = fileInput.files[0];
  if (file) {
      const reader = new FileReader();
      reader.onload = function (e) {
          preview.src = e.target.result;
      };
      reader.readAsDataURL(file);
  }
}

// Función para configurar el spinner
function setupSpinner() {
  if (!document.getElementById('loading-spinner')) {
      const spinnerHTML = `
          <div id="loading-spinner" class="fixed inset-0 z-[900] flex items-center justify-center bg-black bg-opacity-50 hidden">
              <div class="bg-white p-6 rounded-lg shadow-xl flex flex-col items-center z-[1000]">
                  <div class="relative">
                      <div class="w-16 h-16 border-4 border-[#F49A13] border-t-transparent rounded-full animate-spin"></div>
                      <div class="absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2">
                          <i class="fas fa-motorcycle text-[#F49A13] text-xl"></i>
                      </div>
                  </div>
                  <p class="mt-4 text-gray-700 font-medium">Procesando...</p>
              </div>
          </div>
      `;
      document.body.insertAdjacentHTML('beforeend', spinnerHTML);
  }

  let isInitialPageLoad = true;
  setTimeout(() => isInitialPageLoad = false, 500);

  const originalAddToCart = window.addProductToCart;
  if (originalAddToCart) {
      window.addProductToCart = function (productId, quantity, button) {
          if (button) button.disabled = true;
          showSpinner();
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
                  if (button) button.disabled = false;
                  hideSpinner();
              });
      };
  }

  const originalFetch = window.fetch;
  window.fetch = function (url, options = {}) {
      if (isInitialPageLoad) return originalFetch.apply(this, arguments);

      const excludedUrls = ['/api/status', '/heartbeat'];
      const shouldShowSpinner = !excludedUrls.some(excluded => url.includes(excluded));
      if (shouldShowSpinner) showSpinner();

      return originalFetch.apply(this, arguments).finally(() => {
          if (shouldShowSpinner) hideSpinner();
      });
  };

  const forms = document.querySelectorAll('form:not([noajax])');
  forms.forEach(form => {
      form.addEventListener('submit', function (event) {
          if (!form.hasAttribute('novalidate') && !form.checkValidity()) return;
          if (!form.classList.contains('ajax-form') && !form.getAttribute('data-ajax')) {
              showSpinner();
          }
      });
  });
}

// Función para solicitar permiso de notificaciones
function requestNotificationPermission() {
  if (Notification.permission === 'default') {
      Notification.requestPermission().then(permission => {
          console.log(permission === 'granted' ? 'Notificaciones permitidas' : 'Notificaciones denegadas');
      });
  }
}

function mostrarAlertaEliminacion(productId) {
    Swal.fire({
        title: '¿Estás seguro?',
        text: "¿Seguro que quieres eliminar este producto?",
        icon: 'warning',
        showCancelButton: true,
        confirmButtonColor: '#F49A13', // Color principal de tu app
        cancelButtonColor: '#d33',
        confirmButtonText: 'Sí, eliminar',
        cancelButtonText: 'Cancelar'
    }).then((result) => {
        if (result.isConfirmed) {
            // Enviar el formulario cuando se confirma
            document.getElementById('deleteForm' + productId).submit();
        }
    });
}

// Inicialización al cargar el DOM
document.addEventListener('DOMContentLoaded', function () {
  const flash = document.getElementById('flash');
  if (flash) {
      flash.classList.add('slide-in');
      setTimeout(closeFlash, 3000);
  }

  handleGlobalCounter();
  setupSpinner();
  setupProfileModal();
  requestNotificationPermission();
});

