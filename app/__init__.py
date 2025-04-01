# app/__init__.py
from flask import Flask, render_template
from flask_socketio import SocketIO, emit
import os

# Initialize Flask app
app = Flask(__name__)

# Configuración básica
app.secret_key = 'your_secret_key'

# Configuración de correo electrónico
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'dawaryramirezmontero@gmail.com'
app.config['MAIL_PASSWORD'] = 'vgrz dsmi dujs zoum'
app.config['MAIL_DEFAULT_SENDER'] = 'dawaryramirezmontero@gmail.com'

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

# Import modules after app and socketio are defined
from app.extensions import bcrypt, mail
from app.routes.dashboard import DashboardService
from app.routes.admin import AdminController
from app.routes.client import ClientController, CartController
from app.routes.motorizado import MotorizadoController
from app.routes.service import UserService, FileService
from app.routes.auth import AuthController, AuthService, EmailService
from app.IA.recommendation_service import Url_recommendation

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
cart_controller = CartController()

# --- Rutas de Autenticación ---
app.add_url_rule('/register', view_func=auth_controller.register, methods=['GET', 'POST'])
app.add_url_rule('/login', view_func=auth_controller.login, methods=['GET', 'POST'])
app.add_url_rule('/', view_func=auth_controller.login, methods=['GET', 'POST'])
app.add_url_rule('/logout', view_func=auth_controller.logout)

# --- Rutas de Admin ---
app.add_url_rule('/dashboard/admin', view_func=admin_controller.admin_dashboard)
app.add_url_rule('/dashboard/admin/usuarios', view_func=admin_controller.admin_users)
app.add_url_rule('/dashboard/admin/usuarios/deshabilitados', view_func=admin_controller.admin_disabled_users)
app.add_url_rule('/profile/<int:user_id>', view_func=admin_controller.profile)
app.add_url_rule('/update_user/<int:id>', view_func=admin_controller.update_user, methods=['POST'])
app.add_url_rule('/disable_user/<int:user_id>', view_func=admin_controller.disable_user, methods=['POST'])
app.add_url_rule('/enable_user/<int:user_id>', view_func=admin_controller.enable_user, methods=['POST'])
app.add_url_rule('/add_user', view_func=admin_controller.create_user, methods=['POST'])
app.add_url_rule('/dashboard/admin/categoria', view_func=admin_controller.admin_category)
app.add_url_rule('/categorias/crear', view_func=admin_controller.create_category, methods=['POST'])
app.add_url_rule('/categorias/editar/<int:category_id>', view_func=admin_controller.update_category, methods=['POST'])
app.add_url_rule('/categories/<int:category_id>/delete', view_func=admin_controller.delete_category, methods=['POST'])
app.add_url_rule('/category/<int:category_id>/products', view_func=admin_controller.category_products)
app.add_url_rule('/createproduct/<int:category_id>', view_func=admin_controller.create_product, methods=['POST'])
app.add_url_rule('/update_product/<int:product_id>/<int:category_id>', view_func=admin_controller.update_product, methods=['POST'])
app.add_url_rule('/products/delete/<int:category_id>/<int:product_id>', view_func=admin_controller.delete_product, methods=['POST'])
app.add_url_rule('/dashboard/admin/orders', view_func=admin_controller.admin_orders)
app.add_url_rule('/admin/order/<int:order_id>', view_func=admin_controller.order_details)
app.add_url_rule('/assign_motorizado<int:order_id>', view_func=admin_controller.assign_motorizado, methods=['POST'])

# --- Rutas de Cliente ---
app.add_url_rule('/dashboard/cliente', view_func=ClientController.cliente_dashboard)
app.add_url_rule('/carrito', view_func=ClientController.cart_client)
app.add_url_rule('/producto/<int:product_id>', view_func=ClientController.product_detail)
app.add_url_rule('/cliente/orders', view_func=ClientController.client_orders)
app.add_url_rule('/add_to_cart/', view_func=cart_controller.add_to_cart, methods=['POST'])
app.add_url_rule('/update-cart', view_func=cart_controller.update_cart, methods=['POST'])
app.add_url_rule('/remove_from_cart', view_func=cart_controller.remove_from_cart, methods=['POST'])
app.add_url_rule('/checkout', view_func=cart_controller.checkout, methods=['GET', 'POST'])
app.add_url_rule('/checkoutcancel-order', view_func=cart_controller.cancel_order, methods=['POST'])
app.add_url_rule('/order-confirmation/<int:order_id>', view_func=cart_controller.order_confirmation)
app.add_url_rule('/get_cart_count', view_func=cart_controller.get_cart_count, methods=['GET'])
app.add_url_rule('/recommendations', view_func=cart_controller.get_recommendations_ajax, methods=['GET'])
app.add_url_rule('/track-view', view_func=cart_controller.track_view, methods=['POST'])

# --- Rutas de Motorizado ---
app.add_url_rule('/dashboard/motorizado', view_func=MotorizadoController.motorizado_dashboard)
app.add_url_rule('/motorizado/pedidos', view_func=MotorizadoController.motorizado_pedidos)
app.add_url_rule('/marcar_entregado/<int:order_id>', view_func=MotorizadoController.marcar_entregado, methods=['POST'])

# --- Rutas de Recomendaciones ---
app.add_url_rule('/recommendations/<int:user_id>', view_func=Url_recommendation.get_recommendations, methods=['GET'])
app.add_url_rule('/track_view', view_func=Url_recommendation.track_product_view, methods=['POST'])
app.add_url_rule('/cart_patterns/<int:user_id>', view_func=Url_recommendation.analyze_cart_patterns, methods=['GET'])

# Rutas de error
@app.errorhandler(404)
def page_not_found(error):
    return render_template('404.html'), 404