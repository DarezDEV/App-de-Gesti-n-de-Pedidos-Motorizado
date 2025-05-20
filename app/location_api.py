# location_api.py
# API optimizada para gestionar actualizaciones de ubicación, incluyendo actualizaciones en segundo plano y notificaciones push

from flask import jsonify, request, current_app
from flask_socketio import emit
from datetime import datetime
import json
import logging
import os
from werkzeug.utils import secure_filename
from functools import wraps
from webpush import WebPush, WebPushException
from app.db import get_db_connection

# Configuración del logger con nombre específico para mejor seguimiento
logger = logging.getLogger('location_api')

# Cache LRU con TTL para ubicaciones
class LocationCache:
    def __init__(self, max_size=1000):
        self.cache = {}
        self.max_size = max_size
        self.access_order = []  # Para implementar LRU
    
    def get(self, order_id):
        if order_id in self.cache:
            # Actualizar orden de acceso para LRU
            self.access_order.remove(order_id)
            self.access_order.append(order_id)
            return self.cache[order_id]
        return None
    
    def set(self, order_id, role, location_data):
        # Asegurar que el pedido exista en el cache
        if order_id not in self.cache:
            self.cache[order_id] = {}
            self.access_order.append(order_id)
        
        # Actualizar datos
        self.cache[order_id][role] = location_data
        
        # Aplicar política LRU si se excede el tamaño máximo
        if len(self.access_order) > self.max_size:
            oldest_order = self.access_order.pop(0)
            del self.cache[oldest_order]
    
    def cleanup_old_entries(self, max_age_seconds=24*60*60):
        """Elimina entradas antiguas basadas en timestamp"""
        now = datetime.now().timestamp()
        orders_to_remove = []
        
        for order_id in list(self.cache.keys()):
            roles_to_remove = []
            
            for role, location in self.cache[order_id].items():
                timestamp = location.get('timestamp', 0)
                if now - timestamp > max_age_seconds:
                    roles_to_remove.append(role)
            
            for role in roles_to_remove:
                del self.cache[order_id][role]
            
            if not self.cache[order_id]:
                orders_to_remove.append(order_id)
                self.access_order.remove(order_id)
        
        for order_id in orders_to_remove:
            del self.cache[order_id]
    
    def get_filtered_locations(self, order_id, max_age_seconds=30*60):
        """Obtiene ubicaciones que no sean más antiguas que max_age_seconds"""
        if order_id not in self.cache:
            return {}
        
        locations = {}
        now = datetime.now().timestamp()
        
        for role, location in self.cache[order_id].items():
            timestamp = location.get('timestamp', 0)
            if now - timestamp <= max_age_seconds:
                locations[role] = location
        
        return locations

# Inicializar el cache
location_cache = LocationCache(max_size=5000)

