document.addEventListener('DOMContentLoaded', function () {
    initAddToCartButtons();
    initRecommendationButtons();
    initAddToCartForms();
    initCartUpdateForms();
    initRemoveButtons();
    initCheckoutModal();
    
    // Cargar el contador del carrito inmediatamente
    getCartCount();
});

// ─── Función debounce ─────────────────────────────────────────────────────────
function debounce(func, wait) {
    let timeout;
    return function(...args) {
        clearTimeout(timeout);
        timeout = setTimeout(() => func.apply(this, args), wait);
    };
}

// ─── Inicializar botones de "Añadir al carrito" con debounce ───────────────
function initAddToCartButtons() {
    const buttons = document.querySelectorAll('.add-to-cart-btn');
    buttons.forEach(button => {
        if (button._clickHandler) {
            button.removeEventListener('click', button._clickHandler);
        }
        const debouncedAddToCart = debounce(function() {
            let form = this.closest('.add-to-cart-form');
            if (!form) {
                form = document.querySelector('.add-to-cart-form');
            }
            if (form) {
                const formData = new FormData(form);
                const productId = formData.get('product_id');
                const quantity = parseInt(formData.get('quantity'), 10) || 1;
                addProductToCart(productId, quantity, this);
            } else {
                const productId = this.getAttribute('data-product-id');
                addProductToCart(productId, 1, this);
            }
        }, 300);

        button._clickHandler = function(event) {
            if (this.closest('a')) {
                event.preventDefault();
                event.stopPropagation();
            }
            debouncedAddToCart.apply(this);
        };

        button.addEventListener('click', button._clickHandler);
    });
}

// ─── Inicializar botones de recomendados con debounce ──────────────────────────
function initRecommendationButtons() {
    const recButtons = document.querySelectorAll('#recommendations-container .add-to-cart-btn');
    recButtons.forEach(button => {
        if (button._clickHandler) {
            button.removeEventListener('click', button._clickHandler);
        }
        const debouncedAddToCart = debounce(function() {
            const productId = this.getAttribute('data-product-id');
            addProductToCart(productId, 1, this);
        }, 300);

        button._clickHandler = function(event) {
            event.preventDefault();
            event.stopPropagation();
            debouncedAddToCart.apply(this);
        };

        button.addEventListener('click', button._clickHandler);
    });
}

// ─── Inicializar formularios de "Añadir al carrito" ────────────────────────────
function initAddToCartForms() {
    document.querySelectorAll('.add-to-cart-form').forEach(form => {
        form.addEventListener('submit', function (event) {
            event.preventDefault();
            event.stopPropagation();
            const formData = new FormData(form);
            const productId = formData.get('product_id');
            const quantity = parseInt(formData.get('quantity'), 10) || 1;
            addProductToCart(productId, quantity);
        });
    });
}

// ─── Función para agregar un producto al carrito vía AJAX ──────────────────────
function addProductToCart(productId, quantity, button) {
    if (button) button.disabled = true;
    const loadingSpinner = document.getElementById('loading-spinner');
    if (loadingSpinner) loadingSpinner.classList.remove('hidden');
    
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
            if (document.getElementById('cart-items-container')) {
                updateCartItems();
            }
            if (document.getElementById('checkout-modal') && !document.getElementById('checkout-modal').classList.contains('hidden')) {
                updateCheckoutModal();
            }
        } else {
            console.error('Error adding product to cart:', data.error);
            showNotification('Error', 'No se pudo agregar al carrito', 'error');
        }
    })
    .catch(error => {
        console.error('Error:', error);
        showNotification('Error', 'Error al procesar la solicitud', 'error');
    })
    .finally(() => {
        if (button) button.disabled = false;
        if (loadingSpinner) loadingSpinner.classList.add('hidden');
    });
}

// ─── Actualizar contador del carrito ───────────────────────────────────────────
function updateCartCounter(count) {
    // Seleccionar el contador del carrito usando el ID específico que proporcionaste
    const cartCounter = document.getElementById('cart-counter');
    
    if (cartCounter) {
        cartCounter.textContent = count;
        // Añadir una animación para hacer más notable la actualización
        cartCounter.classList.add('scale-125');
        setTimeout(() => {
            cartCounter.classList.remove('scale-125');
        }, 300);
    }
    
    // También actualizar cualquier otro elemento con la clase cart-counter (para mantener compatibilidad)
    document.querySelectorAll('.cart-counter').forEach(el => {
        if (el.id !== 'cart-counter') { // Evitar duplicar la animación en el elemento principal
            el.textContent = count;
            el.classList.add('scale-125');
            setTimeout(() => {
                el.classList.remove('scale-125');
            }, 300);
        }
    });
}

