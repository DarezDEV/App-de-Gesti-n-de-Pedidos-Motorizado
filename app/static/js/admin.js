// Eliminar usuario
function deleteUser(id) {
    fetch(`/delete_user/${id}`, { method: "DELETE" })
        .then(response => response.json())
        .then(data => {
            alert(data.message);
            location.reload(); // Recargar tabla
        })
        .catch(error => console.error('Error al eliminar usuario:', error));
}

// Abrir modal de edición
function openEditModal(userId) {
    let modal = document.getElementById(`editModal${userId}`);
    if (!modal) return;
    
    modal.classList.remove('hidden');
    modal.classList.add('flex');
    sessionStorage.setItem(`editModalOpen${userId}`, 'true');

    setTimeout(() => {
        modal.children[0].classList.remove('scale-95', 'opacity-0');
        modal.children[0].classList.add('scale-100', 'opacity-100');
    }, 10);

    document.addEventListener("keydown", function escHandler(event) {
        if (event.key === "Escape") {
            closeModal(userId);
            document.removeEventListener("keydown", escHandler);
        }
    });

    modal.addEventListener("click", function outsideClickHandler(event) {
        if (event.target === modal) {
            closeModal(userId);
            modal.removeEventListener("click", outsideClickHandler);
        }
    });
}

// Cerrar modal de edición
function closeModal(userId) {
    let modal = document.getElementById(`editModal${userId}`);
    if (!modal) return;
    
    modal.children[0].classList.remove('scale-100', 'opacity-100');
    modal.children[0].classList.add('scale-95', 'opacity-0');
    
    setTimeout(() => {
        modal.classList.remove('flex');
        modal.classList.add('hidden');
        sessionStorage.removeItem(`editModalOpen${userId}`);
    }, 300);
}
//fin

// Abrir modal para agregar usuario
function openAddUserModal() {
    let modal = document.getElementById('addUserModal');
    if (!modal) return;
    
    modal.classList.remove('hidden');
    modal.classList.add('flex');
    
    setTimeout(() => {
        modal.children[0].classList.remove('scale-95', 'opacity-0');
        modal.children[0].classList.add('scale-100', 'opacity-100');
    }, 10);

    document.addEventListener("keydown", function escHandler(event) {
        if (event.key === "Escape") {
            closeAddUserModal();
            document.removeEventListener("keydown", escHandler);
        }
    });

    modal.addEventListener("click", function outsideClickHandler(event) {
        if (event.target === modal) {
            closeAddUserModal();
            modal.removeEventListener("click", outsideClickHandler);
        }
    });
}

// Cerrar modal de agregar usuario
function closeAddUserModal() {
    let modal = document.getElementById('addUserModal');
    if (!modal) return;
    
    modal.children[0].classList.remove('scale-100', 'opacity-100');
    modal.children[0].classList.add('scale-95', 'opacity-0');
    
    setTimeout(() => {
        modal.classList.remove('flex');
        modal.classList.add('hidden');
        sessionStorage.removeItem('addUserModalOpen');
    }, 300);
}
//fin


//add category modal

