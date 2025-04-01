# app/routes/admin.py
import os
import uuid
from flask import jsonify, render_template, session, redirect, url_for, flash, request
from werkzeug.utils import secure_filename
from app.db import get_db_connection
from app.routes.service import UserService, FileService
from app import UPLOAD_FOLDER, socketio

user_service = UserService() 

class AdminController:
    def __init__(self, dashboard_service, user_service: UserService, file_service: FileService):
        self.dashboard_service = dashboard_service
        self.user_service = user_service
        self.file_service = file_service

    def check_admin_permission(self):
        if 'user_id' not in session:
            flash('Debes iniciar sesión primero', 'error')
            return redirect(url_for('login'))
        if not self.dashboard_service.is_admin():
            flash('No tienes permiso para acceder a esta página', 'error')
            return redirect(url_for('login'))

    def admin_dashboard(self):
        if self.check_admin_permission():
            return self.check_admin_permission()
        user = self.dashboard_service.get_user_info()
        return render_template('admin/admin.html', user=user)
    
    def admin_users(self):
        if self.check_admin_permission():
            return self.check_admin_permission()
        user = self.dashboard_service.get_user_info()
        users = self.user_service.get_all_users()
        return render_template('admin/adminUsers.html', users=users, user=user)

    def create_user(self):
        if self.check_admin_permission():
            return self.check_admin_permission()
        name = request.form['name'].strip()
        last_name = request.form['last_name'].strip()
        gmail = request.form['gmail'].strip()
        password = request.form['password'].strip()
        role = request.form['rol'].strip()
        photo = request.files.get('photo')
        filename = self.file_service.save_photo(photo)
        if not all([name, last_name, gmail, password, role]):
            flash('Todos los campos son obligatorios', 'error')
            return redirect(url_for('admin_users'))
        try:
            self.user_service.create_user(name, last_name, gmail, password, role, filename)
            flash('Usuario creado correctamente', 'success')
        except Exception as e:
            flash(str(e), 'error')
        return redirect(url_for('admin_users'))

    def update_user(self, id):
        if self.check_admin_permission():
            return self.check_admin_permission()
        name = request.form['name'].strip()
        last_name = request.form['last_name'].strip()
        gmail = request.form['gmail'].strip()
        role = request.form['rol'].strip()
        photo = request.files.get('photo')
        filename = self.file_service.save_photo(photo)
        if not all([name, last_name, gmail, role]):
            flash('Todos los campos son obligatorios', 'error')
            return redirect(url_for('admin_users'))
        try:
            self.user_service.update_user(id, name, last_name, gmail, role, filename)
            flash('Usuario actualizado correctamente', 'success')
        except Exception as e:
            flash(str(e), 'error')
        return redirect(url_for('admin_users'))
    
    def admin_users(self):
        if self.check_admin_permission():
            return self.check_admin_permission()
        user = self.dashboard_service.get_user_info()
        users = self.user_service.get_active_users()
        return render_template('admin/adminUsers.html', users=users, user=user)
    
    def admin_disabled_users(self):
        if self.check_admin_permission():
            return self.check_admin_permission()
        user = self.dashboard_service.get_user_info()
        disabled_users = self.user_service.get_disabled_users()
        return render_template('admin/adminDisabledUsers.html', users=disabled_users, user=user)
    
    def disable_user(self, user_id):
        if self.check_admin_permission():
            return self.check_admin_permission()
        try:
            self.user_service.disable_user(user_id)
            flash('Usuario deshabilitado correctamente', 'success')
        except Exception as e:
            flash(str(e), 'error')
        return redirect(url_for('admin_users'))
    
    def enable_user(self, user_id):
        if self.check_admin_permission():
            return self.check_admin_permission()
        try:
            self.user_service.enable_user(user_id)
            flash('Usuario habilitado correctamente', 'success')
        except Exception as e:
            flash(str(e), 'error')
        return redirect(url_for('admin_disabled_users'))

    def profile(self, user_id):
        user = self.user_service.get_user_by_id(user_id)
        return render_template('admin/profile.html', user=user)
    
    def admin_category(self):
        if self.check_admin_permission():
            return self.check_admin_permission()
        user = self.dashboard_service.get_user_info()
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM categories")
        categories = cursor.fetchall()
        cursor.close()
        conn.close()
        return render_template('admin/adminCategory.html', user=user, categories=categories)

    def create_category(self):
        if self.check_admin_permission():
            return self.check_admin_permission()
        try:
            name = request.form.get('name')
            description = request.form.get('description', '')
            image = request.files.get('image')
            if not name:
                flash('El nombre es requerido', 'error')
                return redirect(url_for('admin_category'))
            if image and UserService.allowed_file(image.filename):
                filename = secure_filename(f"{uuid.uuid4()}_{image.filename}")
                filepath = os.path.join(UPLOAD_FOLDER, filename)
                image.save(filepath)
            else:
                flash('Imagen inválida o no proporcionada', 'error')
                return redirect(url_for('admin_category'))
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("INSERT INTO categories (name, description, image_path) VALUES (%s, %s, %s)", (name, description, filename))
            conn.commit()
            cursor.close()
            conn.close()
            flash('Categoría creada exitosamente', 'success')
            return redirect(url_for('admin_category'))
        except Exception as e:
            flash(f'Error al crear la categoría: {str(e)}', 'error')
            return redirect(url_for('admin_category'))

    def update_category(self, category_id):
        if self.check_admin_permission():
            return self.check_admin_permission()
        try:
            name = request.form.get('name')
            description = request.form.get('description', '')
            image = request.files.get('image')
            if not name:
                flash('El nombre es requerido', 'error')
                return redirect(url_for('admin_category'))
            if image and UserService.allowed_file(image.filename):
                filename = secure_filename(f"{uuid.uuid4()}_{image.filename}")
                filepath = os.path.join(UPLOAD_FOLDER, filename)
                image.save(filepath)
            else:
                filename = None
            conn = get_db_connection()
            cursor = conn.cursor()
            if filename:
                cursor.execute("UPDATE categories SET name = %s, description = %s, image_path = %s WHERE id = %s", (name, description, filename, category_id))
            else:
                cursor.execute("UPDATE categories SET name = %s, description = %s WHERE id = %s", (name, description, category_id))
            conn.commit()
            cursor.close()
            conn.close()
            flash('Categoría actualizada exitosamente', 'success')
            return redirect(url_for('admin_category'))
        except Exception as e:
            flash(f'Error al actualizar la categoría: {str(e)}', 'error')
            return redirect(url_for('admin_category'))

    def delete_category(self, category_id):
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT image_path FROM categories WHERE id = %s", (category_id,))
            result = cursor.fetchone()
            if result:
                image_path = result[0]
                full_path = os.path.join(UPLOAD_FOLDER, image_path)
                if os.path.exists(full_path):
                    os.remove(full_path)
            cursor.execute("DELETE FROM products WHERE category_id = %s", (category_id,))
            cursor.execute("DELETE FROM categories WHERE id = %s", (category_id,))
            conn.commit()
            cursor.close()
            conn.close()
            flash('Categoría eliminada exitosamente', 'success')
            return redirect(url_for('admin_category'))
        except Exception as e:
            flash(f'Error al eliminar la categoría: {str(e)}', 'error')
            return redirect(url_for('admin_category'))

    def category_products(self, category_id):
        if 'user_id' not in session:
            flash('Debes iniciar sesión primero', 'error')
            return redirect(url_for('login'))
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM categories WHERE id = %s", (category_id,))
        category = cursor.fetchone()
        cursor.execute("SELECT * FROM products WHERE category_id = %s", (category_id,))
        products = cursor.fetchall()
        cursor.close()
        conn.close()
        user = self.dashboard_service.get_user_info()
        return render_template('admin/adminProducts.html', category=category, products=products, user=user)

    def create_product(self, category_id):
        if request.method == 'POST':
            name = request.form['name']
            description = request.form['description']
            price = float(request.form['price'])
            stock = int(request.form['stock'])
            estado = int(request.form['active'])
            main_image = request.files['main_image']
            image2 = request.files.get('image2')
            image3 = request.files.get('image3')
            main_image_filename = ''
            if main_image and UserService.allowed_file(main_image.filename):
                filename = secure_filename(main_image.filename)
                main_image.save(os.path.join(UPLOAD_FOLDER, filename))
                main_image_filename = filename
            image2_filename = '' if not image2 else secure_filename(image2.filename)
            image3_filename = '' if not image3 else secure_filename(image3.filename)
            if image2 and UserService.allowed_file(image2.filename):
                image2.save(os.path.join(UPLOAD_FOLDER, image2_filename))
            if image3 and UserService.allowed_file(image3.filename):
                image3.save(os.path.join(UPLOAD_FOLDER, image3_filename))
            conn = get_db_connection()
            cursor = conn.cursor()
            query = """
                INSERT INTO products (name, description, price, stock, estado, image, image2, image3, category_id)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            values = (name, description, price, stock, estado, main_image_filename, image2_filename, image3_filename, category_id)
            cursor.execute(query, values)
            conn.commit()
            cursor.close()
            conn.close()
        flash('Producto creado exitosamente', 'success')
        return redirect(url_for('category_products', category_id=category_id))

    def update_product(self, product_id, category_id):
        if self.check_admin_permission():
            return self.check_admin_permission()
        try:
            name = request.form['name']
            description = request.form['description']
            price = float(request.form['price'])
            stock = int(request.form['stock'])
            estado = int(request.form['active'])
            current_main_image = request.form.get('current_main_image', '')
            current_image2 = request.form.get('current_image2', '')
            current_image3 = request.form.get('current_image3', '')
            main_image = request.files.get('main_image')
            image2 = request.files.get('image2')
            image3 = request.files.get('image3')
            main_image_filename = current_main_image
            image2_filename = current_image2
            image3_filename = current_image3
            if main_image and main_image.filename and UserService.allowed_file(main_image.filename):
                main_image_filename = secure_filename(f"{uuid.uuid4()}_{main_image.filename}")
                main_image.save(os.path.join(UPLOAD_FOLDER, main_image_filename))
                if current_main_image:
                    try:
                        old_image_path = os.path.join(UPLOAD_FOLDER, current_main_image)
                        if os.path.exists(old_image_path):
                            os.remove(old_image_path)
                    except Exception as e:
                        print(f"Error removing old main image: {str(e)}")
            if image2 and image2.filename and UserService.allowed_file(image2.filename):
                image2_filename = secure_filename(f"{uuid.uuid4()}_{image2.filename}")
                image2.save(os.path.join(UPLOAD_FOLDER, image2_filename))
                if current_image2:
                    try:
                        old_image_path = os.path.join(UPLOAD_FOLDER, current_image2)
                        if os.path.exists(old_image_path):
                            os.remove(old_image_path)
                    except Exception as e:
                        print(f"Error removing old image2: {str(e)}")
            if image3 and image3.filename and UserService.allowed_file(image3.filename):
                image3_filename = secure_filename(f"{uuid.uuid4()}_{image3.filename}")
                image3.save(os.path.join(UPLOAD_FOLDER, image3_filename))
                if current_image3:
                    try:
                        old_image_path = os.path.join(UPLOAD_FOLDER, current_image3)
                        if os.path.exists(old_image_path):
                            os.remove(old_image_path)
                    except Exception as e:
                        print(f"Error removing old image3: {str(e)}")
            conn = get_db_connection()
            cursor = conn.cursor()
            query = """
                UPDATE products 
                SET name = %s, description = %s, price = %s, stock = %s, estado = %s,
                    image = %s, image2 = %s, image3 = %s, updated_at = NOW()
                WHERE id = %s AND category_id = %s
            """
            values = (name, description, price, stock, estado, main_image_filename, image2_filename, image3_filename, product_id, category_id)
            cursor.execute(query, values)
            conn.commit()
            cursor.close()
            conn.close()
            flash('Producto actualizado exitosamente', 'success')
        except Exception as e:
            flash(f'Error al actualizar el producto: {str(e)}', 'error')
        return redirect(url_for('category_products', category_id=category_id))

    def delete_product(self, product_id, category_id):
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT image, image2, image3 FROM products WHERE id = %s', (product_id,))
        product = cursor.fetchone()
        if product:
            for img in product:
                if img:
                    try:
                        os.remove(os.path.join(UPLOAD_FOLDER, img))
                    except:
                        pass
        cursor.execute('DELETE FROM products WHERE id = %s', (product_id,))
        conn.commit()
        cursor.close()
        conn.close()
        flash('Producto eliminado exitosamente', 'success')
        return redirect(url_for('category_products', category_id=category_id))
    
    def admin_orders(self):
        if self.check_admin_permission():
            return self.check_admin_permission()
        user = self.dashboard_service.get_user_info()
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT o.id AS order_id, o.total_amount, o.created_at, o.status, 
                u.name, u.last_name, a.address,
                m.name AS motorizado_name, m.last_name AS motorizado_last_name
            FROM orders o
            JOIN users u ON o.user_id = u.id
            JOIN addresses a ON o.address_id = a.id
            LEFT JOIN users m ON o.motorizado_id = m.id AND m.rol = 'motorizado'
            WHERE o.status != 'cancelado'
            ORDER BY o.created_at DESC
        """)
        orders = cursor.fetchall()
        for order in orders:
            order['total_amount'] = float(order['total_amount'])
            order['created_at'] = order['created_at'].strftime('%d/%m/%Y')
        cursor.close()
        conn.close()
        return render_template('admin/admin_orders.html', user=user, orders=orders)

    def order_details(self, order_id):
        if self.check_admin_permission():
            return self.check_admin_permission()
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT o.id AS order_id, o.total_amount, o.created_at, o.status, 
                u.name AS client_name, u.last_name AS client_last_name, u.gmail AS client_email,
                a.address, m.name AS motorizado_name, m.last_name AS motorizado_last_name
            FROM orders o
            JOIN users u ON o.user_id = u.id
            JOIN addresses a ON o.address_id = a.id
            LEFT JOIN users m ON o.motorizado_id = m.id AND m.rol = 'motorizado'
            WHERE o.id = %s
        """, (order_id,))
        order = cursor.fetchone()
        if not order:
            flash('Pedido no encontrado', 'error')
            return redirect(url_for('admin_orders'))
        order['created_at'] = order['created_at'].strftime('%d/%m/%Y')
        order['total_amount'] = float(order['total_amount'])
        cursor.execute("""
            SELECT oi.product_id, oi.quantity, oi.price, p.name, p.image
            FROM order_items oi
            JOIN products p ON oi.product_id = p.id
            WHERE oi.order_id = %s
        """, (order_id,))
        order['items'] = cursor.fetchall()
        cursor.execute("""
            SELECT u.id, u.name, u.last_name
            FROM users u
            WHERE u.rol = 'motorizado'
            AND u.status = 'disponible'
            AND NOT EXISTS (
                SELECT 1 FROM orders o
                WHERE o.motorizado_id = u.id AND o.status = 'en camino'
            )
        """)
        motorizados = cursor.fetchall()
        cursor.close()
        conn.close()
        user = self.dashboard_service.get_user_info()
        return render_template('admin/order_details.html', order=order, motorizados=motorizados, user=user)
    
    def assign_motorizado(self, order_id):
        motorizado_id = request.form.get("motorizado_id")
        if not motorizado_id:
            flash("Selecciona un motorizado", "error")
            return redirect(url_for("order_details", order_id=order_id))
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute("SELECT COUNT(*) FROM orders WHERE motorizado_id = %s AND status = 'en camino'", (motorizado_id,))
            active_orders = cursor.fetchone()['COUNT(*)']
            if active_orders > 0:
                flash("El motorizado ya tiene un pedido en camino", "error")
                return redirect(url_for("order_details", order_id=order_id))
            cursor.execute("""
                SELECT o.id AS order_id, o.total_amount, o.created_at, o.status, 
                    u.name AS client_name, u.last_name AS client_last_name, a.address,
                    m.name AS motorizado_name, m.last_name AS motorizado_last_name,
                    o.user_id
                FROM orders o
                JOIN users u ON o.user_id = u.id
                JOIN addresses a ON o.address_id = a.id
                LEFT JOIN users m ON o.motorizado_id = m.id
                WHERE o.id = %s
            """, (order_id,))
            order = cursor.fetchone()
            cursor.execute("UPDATE orders SET motorizado_id = %s, status = 'en camino' WHERE id = %s", (motorizado_id, order_id))
            if cursor.rowcount == 0:
                flash("No se encontró el pedido o no se pudo actualizar", "error")
            else:
                conn.commit()
                order_details = {
                    'order_id': order_id,
                    'status': 'en camino',
                    'motorizado_name': f"{order['motorizado_name']} {order['motorizado_last_name']}",
                    'total_amount': float(order['total_amount']),
                    'created_at': order['created_at'].strftime('%d/%m/%Y'),
                    'address': order['address'],
                    'client_id': order['user_id']
                }
                socketio.emit('order_status_update', order_details, namespace='/admin')
                socketio.emit('order_status_update', order_details, namespace='/client')
                socketio.emit('new_delivery', order_details, namespace='/motorizado')
        except Exception as e:
            conn.rollback()
            flash(f"Error al asignar motorizado: {str(e)}", "error")
        finally:
            cursor.close()
            conn.close()
        return redirect(url_for("order_details", order_id=order_id))