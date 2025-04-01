# app/routes/client.py
from flask import jsonify, render_template, session, redirect, url_for, flash, request
from app.db import get_db_connection
from app.routes.dashboard import DashboardService
from app.routes.service import CartService, AddressService, OrderService
from app.IA.recommendation_service import RecommendationAIService
from app import socketio
from datetime import datetime

class ClientController:
    @staticmethod
    def cliente_dashboard():
        if 'user_id' not in session:
            flash('Debes iniciar sesión primero', 'error')
            return redirect(url_for('login'))
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM products WHERE estado = 1 ORDER BY RAND()")
        products = cursor.fetchall()
        user_id = session.get('user_id')
        cart_items = CartService.get_cart_items(user_id)
        cart_count = sum(item['quantity'] for item in cart_items)
        rec_service = RecommendationAIService()
        recommended_products = rec_service.get_recommendations_for_user(user_id)
        cursor.close()
        conn.close()
        return render_template(
            'client/client.html', 
            user=DashboardService.get_user_info(), 
            products=products, 
            cart_count=cart_count,
            recommended_products=recommended_products
        )
    
    @staticmethod
    def cart_client():
        if 'user_id' not in session:
            flash('Debes iniciar sesión primero', 'error')
            return redirect(url_for('login'))
        user_id = session.get('user_id')
        cart_items = CartService.get_cart_items(user_id)
        cart_total = CartService.get_cart_total(user_id)
        rec_service = RecommendationAIService()
        recommended_products = rec_service.get_recommendations_for_user(user_id)
        return render_template(
            'client/cart.html', 
            user=DashboardService.get_user_info(), 
            cart_items=cart_items, 
            cart_total=cart_total,
            recommended_products=recommended_products
        )
    
    @staticmethod
    def product_detail(product_id):
        if 'user_id' not in session:
            flash('Debes iniciar sesión primero', 'error')
            return redirect(url_for('login'))
        user_id = session.get('user_id')
        RecommendationAIService.track_product_view(user_id, product_id)
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT p.*, c.name as category_name
            FROM products p
            LEFT JOIN categories c ON p.category_id = c.id
            WHERE p.id = %s
        """, (product_id,))
        product = cursor.fetchone()
        if not product:
            flash('Producto no encontrado', 'error')
            return redirect(url_for('cliente_dashboard'))
        rec_service = RecommendationAIService()
        recommended_products = rec_service.get_recommendations_for_user(user_id)
        cart_items = CartService.get_cart_items(user_id)
        cart_count = sum(item['quantity'] for item in cart_items)
        cursor.close()
        conn.close()
        return render_template(
            'client/product_detail.html',
            product=product,
            user=DashboardService.get_user_info(),
            recommended_products=recommended_products,
            cart_count=cart_count
        )
    
    @staticmethod
    def client_orders():
        if 'user_id' not in session:
            flash('Debes iniciar sesión primero', 'error')
            return redirect(url_for('login'))
        user_id = session.get('user_id')
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT o.id AS order_id, o.total_amount, o.created_at, o.status, 
                u.name AS client_name, u.last_name AS client_last_name, a.address,
                m.name AS motorizado_name, m.last_name AS motorizado_last_name
            FROM orders o
            JOIN users u ON o.user_id = u.id
            JOIN addresses a ON o.address_id = a.id
            LEFT JOIN users m ON o.motorizado_id = m.id AND m.rol = 'motorizado'
            WHERE o.user_id = %s AND o.status != 'cancelado'
            ORDER BY o.created_at DESC
        """, (user_id,))
        orders = cursor.fetchall()
        for order in orders:
            if isinstance(order['created_at'], str):
                order['created_at'] = datetime.strptime(order['created_at'], '%Y-%m-%d %H:%M:%S')
            order['total_amount'] = float(order['total_amount'])
        cursor.close()
        conn.close()
        return render_template(
            'client/client_orders.html', 
            user=DashboardService.get_user_info(), 
            orders=orders
        )

