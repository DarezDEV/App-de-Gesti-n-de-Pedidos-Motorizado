# app/__init__.py
from flask import Flask, render_template, request, session, redirect, url_for, make_response
from flask_socketio import SocketIO, emit, join_room
from app.db import get_db_connection
import os
import time

# Initialize Flask app
app = Flask(__name__)

os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'
app.config['INSTANCE_PATH'] = os.path.join(app.root_path, 'instance')

# Configuración básica
app.secret_key = '8900098539'

# Configuración de correo electrónico
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'dawaryramirezmontero@gmail.com'
app.config['MAIL_PASSWORD'] = 'vgrz dsmi dujs zoum'  # Asegúrate de que sea la contraseña correcta
app.config['MAIL_DEFAULT_SENDER'] = 'dawaryramirezmontero@gmail.com'

# Configuración de Google OAuth
app.config['GOOGLE_OAUTH_CLIENT_ID'] = '11136398492-d2qu8nhc69g07v6oi3c536p4lm6doe0h.apps.googleusercontent.com'  # Reemplaza con tu ID de cliente de Google
app.config['GOOGLE_OAUTH_CLIENT_SECRET'] = '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'  # Reemplaza con tu clave secreta de Google

# Configuración de VAPID para Web Push
app.config['VAPID_PUBLIC_KEY'] = 'LS0tLS1CRUdJTiBQVUJMSUMgS0VZLS0tLS0KTUZrd0V3WUhLb1pJemowQ0FRWUlLb1pJemowREFRY0RRZ0FFV2J1cHhNMDR4cW9Gb3AyTkhnanBmVWY1QUF5VwpPYzRwbWZlN0xrUzRSUytVVlpTbFBIOHEyT1o0RmZVVmg4V2h5dTdwazFyT2lZM0RhaE9jcG9vZmtnPT0KLS0tLS1FTkQgUFVCTElDIEtFWS0tLS0tCg=='  # Reemplaza con tu clave pública VAPID
app.config['VAPID_PRIVATE_KEY'] = 'LS0tLS1CRUdJTiBQUklWQVRFIEtFWS0tLS0tCk1JR0hBZ0VBTUJNR0J5cUdTTTQ5QWdFR0NDcUdTTTQ5QXdFSEJHMHdhd0lCQVFRZzhZSW5Od3RtNENuY1FhUGYKbjBhYndycTRxSmNkSFl0VmtzWTdBVZzhZSW5Od3RtNENuY1FhUGYKbjBhYndycTRxSmNkSFl0VmtzWTdBVEowMC9paFJBTkNBQVJadTZuRXpUakdxZ1dpblkwZUNPbDlSL2tBREpZNQp6aM2SmpjTnFFNXltaWgrUwotLS0tLUVORCBQUklWQVRFIEtFWS0tLS0W1aOTdzdVJMaEZMNVJWbEtVOGZ5clk1bmdWOVJXSHhhSEs3dW1UV3M2SmpjTnFFNXltaWgrUwotLS0tLUVORCBQUklWQVRFIEtFWS0tLS0tCg=='  # Reemplaza con tu clave privada VAPID
app.config['VAPID_CLAIMS'] = {'sub': 'dawaryramirezmontero@gmail.com'}  # Reemplaza con tu correo

# Set UPLOAD_FOLDER
UPLOAD_FOLDER = os.path.join(app.root_path, 'static/uploads')
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Initialize SocketIO
socketio = SocketIO(app, cors_allowed_origins="*")

@socketio.on('connect', namespace='/admin')
def admin_connect():
    print('Admin connected')

@socketio.on('connect', namespace='/client')
def client_connect():
    print('Client connected')

@socketio.on('connect', namespace='/motorizado')
def motorizado_connect():
    print('Motorizado connected')

# Limpieza periódica de la caché (puedes llamar a esta función con un scheduler)
def clean_location_cache():
    """Limpia ubicaciones antiguas de la caché"""
    now = time.time()
    to_remove = []
    
    for order_id, data in location_cache.items():
        # Remover registros más antiguos que 30 minutos
        if now - data['timestamp'] > 1800:
            to_remove.append(order_id)
    
    for order_id in to_remove:
        del location_cache[order_id]

