from math import e
from flask import render_template, request, redirect, url_for, flash, session, current_app
from app.extensions import Bcrypt, Mail
from werkzeug.utils import secure_filename
import os
from app.db import get_db_connection
from app.models import User
from flask_mail import Message
import random
import string
from datetime import datetime, timedelta

bcrypt = Bcrypt()
mail = Mail()
UPLOAD_FOLDER = os.path.join(os.getcwd(), 'app', 'static', 'uploads')
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
            'motorizado': 'motorizado_dashboard'
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
                    'temp_filename', 'verification_code', 'code_generated_time']
        for key in temp_keys:
            session.pop(key, None)

class AuthController:
    def __init__(self, auth_service: AuthService):
        self.auth_service = auth_service

    def register(self):
        if 'user_id' in session:
            return redirect(self.auth_service.get_dashboard())

        if request.method == 'POST':
            # Verificación del código
            if 'verification_code' in request.form:
                return self._handle_verification_code()
            
            # Registro inicial
            return self._handle_initial_registration()

        return render_template('auth/register.html', show_verification=False)

    def _handle_verification_code(self):
        stored_code = session.get('verification_code')
        stored_time = session.get('code_generated_time')
        
        if not all([stored_code, stored_time]):
            flash('Sesión expirada. Por favor, intente registrarse nuevamente.', 'error')
            return redirect(url_for('register'))
        
        # Verificar si el código ha expirado (10 minutos)
        code_time = datetime.fromisoformat(stored_time)
        if datetime.now() - code_time > timedelta(minutes=10):
            flash('El código ha expirado. Por favor, solicite uno nuevo.', 'error')
            return redirect(url_for('register'))
        
        if request.form['verification_code'] != stored_code:
            flash('Código de verificación incorrecto', 'error')
            return render_template('auth/register.html', show_verification=True)
        
        # Completar registro
        return self._complete_registration()

    def _handle_initial_registration(self):
        name = request.form['name'].strip()
        last_name = request.form['last_name'].strip()
        gmail = request.form['gmail'].strip()
        password = request.form['password'].strip()
        confirm_password = request.form['confirm_password'].strip()
        photo = request.files.get('photo')

        # Validaciones
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

        # Guardar foto y datos temporales
        filename = self.auth_service.save_photo(photo)
        self.auth_service.store_registration_data(name, last_name, gmail, password, filename)
        
        # Generar y enviar código de verificación
        code = EmailService.generate_verification_code()
        session['verification_code'] = code
        session['code_generated_time'] = datetime.now().isoformat()
        
        try:
            msg = Message('Código de Verificación',
                         sender=current_app.config['MAIL_USERNAME'],
                         recipients=[gmail])
            msg.body = f'Tu código de verificación es: {code}\nEste código expirará en 10 minutos.'
            mail.send(msg)
        except Exception as e:
            print(f"Error al enviar el correo: {e}")  # Muestra el error real en la consola
            return f"Error al enviar el código de verificación: {str(e)}"

        if EmailService.send_verification_email(gmail, code):
            return render_template('auth/register.html', show_verification=True)
        else:
            flash(f'Error al enviar el código de verificación {e}', 'error')
            
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

            if user is None or not bcrypt.check_password_hash(user['password'], password):
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