class CartController:
    @staticmethod
    def add_to_cart():
        try:
            data = request.get_json()
            product_id = data.get('product_id')
            quantity = int(data.get('quantity', 1))
            if not product_id or quantity <= 0:
                return jsonify({'success': False, 'error': 'Datos inválidos'}), 400
            success = CartService.add_to_cart(session['user_id'], product_id, quantity)
            if success:
                user_id = session.get('user_id')
                cart_items = CartService.get_cart_items(user_id)
                cart_count = sum(item['quantity'] for item in cart_items)
                return jsonify({
                    'success': True,
                    'cart_count': cart_count,
                    'message': f'Se agregaron {quantity} unidades al carrito'
                })
            return jsonify({'success': False, 'error': 'No se pudo agregar el producto'}), 500
        except Exception as e:
            print(f"Error en add_to_cart: {str(e)}")
            return jsonify({'success': False, 'error': str(e)}), 500

    @staticmethod
    def update_cart():
        cart_id = request.form.get('cart_id')
        quantity = int(request.form.get('quantity', 1))
        success = CartService.update_cart_item(cart_id, quantity)
        if success:
            user_id = session.get('user_id')
            cart_items = CartService.get_cart_items(user_id)
            cart_total = CartService.get_cart_total(user_id)
            html = render_template('client/cart.html', cart_items=cart_items, cart_total=cart_total)
            return jsonify({'success': True, 'html': html, 'cart_total': cart_total})
        return jsonify({'success': False, 'error': 'No se pudo actualizar el carrito'}), 400

    @staticmethod
    def remove_from_cart():
        try:
            data = request.get_json()
            cart_id = data.get('cart_id')
            if not cart_id:
                return jsonify({"success": False, "error": "cart_id no proporcionado"}), 400
            success = CartService.remove_from_cart(cart_id)
            if success:
                return jsonify({"success": True}), 200
            else:
                return jsonify({"success": False, "error": "No se pudo eliminar"}), 500
        except Exception as e:
            print(f"Error: {str(e)}")
            return jsonify({"success": False, "error": str(e)}), 500

    @staticmethod
    def checkout():
        if 'user_id' not in session:
            flash('Debes iniciar sesión primero', 'error')
            return redirect(url_for('login'))
        if request.method == 'POST':
            address_id = request.form.get('address_id')
            new_address = request.form.get('new_address')
            payment_amount = request.form.get('payment_amount')
            if not address_id and not new_address:
                flash('Por favor, selecciona o agrega una dirección de entrega', 'error')
                return redirect(url_for('cart_client'))
            if not payment_amount or float(payment_amount) <= 0:
                flash('Por favor, ingresa un monto de pago válido', 'error')
                return redirect(url_for('cart_client'))
            user_id = session.get('user_id')
            cart_items = CartService.get_cart_items(user_id)
            cart_total = CartService.get_cart_total(user_id)
            if new_address:
                address_id = AddressService.add_address(user_id, new_address)
            order_id = OrderService.create_order(
                user_id=user_id,
                address_id=address_id,
                total_amount=cart_total,
                payment_amount=float(payment_amount),
                payment_method='efectivo'
            )
            for item in cart_items:
                OrderService.add_order_item(
                    order_id=order_id,
                    product_id=item['product_id'],
                    quantity=item['quantity'],
                    price=item['price']
                )
            CartService.clear_cart(user_id)
            conn = get_db_connection()
            cursor = conn.cursor(dictionary=True)
            cursor.execute("SELECT name, last_name FROM users WHERE id = %s", (user_id,))
            user = cursor.fetchone()
            client_name = f"{user['name']} {user['last_name']}" if user else "Cliente Desconocido"
            cursor.close()
            conn.close()
            order_details = {
                'order_id': order_id,
                'client_name': client_name,
                'total_amount': float(cart_total),
                'created_at': datetime.now().strftime('%d/%m/%Y'),
                'address': AddressService.get_user_addresses(user_id)[0]['address'],
                'status': 'pendiente'
            }
            socketio.emit('new_order', order_details, namespace='/admin')
            flash('¡Pedido realizado con éxito!', 'success')
            return redirect(url_for('order_confirmation', order_id=order_id))
        user_id = session.get('user_id')
        cart_items = CartService.get_cart_items(user_id)
        cart_total = CartService.get_cart_total(user_id)
        addresses = AddressService.get_user_addresses(user_id)
        return render_template(
            'client/cart.html',
            cart_items=cart_items,
            cart_total=cart_total,
            addresses=addresses,
            checkout_mode=True
        )

    @staticmethod
    def cancel_order():
        order_id = request.form.get('order_id')
        if not order_id:
            flash('ID de pedido no proporcionado', 'error')
            return redirect(url_for('cliente_dashboard'))
        success = OrderService.cancel_order(order_id)
        if success:
            flash('Pedido cancelado con éxito', 'success')
        else:
            flash('No se pudo cancelar el pedido', 'error')
        return redirect(url_for('cart_client'))

    @staticmethod
    def order_confirmation(order_id):
        if 'user_id' not in session:
            flash('Debes iniciar sesión primero', 'error')
            return redirect(url_for('login'))
        user_id = session.get('user_id')
        order = OrderService.get_order(order_id, user_id)
        if not order:
            flash('Pedido no encontrado', 'error')
            return redirect(url_for('cliente_dashboard'))
        if order.get('status') == 'cancelado':
            flash('Este pedido ha sido cancelado', 'error')
            return redirect(url_for('cliente_dashboard'))
        return render_template('client/order_confirmation.html', order=order)

    @staticmethod
    def get_cart_count():
        user_id = session.get('user_id')
        cart_items = CartService.get_cart_items(user_id)
        cart_count = sum(item['quantity'] for item in cart_items)
        return jsonify({'cart_count': cart_count})
    
    @staticmethod
    def get_recommendations_ajax():
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({'success': False, 'error': 'Usuario no autenticado'}), 401
        recommendations = RecommendationAIService.get_recommendations_for_user(user_id)
        for product in recommendations:
            if 'price' in product:
                product['price'] = float(product['price'])
        return jsonify({'success': True, 'recommendations': recommendations})
    
    @staticmethod
    def track_view():
        if 'user_id' not in session:
            return jsonify({'success': False, 'error': 'Usuario no autenticado'}), 401
        try:
            data = request.get_json()
            product_id = data.get('product_id')
            user_id = session.get('user_id')
            if not product_id:
                return jsonify({'success': False, 'error': 'ID de producto requerido'}), 400
            success = RecommendationAIService.track_product_view(user_id, product_id)
            return jsonify({'success': success})
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500