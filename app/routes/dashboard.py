#dasboard.py get_cart_items
from flask import jsonify, render_template, session, redirect, url_for, flash, request
import os
from werkzeug.utils import secure_filename
import uuid
from app.db import get_db_connection
from app.extensions import bcrypt
from app.IA.recommendation_service import RecommendationAIService 
from app import socketio
from datetime import datetime

# Actualizar la ruta de UPLOAD_FOLDER para que sea absoluta

DEFAULT_IMAGE = 'default.jpg'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}


BASE_DIR = os.path.dirname(os.path.abspath(__file__))  # Directorio base de la aplicación
APP_DIR = os.path.dirname(BASE_DIR)  # Sube un nivel para asegurar que es "app/"
UPLOAD_FOLDER = os.path.join(APP_DIR, 'static', 'uploads')

# Crear la carpeta si no existe
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)


            

class DashboardService:
    @staticmethod
    def get_user_info():
        user_photo = session.get('user_photo', DEFAULT_IMAGE)
        return {'name': session.get('user_name'), 'photo': user_photo}

    @staticmethod
    def is_admin():
        return session.get('user_role') == 'admin'

    @staticmethod
    def is_cliente():
        return session.get('user_role') == 'cliente'

    @staticmethod
    def is_motorizado():
        return session.get('user_role') == 'motorizado'

    @staticmethod
    def admin_dashboard():
        if 'user_id' not in session:
            flash('Debes iniciar sesión primero', 'error')
            return redirect(url_for('login'))
        return render_template('admin/admin.html', user=DashboardService.get_user_info())

    @staticmethod
    def cliente_dashboard():
        if 'user_id' not in session:
            flash('Debes iniciar sesión primero', 'error')
            return redirect(url_for('login'))
        
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Get products to display to client
        cursor.execute("SELECT * FROM products WHERE estado = 1 ORDER BY RAND()")
        products = cursor.fetchall()
        
        # Obtener el conteo de productos en el carrito
        user_id = session.get('user_id')
        cart_items = CartService.get_cart_items(user_id)
        
        # Calcular el total de productos
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
        
        # Obtener recomendaciones basadas en el carrito actual
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
        """Ruta para mostrar detalle de producto y registrar la vista"""
        if 'user_id' not in session:
            flash('Debes iniciar sesión primero', 'error')
            return redirect(url_for('login'))

        user_id = session.get('user_id')
        
        # Registrar la vista del producto
        RecommendationAIService.track_product_view(user_id, product_id)

        # Obtener información del producto
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

        # Obtener productos recomendados
        rec_service = RecommendationAIService()
        recommended_products = rec_service.get_recommendations_for_user(user_id)

        # Obtener el conteo de productos en el carrito
        cart_items = CartService.get_cart_items(user_id)
        cart_count = sum(item['quantity'] for item in cart_items)

        cursor.close()
        conn.close()

        return render_template(
            'client/product_detail.html',
            product=product,
            user=DashboardService.get_user_info(),
            recommended_products=recommended_products,
            cart_count=cart_count  # Pasar el conteo al template
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
        
        # Convertir created_at a datetime si es necesario
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


    @staticmethod
    def motorizado_dashboard():
        if 'user_id' not in session:
            flash('Debes iniciar sesión primero', 'error')
            return redirect(url_for('login'))
        
        return render_template('motorizado/motorizado.html', user=DashboardService.get_user_info())
    
    @staticmethod
    def motorizado_pedidos():
        if 'user_id' not in session or session.get('user_role') != 'motorizado':
            flash('No tienes permiso para acceder a esta página', 'error')
            return redirect(url_for('login'))
        
        user_id = session.get('user_id')
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        cursor.execute("""
            SELECT o.id AS order_id, o.total_amount, o.created_at, o.status, a.address
            FROM orders o
            JOIN addresses a ON o.address_id = a.id
            WHERE o.motorizado_id = %s AND o.status = 'en camino'
            ORDER BY o.created_at DESC
        """, (user_id,))
        pedidos = cursor.fetchall()
        
        for pedido in pedidos:
            pedido['total_amount'] = float(pedido['total_amount'])
            pedido['created_at'] = pedido['created_at'].strftime('%d/%m/%Y')
        
        cursor.close()
        conn.close()
        
        return render_template('motorizado/pedidos.html', pedidos=pedidos, user=DashboardService.get_user_info())
    
    @staticmethod
    def marcar_entregado(order_id):
        if 'user_id' not in session or session.get('user_role') != 'motorizado':
            flash('No tienes permiso para realizar esta acción', 'error')
            return redirect(url_for('login'))
        
        user_id = session.get('user_id')
        conn = get_db_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("SELECT status FROM orders WHERE id = %s AND motorizado_id = %s", (order_id, user_id))
            result = cursor.fetchone()
            
            if not result or result[0] != 'en camino':
                flash('No puedes marcar este pedido como entregado', 'error')
                return redirect(url_for('motorizado_pedidos'))
            
            cursor.execute("UPDATE orders SET status = 'entregado' WHERE id = %s", (order_id,))
            if cursor.rowcount == 0:
                flash("No se pudo actualizar el estado del pedido", "error")
            else:
                conn.commit()
                flash('Pedido marcado como entregado', 'success')
        except Exception as e:
            conn.rollback()
            flash(f'Error al marcar el pedido: {str(e)}', 'error')
        finally:
            cursor.close()
            conn.close()
        
        return redirect(url_for('motorizado_pedidos'))

class UserService:
    @staticmethod
    def get_all_users():
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT id, name, last_name, gmail, rol, photo FROM users")
        users = cursor.fetchall()
        cursor.close()
        conn.close()
        return users

    @staticmethod
    def get_user_by_id(user_id):
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT name, last_name, gmail, rol, photo FROM users WHERE id = %s", (user_id,))
        user = cursor.fetchone()
        cursor.close()
        conn.close()
        return user

    @staticmethod
    def create_user(name, last_name, gmail, password, role, photo_filename):
        if UserService.email_exists(gmail):
            raise Exception("El correo electrónico ya está registrado.")
        
        hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("INSERT INTO users (name, last_name, gmail, password, rol, photo) VALUES (%s, %s, %s, %s, %s, %s)",
                           (name, last_name, gmail, hashed_password, role, photo_filename))
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise Exception(f'Error al crear usuario: {str(e)}')
        finally:
            cursor.close()
            conn.close()

    @staticmethod
    def update_user(id, name, last_name, gmail, role, photo_filename=None):
        if not photo_filename:
            photo_filename = 'default.jpg'

        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("UPDATE users SET name=%s, last_name=%s, gmail=%s, rol=%s, photo=%s WHERE id=%s",
                        (name, last_name, gmail, role, photo_filename, id))
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise Exception(f'Error al actualizar el usuario: {str(e)}')
        finally:
            cursor.close()
            conn.close()

    @staticmethod
    def delete_user(user_id):
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("DELETE FROM users WHERE id = %s", (user_id,))
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise Exception(f'Error al eliminar el usuario: {str(e)}')
        finally:
            cursor.close()
            conn.close()

    @staticmethod
    def email_exists(gmail):
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT COUNT(*) FROM users WHERE gmail = %s", (gmail,))
        result = cursor.fetchone()
        conn.close()
        return result['COUNT(*)'] > 0
    
    @staticmethod
    def allowed_file(filename):
        return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

class FileService:
    @staticmethod
    def save_photo(photo):
        if photo and photo.filename:
            filename = secure_filename(photo.filename)
            # Generar un nombre único para el archivo
            unique_filename = f"{uuid.uuid4()}_{filename}"
            photo_path = os.path.join(UPLOAD_FOLDER, unique_filename)
            try:
                photo.save(photo_path)
                return unique_filename
            except Exception as e:
                flash(f'Error al guardar la imagen: {e}', 'error')
                return DEFAULT_IMAGE
        return DEFAULT_IMAGE

class AdminController:
    def __init__(self, dashboard_service: DashboardService, user_service: UserService, file_service: FileService):
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

    def delete_user(self, user_id):
        if self.check_admin_permission():
            return self.check_admin_permission()

        try:
            self.user_service.delete_user(user_id)
            flash('Usuario eliminado correctamente', 'success')
        except Exception as e:
            flash(str(e), 'error')

        return redirect(url_for('admin_users'))

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
                # Generate unique filename
                filename = secure_filename(f"{uuid.uuid4()}_{image.filename}")
                filepath = os.path.join(UPLOAD_FOLDER, filename)
                image.save(filepath)
            else:
                flash('Imagen inválida o no proporcionada', 'error')
                return redirect(url_for('admin_category'))
            
            conn = get_db_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO categories (name, description, image_path)
                VALUES (%s, %s, %s)
            """, (name, description, filename))
            
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
            # Obtener datos del formulario
            name = request.form.get('name')
            description = request.form.get('description', '')
            image = request.files.get('image')
            
            if not name:
                flash('El nombre es requerido', 'error')
                return redirect(url_for('admin_category'))
            
            # Si se proporciona una imagen y es válida, procesarla
            if image and UserService.allowed_file(image.filename):
                # Generar un nombre de archivo único
                filename = secure_filename(f"{uuid.uuid4()}_{image.filename}")
                filepath = os.path.join(UPLOAD_FOLDER, filename)
                image.save(filepath)
            else:
                filename = None  # Si no se proporciona una imagen, no actualizarla
                
            # Conectar a la base de datos
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # Si se ha proporcionado una nueva imagen, actualizar el campo de la imagen
            if filename:
                cursor.execute("""
                    UPDATE categories 
                    SET name = %s, description = %s, image_path = %s
                    WHERE id = %s
                """, (name, description, filename, category_id))
            else:
                cursor.execute("""
                    UPDATE categories 
                    SET name = %s, description = %s
                    WHERE id = %s
                """, (name, description, category_id))
            
            conn.commit()
            cursor.close()
            conn.close()
            
            flash('Categoría actualizada exitosamente', 'success')
            return redirect(url_for('admin_category'))
        
        except Exception as e:
            flash(f'Error al actualizar la categoría: {str(e)}', 'error')
            return redirect(url_for('admin_category'))


            try:
                # Conexión a la base de datos
                conn = get_db_connection()
                cursor = conn.cursor()

                # Si hay una nueva imagen, actualizar todos los campos
                if filename:
                    # Primero obtener la imagen anterior para borrarla
                    cursor.execute("SELECT image_path FROM categories WHERE id = %s", (category_id,))
                    old_image = cursor.fetchone()
                    
                    # Actualizar la categoría con la nueva imagen
                    cursor.execute("""
                        UPDATE categories 
                        SET name = %s, description = %s, image_path = %s, updated_at = NOW()
                        WHERE id = %s
                        RETURNING id
                    """, (name, description, filename, category_id))
                    
                    # Si existe una imagen anterior, eliminarla
                    if old_image and old_image[0]:
                        old_image_path = os.path.join(UPLOAD_FOLDER, old_image[0])
                        if os.path.exists(old_image_path):
                            os.remove(old_image_path)
                
                else:
                    # Actualizar la categoría sin modificar la imagen
                    cursor.execute("""
                        UPDATE categories 
                        SET name = %s, description = %s, updated_at = NOW()
                        WHERE id = %s
                        RETURNING id
                    """, (name, description, category_id))

                # Verificar si se actualizó algún registro
                if cursor.rowcount == 0:
                    flash('Categoría no encontrada', 'error')
                    return redirect(url_for('admin_category'))

                # Confirmar los cambios
                conn.commit()
                flash('Categoría actualizada exitosamente', 'success')
                
            except Exception as db_error:
                # Manejar errores de base de datos
                if conn:
                    conn.rollback()
                flash('Error al actualizar la base de datos. Por favor, intente nuevamente.', 'error')
                return redirect(url_for('admin_category'))
                
            finally:
                # Cerrar la conexión
                if cursor:
                    cursor.close()
                if conn:
                    conn.close()

            # Redireccionar después de una actualización exitosa
            return redirect(url_for('admin_category'))

        except Exception as e:
            # Capturar cualquier otro error no manejado
            flash(f'Error inesperado: {str(e)}', 'error')
            return redirect(url_for('admin_category'))


        
    def delete_category(self, category_id):
        try:
            conn = get_db_connection()
            cursor = conn.cursor()

            # Obtener la ruta de la imagen de la categoría
            cursor.execute("SELECT image_path FROM categories WHERE id = %s", (category_id,))
            result = cursor.fetchone()

            if result:
                image_path = result[0]
                full_path = os.path.join(UPLOAD_FOLDER, image_path)
                if os.path.exists(full_path):
                    os.remove(full_path)

            # Eliminar primero los productos asociados
            cursor.execute("DELETE FROM products WHERE category_id = %s", (category_id,))

            # Luego eliminar la categoría
            cursor.execute("DELETE FROM categories WHERE id = %s", (category_id,))

            conn.commit()
            cursor.close()
            conn.close()

            flash('Categoría eliminada exitosamente', 'success')
            return redirect(url_for('admin_category'))

        except Exception as e:
            flash(f'Error al eliminar la categoría: {str(e)}', 'error')
            return redirect(url_for('admin_category'))

        
    # Add this to your routes in the main Flask app file

    def category_products(self, category_id):
        if 'user_id' not in session:
            flash('Debes iniciar sesión primero', 'error')
            return redirect(url_for('login'))
        
        # Get category info
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM categories WHERE id = %s", (category_id,))
        category = cursor.fetchone()
        
        # Get products for this category
        cursor.execute("SELECT * FROM products WHERE category_id = %s", (category_id,))
        products = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        user = DashboardService.get_user_info()
        return render_template('admin/adminProducts.html', category=category, products=products, user=user)

    def create_product(self, category_id):
        # Código para crear el producto
        if request.method == 'POST':
            name = request.form['name']
            description = request.form['description']
            price = float(request.form['price'])
            stock = int(request.form['stock'])
            estado = int(request.form['active'])
        
            # Handle file uploads
            main_image = request.files['main_image']
            image2 = request.files.get('image2')
            image3 = request.files.get('image3')
            
            # Save main image
            main_image_filename = ''
            if main_image and UserService.allowed_file(main_image.filename):
                filename = secure_filename(main_image.filename)
                main_image.save(os.path.join(UPLOAD_FOLDER, filename))
                main_image_filename = filename
            
            # Save optional images
            image2_filename = '' if not image2 else secure_filename(image2.filename)
            image3_filename = '' if not image3 else secure_filename(image3.filename)
            
            if image2 and UserService.allowed_file(image2.filename):
                image2.save(os.path.join(UPLOAD_FOLDER, image2_filename))
            if image3 and UserService.allowed_file(image3.filename):
                image3.save(os.path.join(UPLOAD_FOLDER, image3_filename))
            
            # Insert into database
            conn = get_db_connection()
            cursor = conn.cursor()
            
            query = """
                INSERT INTO products (name, description, price, stock, estado, image, image2, image3, category_id)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            values = (name, description, price, stock, estado, main_image_filename, 
                    image2_filename, image3_filename, category_id)
            
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
            # Get form data
            name = request.form['name']
            description = request.form['description']
            price = float(request.form['price'])
            stock = int(request.form['stock'])
            estado = int(request.form['active'])
            
            # Current image values (to maintain if no new image is uploaded)
            current_main_image = request.form.get('current_main_image', '')
            current_image2 = request.form.get('current_image2', '')
            current_image3 = request.form.get('current_image3', '')
            
            # Handle file uploads (check if new files were uploaded)
            main_image = request.files.get('main_image')
            image2 = request.files.get('image2')
            image3 = request.files.get('image3')
            
            # Initialize image filenames with current values
            main_image_filename = current_main_image
            image2_filename = current_image2
            image3_filename = current_image3
            
            # Process main image if a new one is uploaded
            if main_image and main_image.filename and UserService.allowed_file(main_image.filename):
                # Generate unique filename
                main_image_filename = secure_filename(f"{uuid.uuid4()}_{main_image.filename}")
                main_image.save(os.path.join(UPLOAD_FOLDER, main_image_filename))
                
                # Delete old image if it exists
                if current_main_image:
                    try:
                        old_image_path = os.path.join(UPLOAD_FOLDER, current_main_image)
                        if os.path.exists(old_image_path):
                            os.remove(old_image_path)
                    except Exception as e:
                        # Log error but continue
                        print(f"Error removing old main image: {str(e)}")
            
            # Process image2 if a new one is uploaded
            if image2 and image2.filename and UserService.allowed_file(image2.filename):
                image2_filename = secure_filename(f"{uuid.uuid4()}_{image2.filename}")
                image2.save(os.path.join(UPLOAD_FOLDER, image2_filename))
                
                # Delete old image if it exists
                if current_image2:
                    try:
                        old_image_path = os.path.join(UPLOAD_FOLDER, current_image2)
                        if os.path.exists(old_image_path):
                            os.remove(old_image_path)
                    except Exception as e:
                        print(f"Error removing old image2: {str(e)}")
            
            # Process image3 if a new one is uploaded
            if image3 and image3.filename and UserService.allowed_file(image3.filename):
                image3_filename = secure_filename(f"{uuid.uuid4()}_{image3.filename}")
                image3.save(os.path.join(UPLOAD_FOLDER, image3_filename))
                
                # Delete old image if it exists
                if current_image3:
                    try:
                        old_image_path = os.path.join(UPLOAD_FOLDER, current_image3)
                        if os.path.exists(old_image_path):
                            os.remove(old_image_path)
                    except Exception as e:
                        print(f"Error removing old image3: {str(e)}")
            
            # Connect to database
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # Update product in database
            query = """
                UPDATE products 
                SET name = %s, description = %s, price = %s, stock = %s, estado = %s,
                    image = %s, image2 = %s, image3 = %s, updated_at = NOW()
                WHERE id = %s AND category_id = %s
            """
            values = (
                name, description, price, stock, estado,
                main_image_filename, image2_filename, image3_filename,
                product_id, category_id
            )
            
            cursor.execute(query, values)
            conn.commit()
            
            cursor.close()
            conn.close()
            
            flash('Producto actualizado exitosamente', 'success')
        except Exception as e:
            flash(f'Error al actualizar el producto: {str(e)}', 'error')
        
        return redirect(url_for('category_products', category_id=category_id))
        

    def delete_product(self, product_id, category_id):  # Agrega 'self' aquí si es un método de clase
        conn = get_db_connection()
        cursor = conn.cursor()

        # Obtener las imágenes del producto
        cursor.execute('SELECT image, image2, image3 FROM products WHERE id = %s', (product_id,))
        product = cursor.fetchone()

        if product:
            for img in product:
                if img:
                    try:
                        os.remove(os.path.join(UPLOAD_FOLDER, img))
                    except:
                        pass

        # Eliminar el producto de la base de datos
        cursor.execute('DELETE FROM products WHERE id = %s', (product_id,))
        conn.commit()

        cursor.close()
        conn.close()

        flash('Producto eliminado exitosamente','success')
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
        
        # Obtener detalles del pedido
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
        
        # Formatear la fecha
        order['created_at'] = order['created_at'].strftime('%d/%m/%Y')
        order['total_amount'] = float(order['total_amount'])
        
        # Obtener los ítems del pedido
        cursor.execute("""
            SELECT oi.product_id, oi.quantity, oi.price, p.name, p.image
            FROM order_items oi
            JOIN products p ON oi.product_id = p.id
            WHERE oi.order_id = %s
        """, (order_id,))
        order['items'] = cursor.fetchall()
        
        # Obtener motorizados disponibles
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
        cursor = conn.cursor()
        try:
            # Verificar si el motorizado ya tiene un pedido en camino
            cursor.execute("SELECT COUNT(*) FROM orders WHERE motorizado_id = %s AND status = 'en camino'", (motorizado_id,))
            active_orders = cursor.fetchone()[0]
            if active_orders > 0:
                flash("El motorizado ya tiene un pedido en camino", "error")
                return redirect(url_for("order_details", order_id=order_id))

            # Asignar el pedido si no hay conflictos
            cursor.execute("UPDATE orders SET motorizado_id = %s, status = 'en camino' WHERE id = %s", (motorizado_id, order_id))
            if cursor.rowcount == 0:
                flash("No se encontró el pedido o no se pudo actualizar", "error")
            else:
                conn.commit()
                flash("Motorizado asignado con éxito", "success")
        except Exception as e:
            conn.rollback()
            flash(f"Error al asignar motorizado: {str(e)}", "error")
        finally:
            cursor.close()
            conn.close()

        return redirect(url_for("admin_orders"))


class CartService:
    @staticmethod
    def get_cart_items(user_id):
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Consulta para obtener los elementos del carrito con detalles del producto
        query = """
            SELECT c.id, c.product_id, c.quantity, p.name, p.description, p.price, 
                p.image, p.image2, p.image3, p.stock, (p.price * c.quantity) as total_price
            FROM cart c
            JOIN products p ON c.product_id = p.id
            WHERE c.user_id = %s
        """

        
        cursor.execute(query, (user_id,))
        cart_items = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        return cart_items
    
    @staticmethod
    def add_to_cart(user_id, product_id, quantity=1):
        conn = get_db_connection()
        cursor = conn.cursor()
        
        try:
            conn.start_transaction()
            
            # Bloquear la fila para evitar que otras solicitudes la modifiquen
            cursor.execute(
                "SELECT id, quantity FROM cart WHERE user_id = %s AND product_id = %s FOR UPDATE",
                (user_id, product_id)
            )
            existing_item = cursor.fetchone()
            
            if existing_item:
                new_quantity = existing_item[1] + quantity
                cursor.execute(
                    "UPDATE cart SET quantity = %s WHERE id = %s",
                    (new_quantity, existing_item[0])
                )
            else:
                cursor.execute(
                    "INSERT INTO cart (user_id, product_id, quantity) VALUES (%s, %s, %s)",
                    (user_id, product_id, quantity)
                )
            
            conn.commit()
            return True
        except Exception as e:
            conn.rollback()
            print(f"Error al agregar al carrito: {str(e)}")
            return False
        finally:
            cursor.close()
            conn.close()
        
    @staticmethod
    def update_cart_item(cart_id, quantity):
        conn = get_db_connection()
        cursor = conn.cursor()
        
        try:
            if quantity <= 0:
                cursor.execute("DELETE FROM cart WHERE id = %s", (cart_id,))
                conn.commit()
                return True
            else:
                cursor.execute(
                "UPDATE cart SET quantity = %s WHERE id = %s",
                (quantity, cart_id)
            )
            conn.commit()
            return True
        except Exception as e:
            conn.rollback()
            print(f"Error al actualizar carrito: {str(e)}")
            return False
        finally:
            cursor.close()
            conn.close()
    
    @staticmethod
    def remove_from_cart(cart_id):
        conn = get_db_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("DELETE FROM cart WHERE id = %s", (cart_id,))
            conn.commit()
            return True
        except Exception as e:
            conn.rollback()
            print(f"Error al eliminar del carrito: {str(e)}")
            return False
        finally:
            cursor.close()
            conn.close()
    
    @staticmethod
    def get_cart_total(user_id):
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        query = """
        SELECT SUM(p.price * c.quantity) as total
        FROM cart c
        JOIN products p ON c.product_id = p.id
        WHERE c.user_id = %s
        """
        
        cursor.execute(query, (user_id,))
        result = cursor.fetchone()
        
        cursor.close()
        conn.close()
        
        return result['total'] if result['total'] else 0
    
    @staticmethod
    def clear_cart(user_id):
        conn = get_db_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("DELETE FROM cart WHERE user_id = %s", (user_id,))
            conn.commit()
            return True
        except Exception as e:
            conn.rollback()
            print(f"Error al limpiar el carrito: {str(e)}")
            return False
        finally:
            cursor.close()
            conn.close()


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
                # Obtener el nuevo conteo del carrito
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
            # Obtener los datos actualizados del carrito
            user_id = session.get('user_id')
            cart_items = CartService.get_cart_items(user_id)
            cart_total = CartService.get_cart_total(user_id)

            # Renderizar solo la parte del carrito actualizada
            html = render_template('client/cart.html', cart_items=cart_items, cart_total=cart_total)
            
            return jsonify({'success': True, 'html': html, 'cart_total': cart_total})
        
        return jsonify({'success': False, 'error': 'No se pudo actualizar el carrito'}), 400


    @staticmethod
    def remove_from_cart():
        try:
            data = request.get_json()
            print("Datos recibidos:", data)  # 👀 Verifica si llega la info

            cart_id = data.get('cart_id')

            if not cart_id:
                return jsonify({"success": False, "error": "cart_id no proporcionado"}), 400

            success = CartService.remove_from_cart(cart_id)
            
            if success:
                return jsonify({"success": True}), 200
            else:
                return jsonify({"success": False, "error": "No se pudo eliminar"}), 500

        except Exception as e:
            print("Error:", str(e))  # 👀 Imprime errores en el servidor
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
            
            # Fetch client name for notification
            conn = get_db_connection()
            cursor = conn.cursor(dictionary=True)
            cursor.execute("SELECT name, last_name FROM users WHERE id = %s", (user_id,))
            user = cursor.fetchone()
            client_name = f"{user['name']} {user['last_name']}" if user else "Cliente Desconocido"
            cursor.close()
            conn.close()

            # Emit WebSocket event to notify admins
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
        print(f"orden: {order}")

        if not order:
            flash('Pedido no encontrado', 'error')
            return redirect(url_for('cliente_dashboard'))

        # Si el pedido está cancelado, redirigir
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
        
        # Convertir los objetos Decimal a float para serialización JSON
        for product in recommendations:
            if 'price' in product:
                product['price'] = float(product['price'])
        
        return jsonify({
            'success': True,
            'recommendations': recommendations
        })
    
    @staticmethod
    def track_view():
        """Endpoint AJAX para seguimiento de vistas de productos"""
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
        

class AddressService:
    @staticmethod
    def get_user_addresses(user_id):
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        query = """
        SELECT id, address, is_default
        FROM addresses
        WHERE user_id = %s
        ORDER BY is_default DESC, id DESC
        """
        
        cursor.execute(query, (user_id,))
        addresses = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        return addresses
    
    @staticmethod
    def add_address(user_id, address, is_default=False):
        conn = get_db_connection()
        cursor = conn.cursor()
        
        try:
            # Si es la dirección predeterminada, actualizar las demás
            if is_default:
                cursor.execute(
                    "UPDATE addresses SET is_default = FALSE WHERE user_id = %s",
                    (user_id,)
                )
            
            # Insertar la nueva dirección
            cursor.execute(
                "INSERT INTO addresses (user_id, address, is_default) VALUES (%s, %s, %s)",
                (user_id, address, is_default)
            )
            
            address_id = cursor.lastrowid
            conn.commit()
            return address_id
        except Exception as e:
            conn.rollback()
            print(f"Error al agregar dirección: {str(e)}")
            return None
        finally:
            cursor.close()
            conn.close()
    
    @staticmethod
    def set_default_address(user_id, address_id):
        conn = get_db_connection()
        cursor = conn.cursor()
        
        try:
            # Primero, quitar la marca de predeterminado de todas las direcciones
            cursor.execute(
                "UPDATE addresses SET is_default = FALSE WHERE user_id = %s",
                (user_id,)
            )
            
            # Luego, establecer la dirección seleccionada como predeterminada
            cursor.execute(
                "UPDATE addresses SET is_default = TRUE WHERE id = %s AND user_id = %s",
                (address_id, user_id)
            )
            
            conn.commit()
            return True
        except Exception as e:
            conn.rollback()
            print(f"Error al establecer dirección predeterminada: {str(e)}")
            return False
        finally:
            cursor.close()
            conn.close()

class OrderService:
    @staticmethod
    def create_order(user_id, address_id, total_amount, payment_amount, payment_method='efectivo'):
        conn = get_db_connection()
        cursor = conn.cursor()
        
        try:
            # Insertar el pedido
            cursor.execute(
                """
                INSERT INTO orders (user_id, address_id, total_amount, payment_amount, 
                payment_method, status, created_at)
                VALUES (%s, %s, %s, %s, %s, 'pendiente', NOW())
                """,
                (user_id, address_id, total_amount, payment_amount, payment_method)
            )
            
            order_id = cursor.lastrowid
            conn.commit()
            return order_id
        except Exception as e:
            conn.rollback()
            print(f"Error al crear pedido: {str(e)}")
            return None
        finally:
            cursor.close()
            conn.close()
    
    @staticmethod
    def add_order_item(order_id, product_id, quantity, price):
        conn = get_db_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute(
                """
                INSERT INTO order_items (order_id, product_id, quantity, price)
                VALUES (%s, %s, %s, %s)
                """,
                (order_id, product_id, quantity, price)
            )
            
            conn.commit()
            return True
        except Exception as e:
            conn.rollback()
            print(f"Error al agregar item al pedido: {str(e)}")
            return False
        finally:
            cursor.close()
            conn.close()
    
    @staticmethod
    def get_order(order_id, user_id):
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute(
            """
            SELECT o.*, a.address
            FROM orders o
            JOIN addresses a ON o.address_id = a.id
            WHERE o.id = %s AND o.user_id = %s AND o.status != 'cancelado'
            """,
            (order_id, user_id)
        )

        order = cursor.fetchone()

        if order:
            cursor.execute(
                """
                SELECT oi.*, p.name, p.image
                FROM order_items oi
                JOIN products p ON oi.product_id = p.id
                WHERE oi.order_id = %s
                """,
                (order_id,)
            )

            order['items'] = cursor.fetchall()
            order['change'] = float(order['payment_amount']) - float(order['total_amount'])



        cursor.close()
        conn.close()
        
        return order

    
    @staticmethod
    def cancel_order(order_id):
        conn = get_db_connection()
        cursor = conn.cursor()
        
        try:
            # Verificar si el pedido está en estado 'pendiente'
            cursor.execute(
                "SELECT status FROM orders WHERE id = %s",
                (order_id,)
            )
            
            result = cursor.fetchone()
            if not result or result[0] != 'pendiente':
                return False
            
            # Actualizar el estado del pedido
            cursor.execute(
                "UPDATE orders SET status = 'cancelado' WHERE id = %s",
                (order_id,)
            )
            
            conn.commit()
            return True
        except Exception as e:
            conn.rollback()
            print(f"Error al cancelar pedido: {str(e)}")
            return False
        finally:
            cursor.close()
            conn.close()

    @staticmethod
    def get_user_orders(user_id):
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT o.id AS order_id, o.total_amount, o.created_at, o.status, 
                a.address
            FROM orders o
            JOIN addresses a ON o.address_id = a.id
            WHERE o.user_id = %s AND o.status != 'cancelado'
            ORDER BY o.created_at DESC
        """, (user_id,))
        orders = cursor.fetchall()
        
        for order in orders:
            order['total_amount'] = float(order['total_amount'])
            order['created_at'] = order['created_at'].strftime('%d/%m/%Y')
        
        cursor.close()
        conn.close()
        
        return orders