// ─── función para actualizar el total del carrito en toda la UI ─────────────
function updateCartTotal(total) {
    // Actualizar el total principal
    const cartTotalElement = document.getElementById('cart-total');
    if (cartTotalElement) {
        cartTotalElement.textContent = `RD$${total.toFixed(2)}`;
    }
    
    // Actualizar cualquier instancia del total en el modal de checkout
    const checkoutTotals = document.querySelectorAll('#checkout-modal .bg-gray-50 .font-semibold');
    checkoutTotals.forEach(element => {
        element.textContent = `RD$${total.toFixed(2)}`;
    });
    
    // Actualizar el valor mínimo y valor por defecto del campo payment_amount
    const paymentInput = document.getElementById('payment-amount');
    if (paymentInput) {
        paymentInput.min = total;
        paymentInput.value = total;
    }
}

// ─── Función para obtener el contador del carrito ──────────────────────────────
function getCartCount() {
    fetch('/get_cart_count')
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                updateCartCounter(data.cart_count);
            }
        })
        .catch(error => {
            console.error('Error al obtener el contador del carrito:', error);
        });
}

// ─── Función para asegurar que todas las operaciones actualicen el contador ────
function ensureCartCountUpdated() {
    // Después de cualquier acción que modifique el carrito, llamar a getCartCount
    fetch('/get_cart_count')
        .then(response => response.json())
        .then(data => {
            updateCartCounter(data.cart_count);
        })
        .catch(error => {
            console.error('Error al actualizar el contador del carrito:', error);
        });
}

// ─── Inicializar eventos para actualizar la cantidad en el carrito ──────────────
function initCartUpdateForms() {
    document.querySelectorAll('.update-form').forEach(form => {
        form.addEventListener('change', function (event) {
            event.preventDefault();
            updateCartItem(this);
        });
    });
}

// ─── Actualizar un ítem del carrito vía AJAX ──────────────────────────────────
function updateCartItem(form) {
    const formData = new FormData(form);
    
    fetch(form.action, {
        method: 'POST',
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            if (data.html) {
                refreshCartHTML(data.html);
            } else {
                updateCartItems();
            }
            
            // 1. Actualiza el contador del carrito manualmente si el servidor proporciona el count
            if (data.cart_count !== undefined) {
                updateCartCounter(data.cart_count);
            } else {
                // Si el servidor no proporciona el contador, obtenlo explícitamente
                getCartCount();
            }
            
            // 2. Actualiza el valor total en la interfaz de usuario
            if (data.cart_total !== undefined) {
                updateCartTotal(data.cart_total);
            }
            
            // 3. Actualiza el modal de checkout
            updateCheckoutModal();
        } else {
            console.error('Error al actualizar el carrito:', data.error);
            updateCartItems();
        }
    })
    .catch(error => {
        console.error('Error al actualizar el carrito:', error);
        updateCartItems();
    });
}


// ─── Inicializar eventos para eliminar productos ──────────────────────────────
function initRemoveButtons() {
    document.querySelectorAll('.remove-btn').forEach(button => {
        button.addEventListener('click', async function (event) {
            event.stopPropagation();
            const cartId = this.getAttribute('data-id');
            const url = this.getAttribute('data-url');

            if (!url) {
                console.error("Error: La URL es inválida.");
                return;
            }

            try {
                const response = await fetch(url, {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ "cart_id": cartId })
                });

                const result = await response.json();

                if (result.success) {
                    updateCartItems();
                    ensureCartCountUpdated();
                    if (document.getElementById('checkout-modal') && !document.getElementById('checkout-modal').classList.contains('hidden')) {
                        updateCheckoutModal();
                    }
                } else {
                    console.error("Error al eliminar el producto:", result.error);
                    showNotification('Error', 'No se pudo eliminar el producto', 'error');
                }
            } catch (error) {
                console.error("Error en la petición:", error);
                showNotification('Error', 'Error al procesar la solicitud', 'error');
            }
        });
    });
}

