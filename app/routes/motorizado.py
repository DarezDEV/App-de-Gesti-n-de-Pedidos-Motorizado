import datetime
from flask import jsonify, render_template, session, redirect, url_for, flash, request
from app.db import get_db_connection
from app import socketio
from app.routes.dashboard import DashboardService

class MotorizadoController:
    def __init__(self):
        self.dashboard_service = DashboardService()

    def check_motorizado_permission(self):
        if 'user_id' not in session:
            flash('Debes iniciar sesión primero', 'error')
            return redirect(url_for('login'))
        if not self.dashboard_service.is_motorizado():
            flash('No tienes permiso para acceder a esta página', 'error')
            return redirect(url_for('login'))

    def motorizado_pedidos(self):
        if self.check_motorizado_permission():
            return self.check_motorizado_permission()
        user_id = session.get('user_id')
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT o.id AS order_id, o.total_amount, o.created_at, o.status, a.address,
                   CONCAT(u.name, ' ', u.last_name) AS client_name
            FROM orders o
            JOIN addresses a ON o.address_id = a.id
            JOIN users u ON o.user_id = u.id
            WHERE o.motorizado_id = %s AND o.status IN ('pendiente', 'en camino', 'entregado')
            ORDER BY o.created_at DESC
        """, (user_id,))

        pedidos = cursor.fetchall()
        for pedido in pedidos:
            pedido['total_amount'] = float(pedido['total_amount'])
            pedido['created_at'] = pedido['created_at'].strftime('%d/%m/%Y')
        cursor.close()
        conn.close()
        return render_template('motorizado/motorizado_orders.html', pedidos=pedidos, user=DashboardService.get_user_info())

    def motorizado_order_details(self, order_id):
        if self.check_motorizado_permission():
            return self.check_motorizado_permission()

        user_id = session.get('user_id')
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("""
            SELECT o.id AS order_id, o.total_amount, o.created_at, o.status,
                   a.address, CONCAT(u.name, ' ', u.last_name) AS client_name,
                   o.motorizado_confirm_delivery, o.client_confirm_delivery
            FROM orders o
            JOIN addresses a ON o.address_id = a.id
            JOIN users u ON o.user_id = u.id
            WHERE o.id = %s AND o.motorizado_id = %s
        """, (order_id, user_id))
        order = cursor.fetchone()

        if not order:
            flash('Pedido no encontrado o no asignado a ti', 'error')
            cursor.close()
            conn.close()
            return redirect(url_for('motorizado_pedidos'))

        order['created_at'] = order['created_at'].strftime('%d/%m/%Y')
        order['total_amount'] = float(order['total_amount'])

        cursor.execute("""
            SELECT oi.product_id, oi.quantity, oi.price, p.name, p.image
            FROM order_items oi
            JOIN products p ON oi.product_id = p.id
            WHERE oi.order_id = %s
        """, (order_id,))
        order['items'] = cursor.fetchall()

        cursor.close()
        conn.close()

        return render_template(
            'motorizado/order_details.html',
            order=order,
            user=DashboardService.get_user_info()
        )

    def marcar_entregado(self, order_id):
        if 'user_id' not in session or session.get('user_role') != 'motorizado':
            return jsonify({'success': False, 'message': 'No tienes permiso para realizar esta acción'}), 403
        user_id = session.get('user_id')
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute(
                "SELECT status, total_amount, created_at, address_id, client_confirm_delivery, user_id AS client_id FROM orders WHERE id = %s AND motorizado_id = %s",
                (order_id, user_id)
            )
            order = cursor.fetchone()
            if not order:
                return jsonify({'success': False, 'message': 'Pedido no encontrado o no asignado a este motorizado'}), 404
            if order['status'] != 'en camino':
                return jsonify({'success': False, 'message': 'El pedido no está en estado "en camino"'}), 400

            cursor.execute("UPDATE orders SET motorizado_confirm_delivery = TRUE, updated_at = NOW() WHERE id = %s", (order_id,))

            cursor.execute("SELECT name, last_name FROM users WHERE id = %s", (user_id,))
            motorizado = cursor.fetchone()
            motorizado_name = f"{motorizado['name']} {motorizado['last_name']}"

            cursor.execute("SELECT name, last_name FROM users WHERE id = %s", (order['client_id'],))
            cliente = cursor.fetchone()
            cliente_name = f"{cliente['name']} {cliente['last_name']}"

            if order['client_confirm_delivery']:
                cursor.execute("UPDATE orders SET status = 'entregado', updated_at = NOW() WHERE id = %s", (order_id,))
                cursor.execute("UPDATE users SET status = 'disponible' WHERE id = %s", (user_id,))
                fully_delivered = True
            else:
                fully_delivered = False

            conn.commit()

            cursor.execute("SELECT address FROM addresses WHERE id = %s", (order['address_id'],))
            address_record = cursor.fetchone()
            address = address_record['address'] if address_record else "Sin dirección"

            cursor.execute("SELECT status FROM orders WHERE id = %s", (order_id,))
            current_status = cursor.fetchone()['status']

            order_details = {
                'order_id': order_id,
                'status': current_status,
                'motorizado_confirmed': True,
                'client_confirmed': order['client_confirm_delivery'],
                'total_amount': float(order['total_amount']),
                'created_at': order['created_at'].strftime('%d/%m/%Y'),
                'address': address,
                'motorizado_name': motorizado_name,
                'cliente_name': cliente_name
            }

            socketio.emit('order_status_update', order_details, namespace='/admin')
            socketio.emit('order_status_update', order_details, namespace='/client')
            socketio.emit('order_delivery_confirmation', order_details, namespace='/motorizado')

            if not fully_delivered:
                socketio.emit('delivery_confirmed_by_motorizado', {
                    'order_id': order_id,
                    'motorizado_name': motorizado_name
                }, namespace='/client', room=f'client_{order["client_id"]}')

                socketio.emit('delivery_confirmed_by_motorizado', {
                    'order_id': order_id,
                    'motorizado_name': motorizado_name,
                    'cliente_name': cliente_name
                }, namespace='/admin')
            else:
                socketio.emit('order_delivered', order_details, namespace='/admin')
                socketio.emit('order_delivered', order_details, namespace='/client', room=f'client_{order["client_id"]}')
                socketio.emit('order_delivered', order_details, namespace='/motorizado', room=f'motorizado_{user_id}')

            return jsonify({
                'success': True,
                'message': 'Has confirmado la entrega del pedido',
                'status': current_status,
                'fully_delivered': fully_delivered
            }), 200
        except Exception as e:
            conn.rollback()
            return jsonify({'success': False, 'message': f'Error al marcar el pedido: {str(e)}'}), 500
        finally:
            cursor.close()
            conn.close()

    def motorizado_map(self, order_id):
        if self.check_motorizado_permission():
            return self.check_motorizado_permission()

        user_id = session.get('user_id')
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("""
            SELECT o.id AS order_id, o.status, a.address,
                   CONCAT(u.name, ' ', u.last_name) AS client_name
            FROM orders o
            JOIN addresses a ON o.address_id = a.id
            JOIN users u ON o.user_id = u.id
            WHERE o.id = %s AND o.motorizado_id = %s AND o.status = 'en camino'
        """, (order_id, user_id))
        order = cursor.fetchone()

        cursor.close()
        conn.close()

        if not order:
            flash('Pedido no encontrado, no asignado a ti, o no está en camino', 'error')
            return redirect(url_for('motorizado_pedidos'))

        return render_template(
            'motorizado/motorizado_map.html',
            order_id=order_id,
            order=order,
            client_name=order['client_name'],
            user=DashboardService.get_user_info()
        )