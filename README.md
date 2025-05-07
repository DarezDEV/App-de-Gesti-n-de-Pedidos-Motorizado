# Gestion de Pedidos Motorizados (MotoRush)🏍️

## Descripción General
Pedidos Motorizados es una aplicación web desarrollada con Flask que facilita la gestión de entregas a domicilio. La plataforma conecta a usuarios, motorizados y administradores en un sistema integrado que permite realizar y gestionar pedidos de manera eficiente.

## Características Principales
- 🛒 Sistema de carrito de compras (pago contra entrega)
- 📍 Seguimiento de entregas en tiempo real con geolocalización
- 🚀 Panel administrativo para gestión de usuarios, productos y pedidos
- 💳 Gestión de pedidos y estados
- 📱 Diseño responsive para todas las plataformas
- 👤 Perfiles diferenciados (Cliente, Motorizado, Administrador)
- 🔔 Sistema de notificaciones
- 🗺️ Integración con mapas para seguimiento de rutas

## Tecnologías Utilizadas

### Frontend
- HTML5, CSS3, JavaScript
- Tailwind para diseño responsive
- Socket.IO para comunicación en tiempo real
- Mapas interactivos para seguimiento

### Backend
- Python con Flask
- MySQL connector
- Socket.IO para WebSockets
- Sistema de autenticación JWT
- API de geolocalización integrada

### Base de Datos
- MySQL

## Instalación y Ejecución Local

1. Clonar el repositorio:
git clone https://github.com/tu-usuario/pedidos-motorizados.git

2. Crear y activar entorno virtual:
python -m venv env
.\env\Scripts\activate

3. Instalar dependencias:
pip install -r requirements.txt

4. Configurar la base de datos:
- Importar el archivo DB_my_proyec.sql
- Configurar las credenciales en el archivo de configuración

5. Ejecutar la aplicación:
python run.py

La aplicación estará disponible en http://localhost:5000

## Estructura del Proyecto
Proyectofinal/
├── app/
│ ├── IA/ # Lógica del sistema de recomendaciones
│ ├── routes/ # Rutas Flask (auth, admin, cliente, motorizado)
│ ├── static/ # Recursos estáticos (CSS, JS, etc)
│ ├── templates/ # Plantillas JINJA HTML
│ ├── models.py # Modelos de datos
│ ├── location_api.py # API para localización en tiempo real
│ ├── db.py, extensions.py # Configuración de base de datos y extensiones
├── run.py # Punto de entrada principal
├── DB_my_proyec.sql # Script de base de datos
├── README.md # Instrucciones del proyecto
├── Documentacion.md
├── requirements.txt

## Módulos Principales

### Módulo de Cliente
- Registro y autenticación
- Catálogo de productos
- Carrito de compras
- Seguimiento de pedidos
- Historial de compras

### Módulo de Motorizado
- Panel de pedidos asignados
- Sistema de geolocalización
- Actualización de estados
- Historial de entregas

### Módulo de Administrador
- Gestión de usuarios
- Gestión de productos
- Monitoreo de pedidos
- Estadísticas y reportes

## Credenciales de Prueba

### Cliente
- Email: cliente@test.com
- Contraseña: cliente123

### Motorizado
- Email: motorizado@test.com
- Contraseña: moto123

### Administrador
- Email: admin@test.com
- Contraseña: admin123

## Licencia
Este proyecto está bajo la Licencia MIT. Ver el archivo [LICENSE] para más detalles.

---
⭐ Si encuentras útil este proyecto, ¡no olvides darle una estrella en GitHub!