class LocationController:
    def __init__(self):
        self.logger = logging.getLogger('location_api')

    # Decorator para manejo de errores en endpoints
    @staticmethod
    def handle_errors(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            try:
                return f(*args, **kwargs)
            except Exception as e:
                logger.error(f"Error en {f.__name__}: {e}", exc_info=True)
                return jsonify({'error': 'Error interno del servidor'}), 500
        return decorated_function

    # Función para guardar ubicaciones en archivos como respaldo
    def save_location_to_file(self, order_id, data):
        # Asegurarse de que el directorio existe
        location_dir = os.path.join(current_app.config['INSTANCE_PATH'], 'locations')
        os.makedirs(location_dir, exist_ok=True)
        
        # Nombre del archivo basado en el ID del pedido
        filename = secure_filename(f"order_{order_id}_locations.json")
        filepath = os.path.join(location_dir, filename)
        
        # Leer datos existentes si el archivo existe
        existing_data = []
        if os.path.exists(filepath):
            try:
                with open(filepath, 'r') as f:
                    existing_data = json.load(f)
            except (json.JSONDecodeError, IOError) as e:
                self.logger.error(f"Error leyendo archivo de ubicaciones: {e}")
        
        # Añadir nueva ubicación
        existing_data.append({
            'lat': data.get('lat'),
            'lon': data.get('lon'),
            'accuracy': data.get('accuracy'),
            'role': data.get('role'),
            'timestamp': data.get('timestamp', datetime.now().timestamp()),
            'background': data.get('background', False)
        })
        
        # Limitar el número de entradas (mantener solo las últimas 1000)
        if len(existing_data) > 1000:
            existing_data = existing_data[-1000:]
        
        # Guardar datos actualizados
        try:
            with open(filepath, 'w') as f:
                json.dump(existing_data, f)
        except IOError as e:
            self.logger.error(f"Error guardando archivo de ubicaciones: {e}")

    # Función para actualizar la ubicación en la base de datos
    def update_location_in_db(self, order_id, role, lat, lon):
        try:
            with get_db_connection() as conn:
                with conn.cursor() as cursor:
                    if role == 'cliente':
                        cursor.execute(
                            "UPDATE orders SET client_latitude = %s, client_longitude = %s, updated_at = NOW() WHERE id = %s",
                            (lat, lon, order_id)
                        )
                    elif role == 'motorizado':
                        cursor.execute(
                            "UPDATE orders SET motorizado_latitude = %s, motorizado_longitude = %s, updated_at = NOW() WHERE id = %s",
                            (lat, lon, order_id)
                        )
                    conn.commit()
            return True
        except Exception as e:
            self.logger.error(f"Error al actualizar ubicación en la BD: {e}", exc_info=True)
            return False

    # Función para emitir actualización de ubicación por Socket.IO
    def emit_location_update(self, order_id, location_data):
        try:
            if hasattr(current_app, 'socketio'):
                current_app.socketio.emit('location_updated', {
                    'order_id': order_id,
                    'lat': location_data['lat'],
                    'lon': location_data['lon'],
                    'accuracy': location_data.get('accuracy'),
                    'role': location_data['role'],
                    'background': location_data.get('background', False),
                    'timestamp': location_data.get('timestamp')
                }, namespace='/gps')
                self.logger.debug(f"Ubicación emitida por Socket.IO: {order_id}, {location_data['role']}")
            return True
        except Exception as e:
            self.logger.error(f"Error al emitir evento Socket.IO: {e}", exc_info=True)
            return False

    # Endpoint para suscribirse a notificaciones push
    @handle_errors
    def subscribe_push(self):
        data = request.json
        if not data or 'subscription' not in data or 'user_id' not in data or 'role' not in data:
            return jsonify({'error': 'Datos incompletos'}), 400

        subscription = data['subscription']
        user_id = data['user_id']
        role = data['role']

        # Almacenar en la base de datos
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO push_subscriptions (user_id, role, endpoint, p256dh, auth, created_at, updated_at)
                    VALUES (%s, %s, %s, %s, %s, NOW(), NOW())
                    ON DUPLICATE KEY UPDATE
                        endpoint = %s, p256dh = %s, auth = %s, role = %s, updated_at = NOW()
                    """,
                    (
                        user_id,
                        role,
                        subscription['endpoint'],
                        subscription['keys']['p256dh'],
                        subscription['keys']['auth'],
                        subscription['endpoint'],
                        subscription['keys']['p256dh'],
                        subscription['keys']['auth'],
                        role
                    )
                )
                conn.commit()
        
        return jsonify({'success': True}), 200

    # Endpoint para actualizar ubicación (usado por el Service Worker)
    @handle_errors
    def update_location(self):
        data = request.json
        
        if not data or 'order_id' not in data or 'lat' not in data or 'lon' not in data or 'role' not in data:
            return jsonify({'error': 'Datos incompletos'}), 400
        
        order_id = data['order_id']
        role = data['role']
        lat = float(data['lat'])  # Convertir a float para garantizar consistencia
        lon = float(data['lon'])
        timestamp = data.get('timestamp', datetime.now().timestamp())
        
        # Validación básica de coordenadas
        if not (-90 <= lat <= 90) or not (-180 <= lon <= 180):
            return jsonify({'error': 'Coordenadas inválidas'}), 400
        
        # Crear datos de ubicación
        location_data = {
            'lat': lat,
            'lon': lon,
            'accuracy': data.get('accuracy'),
            'timestamp': timestamp,
            'background': data.get('background', False),
            'role': role
        }
        
        # Actualizar el cache
        location_cache.set(order_id, role, location_data)
        
        # Guardar en archivo como respaldo
        self.save_location_to_file(order_id, data)
        
        # Actualizar la base de datos
        self.update_location_in_db(order_id, role, lat, lon)
        
        # Emitir evento a través de Socket.IO
        self.emit_location_update(order_id, location_data)
        
        return jsonify({'success': True}), 200

    # Endpoint para obtener las últimas ubicaciones conocidas
    @handle_errors
    def get_locations(self, order_id):
        # Obtener ubicaciones filtradas (elimina automáticamente las antiguas)
        locations = location_cache.get_filtered_locations(order_id)
        
        if not locations:
            return jsonify({'error': 'No hay ubicaciones recientes para este pedido'}), 404
        
        return jsonify(locations), 200

    # Endpoint para datos del dashboard
    @handle_errors
    def get_dashboard_data(self):
        try:
            with get_db_connection() as conn:
                with conn.cursor(dictionary=True) as cursor:
                    # Obtener ventas semanales
                    cursor.execute("""
                        SELECT 
                            WEEK(created_at) as week_number,
                            YEAR(created_at) as year,
                            SUM(total_amount) as weekly_revenue
                        FROM orders
                        WHERE status = 'completed'
                        AND created_at >= DATE_SUB(NOW(), INTERVAL 8 WEEK)
                        GROUP BY WEEK(created_at), YEAR(created_at)
                        ORDER BY year DESC, week_number DESC
                        LIMIT 8
                    """)
                    weekly_sales = cursor.fetchall()
                    
                    # Obtener productos más vendidos
                    cursor.execute("""
                        SELECT 
                            p.name,
                            SUM(oi.quantity) as total_sold
                        FROM order_items oi
                        JOIN products p ON oi.product_id = p.id
                        JOIN orders o ON oi.order_id = o.id
                        WHERE o.status = 'completed'
                        AND o.created_at >= DATE_SUB(NOW(), INTERVAL 30 DAY)
                        GROUP BY p.id
                        ORDER BY total_sold DESC
                        LIMIT 5
                    """)
                    top_products = cursor.fetchall()
                    
                    # Obtener estadísticas generales
                    cursor.execute("""
                        SELECT
                            (SELECT COUNT(*) FROM orders WHERE status = 'completed') as total_sales,
                            (SELECT SUM(total_amount) FROM orders WHERE status = 'completed') as total_revenue,
                            (SELECT COUNT(*) FROM orders WHERE status = 'pending') as pending_orders,
                            (SELECT COUNT(*) FROM users WHERE last_login >= DATE_SUB(NOW(), INTERVAL 7 DAY)) as active_users
                    """)
                    stats = cursor.fetchone()
            
            # Preparar respuesta
            data = {
                'weekly_sales': weekly_sales or [],
                'top_products': top_products or [],
                'total_sales': stats['total_sales'] if stats else 0,
                'total_revenue': float(stats['total_revenue']) if stats and stats['total_revenue'] else 0,
                'pending_orders': stats['pending_orders'] if stats else 0,
                'active_users': stats['active_users'] if stats else 0
            }
            
            return jsonify(data)
        
        except Exception as e:
            self.logger.error(f"Error al obtener datos del dashboard: {e}", exc_info=True)
            # Fallback a datos de ejemplo si hay error
            data = {
                'weekly_sales': [{'week_number': 1, 'year': 2023, 'weekly_revenue': 1000}],
                'top_products': [{'name': 'Producto A', 'total_sold': 50}],
                'total_sales': 100,
                'total_revenue': 5000,
                'pending_orders': 10,
                'active_users': 20,
                'error': 'Datos parciales disponibles debido a un error'
            }
            return jsonify(data)

    # Socket.IO event handler para solicitar ubicaciones iniciales
    def handle_get_initial_locations(self, data=None):
        if not data or 'order_id' not in data:
            return
        
        order_id = data['order_id']
        
        # Verificar si hay datos en caché y si son válidos
        locations = location_cache.get_filtered_locations(order_id)
        
        # Si no hay datos en la caché, intenta obtenerlos de la base de datos
        if not locations:
            try:
                with get_db_connection() as conn:
                    with conn.cursor(dictionary=True) as cursor:
                        cursor.execute(
                            """
                            SELECT 
                                id, client_latitude, client_longitude, 
                                motorizado_latitude, motorizado_longitude,
                                UNIX_TIMESTAMP(updated_at) as last_update
                            FROM orders WHERE id = %s
                            """,
                            (order_id,)
                        )
                        order = cursor.fetchone()
                
                if order and order['id']:
                    now = datetime.now().timestamp()
                    
                    if order['client_latitude'] and order['client_longitude']:
                        location_cache.set(order_id, 'cliente', {
                            'lat': float(order['client_latitude']),
                            'lon': float(order['client_longitude']),
                            'timestamp': order['last_update'] or now,
                            'accuracy': None,
                            'background': False
                        })
                    
                    if order['motorizado_latitude'] and order['motorizado_longitude']:
                        location_cache.set(order_id, 'motorizado', {
                            'lat': float(order['motorizado_latitude']),
                            'lon': float(order['motorizado_longitude']),
                            'timestamp': order['last_update'] or now,
                            'accuracy': None,
                            'background': False
                        })
                    
                    # Obtener ubicaciones actualizadas
                    locations = location_cache.get_filtered_locations(order_id)
            except Exception as e:
                self.logger.error(f"Error al cargar ubicaciones desde la BD: {e}", exc_info=True)
        
        # Emitir las ubicaciones disponibles
        if locations:
            for role, location in locations.items():
                emit('location_updated', {
                    'order_id': order_id,
                    'lat': location['lat'],
                    'lon': location['lon'],
                    'accuracy': location.get('accuracy'),
                    'role': role,
                    'background': location.get('background', False),
                    'timestamp': location.get('timestamp')
                }, namespace='/gps')
        else:
            # Informar que no hay ubicaciones disponibles
            emit('no_locations_available', {'order_id': order_id}, namespace='/gps')

    # Función para registrar los eventos Socket.IO
    def register_socketio_events(self, socketio):
        @socketio.on('get_initial_locations', namespace='/gps')
        def on_get_initial_locations(data):
            self.handle_get_initial_locations(data)
        
        @socketio.on('update_location', namespace='/gps')
        def on_update_location(data):
            if not data or 'order_id' not in data or 'lat' not in data or 'lon' not in data or 'role' not in data:
                return
            
            try:
                order_id = data['order_id']
                role = data['role']
                lat = float(data['lat'])
                lon = float(data['lon'])
                timestamp = data.get('timestamp', datetime.now().timestamp())
                
                # Validación básica de coordenadas
                if not (-90 <= lat <= 90) or not (-180 <= lon <= 180):
                    self.logger.warning(f"Coordenadas inválidas recibidas: {lat}, {lon}")
                    return
                
                # Crear objeto de ubicación
                location_data = {
                    'lat': lat,
                    'lon': lon,
                    'accuracy': data.get('accuracy'),
                    'timestamp': timestamp,
                    'background': False,  # Este viene directamente del socket, no del background
                    'role': role
                }
                
                # Actualizar la ubicación en el cache
                location_cache.set(order_id, role, location_data)
                
                # Guardar en archivo como respaldo
                self.save_location_to_file(order_id, data)
                
                # Actualizar base de datos
                self.update_location_in_db(order_id, role, lat, lon)
                
                # Reenviar a todos los clientes conectados
                emit('location_updated', {
                    'order_id': order_id,
                    'lat': lat,
                    'lon': lon,
                    'accuracy': data.get('accuracy'),
                    'role': role,
                    'background': False,
                    'timestamp': timestamp
                }, broadcast=True, namespace='/gps')
            
            except Exception as e:
                self.logger.error(f"Error en Socket.IO update_location: {e}", exc_info=True)

    # Función para iniciar tareas periódicas
    def start_background_tasks(self):
        import threading
        import time
        
        def cleanup_task():
            while True:
                try:
                    self.logger.debug("Ejecutando limpieza de ubicaciones antiguas")
                    location_cache.cleanup_old_entries()
                    time.sleep(3600)  # 1 hora
                except Exception as e:
                    self.logger.error(f"Error en tarea de limpieza: {e}", exc_info=True)
                    time.sleep(300)  # En caso de error, esperar 5 minutos antes de reintentar
        
        # Iniciar hilo de limpieza
        cleanup_thread = threading.Thread(target=cleanup_task, daemon=True)
        cleanup_thread.start()
        self.logger.info("Tareas en segundo plano iniciadas")

    def init_app(self, app, socketio):
        # Registrar rutas
        app.add_url_rule('/api/subscribe-push', view_func=self.subscribe_push, methods=['POST'])
        app.add_url_rule('/api/update-location', view_func=self.update_location, methods=['POST'])
        app.add_url_rule('/api/get-locations/<order_id>', view_func=self.get_locations, methods=['GET'])
        app.add_url_rule('/admin/dashboard-data', view_func=self.get_dashboard_data, methods=['GET'])
        
        # Iniciar tareas en segundo plano
        if app.config.get('ENABLE_BACKGROUND_TASKS', True):
            self.start_background_tasks()
        
        # Configurar nivel de logging basado en modo de ejecución
        if app.debug:
            self.logger.setLevel(logging.DEBUG)
        else:
            self.logger.setLevel(logging.INFO)
        
        # Registrar eventos SocketIO
        self.register_socketio_events(socketio)
        
        self.logger.info("Módulo location_api inicializado")