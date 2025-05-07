document.addEventListener('DOMContentLoaded', function() {
    // Galería de imágenes
    const thumbnails = document.querySelectorAll('.thumbnail');
    const mainImage = document.querySelector('#main-image img');
    
    // Slider móvil
    const slider = document.querySelector('.product-slider');
    const slidesContainer = document.querySelector('.slides-container');
    const slides = document.querySelectorAll('.slide');
    const prevBtn = document.querySelector('.slider-nav.prev');
    const nextBtn = document.querySelector('.slider-nav.next');
    const dots = document.querySelectorAll('.dot');
    let currentIndex = 0;
    
    // Selección de cantidad
    const minusBtn = document.querySelector('.quantity-btn.minus');
    const plusBtn = document.querySelector('.quantity-btn.plus');
    const quantitySelect = document.querySelector('.quantity-select');
    
    // Cambiar imagen principal con thumbnails
    if (thumbnails.length > 0 && mainImage) {
        thumbnails.forEach(thumbnail => {
            thumbnail.addEventListener('click', function() {
                mainImage.src = this.querySelector('img').src;
                thumbnails.forEach(item => item.classList.remove('thumbnail-active'));
                this.classList.add('thumbnail-active');
                currentIndex = parseInt(this.getAttribute('data-index'));
            });
            thumbnail.addEventListener('keydown', function(e) {
                if (e.key === 'Enter' || e.key === ' ') {
                    e.preventDefault();
                    this.click();
                }
            });
        });
    }
    
    // Slider móvil
    if (slider && slidesContainer && slides.length > 0) {
        const slideWidth = slider.clientWidth;
        
        function showSlide(index) {
            if (index < 0) index = slides.length - 1;
            if (index >= slides.length) index = 0;
            currentIndex = index;
            slidesContainer.style.transform = `translateX(-${currentIndex * slideWidth}px)`;
            dots.forEach((dot, i) => {
                dot.classList.toggle('active', i === currentIndex);
                dot.style.opacity = i === currentIndex ? '1' : '0.5';
                dot.setAttribute('aria-selected', i === currentIndex);
            });
        }
        
        if (prevBtn && nextBtn) {
            prevBtn.addEventListener('click', () => showSlide(currentIndex - 1));
            nextBtn.addEventListener('click', () => showSlide(currentIndex + 1));
        }
        
        dots.forEach((dot, i) => {
            dot.addEventListener('click', () => showSlide(i));
            dot.addEventListener('keydown', (e) => {
                if (e.key === 'Enter' || e.key === ' ') {
                    e.preventDefault();
                    showSlide(i);
                }
            });
        });
        
        let touchStartX = 0;
        let touchEndX = 0;
        slider.addEventListener('touchstart', (e) => {
            touchStartX = e.changedTouches[0].screenX;
        });
        slider.addEventListener('touchend', (e) => {
            touchEndX = e.changedTouches[0].screenX;
            if (touchEndX < touchStartX - 50) showSlide(currentIndex + 1);
            if (touchEndX > touchStartX + 50) showSlide(currentIndex - 1);
        });
    }
    
    // Control de cantidad
    if (minusBtn && plusBtn && quantitySelect) {
        minusBtn.addEventListener('click', () => {
            if (quantitySelect.value > 1) quantitySelect.value--;
        });
        plusBtn.addEventListener('click', () => {
            if (quantitySelect.value < 10) quantitySelect.value++;
        });
    }
    
    // Acordeones
    const accordionHeaders = document.querySelectorAll('.accordion-header');
    accordionHeaders.forEach(header => {
        header.addEventListener('click', () => {
            const content = header.nextElementSibling;
            const isExpanded = header.getAttribute('aria-expanded') === 'true';
            header.setAttribute('aria-expanded', !isExpanded);
            content.classList.toggle('hidden');
            header.querySelector('i').classList.toggle('rotate-180');
        });
    });

    // Sistema de calificaciones
    initRatingSystem();

    // Funcionalidad para añadir al carrito
    initAddToCartFeature();
});

/**
 * Inicializa el sistema de calificaciones
 */
function initRatingSystem() {
    // Selección de estrellas
    const ratingStars = document.querySelectorAll('.rating-star');
    const submitButton = document.getElementById('submit-rating');
    let selectedRating = 0;
    
    if (!ratingStars.length || !submitButton) return;
    
    // Manejo de selección de estrellas
    ratingStars.forEach(star => {
        star.addEventListener('click', function() {
            const rating = parseInt(this.getAttribute('data-rating'));
            selectedRating = rating;
            
            updateStarDisplay(ratingStars, rating);
            submitButton.disabled = false;
        });
        
        star.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                star.click();
            }
        });
    });

    // Verificación del estado de calificación del usuario
    checkUserRatingStatus();

    // Configuración del envío de calificación
    submitButton.addEventListener('click', function() {
        if (selectedRating === 0) {
            alert('Por favor, selecciona una calificación');
            return;
        }

        submitRating(selectedRating);
    });
}

