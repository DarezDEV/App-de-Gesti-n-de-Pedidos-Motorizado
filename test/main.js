document.addEventListener('DOMContentLoaded', function() {
  // Referencias a elementos del DOM
  const menuBtn = document.getElementById('menuBtn');
  const sidebar = document.getElementById('sidebar');
  
  // Toggle del menú lateral en dispositivos móviles
  menuBtn.addEventListener('click', function() {
      sidebar.classList.toggle('-translate-x-full');
      sidebar.classList.toggle('translate-x-0');
  });
  
  // Cerrar sidebar en pantallas pequeñas cuando se hace clic fuera de él
  document.addEventListener('click', function(event) {
      const isSmallScreen = window.innerWidth < 768;
      const clickedOutsideSidebar = !sidebar.contains(event.target) && !menuBtn.contains(event.target);
      
      if (isSmallScreen && clickedOutsideSidebar && sidebar.classList.contains('translate-x-0')) {
          sidebar.classList.remove('translate-x-0');
          sidebar.classList.add('-translate-x-full');
      }
  });
  
  // Manejar cambios en el tamaño de la ventana
  window.addEventListener('resize', function() {
      if (window.innerWidth >= 768) {
          sidebar.classList.remove('-translate-x-full');
          sidebar.classList.add('translate-x-0');
      } else {
          sidebar.classList.remove('translate-x-0');
          sidebar.classList.add('-translate-x-full');
      }
  });
  
  // Manejar cambios de sección en el panel lateral
  const menuItems = document.querySelectorAll('#sidebar a');
  menuItems.forEach(item => {
      item.addEventListener('click', function(e) {
          // Eliminar clase activa de todos los elementos
          menuItems.forEach(i => i.classList.remove('bg-gray-100'));
          
          // Agregar clase activa al elemento seleccionado
          this.classList.add('bg-gray-100');
          
          // En pantallas pequeñas, cerrar el sidebar después de seleccionar una opción
          if (window.innerWidth < 768) {
              sidebar.classList.remove('translate-x-0');
              sidebar.classList.add('-translate-x-full');
          }
      });
  });
  
  // Funcionalidad para el formulario de perfil
  const profileForm = document.querySelector('.bg-white form');
  if (profileForm) {
      profileForm.addEventListener('submit', function(e) {
          e.preventDefault();
          
          // Aquí se implementaría la lógica para enviar los datos del formulario
          // Por ejemplo, usando fetch API para enviar los datos al servidor
          
          // Mostrar mensaje de éxito (ejemplo)
          const successMessage = document.createElement('div');
          successMessage.className = 'mt-4 p-3 bg-green-100 text-green-800 rounded-md';
          successMessage.textContent = 'Cambios guardados correctamente';
          
          // Agregar el mensaje al formulario
          this.appendChild(successMessage);
          
          // Eliminar el mensaje después de 3 segundos
          setTimeout(() => {
              successMessage.remove();
          }, 3000);
      });
  }
  
  // Funcionalidad para el formulario de cambio de contraseña
  const passwordForm = document.querySelectorAll('.bg-white form')[1];
  if (passwordForm) {
      passwordForm.addEventListener('submit', function(e) {
          e.preventDefault();
          
          const newPassword = this.querySelector('input[type="password"]:nth-of-type(2)').value;
          const confirmPassword = this.querySelector('input[type="password"]:nth-of-type(3)').value;
          
          // Validar que las contraseñas coincidan
          if (newPassword !== confirmPassword) {
              const errorMessage = document.createElement('div');
              errorMessage.className = 'mt-4 p-3 bg-red-100 text-red-800 rounded-md';
              errorMessage.textContent = 'Las contraseñas no coinciden';
              
              // Agregar el mensaje al formulario
              this.appendChild(errorMessage);
              
              // Eliminar el mensaje después de 3 segundos
              setTimeout(() => {
                  errorMessage.remove();
              }, 3000);
              
              return;
          }
          
          // Aquí se implementaría la lógica para enviar la nueva contraseña al servidor
          
          // Mostrar mensaje de éxito
          const successMessage = document.createElement('div');
          successMessage.className = 'mt-4 p-3 bg-green-100 text-green-800 rounded-md';
          successMessage.textContent = 'Contraseña actualizada correctamente';
          
          // Agregar el mensaje al formulario
          this.appendChild(successMessage);
          
          // Eliminar el mensaje después de 3 segundos
          setTimeout(() => {
              successMessage.remove();
          }, 3000);
          
          // Limpiar los campos del formulario
          this.reset();
      });
  }
});