# Import modules after app and socketio are defined
from app.extensions import bcrypt, mail
from app.routes.dashboard import DashboardService
from app.routes.admin import AdminController
from app.routes.client import ClientController, CartController
from app.routes.motorizado import MotorizadoController
from app.routes.service import UserService, FileService
from app.routes.auth import AuthController, AuthService, EmailService
from app.IA.recommendation_service import Url_recommendation
from app.location_api import LocationController

# Inicializar extensiones
bcrypt.init_app(app)
mail.init_app(app)

# Instanciar los servicios y controladores
dashboard_service = DashboardService()
user_service = UserService()
file_service = FileService()
email_service = EmailService()
auth_service = AuthService()
auth_controller = AuthController(auth_service)
admin_controller = AdminController(dashboard_service, user_service, file_service)
client_controller = ClientController()
motorizado_controller = MotorizadoController()
cart_controller = CartController()
location_controller = LocationController()

# Configuración de Google OAuth Blueprint
from flask_dance.contrib.google import make_google_blueprint, google
google_bp = make_google_blueprint(
    client_id=app.config['GOOGLE_OAUTH_CLIENT_ID'],
    client_secret=app.config['GOOGLE_OAUTH_CLIENT_SECRET'],
    scope=[
        "openid",
        "https://www.googleapis.com/auth/userinfo.email",
        "https://www.googleapis.com/auth/userinfo.profile"
    ],
    redirect_to="google_login"  # Changed from "google.login"
)

app.register_blueprint(google_bp, url_prefix="/google")

# Inicializar LocationController
location_controller.init_app(app, socketio)

# Rutas de Autenticación
app.add_url_rule('/auth/register', view_func=auth_controller.register, methods=['GET', 'POST'])
app.add_url_rule('/auth/login', view_func=auth_controller.login, methods=['GET', 'POST'])
app.add_url_rule('/', view_func=auth_controller.login, methods=['GET', 'POST'])
app.add_url_rule('/google_login', view_func=auth_controller.google_login, methods=['GET'])
app.add_url_rule('/auth/logout', view_func=auth_controller.logout)
app.add_url_rule('/update_profile_photo', view_func=auth_controller.update_profile_photo, methods=['POST'])
app.add_url_rule('/request_email_verification', view_func=auth_controller.request_email_verification, methods=['POST'])
app.add_url_rule('/update_profile', view_func=auth_controller.update_profile, methods=['POST'])
app.add_url_rule('/auth/cambiar/contraseña', view_func=auth_controller.change_password, methods=['GET', 'POST'])

# Rutas de Admin
app.add_url_rule('/dashboard/admin', view_func=admin_controller.admin_dashboard)
app.add_url_rule('/dashboard/admin/usuarios', view_func=admin_controller.admin_users)
app.add_url_rule('/dashboard/admin/usuarios/deshabilitados', view_func=admin_controller.admin_disabled_users)
app.add_url_rule('/update_user/<int:id>', view_func=admin_controller.update_user, methods=['POST'])
app.add_url_rule('/disable_user/<int:user_id>', view_func=admin_controller.disable_user, methods=['POST'])
app.add_url_rule('/enable_user/<int:user_id>', view_func=admin_controller.enable_user, methods=['POST'])
app.add_url_rule('/add_user', view_func=admin_controller.create_user, methods=['POST'])
app.add_url_rule('/dashboard/admin/categoria', view_func=admin_controller.admin_category)
app.add_url_rule('/categoria/crear', view_func=admin_controller.create_category, methods=['POST'])
app.add_url_rule('/categoria/editar/<int:category_id>', view_func=admin_controller.update_category, methods=['POST'])
app.add_url_rule('/categoria/<int:category_id>/delete', view_func=admin_controller.delete_category, methods=['POST'])
app.add_url_rule('/dashboard/admin/categoria/productos/<int:category_id>', view_func=admin_controller.category_products)
app.add_url_rule('/crear/productos/<int:category_id>', view_func=admin_controller.create_product, methods=['POST'])
app.add_url_rule('/actualizar/productos/<int:product_id>/<int:category_id>', view_func=admin_controller.update_product, methods=['POST'])
app.add_url_rule('/products/delete/<int:category_id>/<int:product_id>', view_func=admin_controller.delete_product, methods=['POST'])
app.add_url_rule('/dashboard/admin/ordenes', view_func=admin_controller.admin_orders)
app.add_url_rule('/dashboard/admin/ordenes/orden/<int:order_id>', view_func=admin_controller.order_details)
app.add_url_rule('/assign_motorizado/<int:order_id>', view_func=admin_controller.assign_motorizado, methods=['POST'])
app.add_url_rule('/report/motorizado', view_func=admin_controller.generate_motorizado_report, methods=['GET'])
app.add_url_rule('/report/top_products', view_func=admin_controller.generate_top_products_report, methods=['GET'])