document.addEventListener('DOMContentLoaded', function() {
    const modal = document.getElementById('categoryModal');
    const openModalBtn = document.getElementById('openModalBtn');
    const closeModalBtn = document.getElementById('closeModalBtn');
    const cancelBtn = document.getElementById('cancelBtn');
    const categoryForm = document.getElementById('categoryForm');
    const imageInput = document.getElementById('categoryImage');
    const imagePreview = document.getElementById('imagePreview');
    const imagePreviewContainer = document.getElementById('imagePreviewContainer');
    const uploadContainer = document.getElementById('uploadContainer');
    const removeImageBtn = document.getElementById('removeImageBtn');

    // Funciones para el modal
    function openModal() {
        modal.classList.remove('hidden');
        setTimeout(() => modal.classList.remove('opacity-0'), 10);
    }

    function closeModal() {
        modal.classList.add('opacity-0');
        setTimeout(() => modal.classList.add('hidden'), 300);
        resetForm();
    }

    // Función para resetear el formulario
    function resetForm() {
        categoryForm.reset();
        imagePreviewContainer.classList.add('hidden');
        uploadContainer.classList.remove('hidden');
        imagePreview.src = '';
    }

    // Manejadores de eventos para el modal
    openModalBtn.addEventListener('click', openModal);
    closeModalBtn.addEventListener('click', closeModal);
    cancelBtn.addEventListener('click', closeModal);

    // Preview de imagen
    imageInput.addEventListener('change', function(e) {
        const file = e.target.files[0];
        const validTypes = ['image/jpeg', 'image/png', 'image/gif', 'image/webp'];
        
        if (file && !validTypes.includes(file.type)) {
            Swal.fire({
                title: 'Error',
                text: 'Solo se permiten imágenes (JPG, PNG, GIF, WEBP).',
                icon: 'error',
                confirmButtonText: 'Aceptar',
                confirmButtonColor: '#F49A13'
            });
            imageInput.value = '';
            return;
        }
        
        if (file) {
            const reader = new FileReader();
            
            reader.onload = function(e) {
                imagePreview.src = e.target.result;
                imagePreviewContainer.classList.remove('hidden');
                uploadContainer.classList.add('hidden');
            }
            
            reader.readAsDataURL(file);
        }
    });

    // Remover imagen
    removeImageBtn.addEventListener('click', function() {
        imageInput.value = '';
        imagePreviewContainer.classList.add('hidden');
        uploadContainer.classList.remove('hidden');
    });

    // Eliminar categoría con SweetAlert2
    document.querySelectorAll('.delete-category-btn').forEach(button => {
        button.addEventListener('click', function(e) {
            e.preventDefault();
            const categoryId = this.dataset.categoryId;

            Swal.fire({
                title: '¿Eliminar categoría?',
                text: 'Esta acción no se puede deshacer.',
                icon: 'warning',
                showCancelButton: true,
                confirmButtonColor: '#F49A13',
                cancelButtonColor: '#d33',
                confirmButtonText: 'Sí, eliminar',
                cancelButtonText: 'Cancelar'
            }).then((result) => {
                if (result.isConfirmed) {
                    const form = document.createElement('form');
                    form.method = 'POST';
                    form.action = `/categories/${categoryId}/delete`;
                    document.body.appendChild(form);
                    form.submit();
                }
            });
        });
    });
});

//fin

//edit category modal
document.querySelectorAll('.edit-category-btn').forEach(btn => {
    const categoryId = btn.dataset.categoryId;
    const modal = document.getElementById(`editCategoryModal${categoryId}`);
    const closeBtn = document.getElementById(`editcloseModalBtn${categoryId}`);
    const cancelBtn = document.getElementById(`editCancelBtn${categoryId}`);
    const categoryImage = document.getElementById(`categoryImage${categoryId}`);
    const categoryPreview = document.getElementById(`categoryPreview${categoryId}`);
    const removeImageBtn = document.getElementById(`removeImageBtn${categoryId}`);
    const form = document.getElementById(`categoryForm${categoryId}`);
    
    const defaultImage = categoryPreview?.src;
    let hasCustomImage = false;

    const showModal = () => {
        modal.classList.remove("hidden");
        requestAnimationFrame(() => {
            modal.classList.remove("opacity-0");
        });
    };

    const hideModal = () => {
        modal.classList.add("opacity-0");
        setTimeout(() => {
            modal.classList.add("hidden");
        }, 300);
    };

    btn.addEventListener("click", showModal);
    closeBtn?.addEventListener("click", hideModal);
    cancelBtn?.addEventListener("click", hideModal);
    
    modal?.addEventListener("click", (e) => {
        if (e.target === modal) hideModal();
    });

    categoryImage?.addEventListener("change", (event) => {
        const file = event.target.files[0];
        if (file) {
            const validTypes = ["image/jpeg", "image/png", "image/gif", "image/webp"];
            
            if (!validTypes.includes(file.type)) {
                Swal.fire({
                    title: 'Error',
                    text: 'Solo se permiten imágenes (JPG, PNG, GIF, WEBP)',
                    icon: 'error',
                    confirmButtonText: 'Aceptar',
                    confirmButtonColor: '#F49A13'
                });
                categoryImage.value = "";
                return;
            }

            const reader = new FileReader();
            reader.onload = (e) => {
                categoryPreview.src = e.target.result;
                hasCustomImage = true;
                removeImageBtn.classList.remove("hidden");
            };
            reader.readAsDataURL(file);
        }
    });

    removeImageBtn?.addEventListener("click", () => {
        Swal.fire({
            title: '¿Eliminar imagen?',
            text: '¿Estás seguro de que deseas eliminar esta imagen?',
            icon: 'warning',
            showCancelButton: true,
            confirmButtonColor: '#F49A13',
            cancelButtonColor: '#d33',
            confirmButtonText: 'Sí, eliminar',
            cancelButtonText: 'Cancelar'
        }).then((result) => {
            if (result.isConfirmed) {
                categoryPreview.src = defaultImage;
                categoryImage.value = "";
                hasCustomImage = false;
                removeImageBtn.classList.add("hidden");
            }
        });
    });
});