// ─── Refrescar la sección completa del carrito ────────────────────────────────
function updateCartItems() {
    fetch('/dashboard/cliente/carrito', {
        headers: {
            'X-Requested-With': 'XMLHttpRequest'
        }
    })
    .then(response => response.text())
    .then(html => {
        refreshCartHTML(html);
    })
    .catch(error => {
        console.error('Error al actualizar el carrito:', error);
        showNotification('Error', 'No se pudo actualizar el carrito', 'error');
    });
}

// ─── Actualizar el HTML del carrito sin recargar la página ─────────────────────
function refreshCartHTML(html) {
    const parser = new DOMParser();
    const doc = parser.parseFromString(html, 'text/html');
    const newCartItemsContainer = doc.getElementById('cart-items-container');
    const currentCartItemsContainer = document.getElementById('cart-items-container');
    
    if (newCartItemsContainer && currentCartItemsContainer) {
        currentCartItemsContainer.innerHTML = newCartItemsContainer.innerHTML;
        const hasItems = currentCartItemsContainer.querySelector('.cart-item');
        const emptyCartMessage = document.getElementById('empty-cart-message');
        
        if (emptyCartMessage) {
            if (hasItems) {
                emptyCartMessage.classList.add('hidden');
            } else {
                emptyCartMessage.classList.remove('hidden');
            }
        }
        
        // Extraer y actualizar el total del carrito
        const newCartTotal = doc.getElementById('cart-total');
        const currentCartTotal = document.getElementById('cart-total');
        
        if (newCartTotal && currentCartTotal) {
            currentCartTotal.textContent = newCartTotal.textContent;
            
            // Extraer el valor numérico para usar en otros elementos
            const totalValue = parseFloat(newCartTotal.textContent.replace('RD$', ''));
            updateCartTotal(totalValue);
        }
        
        const newCheckoutButton = doc.getElementById('checkout-button');
        const currentCheckoutButton = document.getElementById('checkout-button');
        
        if (newCheckoutButton && currentCheckoutButton) {
            const isDisabled = newCheckoutButton.hasAttribute('disabled');
            currentCheckoutButton.disabled = isDisabled;
        }
        
        // Actualizar el contador del carrito después de refrescar
        getCartCount();
        
        initCartUpdateForms();
        initRemoveButtons();
    } else {
        console.error('No se encontró el contenedor de ítems del carrito en la respuesta o en el DOM');
    }
}
// ─── Mostrar alerta de éxito al agregar producto al carrito ────────────────────
function showFlash() {
    let existingFlash = document.getElementById('flash');
    if (existingFlash) {
        existingFlash.remove();
    }

    const flashHTML = `
    <div id="flash" class="flash-message-success slide-in" role="alert">
        <svg class="flash-icon-success" aria-hidden="true" xmlns="http://www.w3.org/2000/svg" fill="currentColor" viewBox="0 0 20 20">
            <path d="M10 0.5a9.5 9.5 0 1 0 9.5 9.5A9.51 9.51 0 0 0 10 0.5ZM8.293 10.293a1 1 0 0 1 1.414 0L10 10.586l2.293-2.293a1 1 0 1 1 1.414 1.414l-3 3a1 1 0 0 1-1.414 0l-2-2a1 1 0 0 1 1.414-1.414Z"/>
        </svg>
        <div class="message-container-success">
            <span class="message-success">Éxito:</span> Agregado al carrito 
        </div>
        <button onclick="closeFlash()" class="flash-close-success">&times;</button>
    </div>
    `;
    const container = document.createElement('div');
    container.innerHTML = flashHTML;
    const notificationsContainer = document.getElementById('notifications') || document.body;
    notificationsContainer.appendChild(container.firstElementChild);

    setTimeout(() => {
        const flash = document.getElementById('flash');
        if (flash) {
            flash.classList.add('slide-out');
            flash.addEventListener('transitionend', () => {
                flash.remove();
            });
        }
    }, 3000);
}

// ─── Función para cerrar la alerta manualmente ────────────────────────────────
function closeFlash() {
    const flash = document.getElementById('flash');
    if (flash) {
        flash.classList.add('slide-out');
        flash.addEventListener('transitionend', () => {
            flash.remove();
        });
    }
}

