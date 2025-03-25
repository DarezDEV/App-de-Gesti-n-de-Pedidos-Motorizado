
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
z