// Handle Delete Category
document.querySelectorAll('.delete-category-btn').forEach(btn => {
    btn.addEventListener('click', (e) => {
        e.preventDefault();
        Swal.fire({
            title: '¿Eliminar categoría?',
            text: '¿Estás seguro de que deseas eliminar esta categoría? Esta acción no se puede deshacer.',
            icon: 'warning',
            showCancelButton: true,
            confirmButtonColor: '#F49A13',
            cancelButtonColor: '#d33',
            confirmButtonText: 'Sí, eliminar',
            cancelButtonText: 'Cancelar'
        }).then((result) => {
            if (result.isConfirmed) {
                btn.closest('form').submit();
            }
        });
    });
});
//fin

//add product

document.addEventListener('DOMContentLoaded', function() {
    // Modal de Agregar Producto
    const modal = document.getElementById('productModal');
    const openModalBtn = document.getElementById('openModalBtn');
    const closeModalBtn = document.getElementById('closeModalBtn');
    const cancelBtn = document.getElementById('cancelBtn');
    
    // Abrir modal
    openModalBtn.addEventListener('click', function() {
        modal.classList.remove('hidden');
        setTimeout(() => {
            modal.classList.add('opacity-100');
        }, 10);
    });
    
    // Cerrar modal
    function closeModal() {
        modal.classList.remove('opacity-100');
        setTimeout(() => {
            modal.classList.add('hidden');
        }, 300);
    }
    
    closeModalBtn.addEventListener('click', closeModal);
    cancelBtn.addEventListener('click', closeModal);
    
    // Preview de la imagen principal
    const mainImage = document.getElementById('mainImage');
    const mainImagePreview = document.getElementById('mainImagePreview');
    const mainImageContainer = document.getElementById('mainImageContainer');
    const removeMainImageBtn = document.getElementById('removeMainImageBtn');
    
    mainImage.addEventListener('change', function() {
        if (this.files && this.files[0]) {
            const reader = new FileReader();
            reader.onload = function(e) {
                mainImagePreview.querySelector('img').src = e.target.result;
                mainImageContainer.classList.add('hidden');
                mainImagePreview.classList.remove('hidden');
            }
            reader.readAsDataURL(this.files[0]);
        }
    });
    
    removeMainImageBtn.addEventListener('click', function() {
        mainImage.value = '';
        mainImageContainer.classList.remove('hidden');
        mainImagePreview.classList.add('hidden');
    });
    
    // Preview de imagen 2
    const image2 = document.getElementById('image2');
    const image2Preview = document.getElementById('image2Preview');
    const image2Container = document.getElementById('image2Container');
    const removeImage2Btn = document.getElementById('removeImage2Btn');
    
    image2.addEventListener('change', function() {
        if (this.files && this.files[0]) {
            const reader = new FileReader();
            reader.onload = function(e) {
                image2Preview.querySelector('img').src = e.target.result;
                image2Container.classList.add('hidden');
                image2Preview.classList.remove('hidden');
            }
            reader.readAsDataURL(this.files[0]);
        }
    });
    
    removeImage2Btn.addEventListener('click', function() {
        image2.value = '';
        image2Container.classList.remove('hidden');
        image2Preview.classList.add('hidden');
    });
    
    // Preview de imagen 3
    const image3 = document.getElementById('image3');
    const image3Preview = document.getElementById('image3Preview');
    const image3Container = document.getElementById('image3Container');
    const removeImage3Btn = document.getElementById('removeImage3Btn');
    
    image3.addEventListener('change', function() {
        if (this.files && this.files[0]) {
            const reader = new FileReader();
            reader.onload = function(e) {
                image3Preview.querySelector('img').src = e.target.result;
                image3Container.classList.add('hidden');
                image3Preview.classList.remove('hidden');
            }
            reader.readAsDataURL(this.files[0]);
        }
    });
    
    removeImage3Btn.addEventListener('click', function() {
        image3.value = '';
        image3Container.classList.remove('hidden');
        image3Preview.classList.add('hidden');
    });
});
//fin

