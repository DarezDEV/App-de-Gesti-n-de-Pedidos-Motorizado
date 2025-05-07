# app/auth.py
from math import e
from flask import render_template, request, redirect, url_for, flash, session, current_app, jsonify
from app.extensions import Bcrypt, Mail
from werkzeug.utils import secure_filename
import os
from app.db import get_db_connection
from app.models import User
from flask_mail import Message
import random
import string
from datetime import datetime, timedelta
from flask_dance.contrib.google import google

bcrypt = Bcrypt()
mail = Mail()
UPLOAD_FOLDER = os.path.join(os.getcwd(), 'app', 'static', 'Uploads')
DEFAULT_IMAGE = 'default.jpg'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

class EmailService:
    @staticmethod
    def generate_verification_code():
        """Generate a 6-digit verification code"""
        return ''.join(random.choices(string.digits, k=6))

    @staticmethod
    def send_verification_email(email, code):
        """Send verification email to user"""
        try:
            msg = Message('Código de Verificación',
                         sender=current_app.config['MAIL_USERNAME'],
                         recipients=[email])
            msg.body = f'Tu código de verificación es: {code}\nEste código expirará en 10 minutos.'
            mail.send(msg)
            return True
        except Exception as e:
            print(f"Error sending email: {e}")
            return False

class AuthService:
    def __init__(self):
        self.upload_folder = UPLOAD_FOLDER
        self.default_image = DEFAULT_IMAGE
        self.email_service = EmailService()

    def generate_unique_filename(self, filename):
        base, ext = os.path.splitext(filename)
        counter = 1
        new_filename = filename
        while os.path.exists(os.path.join(self.upload_folder, new_filename)):
            new_filename = f"{base}_{counter}{ext}"
            counter += 1
        return new_filename

    def get_dashboard(self):
        role = session.get('user_role', '')
        dashboards = {
            'admin': 'admin_dashboard',
            'cliente': 'cliente_dashboard',
            'motorizado': 'motorizado_pedidos'
        }
        return url_for(dashboards.get(role, 'login'))

    def save_photo(self, photo):
        filename = self.default_image
        if photo and photo.filename:
            filename = secure_filename(photo.filename)
            filename = self.generate_unique_filename(filename)
            photo_path = os.path.join(self.upload_folder, filename)
            try:
                photo.save(photo_path)
            except Exception as e:
                print(f"Error al guardar la imagen: {e}")
                filename = self.default_image
        return filename

    def store_registration_data(self, name, last_name, gmail, password, filename):
        session['temp_name'] = name
        session['temp_last_name'] = last_name
        session['temp_email'] = gmail
        session['temp_password'] = password
        session['temp_filename'] = filename
        
    def clear_temp_data(self):
        temp_keys = ['temp_name', 'temp_last_name', 'temp_email', 'temp_password', 
                    'temp_filename', 'verification_code', 'code_generated_time',
                    'temp_new_email']
        for key in temp_keys:
            session.pop(key, None)