// ─── Script para el modal de checkout (cart.html) ─────────────────────────────
function initCheckoutModal() {
    const checkoutButton = document.getElementById('checkout-button');
    const checkoutModal = document.getElementById('checkout-modal');
    const closeCheckoutModal = document.getElementById('close-checkout-modal');
    const cancelCheckout = document.getElementById('cancel-checkout');
    
    if (checkoutButton) {
        checkoutButton.addEventListener('click', function() {
            if (checkoutModal) {
                checkoutModal.classList.remove('hidden');
            }
        });
    }
    
    if (closeCheckoutModal) {
        closeCheckoutModal.addEventListener('click', function() {
            if (checkoutModal) {
                checkoutModal.classList.add('hidden');
            }
        });
    }
    
    if (cancelCheckout) {
        cancelCheckout.addEventListener('click', function() {
            if (checkoutModal) {
                checkoutModal.classList.add('hidden');
            }
        });
    }
    
    if (checkoutModal) {
        window.addEventListener('click', function(event) {
            if (event.target === checkoutModal) {
                checkoutModal.classList.add('hidden');
            }
        });
    }
}

// ─── Mostrar notificación personalizada ─────────────────────────────────────────
function showNotification(title, message, type) {
    const notification = document.createElement('div');
    notification.setAttribute('role', 'alert');
    notification.id = 'flash';

    if (type === 'error') {
        notification.className = 'flash-message slide-in';
        notification.innerHTML = `
            <svg class="flash-icon" aria-hidden="true" xmlns="http://www.w3.org/2000/svg" fill="currentColor" viewBox="0 0 20 20">
                <path d="M10 .5a9.5 9.5 0 1 0 9.5 9.5A9.51 9.51 0 0 0 10 .5ZM9.5 4a1.5 1.5 0 1 1 0 3 1.5 1.5 0 0 1 0-3ZM12 15H8a1 1 0 0 1 0-2h1v-3H8a1 1 0 0 1 0-2h2a1 1 0 1 1 1 1v4h1a1 1 0 0 1 0 2Z"/>
            </svg>
            <div class="message-container">
                <span class="message">Advertencia:</span> ${message}
            </div>
            <button onclick="closeFlash()" class="flash-close">&times;</button>
        `;
    } else if (type === 'success') {
        notification.className = 'flash-message-success slide-in';
        notification.innerHTML = `
            <svg class="flash-icon-success" aria-hidden="true" xmlns="http://www.w3.org/2000/svg" fill="currentColor" viewBox="0 0 20 20">
                <path d="M10 0.5a9.5 9.5 0 1 0 9.5 9.5A9.51 9.51 0 0 0 10 0.5ZM8.293 10.293a1 1 0 0 1 1.414 0L10 10.586l2.293-2.293a1 1 0 1 1 1.414 1.414l-3 3a1 1 0 0 1-1.414 0l-2-2a1 1 0 0 1 1.414-1.414Z"/>
            </svg>
            <div class="message-container-success">
                <span class="message-success">Éxito:</span> ${message}
            </div>
            <button onclick="closeFlash()" class="flash-close-success">&times;</button>
        `;
    } else {
        notification.className = 'flash-message slide-in';
        notification.innerHTML = `
            <div class="message-container">
                <span class="message"><strong>${title}:</strong></span> ${message}
            </div>
            <button onclick="closeFlash()" class="flash-close">&times;</button>
        `;
    }
    const notificationsContainer = document.getElementById('notifications') || document.body;
    notificationsContainer.appendChild(notification);

    setTimeout(() => {
        notification.classList.add('slide-out');
        notification.addEventListener('transitionend', () => {
            notification.remove();
        });
    }, 3000);
}

// ─── Actualizar el modal de checkout con datos actuales ───────────
function updateCheckoutModal() {
    fetch('/get_cart_data', {
        method: 'GET',
        headers: { 'Content-Type': 'application/json' }
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            // Actualizar todos los elementos relacionados con el total
            updateCartTotal(data.cart_total);
        } else {
            console.error('Error al obtener datos del carrito:', data.error);
        }
    })
    .catch(error => {
        console.error('Error al actualizar el modal de checkout:', error);
    });
}

// ─── Inicializar actualización del modal al abrirlo ────────────────────────────
function initModalUpdate() {
    const checkoutModal = document.getElementById('checkout-modal');
    if (checkoutModal) {
        checkoutModal.addEventListener('show.bs.modal', function () {
            updateCheckoutModal();
        });
    }
}

initModalUpdate();