// Edit Product Modal F
document.addEventListener('DOMContentLoaded', function() {
    const editProductModal = document.getElementById('editProductModal');
    const editProductForm = document.getElementById('editProductForm');
    const closeEditModalBtn = document.getElementById('closeEditModalBtn');
    const cancelEditBtn = document.getElementById('cancelEditBtn');
    
    // Fields for edit form
    const editProductId = document.getElementById('edit_product_id');
    const editProductName = document.getElementById('edit_productName');
    const editProductPrice = document.getElementById('edit_productPrice');
    const editProductStock = document.getElementById('edit_productStock');
    const editActive1 = document.getElementById('edit_active_1');
    const editActive0 = document.getElementById('edit_active_0');
    const editDescription = document.getElementById('edit_description');
    
    // Image previews
    const editMainImagePreview = document.getElementById('editMainImagePreview');
    const editImage2Preview = document.getElementById('editImage2Preview');
    const editImage3Preview = document.getElementById('editImage3Preview');
    const currentMainImage = document.getElementById('current_main_image');
    const currentImage2 = document.getElementById('current_image2');
    const currentImage3 = document.getElementById('current_image3');
    
    // File inputs for image updates
    const editMainImage = document.getElementById('editMainImage');
    const editImage2 = document.getElementById('editImage2');
    const editImage3 = document.getElementById('editImage3');

    // Add click event to edit buttons
    document.querySelectorAll('.edit-product-btn').forEach(button => {
        button.addEventListener('click', function(e) {
            e.preventDefault();
            e.stopPropagation();
            
            const productId = this.getAttribute('data-product-id');
            const productName = this.getAttribute('data-name');
            const productPrice = this.getAttribute('data-price');
            const productStock = this.getAttribute('data-stock');
            const productStatus = this.getAttribute('data-status');
            const productDescription = this.getAttribute('data-description');
            const mainImagePath = this.getAttribute('data-main-image');
            const image2Path = this.getAttribute('data-image2') || '';
            const image3Path = this.getAttribute('data-image3') || '';
            const categoryId = this.getAttribute('data-category-id');
            
            // Set form action
            editProductForm.action = `/update_product/${productId}/${categoryId}`;
            
            // Populate form fields
            editProductId.value = productId;
            editProductName.value = productName;
            editProductPrice.value = productPrice;
            editProductStock.value = productStock;
            editDescription.value = productDescription;
            
            // Set radio button status
            if (productStatus === '1') {
                editActive1.checked = true;
            } else {
                editActive0.checked = true;
            }
            
            // Set current images and display previews
            currentMainImage.value = mainImagePath;
            currentImage2.value = image2Path;
            currentImage3.value = image3Path;
            
            // Update image previews
            if (mainImagePath) {
                editMainImagePreview.querySelector('img').src = `/static/uploads/${mainImagePath}`;
                editMainImagePreview.classList.remove('hidden');
                document.getElementById('editMainImageContainer').classList.add('hidden');
            } else {
                editMainImagePreview.classList.add('hidden');
                document.getElementById('editMainImageContainer').classList.remove('hidden');
            }
            
            if (image2Path) {
                editImage2Preview.querySelector('img').src = `/static/uploads/${image2Path}`;
                editImage2Preview.classList.remove('hidden');
                document.getElementById('editImage2Container').classList.add('hidden');
            } else {
                editImage2Preview.classList.add('hidden');
                document.getElementById('editImage2Container').classList.remove('hidden');
            }
            
            if (image3Path) {
                editImage3Preview.querySelector('img').src = `/static/uploads/${image3Path}`;
                editImage3Preview.classList.remove('hidden');
                document.getElementById('editImage3Container').classList.add('hidden');
            } else {
                editImage3Preview.classList.add('hidden');
                document.getElementById('editImage3Container').classList.remove('hidden');
            }
            
            // Show modal
            editProductModal.classList.remove('hidden');
            setTimeout(() => {
                editProductModal.classList.add('opacity-100');
            }, 10);
        });
    });
    
    // Image preview for main image upload
    editMainImage.addEventListener('change', function() {
        if (this.files && this.files[0]) {
            const reader = new FileReader();
            reader.onload = function(e) {
                editMainImagePreview.querySelector('img').src = e.target.result;
                editMainImagePreview.classList.remove('hidden');
                document.getElementById('editMainImageContainer').classList.add('hidden');
            };
            reader.readAsDataURL(this.files[0]);
        }
    });
    
    // Image preview for image2 upload
    editImage2.addEventListener('change', function() {
        if (this.files && this.files[0]) {
            const reader = new FileReader();
            reader.onload = function(e) {
                editImage2Preview.querySelector('img').src = e.target.result;
                editImage2Preview.classList.remove('hidden');
                document.getElementById('editImage2Container').classList.add('hidden');
            };
            reader.readAsDataURL(this.files[0]);
        }
    });
    
    // Image preview for image3 upload
    editImage3.addEventListener('change', function() {
        if (this.files && this.files[0]) {
            const reader = new FileReader();
            reader.onload = function(e) {
                editImage3Preview.querySelector('img').src = e.target.result;
                editImage3Preview.classList.remove('hidden');
                document.getElementById('editImage3Container').classList.add('hidden');
            };
            reader.readAsDataURL(this.files[0]);
        }
    });
    
    // Close modal functions
    const closeEditModal = () => {
        editProductModal.classList.remove('opacity-100');
        setTimeout(() => {
            editProductModal.classList.add('hidden');
        }, 300);
    };
    
    closeEditModalBtn.addEventListener('click', closeEditModal);
    cancelEditBtn.addEventListener('click', closeEditModal);
    
    // Close when clicking outside
    editProductModal.addEventListener('click', function(e) {
        if (e.target === editProductModal) {
            closeEditModal();
        }
    });
});
//fin


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