/**
 * Verifica si el usuario ya ha calificado este producto
 */
function checkUserRatingStatus() {
    const productId = document.querySelector('input[name="product_id"]').value;
    const ratingForm = document.getElementById('rating-form');
    const alreadyRated = document.getElementById('already-rated');
    const loginRequired = document.getElementById('login-required');
    const ratingFormContainer = document.getElementById('rating-form-container');
    
    if (!ratingFormContainer || !ratingForm || !alreadyRated || !loginRequired) return;
    
    fetch(`/check_user_rating/${productId}`)
        .then(response => response.json())
        .then(data => {
            const isLoggedIn = ratingFormContainer.dataset.userLoggedIn === 'true';
            
            if (!data.has_rated && isLoggedIn) {
                ratingForm.style.display = 'block';
                alreadyRated.style.display = 'none';
                loginRequired.style.display = 'none';
            } else if (data.has_rated) {
                ratingForm.style.display = 'none';
                alreadyRated.style.display = 'block';
                loginRequired.style.display = 'none';
            } else {
                ratingForm.style.display = 'none';
                alreadyRated.style.display = 'none';
                loginRequired.style.display = 'block';
            }
        })
        .catch(error => {
            console.error('Error checking user rating:', error);
        });
}

/**
 * Actualiza la interfaz de estrellas seleccionables
 * @param {NodeList} stars - Lista de elementos estrella
 * @param {Number} rating - Calificación seleccionada
 */
function updateStarDisplay(stars, rating) {
    stars.forEach(s => {
        const starRating = parseInt(s.getAttribute('data-rating'));
        s.classList.remove('fas', 'selected');
        s.classList.add('far');
        
        if (starRating <= rating) {
            s.classList.add('fas', 'selected');
            s.classList.remove('far');
        }
        
        s.setAttribute('aria-checked', starRating <= rating);
    });
}

/**
 * Envía la calificación al servidor
 * @param {Number} rating - Calificación seleccionada
 */
function submitRating(rating) {
    const comment = document.getElementById('comment').value;
    const productId = document.querySelector('input[name="product_id"]').value;

    fetch('/submit_product_evaluation', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            product_id: parseInt(productId),
            rating: rating,
            comment: comment
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            updateRatingUI(data.evaluation, data.new_avg, data.review_count, data.rating_distribution);
            document.getElementById('rating-form').style.display = 'none';
            document.getElementById('already-rated').style.display = 'block';
        } else {
            alert(data.message || 'Error al enviar la calificación');
        }
    })
    .catch(error => {
        console.error('Error:', error);
        alert('Error al enviar la calificación');
    });
}

/**
 * Actualiza toda la interfaz de calificaciones
 * @param {Object} evaluation - Objeto con la evaluación enviada
 * @param {Number} newAvg - Nueva calificación promedio
 * @param {Number} reviewCount - Nuevo número de reseñas
 * @param {Object} ratingDistribution - Distribución de calificaciones por estrellas
 */
function updateRatingUI(evaluation, newAvg, reviewCount, ratingDistribution) {
    // 1. Actualizar calificación promedio y conteo
    updateRatingSummary(newAvg, reviewCount);
    
    // 2. Actualizar distribución de estrellas
    updateRatingDistribution(ratingDistribution);
    
    // 3. Añadir el nuevo comentario a la lista
    addNewComment(evaluation);
    
    // 4. Actualizar la calificación mostrada en el encabezado del producto
    updateHeaderRating(newAvg, reviewCount);
}

/**
 * Actualiza el resumen principal de calificaciones
 * @param {Number} avgRating - Calificación promedio
 * @param {Number} reviewCount - Total de reseñas
 */
function updateRatingSummary(avgRating, reviewCount) {
    const avgRatingElement = document.getElementById('avg-rating');
    const summaryCountElement = document.getElementById('summary-count');
    
    if (avgRatingElement) {
        avgRatingElement.textContent = avgRating.toFixed(1);
    }
    
    if (summaryCountElement) {
        summaryCountElement.textContent = reviewCount;
    }
    
    // Actualizar estrellas del resumen
    updateStarElements('summary-stars', avgRating);
}

/**
 * Actualiza la visualización de estrellas en un elemento
 * @param {String} elementId - ID del elemento contenedor de estrellas
 * @param {Number} rating - Calificación a mostrar
 */
