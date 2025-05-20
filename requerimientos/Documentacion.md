# 📦 Documentación del Proyecto: Sistema de Pedidos Motorizados (MotoRush)

## 📋 Resumen del Proyecto
Este proyecto es una aplicación web desarrollada con Python (Flask) que permite gestionar pedidos y entregas mediante motorizados. Proporciona interfaces diferenciadas para clientes, motorizados y administradores, incluyendo funcionalidades como geolocalización en tiempo real, recomendaciones inteligentes y notificaciones en vivo.

## 🎯 Objetivos del Proyecto
- Facilitar el proceso de pedidos y entregas para pequeños negocios como restaurabtes y colmados.
- Ofrecer una experiencia eficiente tanto para clientes como para repartidores.
- Optimizar la asignación y seguimiento de pedidos con herramientas modernas como mapas y notificaciones.

## 🚀 Diario de Desarrollo
### Semana 1: Fundamentos y Base de Datos
- Diseño de la base de datos en MySQL.
- Creación de tablas: usuarios, productos, categorías, pedidos.
- Configuración base del entorno Flask.

### Semana 2: Sistema de Autenticación
- Módulo `auth.py`: login y registro de usuarios.
- Redirección según tipo de usuario.

### Semana 3: Panel de Administración
- CRUD de usuarios (`admin.py`).
- Gestión de productos y categorías.
- Vistas HTML administrativas (`adminUsers.html`, `adminCategory.html`, `adminProducts.html`).

### Semana 4: Interfaz del Cliente
- Catálogo de productos.
- Carrito de compras funcional.
- Detalles de productos y pedidos anteriores.

### Semana 5: Sistema de Pedidos y Gestión Administrativa
- Implementación del sistema para que el cliente pueda realizar pedidos desde el catálogo.
- Envío automático de pedidos al panel del administrador para su revisión y gestión.
- Visualización de pedidos entrantes por parte del administrador.
- Almacenamiento de los pedidos en la base de datos con estado inicial «Pendiente».

### Semana 6: Gestión de Motorizados y Asignación de Pedidos
- Diseño de la interfaz del panel del motorizado.
- Funcionalidad para que el administrador pueda asignar un pedido a un motorizado disponible.
- Visualización de pedidos asignados en el panel del motorizado.
- Confirmación de recepción del pedido por parte del motorizado.

### Semana 7: Seguimiento y Confirmación de Pedidos
- Todos los usuarios (cliente, motorizado y administrador) pueden acceder a los detalles del pedido.
- Visualización del estado actualizado del pedido en tiempo real.
- El motorizado tiene la opción de marcar el pedido como «Entregado» una vez completada la entrega.
- Actualización automática del estado en la base de datos y en todas interfaz.

### Semana 8: Sistema de Recomendación Inteligente para Clientes
- Implementación del sistema de recomendaciones basado en IA.
- Módulo de recomendaciones (`recommendation_service.py`).
- Para usuarios nuevos sin historial, se muestran productos populares entre otros clientes.
- Para usuarios con historial, se recomiendan productos similares a los que ha comprado o visualizado.
- Integración del sistema de recomendación con el catálogo del cliente.

### Semana 9: Notificaciones en Tiempo Real
- Integración de Socket.IO en el sistema.
- Implementación de notificaciones push para todos los usuarios.
- Los clientes reciben alertas cuando su pedido cambia de estado.
- Los motorizados y administradores reciben notificaciones sobre nuevos pedidos o asignaciones.

### Semana 10: Seguimiento en Tiempo Real con Geolocalización
- Implementación de mapas interactivos con geolocalización.
- Uso de mapas interactivos (Leaflet.js).
- Cuando el administrador asigna un motorizado, el cliente puede ver en tiempo real su ubicación mientras se dirige al destino.
- El motorizado también puede visualizar la ubicación del cliente para facilitar la entrega.
- Mejora en la experiencia del usuario mediante seguimiento en vivo.

### Semana 11: Diseño Responsive con Tailwind CSS
- Aplicación de un diseño completamente adaptable a todos los dispositivos (móviles, tabletas y escritorios).
- Uso de Tailwind CSS para crear una interfaz moderna y responsiva.
- Mejora en la experiencia de usuario con layouts flexibles y componentes reutilizables.
- Pruebas de compatibilidad en diferentes resoluciones de pantalla.

### Semana 12: Optimización y Mejoras en la Experiencia de Usuario
- Sustitución de alertas nativas de JavaScript por **SweetAlert** para una presentación más moderna e intuitiva.
- Optimización del rendimiento general de la aplicación.
- Reducción de tiempos de carga mediante compresión de imágenes y limpieza de código.
- Mejora de la navegación y retroalimentación visual para el usuario.

## 🛠️ Estructura del Proyecto
Proyectofinal/
├── app/
│ ├── IA/ # Lógica del sistema de recomendaciones
│ ├── routes/ # Rutas Flask (auth, admin, cliente, motorizado)
│ ├── static/ # Recursos estáticos (CSS, imágenes)
│ ├── templates/ # Plantillas HTML
│ ├── models.py # Modelos de datos SQLAlchemy
│ ├── location_api.py # API para localización en tiempo real
│ ├── db.py, extensions.py # Configuración de base de datos y extensiones
├── run.py # Punto de entrada principal
├── DB_my_proyec.sql # Script de base de datos
├── README.md # Instrucciones del proyecto
├── Documentacion.md
├── requirements.txt
 
## 💻 Tecnologías Implementadas
- **Backend:** Python, Flask, MySql Connector
- **Frontend:** HTML5, CSS3, Tailwind CSS, JavaScript
- **Base de Datos:** MySQL
- **Mapas:** Leaflet.js (API de geolocalización)
- **IA:** Sistema de recomendaciones basado en similitud de productos
- **Tiempo real:** Socket.IO

## 🏆 Logros Destacados
- Plataforma funcional con gestión de pedidos.
- Seguimiento en tiempo real mediante mapas interactivos.
- Sistema de recomendaciones basado en IA.
- Interfaz adaptada a dispositivos móviles.
- Notificaciones en tiempo real con WebSockets.

## 🔮 Trabajo Futuro
- Integrar pasarelas de pago (ej: Stripe, Apple Pay).
- Mejorar la interfaz del cliente con filtros y búsqueda avanzada.