// Ordenar columnas de la tabla
const table = document.querySelector('#customers_table');
if (table) {
    const headers = table.querySelectorAll('thead th');
    const rows = table.querySelectorAll('tbody tr');
    
    headers.forEach((th, i) => {
        th.addEventListener('click', () => {
            const sortedRows = [...rows].sort((a, b) => {
                const tda = a.cells[i]?.textContent.trim().toLowerCase() || '';
                const tdb = b.cells[i]?.textContent.trim().toLowerCase() || '';
                return tda.localeCompare(tdb);
            });
            sortedRows.forEach(row => table.querySelector('tbody').appendChild(row));
        });
    });
}


function confirmDisable(userId) {
    Swal.fire({
        title: '¿Está seguro?',
        text: "¿Desea deshabilitar este usuario?",
        icon: 'warning',
        showCancelButton: true,
        confirmButtonColor: '#ef5350',
        cancelButtonColor: '#6c757d',
        confirmButtonText: 'Sí, deshabilitar',
        cancelButtonText: 'Cancelar'
    }).then((result) => {
        if (result.isConfirmed) {
            // If confirmed, submit the form
            document.getElementById('disableForm-' + userId).submit();
        }
    });

}

function confirmEnable(userId) {
    Swal.fire({
        title: '¿Está seguro?',
        text: "¿Desea habilitar este usuario?",
        icon: 'success',
        showCancelButton: true,
        confirmButtonColor: '#22c55e',
        cancelButtonColor: '#6c757d',
        confirmButtonText: 'Sí, habilitar',
        cancelButtonText: 'Cancelar'
    }).then((result) => {
        if (result.isConfirmed) {
            // If confirmed, submit the form
            document.getElementById('enableForm-' + userId).submit();
        }
    });

}