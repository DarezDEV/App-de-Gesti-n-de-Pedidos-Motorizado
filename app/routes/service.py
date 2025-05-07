# app/routes/service.py
import os
from flask import flash
from werkzeug.utils import secure_filename
import uuid
from app.db import get_db_connection
from app.extensions import bcrypt
from datetime import datetime

DEFAULT_IMAGE = 'default.jpg'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
APP_DIR = os.path.dirname(BASE_DIR)
UPLOAD_FOLDER = os.path.join(APP_DIR, 'static', 'uploads')

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

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
            cursor.execute("INSERT INTO users (name, last_name, gmail, password, rol, photo, status) VALUES (%s, %s, %s, %s, %s, %s, %s)",
               (name, last_name, gmail, hashed_password, role, photo_filename, "disponible" if role == "motorizado" else "activo"))
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
            cursor.execute("UPDATE users SET name=%s, last_name=%s, gmail=%s, rol=%s, photo=%s, status=%s WHERE id=%s",
               (name, last_name, gmail, role, photo_filename, "disponible" if role == "motorizado" else "activo", id))
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise Exception(f'Error al actualizar el usuario: {str(e)}')
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
    
    @staticmethod
    def disable_user(user_id):
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            # Check if user exists and is not an admin
            cursor.execute("SELECT rol FROM users WHERE id = %s", (user_id,))
            user = cursor.fetchone()
            if not user:
                raise Exception("Usuario no encontrado")
            if user[0] == 'admin':
                raise Exception("No se puede deshabilitar un administrador")
            
            # Set user status to 'inactivo'
            cursor.execute("UPDATE users SET status = 'inactivo' WHERE id = %s", (user_id,))
            conn.commit()
            return True
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            cursor.close()
            conn.close()
    
    @staticmethod
    def enable_user(user_id):
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            # Check if user exists
            cursor.execute("SELECT id FROM users WHERE id = %s", (user_id,))
            if not cursor.fetchone():
                raise Exception("Usuario no encontrado")
            
            # Set user status back to 'activo'
            cursor.execute("UPDATE users SET status = 'activo' WHERE id = %s", (user_id,))
            conn.commit()
            return True
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            cursor.close()
            conn.close()
    
    @staticmethod
    def get_active_users():
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM users WHERE status != 'inactivo'")
        users = cursor.fetchall()
        cursor.close()
        conn.close()
        return users
    
    @staticmethod
    def get_disabled_users():
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM users WHERE status = 'inactivo'")
        users = cursor.fetchall()
        cursor.close()
        conn.close()
        return users

class FileService:
    @staticmethod
    def save_photo(photo):
        if photo and photo.filename:
            filename = secure_filename(photo.filename)
            unique_filename = f"{uuid.uuid4()}_{filename}"
            photo_path = os.path.join(UPLOAD_FOLDER, unique_filename)
            try:
                photo.save(photo_path)
                return unique_filename
            except Exception as e:
                flash(f'Error al guardar la imagen: {e}', 'error')
                return DEFAULT_IMAGE
        return DEFAULT_IMAGE

class CartService:
    @staticmethod
    def get_cart_items(user_id):
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
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
                cursor.execute("UPDATE cart SET quantity = %s WHERE id = %s", (quantity, cart_id))
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
            if is_default:
                cursor.execute("UPDATE addresses SET is_default = FALSE WHERE user_id = %s", (user_id,))
            cursor.execute("INSERT INTO addresses (user_id, address, is_default) VALUES (%s, %s, %s)", (user_id, address, is_default))
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

class OrderService:
    @staticmethod
    def create_order(user_id, address_id, total_amount, payment_amount, payment_method='efectivo'):
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
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
            cursor.execute("SELECT status FROM orders WHERE id = %s", (order_id,))
            result = cursor.fetchone()
            if not result or result[0] != 'pendiente':
                return False
            cursor.execute("UPDATE orders SET status = 'cancelado' WHERE id = %s", (order_id,))
            conn.commit()
            return True
        except Exception as e:
            conn.rollback()
            print(f"Error al cancelar pedido: {str(e)}")
            return False
        finally:
            cursor.close()
            conn.close()