class AuthController:
    def __init__(self, auth_service: AuthService):
        self.auth_service = auth_service

    def register(self):
        if 'user_id' in session:
            return redirect(self.auth_service.get_dashboard())

        if request.method == 'POST':
            if 'verification_code' in request.form:
                return self._handle_verification_code()
            return self._handle_initial_registration()

        return render_template('auth/register.html', show_verification=False)

    def _handle_verification_code(self):
        stored_code = session.get('verification_code')
        stored_time = session.get('code_generated_time')
        
        if not all([stored_code, stored_time]):
            flash('Sesión expirada. Por favor, intente registrarse nuevamente.', 'error')
            return redirect(url_for('register'))
        
        code_time = datetime.fromisoformat(stored_time)
        if datetime.now() - code_time > timedelta(minutes=10):
            flash('El código ha expirado. Por favor, solicite uno nuevo.', 'error')
            return redirect(url_for('register'))
        
        if request.form['verification_code'] != stored_code:
            flash('Código de verificación incorrecto', 'error')
            return render_template('auth/register.html', show_verification=True)
        
        return self._complete_registration()

    def _handle_initial_registration(self):
        name = request.form['name'].strip()
        last_name = request.form['last_name'].strip()
        gmail = request.form['gmail'].strip()
        password = request.form['password'].strip()
        confirm_password = request.form['confirm_password'].strip()
        photo = request.files.get('photo')

        if not all([name, last_name, gmail, password, confirm_password]):
            flash('Complete todos los campos', 'error')
            return redirect(url_for('register'))

        if password != confirm_password:
            flash('Las contraseñas no coinciden', 'error')
            return redirect(url_for('register'))

        if len(password) < 8:
            flash('La contraseña debe tener al menos 8 caracteres', 'error')
            return redirect(url_for('register'))

        if User.get_user_by_email(gmail):
            flash('El correo ya está registrado', 'error')
            return redirect(url_for('register'))

        filename = self.auth_service.save_photo(photo)
        self.auth_service.store_registration_data(name, last_name, gmail, password, filename)
        
        code = EmailService.generate_verification_code()
        session['verification_code'] = code
        session['code_generated_time'] = datetime.now().isoformat()
        
        if EmailService.send_verification_email(gmail, code):
            return render_template('auth/register.html', show_verification=True)
        else:
            flash('Error al enviar el código de verificación', 'error')
            return redirect(url_for('register'))

    def _complete_registration(self):
        name = session.get('temp_name')
        last_name = session.get('temp_last_name')
        gmail = session.get('temp_email')
        password = session.get('temp_password')
        filename = session.get('temp_filename')
        
        hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
        
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("""
                INSERT INTO users (name, last_name, gmail, password, rol, photo) 
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (name, last_name, gmail, hashed_password, 'cliente', filename))
            conn.commit()
            
            self.auth_service.clear_temp_data()
            flash('Registro exitoso, ahora puedes iniciar sesión', 'success')
            return redirect(url_for('login'))
        except Exception as e:
            conn.rollback()
            flash(f'Error en el registro: {str(e)}', 'error')
            return redirect(url_for('register'))
        finally:
            cursor.close()
            conn.close()

    def login(self):
        if 'user_id' in session:
            return redirect(self.auth_service.get_dashboard())

        if request.method == 'POST':
            gmail = request.form['gmail'].strip()
            password = request.form['password'].strip()
            user = User.get_user_by_email(gmail)

            if not all([gmail, password]):
                flash('Complete todos los campos', 'error')
                return redirect(url_for('login'))

            # … después de obtener `user` …
            if user is None:
                flash('Correo o contraseña incorrectos', 'error')
                return redirect(url_for('login'))

            # Intentamos verificar el hash; si salta ValueError, lo consideramos inválido
            try:
                password_ok = bcrypt.check_password_hash(user['password'], password)
            except ValueError:
                password_ok = False

            if not password_ok:
                flash('Correo o contraseña incorrectos', 'error')
                return redirect(url_for('login'))


            session['user_id'] = user['id']
            session['user_role'] = user['rol']
            session['user_name'] = user['name']
            session['user_last_name'] = user['last_name']
            session['user_gmail'] = user['gmail']
            session['user_photo'] = user['photo']
            flash('Inicio de sesión exitoso', 'success')
            return redirect(self.auth_service.get_dashboard())

        return render_template('auth/login.html')

    def logout(self):
        session.clear()
        flash('La sesión se cerró correctamente', 'success')
        return redirect(url_for('login'))
    
    def google_login(self):
        if 'user_id' in session:
            return redirect(self.auth_service.get_dashboard())

        if not google.authorized:
            return redirect(url_for("google.login"))

        resp = google.get("/oauth2/v2/userinfo")
        if resp.ok:
            user_info = resp.json()
            gmail = user_info['email']
            user = User.get_user_by_email(gmail)

            if user is None:
                # Generar una contraseña aleatoria para usuarios de Google
                import secrets
                random_password = secrets.token_urlsafe(16)
                hashed_password = bcrypt.generate_password_hash(random_password).decode('utf-8')
                
                # Descargar la foto de perfil de Google
                photo_url = user_info.get('picture')
                filename = self.auth_service.default_image  # Por defecto, usar imagen predeterminada
                if photo_url:
                    try:
                        import requests
                        from io import BytesIO
                        from PIL import Image
                        response = requests.get(photo_url)
                        if response.status_code == 200:
                            image = Image.open(BytesIO(response.content))
                            filename = self.auth_service.generate_unique_filename(f"{gmail.split('@')[0]}.jpg")
                            photo_path = os.path.join(self.auth_service.upload_folder, filename)
                            image.save(photo_path)
                        else:
                            print(f"Error al descargar la imagen: Código de estado {response.status_code}")
                    except Exception as e:
                        print(f"Error al procesar la imagen: {e}")
                        filename = self.auth_service.default_image
                
                # Registrar nuevo usuario con la foto local
                conn = get_db_connection()
                cursor = conn.cursor()
                try:
                    cursor.execute("""
                        INSERT INTO users (name, last_name, gmail, password, rol, photo) 
                        VALUES (%s, %s, %s, %s, %s, %s)
                    """, (
                        user_info['given_name'],
                        user_info.get('family_name', ''),
                        gmail,
                        hashed_password,
                        'cliente',
                        filename
                    ))
                    conn.commit()
                    user = User.get_user_by_email(gmail)
                except Exception as e:
                    conn.rollback()
                    flash(f'Error al registrar usuario con Google: {str(e)}', 'error')
                    return redirect(url_for('login'))
                finally:
                    cursor.close()
                    conn.close()

            # Configurar la sesión con los datos del usuario
            session['user_id'] = user['id']
            session['user_role'] = user['rol']
            session['user_name'] = user['name']
            session['user_last_name'] = user['last_name']
            session['user_gmail'] = user['gmail']
            session['user_photo'] = user['photo']  # Nombre del archivo local
            flash('Inicio de sesión con Google exitoso', 'success')
            return redirect(self.auth_service.get_dashboard())
        else:
            flash('Error al iniciar sesión con Google', 'error')
            return redirect(url_for('login'))

    def update_profile_photo(self):
        if 'user_id' not in session:
            return jsonify({'success': False, 'message': 'No autorizado'}), 401

        photo = request.files.get('photo')
        if not photo:
            return jsonify({'success': False, 'message': 'No se proporcionó ninguna foto'})

        filename = self.auth_service.save_photo(photo)
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("UPDATE users SET photo = %s WHERE id = %s", (filename, session['user_id']))
            conn.commit()
            session['user_photo'] = filename
            return jsonify({'success': True, 'filename': filename})
        except Exception as e:
            conn.rollback()
            return jsonify({'success': False, 'message': f'Error al actualizar la foto: {str(e)}'})
        finally:
            cursor.close()
            conn.close()

    def request_email_verification(self):
        if 'user_id' not in session:
            return jsonify({'success': False, 'message': 'No autorizado'}), 401

        new_email = request.json.get('new_email')
        if not new_email:
            return jsonify({'success': False, 'message': 'Correo electrónico requerido'})

        if User.get_user_by_email(new_email):
            return jsonify({'success': False, 'message': 'El correo ya está registrado'})

        code = EmailService.generate_verification_code()
        session['verification_code'] = code
        session['code_generated_time'] = datetime.now().isoformat()
        session['temp_new_email'] = new_email

        if EmailService.send_verification_email(new_email, code):
            return jsonify({'success': True})
        else:
            return jsonify({'success': False, 'message': 'Error al enviar el código de verificación'})

    def update_profile(self):
        if 'user_id' not in session:
            return jsonify({'success': False, 'message': 'No autorizado'}), 401

        name = request.form.get('name').strip()
        last_name = request.form.get('last_name').strip()
        gmail = request.form.get('gmail').strip()
        verification_code = request.form.get('verification_code')

        if not all([name, last_name, gmail]):
            return jsonify({'success': False, 'message': 'Complete todos los campos'})

        original_email = session['user_gmail']
        if gmail != original_email:
            # Verify email change
            stored_code = session.get('verification_code')
            stored_time = session.get('code_generated_time')
            temp_new_email = session.get('temp_new_email')

            if not all([stored_code, stored_time, temp_new_email]):
                return jsonify({'success': False, 'message': 'Sesión de verificación expirada'})

            if temp_new_email != gmail:
                return jsonify({'success': False, 'message': 'El correo proporcionado no coincide con el verificado'})

            code_time = datetime.fromisoformat(stored_time)
            if datetime.now() - code_time > timedelta(minutes=10):
                return jsonify({'success': False, 'message': 'El código ha expirado'})

            if verification_code != stored_code:
                return jsonify({'success': False, 'message': 'Código de verificación incorrecto'})

        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("""
                UPDATE users SET name = %s, last_name = %s, gmail = %s WHERE id = %s
            """, (name, last_name, gmail, session['user_id']))
            conn.commit()
            session['user_name'] = name
            session['user_last_name'] = last_name
            session['user_gmail'] = gmail
            self.auth_service.clear_temp_data()
            return jsonify({
                'success': True,
                'user': {
                    'name': name,
                    'last_name': last_name,
                    'gmail': gmail
                }
            })
        except Exception as e:
            conn.rollback()
            return jsonify({'success': False, 'message': f'Error al actualizar el perfil: {str(e)}'})
        finally:
            cursor.close()
            conn.close()

    def change_password(self):
        if 'user_id' not in session:
            flash('Debe iniciar sesión para cambiar su contraseña', 'error')
            return redirect(url_for('login'))

        if request.method == 'POST':
            current_password = request.form.get('current_password').strip()
            new_password = request.form.get('new_password').strip()
            confirm_password = request.form.get('confirm_password').strip()

            if not all([current_password, new_password, confirm_password]):
                flash('Complete todos los campos', 'error')
                return redirect(url_for('change_password'))

            if new_password != confirm_password:
                flash('Las contraseñas nuevas no coinciden', 'error')
                return redirect(url_for('change_password'))

            if len(new_password) < 8:
                flash('La nueva contraseña debe tener al menos 8 caracteres', 'error')
                return redirect(url_for('change_password'))

            user = User.get_user_by_id(session['user_id'])
            if not bcrypt.check_password_hash(user['password'], current_password):
                flash('La contraseña actual es incorrecta', 'error')
                return redirect(url_for('change_password'))

            hashed_password = bcrypt.generate_password_hash(new_password).decode('utf-8')
            conn = get_db_connection()
            cursor = conn.cursor()
            try:
                cursor.execute("UPDATE users SET password = %s WHERE id = %s", (hashed_password, session['user_id']))
                conn.commit()
                session.clear()
                flash('Contraseña cambiada exitosamente. Por favor, inicie sesión nuevamente', 'success')
                return redirect(url_for('login'))
            except Exception as e:
                conn.rollback()
                flash(f'Error al cambiar la contraseña: {str(e)}', 'error')
                return redirect(url_for('change_password'))
            finally:
                cursor.close()
                conn.close()

        return render_template('auth/change_password.html')