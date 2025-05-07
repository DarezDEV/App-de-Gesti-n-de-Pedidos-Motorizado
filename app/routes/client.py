# app/routes/client.py
from unicodedata import category
from flask import jsonify, render_template, session, redirect, url_for, flash, request
from app.db import get_db_connection
from app.routes.dashboard import DashboardService
from app.routes.service import CartService, AddressService, OrderService
from app.IA.recommendation_service import RecommendationAIService
from app import socketio
from datetime import datetime
from decimal import Decimal

class ClientController:
    def __init__(self):
        self.dashboard_service = DashboardService()

    def check_cliente_permission(self):
        if 'user_id' not in session:
            flash('Debes iniciar sesión primero', 'error')
            return redirect(url_for('login'))
        if not self.dashboard_service.is_cliente():
            flash('No tienes permiso para acceder a esta página', 'error')
            return redirect(url_for('login'))
    
    def cliente_dashboard(self):
        if self.check_cliente_permission():
            return self.check_cliente_permission()
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM products WHERE estado = 1 ORDER BY RAND()")
        products = cursor.fetchall()
        cursor.execute("SELECT id, name, description, image_path as image FROM categories")
        categories = cursor.fetchall()
        user_id = session.get('user_id')
        cart_items = CartService.get_cart_items(user_id)
        cart_count = sum(item['quantity'] for item in cart_items)
        rec_service = RecommendationAIService()
        recommended_products = rec_service.get_recommendations_for_user(user_id)
        cursor.close()
        conn.close()
        return render_template(
            'client/client.html',
            categories=categories, 
            user=DashboardService.get_user_info(), 
            products=products, 
            cart_count=cart_count,
            recommended_products=recommended_products
        )
    
    def cart_client(self):
        if self.check_cliente_permission():
            return self.check_cliente_permission()
        user_id = session.get('user_id')
        cart_items = CartService.get_cart_items(user_id)
        cart_total = CartService.get_cart_total(user_id)
        rec_service = RecommendationAIService()
        recommended_products = rec_service.get_recommendations_for_user(user_id)
        addresses = AddressService.get_user_addresses(user_id)
        return render_template(
            'client/cart.html',
            user=DashboardService.get_user_info(),
            cart_items=cart_items,
            cart_total=cart_total,
            recommended_products=recommended_products,
            addresses=addresses
        )

    def product_detail(self, product_id):
        if self.check_cliente_permission():
            return self.check_cliente_permission()

        user_id = session.get('user_id')
        RecommendationAIService.track_product_view(user_id, product_id)
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # Categorías
        cursor.execute("SELECT id, name, description, image_path AS image FROM categories")
        categories = cursor.fetchall()

        # Producto principal
        cursor.execute("""
            SELECT p.*, c.name AS category_name
            FROM products p
            LEFT JOIN categories c ON p.category_id = c.id
            WHERE p.id = %s
        """, (product_id,))
        product = cursor.fetchone()
        if not product:
            flash('Producto no encontrado', 'error')
            return redirect(url_for('cliente_dashboard'))

        # Obtener evaluaciones del producto
        cursor.execute("""
            SELECT pe.rating, pe.comment, pe.created_at, u.name, u.last_name
            FROM product_evaluations pe
            JOIN users u ON pe.user_id = u.id
            WHERE pe.product_id = %s
            ORDER BY pe.created_at DESC
        """, (product_id,))
        evaluations = cursor.fetchall()

        # Calcular calificación promedio
        cursor.execute("""
            SELECT AVG(rating) as avg_rating, COUNT(*) as review_count
            FROM product_evaluations
            WHERE product_id = %s
        """, (product_id,))
        rating_info = cursor.fetchone()
        avg_rating = round(float(rating_info['avg_rating']), 1) if rating_info['avg_rating'] else 0
        review_count = rating_info['review_count']

        rec_service = RecommendationAIService()
        personalized_recommendations = rec_service.get_recommendations_for_user(user_id)
        product_data = rec_service.get_product_data()
        content_scores = rec_service.compute_content_based_similarity(product_id, product_data)
        similar_product_ids = sorted(content_scores.items(), key=lambda x: x[1], reverse=True)[:4]

        # Consulta dinámica de similares
        ids = [pid for pid, _ in similar_product_ids]
        if ids:
            placeholders = ', '.join(['%s'] * len(ids))
            sql_similar = (
                f"SELECT * FROM products "
                f"WHERE id IN ({placeholders}) AND estado = %s"
            )
            params = ids + [1]
            cursor.execute(sql_similar, params)
            similar_products = cursor.fetchall()
        else:
            similar_products = []

        recommended_products = []
        seen = {product_id}
        for p in personalized_recommendations + similar_products:
            if p['id'] not in seen:
                recommended_products.append(p)
                seen.add(p['id'])
            if len(recommended_products) >= 4:
                break

        cart_items = CartService.get_cart_items(user_id)
        cart_count = sum(item['quantity'] for item in cart_items)

        cursor.close()
        conn.close()

        return render_template(
            'client/product_detail.html',
            categories=categories,
            product=product,
            user=DashboardService.get_user_info(),
            recommended_products=recommended_products,
            cart_count=cart_count,
            evaluations=evaluations,
            avg_rating=avg_rating,
            review_count=review_count
        )

    
    
    def client_orders(self):
        if self.check_cliente_permission():
            return self.check_cliente_permission()
        user_id = session.get('user_id')
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT id, name, description, image_path as image FROM categories")
        categories = cursor.fetchall()
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
            categories=categories, 
            user=DashboardService.get_user_info(), 
            orders=orders
        )
    
    def order_details_client(self, order_id):
        if self.check_cliente_permission():
            return self.check_cliente_permission()
        
        user_id = session.get('user_id')
        
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("SELECT id, name, description, image_path as image FROM categories")
        categories = cursor.fetchall()
        
        # Obtener la información básica de la orden
        cursor.execute("""
            SELECT o.id AS order_id, o.total_amount, o.created_at, o.status, 
                a.address, m.name AS motorizado_name, m.last_name AS motorizado_last_name
            FROM orders o
            JOIN addresses a ON o.address_id = a.id
            LEFT JOIN users m ON o.motorizado_id = m.id
            WHERE o.id = %s AND o.user_id = %s
        """, (order_id, user_id))
        
        order = cursor.fetchone()
        
        if not order:
            flash('Pedido no encontrado o no tienes permiso para ver este pedido', 'error')
            return redirect(url_for('client_orders'))
        
        # Formatear la fecha
        order['created_at'] = order['created_at'].strftime('%d/%m/%Y')
        
        # Convertir el total a flotante
        order['total_amount'] = float(order['total_amount'])
        
        # Obtener los items del pedido
        cursor.execute("""
            SELECT oi.product_id, oi.quantity, oi.price, p.name, p.image
            FROM order_items oi
            JOIN products p ON oi.product_id = p.id
            WHERE oi.order_id = %s
        """, (order_id,))
        
        order['items'] = cursor.fetchall()
        
        # Verificar si ya existe una evaluación
        cursor.execute("""
            SELECT rating FROM evaluations 
            WHERE order_id = %s AND user_id = %s
        """, (order_id, user_id))
        evaluation = cursor.fetchone()
        
        cursor.close()
        conn.close()
        
        return render_template(
            'client/order_details.html',
            categories=categories, 
            order=order,
            evaluation=evaluation,  # Pasar la evaluación si existe
            user=DashboardService.get_user_info(),
            session=session
        )
    
    def submit_evaluation_moto(self, order_id):
        """Registra la evaluación del motorizado para este pedido."""
        if 'user_id' not in session:
            flash('Debes iniciar sesión para evaluar el servicio', 'error')
            return redirect(url_for('login'))

        rating = int(request.form.get('rating', 0))
        comment = request.form.get('comment', '').strip()

        # Validaciones básicas
        if rating < 1 or rating > 5:
            flash('Calificación inválida', 'error')
            return redirect(url_for('order_details_client', order_id=order_id))

        user_id = session['user_id']
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("""
                INSERT INTO evaluations (order_id, user_id, rating, comment)
                VALUES (%s, %s, %s, %s)
            """, (order_id, user_id, rating, comment))
            conn.commit()
            flash('¡Gracias por tu evaluación!', 'success')
        except Exception as e:
            conn.rollback()
            flash(f'Error al guardar la evaluación: {e}', 'error')
        finally:
            cursor.close()
            conn.close()

        return redirect(url_for('order_details_client', order_id=order_id))


    def product_detail(self, product_id):
        # Verificar permisos del cliente
        if self.check_cliente_permission():
            return self.check_cliente_permission()

        # Obtener el ID del usuario desde la sesión
        user_id = session.get('user_id')
        RecommendationAIService.track_product_view(user_id, product_id)

        # Conexión a la base de datos
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # Obtener categorías
        cursor.execute("SELECT id, name, description, image_path AS image FROM categories")
        categories = cursor.fetchall()

        # Obtener detalles del producto principal
        cursor.execute("""
            SELECT p.*, c.name AS category_name
            FROM products p
            LEFT JOIN categories c ON p.category_id = c.id
            WHERE p.id = %s
        """, (product_id,))
        product = cursor.fetchone()
        if not product:
            flash('Producto no encontrado', 'error')
            return redirect(url_for('cliente_dashboard'))

        # Calcular el precio tachado usando Decimal
        if 'price' in product and isinstance(product['price'], Decimal):
            crossed_price = (product['price'] * Decimal('1.2')).quantize(Decimal('0.01'))
            product['crossed_price'] = crossed_price
        else:
            product['crossed_price'] = None

        # Obtener evaluaciones del producto
        cursor.execute("""
            SELECT pe.rating, pe.comment, pe.created_at, CONCAT(u.name, ' ', u.last_name) AS user_name
            FROM product_evaluations pe
            JOIN users u ON pe.user_id = u.id
            WHERE pe.product_id = %s
            ORDER BY pe.created_at DESC
        """, (product_id,))
        reviews = cursor.fetchall()

        # Calcular calificación promedio y conteo de reseñas
        cursor.execute("""
            SELECT AVG(rating) as avg_rating, COUNT(*) as review_count
            FROM product_evaluations
            WHERE product_id = %s
        """, (product_id,))
        rating_info = cursor.fetchone()
        avg_rating = round(float(rating_info['avg_rating']), 1) if rating_info['avg_rating'] else 0
        review_count = rating_info['review_count']

        # Obtener recomendaciones
        rec_service = RecommendationAIService()
        personalized_recommendations = rec_service.get_recommendations_for_user(user_id)
        product_data = rec_service.get_product_data()
        content_scores = rec_service.compute_content_based_similarity(product_id, product_data)
        similar_product_ids = sorted(content_scores.items(), key=lambda x: x[1], reverse=True)[:4]

        # Obtener productos similares
        ids = [pid for pid, _ in similar_product_ids]
        if ids:
            placeholders = ', '.join(['%s'] * len(ids))
            sql_similar = f"SELECT * FROM products WHERE id IN ({placeholders}) AND estado = %s"
            params = ids + [1]
            cursor.execute(sql_similar, params)
            similar_products = cursor.fetchall()
        else:
            similar_products = []

        # Combinar recomendaciones personalizadas y productos similares
        recommended_products = []
        seen = {product_id}
        for p in personalized_recommendations + similar_products:
            if p['id'] not in seen:
                recommended_products.append(p)
                seen.add(p['id'])
            if len(recommended_products) >= 12:
                break

        # Obtener ítems del carrito y contar la cantidad total
        cart_items = CartService.get_cart_items(user_id)
        cart_count = sum(item['quantity'] for item in cart_items)

        # Cerrar conexión a la base de datos
        cursor.close()
        conn.close()

        # Renderizar la plantilla con todos los datos
        return render_template(
            'client/product_detail.html',
            categories=categories,
            product=product,
            user=DashboardService.get_user_info(),
            recommended_products=recommended_products,
            cart_count=cart_count,
            reviews=reviews,
            avg_rating=avg_rating,
            review_count=review_count
        )
        
    def submit_product_evaluation(self):
        """Submit a product evaluation without page refresh"""
        if not session.get('user_id'):
            return jsonify({'success': False, 'message': 'Debes iniciar sesión para evaluar productos'})
        
        try:
            data = request.get_json()
            user_id = session.get('user_id')
            product_id = data.get('product_id')
            rating = data.get('rating')
            comment = data.get('comment', '')
            
            # Validación mejorada
            if not all([product_id, rating]):
                return jsonify({'success': False, 'message': 'Datos incompletos'})
                
            # Asegurarnos que rating es un entero dentro del rango válido
            try:
                rating = int(rating)
                if rating < 1 or rating > 5:
                    return jsonify({'success': False, 'message': 'La calificación debe estar entre 1 y 5'})
            except (TypeError, ValueError):
                return jsonify({'success': False, 'message': 'La calificación debe ser un número'})
            
            conn = get_db_connection()
            cursor = conn.cursor(dictionary=True)
            
            # Check if user has already rated this product
            cursor.execute("""
                SELECT id FROM product_evaluations 
                WHERE user_id = %s AND product_id = %s
            """, (user_id, product_id))
            
            existing_rating = cursor.fetchone()
            
            if existing_rating:
                cursor.close()
                conn.close()
                return jsonify({'success': False, 'message': 'Ya has evaluado este producto'})
            
            # Insert the new evaluation
            cursor.execute("""
                INSERT INTO product_evaluations (user_id, product_id, rating, comment)
                VALUES (%s, %s, %s, %s)
            """, (user_id, product_id, rating, comment))
            
            evaluation_id = cursor.lastrowid
            
            # Get user info for the response
            cursor.execute("SELECT name, last_name FROM users WHERE id = %s", (user_id,))
            user = cursor.fetchone()
            
            # Calculate new average rating
            cursor.execute("""
                SELECT AVG(rating) as avg_rating, COUNT(*) as review_count
                FROM product_evaluations
                WHERE product_id = %s
            """, (product_id,))
            
            rating_info = cursor.fetchone()
            avg_rating = round(float(rating_info['avg_rating']), 1) if rating_info['avg_rating'] else 0
            review_count = rating_info['review_count']
            
            conn.commit()
            cursor.close()
            conn.close()
            
            # Registrar datos para depuración
            print(f"User {user_id} submitted rating {rating} for product {product_id}")
            
            # Return the data needed to update the UI
            return jsonify({
                'success': True,
                'evaluation': {
                    'id': evaluation_id,
                    'user_id': user_id,
                    'user_name': f"{user['name']} {user['last_name']}",
                    'rating': rating,  # Asegurar que se devuelve el rating correcto
                    'comment': comment
                },
                'new_avg': avg_rating,
                'review_count': review_count
            })
            
        except Exception as e:
            print(f"Error submitting evaluation: {e}")
            return jsonify({'success': False, 'message': f'Error al procesar la evaluación: {str(e)}'})

    def check_user_rating(self, product_id):
        """Check if the current user has already rated this product"""
        if not session.get('user_id'):
            return jsonify({'has_rated': False})
        
        user_id = session.get('user_id')
        
        try:
            conn = get_db_connection()
            cursor = conn.cursor(dictionary=True)
            
            cursor.execute("""
                SELECT id FROM product_evaluations 
                WHERE user_id = %s AND product_id = %s
            """, (user_id, product_id))
            
            has_rated = cursor.fetchone() is not None
            
            cursor.close()
            conn.close()
            
            return jsonify({'has_rated': has_rated})
            
        except Exception as e:
            print(f"Error checking user rating: {e}")
            return jsonify({'has_rated': False, 'error': str(e)})
    
    def get_categories(self):
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT id, name, description, image_path as image FROM categories")
        categories = cursor.fetchall()
        cursor.close()
        conn.close()
        return jsonify({'success': True, 'categories': categories})
    
    def client_category_products(self, category_id):
        if 'user_id' not in session:
            flash('Debes iniciar sesión primero', 'error')
            return redirect(url_for('login'))
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT id, name, description, image_path as image FROM categories WHERE id = %s", (category_id,))
        category = cursor.fetchone()
        if not category:
            flash('Categoría no encontrada', 'error')
            return redirect(url_for('cliente_dashboard'))
        cursor.execute("SELECT id, name, description, price, image, stock FROM products WHERE category_id = %s AND estado = 1", (category_id,))
        products = cursor.fetchall()
        user_id = session.get('user_id')
        rec_service = RecommendationAIService()
        recommended_products = rec_service.get_recommendations_for_user(user_id)
        cart_items = CartService.get_cart_items(user_id)
        cart_count = sum(item['quantity'] for item in cart_items)
        cursor.execute("SELECT id, name, description, image_path as image FROM categories WHERE id != %s", (category_id,))
        categories = cursor.fetchall()
        cursor.close()
        conn.close()
        return render_template(
            'client/category_products.html',
            categories=categories,
            category=category,
            products=products,
            recommended_products=recommended_products,
            cart_count=cart_count,
            user=DashboardService.get_user_info()
        )

    def client_map(self, order_id):
        if self.check_cliente_permission():
            return self.check_cliente_permission()
        
        user_id = session.get('user_id')
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Verify order exists and belongs to this client
        cursor.execute("""
            SELECT o.id AS order_id, o.status, a.address, 
                   CONCAT(m.name, ' ', m.last_name) AS motorizado_name
            FROM orders o
            JOIN addresses a ON o.address_id = a.id
            LEFT JOIN users m ON o.motorizado_id = m.id
            WHERE o.id = %s AND o.user_id = %s AND o.status = 'en camino'
        """, (order_id, user_id))
        order = cursor.fetchone()
        
        cursor.close()
        conn.close()
        
        if not order:
            flash('Pedido no encontrado, no pertenece a ti, o no está en camino', 'error')
            return redirect(url_for('client_orders'))
        
        return render_template(
            'client/client_map.html',
            order_id=order_id,
            order=order,
            motorizado_name=order['motorizado_name'] or 'Motorizado no asignado',
            user=DashboardService.get_user_info()
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
            # Obtener el contador del carrito para devolverlo en la respuesta
            cart_count = sum(item['quantity'] for item in cart_items)
            recommended_products = RecommendationAIService.get_recommendations_for_user(user_id)
            addresses = AddressService.get_user_addresses(user_id)
            html = render_template(
                'client/cart.html',
                cart_items=cart_items,
                cart_total=cart_total,
                recommended_products=recommended_products,
                addresses=addresses,
                user=DashboardService.get_user_info()
            )
            return jsonify({
                'success': True, 
                'html': html, 
                'cart_total': cart_total,
                'cart_count': cart_count  # Añadir el contador a la respuesta
            })
        return jsonify({'success': False, 'error': 'No se pudo actualizar el carrito'}), 400

    @staticmethod
    def get_cart_data():
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({'success': False, 'error': 'Usuario no autenticado'}), 401
        
        try:
            cart_items = CartService.get_cart_items(user_id)
            cart_total = CartService.get_cart_total(user_id)
            cart_count = sum(item['quantity'] for item in cart_items)
            
            return jsonify({
                'success': True,
                'cart_total': cart_total,
                'cart_count': cart_count,
                'has_items': len(cart_items) > 0
            })
        except Exception as e:
            print(f"Error al obtener datos del carrito: {str(e)}")
            return jsonify({'success': False, 'error': str(e)}), 500

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
            if request.headers.get('Content-Type') == 'application/json':
                return jsonify({'success': False, 'error': 'Debes iniciar sesión primero'}), 401
            flash('Debes iniciar sesión primero', 'error')
            return redirect(url_for('login'))
        
        user_id = session.get('user_id')
        
        if request.method == 'POST':
            # Determinar si es una petición AJAX o un envío de formulario normal
            is_json_request = request.headers.get('Content-Type') == 'application/json'
            
            if is_json_request:
                data = request.get_json()
                address_id = data.get('address_id')
                new_address = data.get('new_address')
                payment_amount = data.get('payment_amount')
            else:
                address_id = request.form.get('address_id')
                new_address = request.form.get('new_address')
                payment_amount = request.form.get('payment_amount')
            
            # Validación de la dirección
            if not address_id and not new_address:
                if is_json_request:
                    return jsonify({
                        'success': False, 
                        'error': 'Por favor, selecciona o agrega una dirección de entrega'
                    }), 400
                flash('Por favor, selecciona o agrega una dirección de entrega', 'error')
                return redirect(url_for('cart_client'))
            
            # Validación del monto de pago
            if not payment_amount or float(payment_amount) <= 0:
                if is_json_request:
                    return jsonify({
                        'success': False, 
                        'error': 'Por favor, ingresa un monto de pago válido'
                    }), 400
                flash('Por favor, ingresa un monto de pago válido', 'error')
                return redirect(url_for('cart_client'))
            
            # Obtener los items del carrito y el total
            cart_items = CartService.get_cart_items(user_id)
            cart_total = CartService.get_cart_total(user_id)
            
            # Si no hay items en el carrito
            if not cart_items:
                if is_json_request:
                    return jsonify({
                        'success': False, 
                        'error': 'El carrito está vacío'
                    }), 400
                flash('El carrito está vacío', 'error')
                return redirect(url_for('cart_client'))
            
            # Verificar si se debe crear una nueva dirección
            if new_address:
                address_id = AddressService.add_address(user_id, new_address)
            
            # Crear el pedido
            try:
                order_id = OrderService.create_order(
                    user_id=user_id,
                    address_id=address_id,
                    total_amount=cart_total,
                    payment_amount=float(payment_amount),
                    payment_method='efectivo'
                )
                
                # Agregar los items al pedido
                for item in cart_items:
                    OrderService.add_order_item(
                        order_id=order_id,
                        product_id=item['product_id'],
                        quantity=item['quantity'],
                        price=item['price']
                    )
                
                # Limpiar el carrito
                CartService.clear_cart(user_id)
                
                # Obtener información del usuario para notificación en tiempo real
                conn = get_db_connection()
                cursor = conn.cursor(dictionary=True)
                cursor.execute("SELECT name, last_name FROM users WHERE id = %s", (user_id,))
                user = cursor.fetchone()
                client_name = f"{user['name']} {user['last_name']}" if user else "Cliente Desconocido"
                cursor.close()
                conn.close()
                
                # Preparar detalles del pedido para la notificación
                order_details = {
                    'order_id': order_id,
                    'client_name': client_name,
                    'total_amount': float(cart_total),
                    'created_at': datetime.now().strftime('%d/%m/%Y'),
                    'address': AddressService.get_user_addresses(user_id)[0]['address'],
                    'status': 'pendiente'
                }
                
                # Emitir notificación de nuevo pedido
                socketio.emit('new_order', order_details, namespace='/admin')
                
                # Responder según el tipo de petición
                if is_json_request:
                    return jsonify({
                        'success': True,
                        'order_id': order_id,
                        'message': '¡Pedido realizado con éxito!'
                    })
                
                flash('¡Pedido realizado con éxito!', 'success')
                return redirect(url_for('order_confirmation', order_id=order_id))
                
            except Exception as e:
                print(f"Error en checkout: {str(e)}")
                if is_json_request:
                    return jsonify({
                        'success': False,
                        'error': f"Error al procesar el pedido: {str(e)}"
                    }), 500
                
                flash(f'Error al procesar el pedido: {str(e)}', 'error')
                return redirect(url_for('cart_client'))
        
        # Si es una petición GET, mostrar la página del carrito
        cart_items = CartService.get_cart_items(user_id)
        cart_total = CartService.get_cart_total(user_id)
        addresses = AddressService.get_user_addresses(user_id)
        recommended_products = RecommendationAIService.get_recommendations_for_user(user_id)
        
        return render_template(
            'client/cart.html',
            cart_items=cart_items,
            cart_total=cart_total,
            addresses=addresses,
            recommended_products=recommended_products,
            checkout_mode=True,
            user=DashboardService.get_user_info()
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
        
        user=DashboardService.get_user_info()

        return render_template('client/order_confirmation.html', order=order, user=user)

    @staticmethod
    def get_cart_count():
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({'cart_count': 0})
        
        try:
            cart_items = CartService.get_cart_items(user_id)
            cart_count = sum(item['quantity'] for item in cart_items)
            return jsonify({'success': True, 'cart_count': cart_count})
        except Exception as e:
            print(f"Error al obtener contador del carrito: {str(e)}")
            return jsonify({'success': False, 'cart_count': 0, 'error': str(e)})
    
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