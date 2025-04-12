# app/routes/maps.py
import datetime
from flask import render_template, session, redirect, url_for, flash, request, jsonify
from app.db import get_db_connection
from app.routes.dashboard import DashboardService
from app import socketio

class MapsController:
    @staticmethod
    def cliente_mapa(order_id):
        """Vista del mapa para el cliente que muestra la ubicación del motorizado y la ruta"""
        if 'user_id' not in session or session.get('user_role') != 'cliente':
            flash('No tienes permiso para acceder a esta página', 'error')
            return redirect(url_for('login'))
        
        user_id = session.get('user_id')
        
        # Verificar que el pedido pertenece al cliente
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT o.id, o.status, o.motorizado_id, a.address,
                   m.name as motorizado_name, m.last_name as motorizado_lastname
            FROM orders o
            JOIN addresses a ON o.address_id = a.id
            LEFT JOIN users m ON o.motorizado_id = m.id
            WHERE o.id = %s AND o.user_id = %s
        """, (order_id, user_id))
        
        order = cursor.fetchone()
        cursor.close()
        conn.close()
        
        if not order:
            flash('Pedido no encontrado o no pertenece a este usuario', 'error')
            return redirect(url_for('client_orders'))
        
        if order['status'] not in ['en camino']:
            flash('El seguimiento en mapa solo está disponible para pedidos en camino', 'info')
            return redirect(url_for('order_details_client', order_id=order_id))
        
        motorizado_name = f"{order['motorizado_name']} {order['motorizado_lastname']}" if order['motorizado_id'] else "No asignado"
        
        return render_template(
            'client/client_map.html',
            user=DashboardService.get_user_info(),
            order_id=order_id,
            order=order,
            motorizado_name=motorizado_name
        )
    
    @staticmethod
    def motorizado_mapa(order_id):
        """Vista del mapa para el motorizado que muestra la ruta hacia el cliente"""
        if 'user_id' not in session or session.get('user_role') != 'motorizado':
            flash('No tienes permiso para acceder a esta página', 'error')
            return redirect(url_for('login'))
        
        user_id = session.get('user_id')
        
        # Verificar que el pedido está asignado al motorizado
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT o.id, o.status, o.user_id, a.address,
                   u.name as client_name, u.last_name as client_lastname
            FROM orders o
            JOIN addresses a ON o.address_id = a.id
            JOIN users u ON o.user_id = u.id
            WHERE o.id = %s AND o.motorizado_id = %s
        """, (order_id, user_id))
        
        order = cursor.fetchone()
        cursor.close()
        conn.close()
        
        if not order:
            flash('Pedido no encontrado o no asignado a este motorizado', 'error')
            return redirect(url_for('motorizado_pedidos'))
        
        if order['status'] not in ['pendiente', 'en camino']:
            flash('La navegación en mapa solo está disponible para pedidos pendientes o en camino', 'info')
            return redirect(url_for('motorizado_order_details', order_id=order_id))
        
        client_name = f"{order['client_name']} {order['client_lastname']}"
        
        return render_template(
            'motorizado/motorizado_map.html',
            user=DashboardService.get_user_info(),
            order_id=order_id,
            order=order,
            client_name=client_name
        )
    
    @staticmethod
    def actualizar_ubicacion():
        """Endpoint para actualizar la ubicación del motorizado o cliente"""
        if 'user_id' not in session:
            return jsonify({'success': False, 'message': 'No autenticado'}), 401
        
        try:
            data = request.get_json()
            user_id = session.get('user_id')
            order_id = data.get('order_id')
            latitude = data.get('latitude')
            longitude = data.get('longitude')
            user_type = session.get('user_role')
            
            if not all([order_id, latitude, longitude]):
                return jsonify({'success': False, 'message': 'Datos incompletos'}), 400
            
            # Verificar permisos según el tipo de usuario
            conn = get_db_connection()
            cursor = conn.cursor(dictionary=True)
            
            if user_type == 'motorizado':
                cursor.execute(
                    "SELECT id FROM orders WHERE id = %s AND motorizado_id = %s",
                    (order_id, user_id)
                )
            elif user_type == 'cliente':
                cursor.execute(
                    "SELECT id FROM orders WHERE id = %s AND user_id = %s",
                    (order_id, user_id)
                )
            else:
                cursor.close()
                conn.close()
                return jsonify({'success': False, 'message': 'Rol no autorizado'}), 403
            
            if not cursor.fetchone():
                cursor.close()
                conn.close()
                return jsonify({'success': False, 'message': 'Pedido no encontrado o no autorizado'}), 404
            
            # Enviar actualización a través de SocketIO
            location_data = {
                'order_id': order_id,
                'user_type': user_type,
                'latitude': latitude,
                'longitude': longitude,
                'user_id': user_id,
                'timestamp': str(datetime.datetime.now())
            }
            
            # Emitir el evento a las salas correspondientes
            socketio.emit(f'location_update_{order_id}', location_data)
            
            cursor.close()
            conn.close()
            return jsonify({'success': True, 'message': 'Ubicación actualizada'}), 200
            
        except Exception as e:
            return jsonify({'success': False, 'message': str(e)}), 500
    
    @staticmethod
    def iniciar_entrega(order_id):
        """Marcar un pedido como 'en camino' e iniciar el seguimiento"""
        if 'user_id' not in session or session.get('user_role') != 'motorizado':
            return jsonify({'success': False, 'message': 'No autorizado'}), 403
        
        user_id = session.get('user_id')
        
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        try:
            cursor.execute(
                "SELECT status FROM orders WHERE id = %s AND motorizado_id = %s", 
                (order_id, user_id)
            )
            order = cursor.fetchone()
            
            if not order:
                return jsonify({'success': False, 'message': 'Pedido no encontrado o no asignado a este motorizado'}), 404
            
            if order['status'] != 'pendiente':
                return jsonify({'success': False, 'message': f'El pedido no puede ser iniciado porque su estado es {order["status"]}'}), 400
            
            cursor.execute(
                "UPDATE orders SET status = 'en camino', updated_at = NOW() WHERE id = %s",
                (order_id,)
            )
            conn.commit()
            
            # Notificar al cliente y admin que el pedido está en camino
            socketio.emit('order_status_update', {
                'order_id': order_id,
                'status': 'en camino',
                'message': 'El motorizado ha iniciado la entrega'
            }, namespace='/client')
            
            socketio.emit('order_status_update', {
                'order_id': order_id,
                'status': 'en camino',
                'message': 'El motorizado ha iniciado la entrega'
            }, namespace='/admin')
            
            return jsonify({'success': True, 'message': 'Entrega iniciada correctamente'}), 200
            
        except Exception as e:
            conn.rollback()
            return jsonify({'success': False, 'message': str(e)}), 500
        finally:
            cursor.close()
            conn.close()