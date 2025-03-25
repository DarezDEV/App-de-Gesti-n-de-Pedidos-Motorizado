document.addEventListener('DOMContentLoaded', function () {
    initAddToCartButtons();
    initRecommendationButtons();
    initAddToCartForms();
    initCartUpdateForms();
    initRemoveButtons();
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
        // Si ya existe un manejador asignado, se elimina para evitar duplicados
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
        }, 300); // 300 ms de espera

        button._clickHandler = function(event) {
            // Si el botón está dentro de un enlace (<a>), se evita la navegación
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
        }, 300); // 300 ms de espera

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
    if (button) button.disabled = true; // Deshabilitar botón
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
    });
}

// ─── Actualizar contador del carrito ───────────────────────────────────────────
function updateCartCounter(count) {
    document.querySelectorAll('.cart-counter').forEach(el => {
        el.textContent = count;
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
        if (data.success && data.html) {
            refreshCartHTML(data.html);
        }
    })
    .catch(error => {
        console.error('Error al actualizar el carrito:', error);
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
                } else {
                    console.error("Error al eliminar el producto:", result.error);
                }
            } catch (error) {
                console.error("Error en la petición:", error);
            }
        });
    });
}

// ─── Refrescar la sección completa del carrito ────────────────────────────────
function updateCartItems() {
    fetch('/carrito')
    .then(response => response.text())
    .then(html => refreshCartHTML(html))
    .catch(error => {
        console.error('Error al actualizar el carrito:', error);
    });
}

// ─── Actualizar el HTML del carrito sin recargar la página ─────────────────────
function refreshCartHTML(html) {
    const parser = new DOMParser();
    const doc = parser.parseFromString(html, 'text/html');

    const newCartItems = doc.getElementById('cart-items-container');
    if (newCartItems) {
        document.getElementById('cart-items-container').innerHTML = newCartItems.innerHTML;
    }

    const newCartTotal = doc.getElementById('cart-total');
    if (newCartTotal) {
        document.getElementById('cart-total').textContent = newCartTotal.textContent;
    }

    initCartUpdateForms();
    initRemoveButtons();
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
    document.body.appendChild(container.firstElementChild);

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
document.addEventListener('DOMContentLoaded', function() {
    const checkoutButton = document.getElementById('checkout-button');
    const checkoutModal = document.getElementById('checkout-modal');
    const closeCheckoutModal = document.getElementById('close-checkout-modal');
    const cancelCheckout = document.getElementById('cancel-checkout');
    const paymentAmountInput = document.getElementById('payment-amount');
    const newAddressTextarea = document.getElementById('new-address');
    const addressRadios = document.querySelectorAll('input[name="address_id"]');
    
    if (checkoutButton) {
        checkoutButton.addEventListener('click', function() {
            checkoutModal.classList.remove('hidden');
        });
    }
    
    if (closeCheckoutModal) {
        closeCheckoutModal.addEventListener('click', function() {
            checkoutModal.classList.add('hidden');
        });
    }
    
    if (cancelCheckout) {
        cancelCheckout.addEventListener('click', function() {
            checkoutModal.classList.add('hidden');
        });
    }
    
    addressRadios.forEach(radio => {
        radio.addEventListener('change', function() {
            if (this.checked) {
                newAddressTextarea.value = '';
            }
        });
    });
    
    if (newAddressTextarea) {
        newAddressTextarea.addEventListener('input', function() {
            if (this.value.trim() !== '') {
                addressRadios.forEach(radio => {
                    radio.checked = false;
                });
            }
        });
    }
    
    window.addEventListener('click', function(event) {
        if (event.target === checkoutModal) {
            checkoutModal.classList.add('hidden');
        }
    });
});