# Rutas de Cliente
app.add_url_rule('/dashboard/cliente/inicio', view_func=client_controller.cliente_dashboard)
app.add_url_rule('/dashboard/cliente/carrito', view_func=client_controller.cart_client)
app.add_url_rule('/dashboard/cliente/producto/<int:product_id>', view_func=client_controller.product_detail)
app.add_url_rule('/submit_product_evaluation', view_func=client_controller.submit_product_evaluation, methods=['POST'])
app.add_url_rule('/check_user_rating/<int:product_id>', view_func=client_controller.check_user_rating, methods=['GET'])
app.add_url_rule('/dashboard/cliente/ordenes', view_func=client_controller.client_orders)
app.add_url_rule('/dashboard/cliente/ordenes/orden/<int:order_id>', view_func=client_controller.order_details_client, methods=['GET'])
app.add_url_rule('/add_to_cart/', view_func=cart_controller.add_to_cart, methods=['POST'])
app.add_url_rule('/update-cart', view_func=cart_controller.update_cart, methods=['POST'])
app.add_url_rule('/remove_from_cart', view_func=cart_controller.remove_from_cart, methods=['POST'])
app.add_url_rule('/checkout', view_func=cart_controller.checkout, methods=['GET', 'POST'])
app.add_url_rule('/checkoutcancel-order', view_func=cart_controller.cancel_order, methods=['POST'])
app.add_url_rule('/dashboard/cliente/orden/confirmación/<int:order_id>', view_func=cart_controller.order_confirmation)
app.add_url_rule('/get_cart_count', view_func=cart_controller.get_cart_count, methods=['GET'])
app.add_url_rule('/recommendations', view_func=cart_controller.get_recommendations_ajax, methods=['GET'])
app.add_url_rule('/track-view', view_func=cart_controller.track_view, methods=['POST'])
app.add_url_rule('/dashboard/cliente/categoria/<int:category_id>', view_func=client_controller.client_category_products)
app.add_url_rule('/dashboard/cliente/ordenes/orden/map/<int:order_id>', view_func=client_controller.client_map, methods=['GET'])
app.add_url_rule('/submit_evaluation/<int:order_id>', view_func=client_controller.submit_evaluation_moto, methods=['POST'])
app.add_url_rule('/cliente/confirmar-entrega', view_func=client_controller.confirmar_entrega_cliente, methods=['POST'])


# Rutas de Motorizado
app.add_url_rule('/dashboard/motorizado/ordenes', view_func=motorizado_controller.motorizado_pedidos)
app.add_url_rule('/dashboard/motorizad/ordenes/orden/<int:order_id>', view_func=motorizado_controller.motorizado_order_details, methods=['GET'])
app.add_url_rule('/marcar_entregado/<int:order_id>', view_func=motorizado_controller.marcar_entregado, methods=['POST'])
app.add_url_rule('/dashboard/motorizado/ordenes/orden/mapa/<int:order_id>', view_func=motorizado_controller.motorizado_map, methods=['GET'])

# Rutas de Recomendaciones
app.add_url_rule('/recommendations/<int:user_id>', view_func=Url_recommendation.get_recommendations, methods=['GET'])
app.add_url_rule('/track_view', view_func=Url_recommendation.track_product_view, methods=['POST'])
app.add_url_rule('/cart_patterns/<int:user_id>', view_func=Url_recommendation.analyze_cart_patterns, methods=['GET'])

# Rutas de error
@app.errorhandler(404)
def page_not_found(error):
    return render_template('404.html'), 404