// ─── Función para manejar la confirmación del pedido ───────────────────────────
function confirmOrder() {
    // Obtener los valores del formulario
    const checkoutForm = document.querySelector('#checkout-modal form');
    const formData = new FormData(checkoutForm);
    
    // Extraer los datos necesarios
    const newAddress = formData.get('new_address');
    const paymentAmount = formData.get('payment_amount');
    
    // Validar que hay una dirección
    if (!newAddress || newAddress.trim() === '') {
        showNotification('Error', 'Por favor, ingresa una dirección de entrega', 'error');
        return;
    }
    
    // Validar que hay un monto de pago válido
    if (!paymentAmount || parseFloat(paymentAmount) <= 0) {
        showNotification('Error', 'Por favor, ingresa un monto de pago válido', 'error');
        return;
    }
    
    // Crear el objeto de datos a enviar
    const orderData = {
        new_address: newAddress,
        payment_amount: paymentAmount
    };
    
    // Mostrar indicador de carga
    const loadingSpinner = document.getElementById('loading-spinner');
    if (loadingSpinner) loadingSpinner.classList.remove('hidden');
    
    // Realizar la petición al servidor
    fetch('/checkout', {
        method: 'POST',
        headers: { 
            'Content-Type': 'application/json',
            'X-CSRFToken': getCsrfToken()  // Función para obtener el token CSRF (definida más abajo)
        },
        body: JSON.stringify(orderData)
    })
    .then(response => {
        if (response.redirected) {
            // Si el servidor redirige, seguimos la redirección
            window.location.href = response.url;
            return;
        }
        return response.json();
    })
    .then(data => {
        if (data && data.success) {
            showNotification('Éxito', 'Pedido confirmado', 'success');
            const checkoutModal = document.getElementById('checkout-modal');
            if (checkoutModal) {
                checkoutModal.classList.add('hidden');
            }
            // Redirigir a la página de confirmación si existe un order_id
            if (data.order_id) {
                window.location.href = `/dashboard/cliente/orden/confirmación/${data.order_id}`;
            }
        } else if (data && data.error) {
            showNotification('Error', data.error, 'error');
        } else {
            showNotification('Error', 'No se pudo confirmar el pedido', 'error');
        }
    })
    .catch(error => {
        console.error('Error al confirmar el pedido:', error);
        showNotification('Error', 'Error al procesar la solicitud', 'error');
    })
    .finally(() => {
        if (loadingSpinner) loadingSpinner.classList.add('hidden');
    });

}

// Función para obtener el token CSRF (necesario para peticiones POST)
function getCsrfToken() {
    // Buscar el token en una meta etiqueta
    const csrfTokenMeta = document.querySelector('meta[name="csrf-token"]');
    if (csrfTokenMeta) {
        return csrfTokenMeta.getAttribute('content');
    }
    
    // Alternativa: buscar en un input oculto en el formulario
    const csrfTokenInput = document.querySelector('input[name="csrf_token"]');
    if (csrfTokenInput) {
        return csrfTokenInput.value;
    }
    
    return '';
}

// ─── Inicializar el botón de confirmación del pedido ───────────────────────────
function initConfirmOrderButton() {
    const checkoutForm = document.querySelector('#checkout-modal form');
    if (checkoutForm) {
        checkoutForm.addEventListener('submit', function(event) {
            event.preventDefault();
            confirmOrder();
        });
    }
}

initConfirmOrderButton();

// ─── Función para manejar la cancelación del pedido ────────────────────────────
function cancelOrder() {
    const checkoutModal = document.getElementById('checkout-modal');
    if (checkoutModal) {
        checkoutModal.classList.add('hidden');
    }
}

// ─── Inicializar el botón de cancelación del pedido ────────────────────────────
function initCancelOrderButton() {
    const cancelButton = document.getElementById('cancel-checkout');
    if (cancelButton) {
        cancelButton.addEventListener('click', function() {
            cancelOrder();
        });
    }
}

initCancelOrderButton();

// ─── Función para manejar la selección de dirección ────────────────────────────
function handleAddressSelection() {
    const addressRadios = document.querySelectorAll('input[name="address_id"]');
    const newAddressTextarea = document.getElementById('new-address');
    
    addressRadios.forEach(radio => {
        radio.addEventListener('change', function() {
            if (this.checked) {
                newAddressTextarea.value = '';
            }
        });
    });
    
    newAddressTextarea.addEventListener('input', function() {
        if (this.value.trim() !== '') {
            addressRadios.forEach(radio => {
                radio.checked = false;
            });
        }
    });
}

handleAddressSelection();