function updateStarElements(elementId, rating) {
    const starsContainer = document.getElementById(elementId);
    if (!starsContainer) return;
    
    starsContainer.innerHTML = '';
    
    for (let i = 1; i <= 5; i++) {
        const star = document.createElement('i');
        star.setAttribute('aria-hidden', 'true');
        
        if (rating >= i) {
            star.className = 'fas fa-star';
        } else if (rating > i - 1) {
            star.className = 'fas fa-star-half-alt';
        } else {
            star.className = 'far fa-star';
        }
        
        starsContainer.appendChild(star);
    }
    
    // Actualizar el atributo aria-label
    starsContainer.setAttribute('aria-label', `Calificación promedio: ${rating.toFixed(1)} de 5`);
}

/**
 * Actualiza la distribución de calificaciones por estrellas
 * @param {Object} distribution - Objeto con conteo por estrellas
 */
function updateRatingDistribution(distribution) {
    if (!distribution) return;
    
    // Actualizar la barra de distribución para cada nivel de estrellas
    for (let i = 5; i >= 1; i--) {
        const barElement = document.querySelector(`.h-2.bg-gray-200.rounded-full.flex-1.overflow-hidden + span:contains("${i}")`);
        const countElement = document.querySelector(`span.text-xs:contains("${i} ★") + div + span.text-xs.text-gray-500`);
        
        if (barElement && countElement) {
            const count = distribution[i] || 0;
            const percentage = distribution.total > 0 ? (count / distribution.total) * 100 : 0;
            
            barElement.querySelector('.bg-yellow-400').style.width = `${percentage}%`;
            countElement.textContent = count;
        }
    }
}

/**
 * Añade un nuevo comentario a la lista de comentarios
 * @param {Object} evaluation - Objeto con la evaluación enviada
 */
function addNewComment(evaluation) {
    const commentsContainer = document.getElementById('comments-container');
    if (!commentsContainer) return;
    
    // Ocultar el mensaje de "no hay reseñas" si existe
    const noReviews = document.getElementById('no-reviews');
    if (noReviews) {
        noReviews.style.display = 'none';
    }
    
    // Crear el nuevo comentario
    const newComment = document.createElement('div');
    newComment.className = 'border-b border-gray-200 pb-4 last:border-b-0 last:pb-0';
    
    // Generar HTML de estrellas
    let starsHTML = '';
    for (let i = 1; i <= 5; i++) {
        if (i <= evaluation.rating) {
            starsHTML += '<i class="fas fa-star text-sm" aria-hidden="true"></i>';
        } else {
            starsHTML += '<i class="far fa-star text-sm" aria-hidden="true"></i>';
        }
    }
    
    const formattedDate = new Date().toLocaleDateString('es-ES', {
        day: '2-digit',
        month: '2-digit',
        year: 'numeric'
    });
    
    newComment.innerHTML = `
        <div class="flex justify-between items-start mb-2">
            <div>
                <div class="flex text-yellow-400 mb-1" role="img" aria-label="Calificación: ${evaluation.rating} de 5">
                    ${starsHTML}
                </div>
                <h4 class="text-sm font-medium">${evaluation.user_name}</h4>
            </div>
            <div class="text-xs text-gray-500">${formattedDate}</div>
        </div>
        <p class="text-sm text-gray-700">${evaluation.comment || 'Sin comentario'}</p>
    `;
    
    // Insertar al principio de la lista
    commentsContainer.insertBefore(newComment, commentsContainer.firstChild);
}

/**
 * Actualiza la calificación en el encabezado del producto
 * @param {Number} avgRating - Calificación promedio
 * @param {Number} reviewCount - Total de reseñas
 */
function updateHeaderRating(avgRating, reviewCount) {
    const headerRating = document.querySelector('.flex.text-yellow-400[role="img"][aria-label^="Calificación promedio"]');
    if (!headerRating) return;
    
    // Actualizar estrellas
    let starsHTML = '';
    for (let i = 1; i <= 5; i++) {
        if (avgRating >= i) {
            starsHTML += '<i class="fas fa-star text-sm" aria-hidden="true"></i>';
        } else if (avgRating > i - 1) {
            starsHTML += '<i class="fas fa-star-half-alt text-sm" aria-hidden="true"></i>';
        } else {
            starsHTML += '<i class="far fa-star text-sm" aria-hidden="true"></i>';
        }
    }
    headerRating.innerHTML = starsHTML;
    
    // Actualizar el contador de reseñas
    const ratingCountElement = headerRating.nextElementSibling;
    if (ratingCountElement) {
        ratingCountElement.textContent = reviewCount;
    }
}
